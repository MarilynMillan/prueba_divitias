# -*- coding: utf-8 -*-

import base64
import logging
import random

from collections import defaultdict, Counter
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND
from odoo.tools import float_round, date_utils, convert_file, html2plaintext, is_html_empty, format_amount
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)



class payslip_modificacion(models.Model):
    _inherit = 'hr.payslip'
    _description = 'modificar comportamiento de payslip para conseguir promedio para prima'

    prima = fields.Boolean(string='Terminacion de contrato, Prima en otro mes', default=False)
    id_contratico = fields.Integer(string="id_contrato",compute="_id_contratico")

    def _id_contratico(self):
        # if self.employee_id:
        self.id_contratico = self.contract_id.id
    ############PROCEDIMIENTOS PARA TRAER EL PROMEDIO DE PRIMA#################

    def _get_payslip_lines(self):
        line_vals = []
        generoerror = False
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_("There's no contract set on payslip %s for %s. Check that there is at least a contract set on the employee form.", payslip.name, payslip.employee_id.name))

            localdict = self.env.context.get('force_payslip_localdict', None)
            if localdict is None:
                localdict = payslip._get_localdict()

            rules_dict = localdict['rules']
            result_rules_dict = localdict['result_rules']
            reglas_sueldo_variable = []
            blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            result = {}
            valor_comprobante_variable = 0
            for rule in sorted(payslip.struct_id.rule_ids, key=lambda x: x.sequence):
                if rule.id in blacklisted_rule_ids:
                    continue
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100,
                    'result_name': False
                })
                
                if rule._satisfy_condition(localdict):
                    # Retrieve the line name in the employee's lang
                    employee_lang = payslip.employee_id.sudo().employee_address_home.lang
                    # This actually has an impact, don't remove this line
                    context = {'lang': employee_lang}
                    if rule.code in localdict['same_type_input_lines']:
                        print('RULE CODE 1: ', rule.code)
                        for multi_line_rule in localdict['same_type_input_lines'][rule.code]:
                            localdict['inputs'][rule.code] = multi_line_rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            # tot_rule = amount * qty * rate / 100.0
                            tot_rule = payslip._get_payslip_line_total(amount, qty, rate, rule)
                            localdict = rule.category_id._sum_salary_rule_category(localdict,
                                                                                   tot_rule)
                            rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                            line_vals.append({
                                'sequence': rule.sequence,
                                'code': rule.code,
                                'name':  rule_name,
                                # 'note': html2plaintext(rule.note) if not is_html_empty(rule.note) else '',
                                'salary_rule_id': rule.id,
                                'contract_id': localdict['contract'].id,
                                'employee_id': localdict['employee'].id,
                                'amount': amount,
                                'quantity': qty,
                                'rate': rate,
                                'total': tot_rule,
                                'slip_id': payslip.id,
                            })
                    else:
                        ####AGREGAR CODIGO PARA CALCULAR PROMEDIO DE PRIMA
                        print('RULE CODE2: ', rule.code)
                        print('sueldo variable: ', rule.sueldo_variable)
                        print(rule.amount_python_compute[0:8])
                        # valor_comprobante_variable = valor_comprobante_variable+regla.total
                        if rule.sueldo_variable:
                            if rule.code not in reglas_sueldo_variable:
                                reglas_sueldo_variable.append(rule.code) 
                        
                        if rule.amount_python_compute[0:8].upper() == 'PROMEDIO':
                            ##calcular promedio
                            #revizar reglas a promediar
                            #PROMEDIO(GROSS,NETO,BASICO,ETC
                            import re
                            cadena = rule.amount_python_compute
                            # Extraemos el contenido entre paréntesis
                            # match = re.search(r'\((.*?)\)', cadena)
                            matches = re.findall(r'\((.*?)\)', cadena)
                            # Verificamos que hemos encontrado exactamente dos grupos de texto entre paréntesis
                            if len(matches) == 2:
                                # Dividimos cada grupo de texto por la coma para obtener los elementos individuales
                                reglas = matches[0].split(',')
                                reglasdias = matches[1].split(',')
                            else:
                                reglas = []
                                reglasdias = []

                            valor_comprobante_actual = 0
                            valor_variable = 0
                            
                            for regla in reglas:
                                if regla.strip() not in result_rules_dict:
                                    generoerror = True
                                    #UserError(_("No se ha calculado la regla "+regla+" por lo tanto, se debe revizar la secuencia para hallar el promedio."))
                                    print("NO ESTA LA REGLA "+regla)
                                else:
                                    print(regla)
                                    print(result_rules_dict[regla].get('total'))
                                    valor_comprobante_actual = valor_comprobante_actual + result_rules_dict[regla].get('total')
                            print(reglas_sueldo_variable)
                            for reglak in reglas_sueldo_variable:
                                print("y las reglas variable")
                                print(reglak)
                                if reglak in reglas_sueldo_variable:
                                    valor_variable = valor_variable+result_rules_dict[reglak].get('total')
                                # print(result_rules_dict[regla].get('total'))
                                # if regla.sueldo_variable:
                                #     valor_comprobante_variable = valor_comprobante_variable+result_rules_dict[regla].get('total')
                           # match = re.search(r'\)\s*([\+\-]?\w+)$', cadena)
                            # Obtenemos la parte capturada si hay coincidencia
                            # sin_promedio = match.group(1) if match else None
                            # print('last_part: ', sin_promedio)
                            # print(rule.amount_python_compute[9:18].upper())
                            if rule.amount_python_compute[8:17].upper() == 'SEISMESES': ##PROMEDIO_SEISMESES
                                amount, qty, rate = self.promedio(localdict['employee'].id, payslip ,reglas,reglasdias,valor_comprobante_actual)
                            if rule.amount_python_compute[8:16].upper() == 'CONTRATO': ##PROMEDIO_CONTRATO
                                amount, qty, rate = self.promediocontrato(localdict['employee'].id, payslip ,reglas,reglasdias,valor_comprobante_actual)
                            if rule.amount_python_compute[8:22].upper() == 'ADMINISTRATIVO': ##PROMEDIO_CONTRATO
                                amount, qty, rate = self.promediovariableseparada(localdict['employee'].id, payslip ,reglas,reglasdias,valor_comprobante_actual)
                            if rule.amount_python_compute[8:13].upper() == 'PRIMA': ##PROMEDIO_VARIABLE
                                
                                amount, qty, rate = self.promedioPRIMA(localdict['employee'].id, payslip ,reglas,reglasdias,valor_variable,valor_comprobante_actual)
                            if rule.amount_python_compute[8:18].upper() == 'VACACIONES': ##PROMEDIO_VARIABLE
                                amount, qty, rate = self.promedioVACACIONES(localdict['employee'].id, payslip ,reglas,reglasdias,valor_comprobante_actual)
                            # else:
                            #    pass
                            # palabras = [x.strip() for x in palabras]
                            # if "GROSS" not in result_rules_dict:
                            #     print('sale de regla: ', rule.code)
                            #     generoerror = True
                            #     UserError(_("No se ha calculado el salario base, por lo tanto, debe realizarse el cálculo de prima después de GROSS."))
                            # else:
                        else:
                            amount, qty, rate = rule._compute_rule(localdict)
                        #check if there is already a rule computed with that code
                        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                        #set/overwrite the amount computed for this rule in the localdict
                        tot_rule = amount * qty * rate / 100.0
                        localdict[rule.code] = tot_rule
                        result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty, 'rate': rate}
                        rules_dict[rule.code] = rule
                        # sum the amount for its salary category
                        localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
                        rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                        # create/overwrite the rule in the temporary results
                        #if rule.code == 'RetencionFuente':
                        # If the rule is RetencionFuente, we need to compute it after all other rules
                        #    amount=self.rtf(localdict['employee'],localdict['contract'], payslip,localdict['worked_days'] , localdict['categories'],localdict['result_rules'])
                        #    tot_rule = amount

                        result[rule.code] = {
                            'sequence': rule.sequence,
                            'code': rule.code,
                            'name': rule_name,
                            # 'note': html2plaintext(rule.note) if not is_html_empty(rule.note) else '',
                            'salary_rule_id': rule.id,
                            'contract_id': localdict['contract'].id,
                            'employee_id': localdict['employee'].id,
                            'amount': amount,
                            'quantity': qty,
                            'rate': rate,
                            'total': tot_rule,
                            'slip_id': payslip.id,
                        }

            
            line_vals += list(result.values())
        # if generoerror == True:
        #     #raise UserError(_("No se ha calculado la regla "+regla+" por lo tanto, se debe revizar la secuencia para hallar el promedio."))
        #     pass
        # else:
        return line_vals


    def rtf(self, empleado_id, contract, payslip, worked_days, categories, result_rules):
        print(payslip)
        print(empleado_id)

        if not contract.uvt or not contract.wage:
            return 0

        uvt = contract.uvt

        # 1. Verificar si es primera quincena
        if payslip.date_to.day <=15:
            return 0

        # 2. Obtener payslip de primera quincena del mismo mes
        payslip_1q = self.env['hr.payslip'].search([
            ('employee_id', '=', empleado_id.id),
            ('state', '=', 'done'),
            ('date_from', '>=', payslip.date_from.replace(day=1)),
            ('date_to', '<=', payslip.date_to.replace(day=15)),
        ], limit=1, order='date_to desc')

        # 3. Días trabajados (acumulados)
        dias_trabajados = 0
        for code, wd in worked_days.items():
            if code == 'WORK100':
                dias_trabajados = wd.number_of_days
                break
        dias_trabajados += payslip_1q.worked_days_line_ids.filtered(lambda w: w.code == 'WORK100').number_of_days if payslip_1q else 0
        dias_trabajados = dias_trabajados or 30  # por defecto 30

        # 4. Salario mensual estimado (suma de ambas quincenas)
        wage_actual = contract.wage or 0
        wage_1q = payslip_1q and sum(payslip_1q.line_ids.filtered(lambda l: l.code == 'BASIC').mapped('total')) or 0
        wage = wage_actual + wage_1q

        # 5. Deducciones acumuladas
        deducciones_actual = categories.get('DED1', 0.0)
        deducciones_1q = 0.0
        if payslip_1q:
            deducciones_1q = sum(payslip_1q.line_ids.filtered(lambda l: l.category_id.code == 'DED1').mapped('total'))

        deducciones_categoria = deducciones_actual + deducciones_1q

        # 6. Intereses préstamo de vivienda
        intereses = contract.x_studio_intereses_por_prestamo_de_vivienda or 0
        intereses_mensual = intereses / 12.0
        intereses_deducibles = intereses_mensual if intereses <= uvt * 100 else 0.0

        # 7. Plan complementario
        plan_comp = result_rules.get('PlanComplementarios', {}).get('amount', 0.0)
        plan_deducible = plan_comp if plan_comp <= uvt * 16 else 0.0

        # 8. Dependientes
        deduccion_dep = 0.0
        if contract.x_studio_dependiente:
            deduccion_dep = min(wage * 0.10, uvt * 32)

        # 9. Base sujeta
        total_deducciones = deducciones_categoria + intereses_deducibles + plan_deducible + deduccion_dep
        base_sujeta = wage - total_deducciones

        # 10. Si salario mensual <= 95 UVT, no hay retención
        if wage <= uvt * 95:
            return 0

        # 11. Deducción del 25% + tabla progresiva
        base_retenible = base_sujeta * 0.75
        uvt_equiv = base_retenible / uvt

        if uvt_equiv <= 95:
            impuesto_uvt = 0
        elif uvt_equiv <= 150:
            impuesto_uvt = (uvt_equiv - 95) * 0.19
        elif uvt_equiv <= 360:
            impuesto_uvt = ((uvt_equiv - 150) * 0.28) + 10
        elif uvt_equiv <= 640:
            impuesto_uvt = ((uvt_equiv - 360) * 0.33) + 69
        elif uvt_equiv <= 945:
            impuesto_uvt = ((uvt_equiv - 640) * 0.35) + 162
        elif uvt_equiv <= 2300:
            impuesto_uvt = ((uvt_equiv - 945) * 0.37) + 268
        else:
            impuesto_uvt = ((uvt_equiv - 2300) * 0.39) + 770

        # 12. Convertir a pesos
        impuesto_pesos = impuesto_uvt * uvt

        # 13. Prorratear por días trabajados
        prorrateado = (impuesto_pesos / 30.0) * dias_trabajados
        result = round(prorrateado, -3)
        return result


    def promedioVACACIONES(self,empleado_id,payslip,reglas,reglasdias,valor_comprobante_actual):
        import logging
        _logger = logging.getLogger("VACACIONES VARIABLE")
        periodo = 0
        contrato_actual = payslip.contract_id
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte
        comprobantes_promedio = self.env['hr.payslip'].search([('contract_id','=',contrato_actual.id),('state','=','done')])
        print(comprobantes_promedio)
        # _logger.info("en promedio aha "+comprobantes_promedio)
        ano_trabajado = str(payslip.date_from.year)
        contrato_actual = payslip.contract_id
        sueldo = payslip.contract_id.wage
        promedio = 0
        valor_comprobantes = 0
        dias_trabajados = 0
        valor_sueldo_variable = valor_comprobante_actual
        dias_trabajados_promedio = 0
        valorsueldo = 0
        # print("comprobantes_promedio")
        # print(comprobantes_promedio)
        for comprobante in comprobantes_promedio:
            _logger.info("en promedio aha "+comprobante.name)
            # print("comprobante promedio")
            # print(comprobante.name)
            
            for line in comprobante.line_ids:
                if line.salary_rule_id.sueldo_variable:
                    print(line.salary_rule_id.code)
                    _logger.info("DENTRO DEL COMPROBANTE "+str(line.total))
                    valor_sueldo_variable = valor_sueldo_variable + line.total
                
            _logger.info("la suma de todos da "+str(valor_sueldo_variable))
            
            # print("Y LOS VALORES")
            # print(valor_sueldo_variable)
        if contrato_actual.date_start and contrato_actual.date_end:
            start_date = contrato_actual.date_start
            end_date = contrato_actual.date_end
        else:
            return 0,0,100.0
        dias_trabajados = self.dias360(start_date, end_date) + 1
        # print("dias laborados en el contrato")
        # print(dias_trabajados)
        dias_trabajados_promedio = dias_trabajados_promedio + dias_trabajados
        # print("dias_trabajados_promedio")
        # print(dias_trabajados_promedio)
        # if dias_trabajados_promedio < 30:
        #     numero_meses = 1
        # else:
        numero_meses = round(dias_trabajados_promedio*15/360, 6) #float_round(dias_trabajados_promedio/30.44, precision_rounding=2 )
            #numero_meses = round(dias_trabajados_promedio/30, 0) float_round(dias_trabajados_promedio/30.44, precision_rounding=2 )
        
        _logger.info("dias/30 "+str(numero_meses))

        if numero_meses == 0:
            return 0,0,100.0
        
        valor_promedio = (valor_sueldo_variable)/numero_meses
        _logger.info("valor sueldo variable "+str(valor_promedio))
        
        # salario_minimo = contrato_actual.salario_minimo #1160000
        # auxilio_transporte = contrato_actual.auxilio_de_transporte#140606
        # valor_promedio = valor_promedio + sueldo
        # _logger.info("valor sueldo variable + sueldo"+str(valor_promedio))
        

        # #if valor_promedio > salario_minimo*2:
        # if sueldo > salario_minimo*2:
        #     _logger.info("no es mayor a salariominimo por 2"+str(valor_promedio + sueldo))
        #     ##incluir subsidio de transporte
        #     pass
        # else:
        #     valor_promedio = valor_promedio + auxilio_transporte

        # _logger.info("VALOR + auxilio de transporte es total base liquidacion"+str(valor_promedio))
        # _logger.info("dias trabajados "+str(dias_trabajados_promedio))

        print("valor comprobantes")
        print(valor_comprobantes)
        print("dias")
        print(dias_trabajados)
        print("total base liquidacion")
        print(valor_promedio)
        ano_actual = str(contrato_actual.date_end.year)
        start_date = start_date = datetime.strptime(ano_actual+'-01-01', '%Y-%m-%d') #contrato_actual.date_start
        end_date = contrato_actual.date_end
        dias_pagar = self.dias360(start_date, end_date) + 1
        print("dias laborados en el contrato")
        print(dias_trabajados)

        return sueldo/30,numero_meses,100.0

    def promedioPRIMA(self, empleado_id, payslip, reglas, reglasdias,valorvariable, valor_comprobante_actual):
        import logging
        from odoo.fields import Date

        _logger = logging.getLogger("NOMINA VARIABLE")

        
        _logger.info(
            "valores | valorvariable actual=%s | valor comprobante actual=%s",
            valorvariable, valor_comprobante_actual
        )
        contrato_actual = payslip.contract_id
        sueldo = contrato_actual.wage
        total_basico = valor_comprobante_actual
        auxilio_transporte = contrato_actual.auxilio_de_transporte
        salario_minimo = contrato_actual.salario_minimo
        
        
        for comprobante in self:
            valor_comprobante = 0
            dias_pagar = 0
            for line_dias in comprobante.worked_days_line_ids:
                # print("tipo_de_dias")
                # print(line_dias.work_entry_type_id.name)
                if line_dias.work_entry_type_id.name == "Primas":
                    dias_pagar = line_dias.number_of_days

            

        # --- Semestre legal + inicio real por date_start del contrato ---
        if payslip.date_from.month <= 6:
            semestre_inicio = Date.to_date(f"{payslip.date_from.year}-01-01")
            semestre_fin = Date.to_date(f"{payslip.date_from.year}-06-30")
        else:
            semestre_inicio = Date.to_date(f"{payslip.date_from.year}-07-01")
            semestre_fin = Date.to_date(f"{payslip.date_from.year}-12-31")

        inicio_calculo = max(semestre_inicio, contrato_actual.date_start or semestre_inicio)

        _logger.info(
            "PRIMA | semestre_inicio=%s | semestre_fin=%s | contrato_date_start=%s | inicio_calculo=%s",
            semestre_inicio, semestre_fin, contrato_actual.date_start, inicio_calculo
        )

        # --- SOLO comprobantes del semestre (últimos 6 meses) ---
        comprobantes_promedio = self.env['hr.payslip'].search([
            ('employee_id', '=', empleado_id),
            ('contract_id', '=', contrato_actual.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', inicio_calculo),
            ('date_to', '<=', semestre_fin),
        ])

        print("comprobantes_promedio")
        print(comprobantes_promedio)

        # --- Suma de sueldo variable (histórico semestre + actual) ---
        valor_sueldo_variable = valorvariable
        

        for comprobante in comprobantes_promedio:
            _logger.info(
                "COMPROBANTE | name=%s | from=%s | to=%s | state=%s",
                comprobante.name, comprobante.date_from, comprobante.date_to, comprobante.state
            )

            for line in comprobante.line_ids:
                if line.salary_rule_id.code == "Basico":
                    _logger.info("basico comprobante actual=%s", line.total)
                    total_basico += line.total
                if line.salary_rule_id.sueldo_variable:
                    _logger.info("  regla_var=%s total=%s", line.salary_rule_id.code, line.total)
                    valor_sueldo_variable += line.total

            _logger.info("ACUM_VAR (incluye actual)=%s", valor_sueldo_variable)

        # --- Días laborados para prima: dentro del semestre, desde date_start ---
        if not contrato_actual.date_start:
            return 0, 0, 100.0

        fin_calculo = min(semestre_fin, contrato_actual.date_end or semestre_fin)
        if fin_calculo < inicio_calculo:
            return 0, 0, 100.0

        dias_trabajados_promedio = self.dias360_prima(inicio_calculo, fin_calculo) + 1
        _logger.info("DIAS | inicio=%s | fin=%s | dias360_prima+1=%s", inicio_calculo, fin_calculo, dias_trabajados_promedio)

        # Tope 180 días (6 meses)
        if dias_trabajados_promedio > 180:
            _logger.info("DIAS > 180, se limita a 180. Antes: %s", dias_trabajados_promedio)
            dias_trabajados_promedio = 180

        # Meses del semestre (ya con tope 180)
        if dias_trabajados_promedio < 30:
            numero_meses = 1
        else:
            numero_meses = round(dias_trabajados_promedio / 30.0, 6)

        _logger.info("numero_meses=%s (dias/30)", numero_meses)

        if not numero_meses:
            return 0, 0, 100.0

        # Promedio variable mensual del semestre + sueldo base mensual
        _logger.info("total_basico=%s", total_basico)
        _logger.info("valor_sueldo_variable=%s", valor_sueldo_variable)
        valor_promedio_var_mensual = (valor_sueldo_variable + total_basico) / numero_meses
        _logger.info("valor_promedio_diario=%s", valor_promedio_var_mensual)
        
        valor_promedio = valor_promedio_var_mensual /360
        _logger.info("base + sueldo=%s", valor_promedio)

        # Auxilio transporte según regla (aquí mantengo tu lógica por sueldo > SM*2)
        # if sueldo > salario_minimo * 2:
        #     pass
        # else:
        #     valor_promedio += auxilio_transporte

        _logger.info("TOTAL base liquidacion (con aux si aplica)=%s", valor_promedio)
        _logger.info("dias_trabajados_promedio=%s", dias_trabajados_promedio)


        return valor_promedio , dias_pagar, 100.0

        
    def dias360_prima(self,start_date, end_date):
        # Asegurar que start_date no sea más de un año antes de end_date
        print("start_day")
        print(start_date)
        start_date = datetime(end_date.year , 1, 1)
        # un_ano_antes = end_date - timedelta(days=365)
        # if start_date < un_ano_antes:
        #     print("un año antes")
        #     start_date = un_ano_antes
        print("start_day")
        print(start_date)
        # Asumiendo que start_date y end_date son objetos datetime
        start_day = 30 if start_date.day == 31 else start_date.day
        end_day = 30 if end_date.day == 31 else end_date.day

        # Calcular la diferencia de días basado en un año de 360 días
        days_difference = 360 * (end_date.year - start_date.year) + 30 * (end_date.month - start_date.month) + (end_day - start_day)

        return days_difference


    def dias360(self,start_date, end_date):
        # Asumiendo que start_date y end_date son objetos datetime
        start_day = 30 if start_date.day == 31 else start_date.day
        end_day = 30 if end_date.day == 31 else end_date.day

        # Calcular la diferencia de días basado en un año de 360 días
        days_difference = 360 * (end_date.year - start_date.year) + 30 * (end_date.month - start_date.month) + (end_day - start_day)

        return days_difference

    
    
    def promediovariableseparada(self,empleado_id,payslip,reglas,reglasdias,valor_comprobante_actual):
        import logging
        _logger = logging.getLogger("NOMINA")
        periodo = 0
        # if payslip.prima == True:
        if payslip.date_from.month <= 6:
            periodo = 1
        else:
            periodo = 2

        contrato_actual = payslip.contract_id
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte
        comprobantes_promedio = self.env['hr.payslip'].search([('contract_id','=',contrato_actual.id),('state','=','done')])
        print(comprobantes_promedio)
        # _logger.info("en promedio aha "+comprobantes_promedio)
        ano_trabajado = str(payslip.date_from.year)
        contrato_actual = payslip.contract_id
        sueldo = payslip.contract_id.wage
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte
        if periodo == 1:
            comprobantes = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-01-01'),('date_to','<=',ano_trabajado+'-06-30'),('contract_id','=',contrato_actual.id),('state','=','done')])
        elif periodo == 2:
            #comprobantes_promedio = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-01-01'),('date_to','<=',ano_trabajado+'-06-30'),('contract_id','=',contrato_actual.id),('state','=','done')])
            comprobantes = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-07-01'),('date_to','<=',ano_trabajado+'-12-31'),('contract_id','=',contrato_actual.id),('state','=','done')])
        # else:
        #     return 0,0,0

        #promedio de regla de enero a junio
        promedio = 0
        valor_comprobantes = 0
        dias_trabajados = 0
        valor_sueldo_variable = 0
        # numero_meses = 1
        for comprobante in self:
            valor_comprobante = 0
            dias = 0
            for line_dias in comprobante.worked_days_line_ids:
                # print("tipo_de_dias")
                # print(line_dias.work_entry_type_id.name)
                if line_dias.work_entry_type_id.name in reglasdias:
                    dias = dias + line_dias.number_of_days
                if line_dias.work_entry_type_id.name == "Primas":
                    dias_pagar = line_dias.number_of_days

            for line in comprobante.line_ids:
                # for regla in reglas:
                if line.salary_rule_id.sueldo_variable:
                    print(line.salary_rule_id.code)
                    valor_sueldo_variable = valor_sueldo_variable + line.total

            print("dias DEVENGADOS comprobante")
            print(dias)
            print("valor sueldo variable")
            print(valor_sueldo_variable)
            dias_trabajados = dias_trabajados + dias


        dias_trabajados_promedio = 0
        valorsueldo = 0
        print("comprobantes_promedio")
        print(comprobantes_promedio)
        for comprobante in comprobantes_promedio:
            _logger.info("en promedio aha "+comprobante.name)
            print("comprobante promedio")
            print(comprobante.name)
            valor_comprobante_promedio = 0
            dias_promedio = 0
            for line_dias in comprobante.worked_days_line_ids:
                if line_dias.work_entry_type_id.name in reglasdias:
                    dias_promedio = dias_promedio + line_dias.number_of_days

            for line in comprobante.line_ids:
                if line.salary_rule_id.sueldo_variable:
                    print(line.salary_rule_id.code)
                    valor_sueldo_variable = valor_sueldo_variable + line.total
                # for regla in reglas:
                #     if line.salary_rule_id.code==regla:
                #         ##el valor del sueldo
                #         valorsueldo = line.total
            _logger.info("la suma de todos da "+str(valor_sueldo_variable))
            # numero_meses = numero_meses + 1
            # print("valor DEVENGADOS comprobante")
            # print(valor_comprobante_promedio)
            # print(comprobante.state)
            # print("dias DEVENGADOS comprobante")
            # print(dias_promedio)
            print("Y LOS VALORES")
            print(valor_sueldo_variable)
            print(dias_trabajados_promedio)

            dias_trabajados_promedio = dias_trabajados_promedio + dias_promedio

        ##no es el numero de meses de comprobantes es la formula para el numero de meses
        # print("dias_trabajados_promedio")
        # print(dias_trabajados_promedio)
        dias_trabajados_promedio = dias_trabajados_promedio + dias_trabajados

        print("dias_trabajados_promedio")
        print(dias_trabajados_promedio)

        if dias_trabajados_promedio < 30:
            numero_meses = 1
        else:
            numero_meses = round(dias_trabajados_promedio/30, 0) #float_round(dias_trabajados_promedio/30.44, precision_rounding=2 )
        _logger.info("dias/30 "+str(numero_meses))

        if numero_meses == 0:
            return 0,0,100.0
        valor_promedio = (valor_sueldo_variable + valorsueldo)/numero_meses
        _logger.info("valor sueldo variable "+str(valor_promedio))
        salario_minimo = contrato_actual.salario_minimo #1160000
        auxilio_transporte = contrato_actual.auxilio_de_transporte#140606
        valor_promedio = valor_promedio + sueldo
        _logger.info("valor sueldo variable + sueldo"+str(valor_promedio))
        if valor_promedio > salario_minimo*2:
            _logger.info("no es mayor a salariominimo por 2"+str(valor_promedio + sueldo))
            ##incluir subsidio de transporte
            pass
        else:
            valor_promedio = valor_promedio + auxilio_transporte

        # if dias_trabajados > 0:
        #     promedio = (valor_promedio / dias_trabajados)

        # if sin_promedio == "+auxilio_transporte>2":
        #     print("sumando auxilio de transporte")
        #     print(auxilio_de_transporte)
        #     valor_promedio = valor_promedio + auxilio_de_transporte

        _logger.info("VALOR + auxilio de transporte"+str(valor_promedio))
        _logger.info("dias trabajados "+str(dias_trabajados_promedio))

        print("valor comprobantes")
        print(valor_comprobantes)
        print("dias")
        print(dias_trabajados)
        print("promedio")
        print(valor_promedio)
        return valor_promedio/360,dias_pagar,100.0



    def promedio(self,empleado_id,payslip,reglas,reglasdias,valor_comprobante_actual):
        import logging
        _logger = logging.getLogger("NOMINA")
        periodo = 0
        # if payslip.prima == True:
        if payslip.date_from.month <= 6:
            periodo = 1
        else:
            periodo = 2

        contrato_actual = payslip.contract_id
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte

        comprobantes_promedio = self.env['hr.payslip'].search([('contract_id','=',contrato_actual.id),('state', 'in', ['done', 'paid'])])
        print(comprobantes_promedio)
        # _logger.info("en promedio aha "+comprobantes_promedio)
        ano_trabajado = str(payslip.date_from.year)
        # print("anyo trabajado")
        # print(ano_trabajado)
        # print("periodo")
        # print(periodo)
        # print(payslip.date_from)
        contrato_actual = payslip.contract_id
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte
        if periodo == 1:
            comprobantes = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-01-01'),('date_to','<=',ano_trabajado+'-06-30'),('contract_id','=',contrato_actual.id),('state', 'in', ['done', 'paid'])])
        elif periodo == 2:
            #comprobantes_promedio = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-01-01'),('date_to','<=',ano_trabajado+'-06-30'),('contract_id','=',contrato_actual.id),('state','=','done')])
            comprobantes = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-07-01'),('date_to','<=',ano_trabajado+'-12-31'),('contract_id','=',contrato_actual.id),('state', 'in', ['done', 'paid'])])
        # else:
        #     return 0,0,0

        #promedio de regla de enero a junio
        promedio = 0
        valor_comprobantes = 0
        dias_trabajados = 0
        # numero_meses = 1
        for comprobante in self:
            # print("comprobante actual")
            # print(comprobante.name)
            # print(comprobante.state)
            # print(comprobante.contract_id)
            valor_comprobante = 0
            dias = 0
            for line_dias in comprobante.worked_days_line_ids:
                # print("tipo_de_dias")
                # print(line_dias.work_entry_type_id.name)
                if line_dias.work_entry_type_id.name in reglasdias:
                    dias = dias + line_dias.number_of_days
                if line_dias.work_entry_type_id.name == "Primas":
                    dias_pagar = line_dias.number_of_days
            print("dias DEVENGADOS comprobante")
            print(dias)
            print("valor comprobante")
            print(valor_comprobante_actual)
            valor_comprobantes = valor_comprobantes + valor_comprobante_actual
            dias_trabajados = dias_trabajados + dias

        # for comprobante in comprobantes:
        #     # print("comprobante")
        #     # print(comprobante.name)
        #     # print(comprobante.state)
        #     # print(comprobante.contract_id)
        #     # print(reglasdias)
        #     valor_comprobante = 0
        #     dias = 0
        #     for line_dias in comprobante.worked_days_line_ids:
        #         # print("tipo_de_dias")
        #         # print(line_dias.work_entry_type_id.name)
        #         if line_dias.work_entry_type_id.name in reglasdias:
        #             dias = dias + line_dias.number_of_days

        #     for line in comprobante.line_ids:
        #         for regla in reglas:
        #             if line.salary_rule_id.code == regla:
        #                 valor_comprobante = valor_comprobante + line.total
        #     numero_meses = numero_meses + 1
        #     # print("valor DEVENGADOS comprobante")
        #     # print(valor_comprobante)
        #     # print("dias DEVENGADOS comprobante")
        #     # print(dias)
        #     valor_comprobantes = valor_comprobantes + valor_comprobante
        #     dias_trabajados = dias_trabajados + dias

        dias_trabajados_promedio = 0
        valor_comprobantes_promedio = 0
        print("comprobantes_promedio")
        print(comprobantes)
        for comprobante in comprobantes:
            _logger.info("en promedio aha "+comprobante.name)
            print("comprobante promedio")
            print(comprobante.name)
            valor_comprobante_promedio = 0
            dias_promedio = 0
            valorsito = 0
            for line_dias in comprobante.worked_days_line_ids:
                if line_dias.work_entry_type_id.name in reglasdias:
                    dias_promedio = dias_promedio + line_dias.number_of_days

            for line in comprobante.line_ids:
                for regla in reglas:
                    if line.salary_rule_id.code == regla:
                        valor_comprobante_promedio = valor_comprobante_promedio + line.total
                        valorsito = valorsito + line.total
            _logger.info("valor comprobante "+str(valorsito))        
            # numero_meses = numero_meses + 1
            # print("valor DEVENGADOS comprobante")
            # print(valor_comprobante_promedio)
            # print(comprobante.state)
            # print("dias DEVENGADOS comprobante")
            # print(dias_promedio)
            print("Y LOS VALORES")
            print(valor_comprobantes_promedio)
            print(dias_trabajados_promedio)
            valor_comprobantes_promedio = valor_comprobantes_promedio + valor_comprobante_promedio
            dias_trabajados_promedio = dias_trabajados_promedio + dias_promedio

        ##no es el numero de meses de comprobantes es la formula para el numero de meses
        # print("dias_trabajados_promedio")
        # print(dias_trabajados_promedio)
        dias_trabajados_promedio = dias_trabajados_promedio + dias_trabajados


        numero_meses = round(dias_trabajados_promedio/30, 2) #float_round(dias_trabajados_promedio/30.44, precision_rounding=2 )
        _logger.info("se cambio esta formula dias/30.44 "+str(numero_meses))

        if numero_meses == 0:
            return 0,0,100.0
        valor_promedio = (valor_comprobantes_promedio + valor_comprobante_actual)/numero_meses
        _logger.info("valor promedio "+str(valor_promedio))
        salario_minimo = contrato_actual.salario_minimo #1160000
        auxilio_transporte = contrato_actual.auxilio_de_transporte#140606
        if valor_promedio > salario_minimo*2:
            ##incluir subsidio de transporte
            pass
        else:
            valor_promedio = valor_promedio + auxilio_transporte
        if dias_trabajados > 0:
            promedio = (valor_comprobantes / dias_trabajados)

        # if sin_promedio == "+auxilio_transporte>2":
        #     print("sumando auxilio de transporte")
        #     print(auxilio_de_transporte)
        #     valor_promedio = valor_promedio + auxilio_de_transporte
        _logger.info("VALOR 1"+str(valor_comprobante_actual))
        _logger.info("VALOR 2"+str(valor_comprobantes_promedio))
        _logger.info("dias trabajados "+str(dias_trabajados_promedio))
        _logger.info("promedio "+str(valor_promedio))

        print("valor comprobantes")
        print(valor_comprobantes)
        print("dias")
        print(dias_trabajados)
        print("promedio")
        print(valor_promedio)
        return valor_promedio/360,dias_trabajados_promedio,100.0


    def promediocontrato(self,empleado_id,payslip,reglas,reglasdias,valor_comprobante_actual):
        import logging
        _logger = logging.getLogger("VACACIONES")
        periodo = 0
        # if payslip.prima == True:
        if payslip.date_from.month <= 6:
            periodo = 1
        else:
            periodo = 2

        contrato_actual = payslip.contract_id
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte

        comprobantes_promedio = self.env['hr.payslip'].search([('contract_id','=',contrato_actual.id),('state','=','done')])
        print(comprobantes_promedio)
        # _logger.info("en promedio aha "+comprobantes_promedio)
        ano_trabajado = str(payslip.date_from.year)
        # print("anyo trabajado")
        # print(ano_trabajado)
        # print("periodo")
        # print(periodo)
        # print(payslip.date_from)
        contrato_actual = payslip.contract_id
        ##conseguir todos los comprobantes de nomina del contrato
        auxilio_de_transporte = contrato_actual.auxilio_de_transporte
        if periodo == 1:
            comprobantes = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-01-01'),('date_to','<=',ano_trabajado+'-06-30'),('contract_id','=',contrato_actual.id),('state','=','done')])
        elif periodo == 2:
            #comprobantes_promedio = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-01-01'),('date_to','<=',ano_trabajado+'-06-30'),('contract_id','=',contrato_actual.id),('state','=','done')])
            comprobantes = self.env['hr.payslip'].search([('employee_id','=',empleado_id),('date_from','>=',ano_trabajado+'-07-01'),('date_to','<=',ano_trabajado+'-12-31'),('contract_id','=',contrato_actual.id),('state','=','done')])
        # else:
        #     return 0,0,0

        #promedio de regla de enero a junio
        promedio = 0
        valor_comprobantes = 0
        dias_trabajados = 0
        dias_pagar = 0
        # numero_meses = 1
        for comprobante in self:
            # print("comprobante actual")
            # print(comprobante.name)
            # print(comprobante.state)
            # print(comprobante.contract_id)
            valor_comprobante = 0
            dias = 0
            for line_dias in comprobante.worked_days_line_ids:
                # print("tipo_de_dias")
                # print(line_dias.work_entry_type_id.name)
                if line_dias.work_entry_type_id.name in reglasdias:
                    dias = dias + line_dias.number_of_days
                if line_dias.work_entry_type_id.name == "Vacaciones Comunes":
                    dias_pagar = line_dias.number_of_days
                if line_dias.work_entry_type_id.name == "Vacaciones Compensadas":
                    dias_pagar = line_dias.number_of_days
            print("dias DEVENGADOS comprobante")
            print(dias)
            print("valor comprobante")
            print(valor_comprobante_actual)
            valor_comprobantes = valor_comprobantes + valor_comprobante_actual
            dias_trabajados = dias_trabajados + dias

        # for comprobante in comprobantes:
        #     # print("comprobante")
        #     # print(comprobante.name)
        #     # print(comprobante.state)
        #     # print(comprobante.contract_id)
        #     # print(reglasdias)
        #     valor_comprobante = 0
        #     dias = 0
        #     for line_dias in comprobante.worked_days_line_ids:
        #         # print("tipo_de_dias")
        #         # print(line_dias.work_entry_type_id.name)
        #         if line_dias.work_entry_type_id.name in reglasdias:
        #             dias = dias + line_dias.number_of_days

        #     for line in comprobante.line_ids:
        #         for regla in reglas:
        #             if line.salary_rule_id.code == regla:
        #                 valor_comprobante = valor_comprobante + line.total
        #     numero_meses = numero_meses + 1
        #     # print("valor DEVENGADOS comprobante")
        #     # print(valor_comprobante)
        #     # print("dias DEVENGADOS comprobante")
        #     # print(dias)
        #     valor_comprobantes = valor_comprobantes + valor_comprobante
        #     dias_trabajados = dias_trabajados + dias

        dias_trabajados_promedio = 0
        valor_comprobantes_promedio = 0
        print("comprobantes_promedio")
        print(comprobantes_promedio)
        for comprobante in comprobantes_promedio:
            _logger.info("en promedio aha "+comprobante.name)
            print("comprobante promedio")
            print(comprobante.name)
            valor_comprobante_promedio = 0
            dias_promedio = 0
            for line_dias in comprobante.worked_days_line_ids:
                if line_dias.work_entry_type_id.name in reglasdias:
                    dias_promedio = dias_promedio + line_dias.number_of_days

            for line in comprobante.line_ids:
                for regla in reglas:
                    if line.salary_rule_id.code == regla:
                        valor_comprobante_promedio = valor_comprobante_promedio + line.total

            # numero_meses = numero_meses + 1
            # print("valor DEVENGADOS comprobante")
            # print(valor_comprobante_promedio)
            # print(comprobante.state)
            # print("dias DEVENGADOS comprobante")
            # print(dias_promedio)
            print("Y LOS VALORES")
            print(valor_comprobantes_promedio)
            print(dias_trabajados_promedio)
            valor_comprobantes_promedio = valor_comprobantes_promedio + valor_comprobante_promedio
            dias_trabajados_promedio = dias_trabajados_promedio + dias_promedio

        ##no es el numero de meses de comprobantes es la formula para el numero de meses
        # print("dias_trabajados_promedio")
        # print(dias_trabajados_promedio)
        dias_trabajados_promedio = dias_trabajados_promedio + dias_trabajados


        dias_vacaciones = round(dias_trabajados_promedio/30.44, 2) #float_round(dias_trabajados_promedio/30.44, precision_rounding=2 ) ##dias_trabajados_promedio*15/360
        _logger.info("dias vacaciones "+str(dias_vacaciones))

        if dias_vacaciones == 0:
            return 0,0,100.0
        valor_promedio = (valor_comprobantes_promedio + valor_comprobante_actual)/dias_vacaciones
        _logger.info("valor promedio "+str(valor_promedio))
        salario_minimo = 1160000
        auxilio_transporte = 140606
        # if valor_promedio > salario_minimo*2:
        #     ##incluir subsidio de transporte
        #     pass
        # else:
        #     valor_promedio = valor_promedio + auxilio_transporte
        if dias_trabajados > 0:
            promedio = (valor_comprobantes / dias_trabajados)

        # if sin_promedio == "+auxilio_transporte>2":
        #     print("sumando auxilio de transporte")
        #     print(auxilio_de_transporte)
        #     valor_promedio = valor_promedio + auxilio_de_transporte
        _logger.info("VALOR 1"+str(valor_comprobante_actual))
        _logger.info("VALOR 2"+str(valor_comprobantes_promedio))
        _logger.info("dias trabajados "+str(dias_trabajados_promedio))
        _logger.info("promedio "+str(valor_promedio))

        print("valor comprobantes")
        print(valor_comprobantes)
        print("dias")
        print(dias_trabajados)
        print("promedio")
        print(valor_promedio)
        return valor_promedio/30,dias_pagar,100.0



        ############PROCEDIMIENTOS PARA AGREGAR TERCERO Y CUENTA CONTABLE AL COMPROBANTE NOMINA#################

    def _prepare_slip_lines(self, date, line_ids):
        print("si entro pero no")
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Payroll')
        new_lines = []
        todas = self.env['hr.administradoras'].search([("ccostos.departamentos.id",'=',self.employee_id.department_id.id),("centro_costos","=",True)]) ##
        # print(self.employee_id.department_id.id)
        # print("todas")
        # print(todas)
        # for to in todas:
        #     print("centro de costos")
        #     print(to.ccostos.departamentos.id)

        for line in self.line_ids.filtered(lambda line: line.category_id):
            amount = line.total
            if line.code == 'NET': # Check if the line is the 'Net Salary'.
                for tmp_line in self.line_ids.filtered(lambda line: line.category_id):
                    if tmp_line.salary_rule_id.not_computed_in_net: # Check if the rule must be computed in the 'Net Salary' or not.
                        if amount > 0:
                            amount -= abs(tmp_line.total)
                        elif amount < 0:
                            amount += abs(tmp_line.total)
            if float_is_zero(amount, precision_digits=precision):
                continue
            # print("haber que paso paso paso")
            ##buscar centro de costos
            debit_account_id = False
            credit_account_id = False

            for administradora in todas:
                if line.salary_rule_id.name == administradora.administradora.name:
                    if administradora.administradora.name == line.salary_rule_id.name:
                        print("coincidencia administradora.administradora.name")
                        print(administradora.administradora.name)
                        print(line.salary_rule_id.code)
                        debit_account_id = administradora.cuenta_debito.id if administradora.cuenta_debito else False
                        credit_account_id = administradora.cuenta_credito.id if administradora.cuenta_credito else False
                        partner_id_debit = administradora.tercero.id if administradora.tercero else line.slip_id.employee_id.employee_address_home.id
                        partner_id_credit = administradora.tercero.id if administradora.tercero else line.slip_id.employee_id.employee_address_home.id

            # if line.salary_rule_id.name == "Libranzas":
            #     print(line.salary_rule_id.name)
            #     print(amount)

            ##SI EXISTE CUENTA CONTABLE debito EN LA REGLA
            if line.salary_rule_id.account_debit:
                debit_account_id = line.salary_rule_id.account_debit.id
                partner_id_debit = line.salary_rule_id.partner_id_debit.id if line.salary_rule_id.partner_id_debit.id else line.slip_id.employee_id.employee_address_home.id
            else:
                for administradora in line.slip_id.contract_id.administradoras_ids:
                    # print(administradora.administradora.name)
                    if administradora.administradora.name == line.salary_rule_id.name:
                        ##guardar cuentas contables y partner
                        if administradora.cuenta_debito:
                            debit_account_id = administradora.cuenta_debito.id
                            partner_id_debit = administradora.tercero.id if administradora.tercero else line.slip_id.employee_id.employee_address_home.id

            if (not debit_account_id):
                for administradora in line.slip_id.company_id.administradoras_ids:
                    if administradora.administradora.name == line.salary_rule_id.name:
                        ##guardar cuentas contables y partner
                        if administradora.cuenta_debito:
                            debit_account_id = administradora.cuenta_debito.id
                            partner_id_debit = administradora.tercero.id if administradora.tercero else line.slip_id.employee_id.employee_address_home.id

            # print(line.salary_rule_id.name)
            ##SI EXISTE CUENTA CONTABLE credito EN LA REGLA

            if line.salary_rule_id.account_credit:
                credit_account_id = line.salary_rule_id.account_credit.id
                partner_id_credit = line.salary_rule_id.partner_id_credit.id if line.salary_rule_id.partner_id_credit.id else line.slip_id.employee_id.employee_address_home.id
            else:
                # print("y era por aca la jugada")
                for administradora in line.slip_id.contract_id.administradoras_ids:
                    # print("administradora.administradora.name")
                    # print(administradora.administradora.name)
                    if administradora.administradora.name == line.salary_rule_id.name:
                        ##guardar cuentas contables y partner
                        # print("y es igual")
                        # print(administradora.cuenta_credito)
                        if administradora.cuenta_credito:
                            credit_account_id = administradora.cuenta_credito.id
                            partner_id_credit = administradora.tercero.id if administradora.tercero else line.slip_id.employee_id.employee_address_home.id

            if (not credit_account_id):
                for administradora in line.slip_id.company_id.administradoras_ids:
                    # print("adentro")
                    # print(administradora.administradora.name)
                    # print(line.salary_rule_id.name)
                    if administradora.administradora.name == line.salary_rule_id.name:
                        ##guardar cuentas contables y partner
                        if administradora.cuenta_credito:
                            credit_account_id = administradora.cuenta_credito.id
                            partner_id_credit = administradora.tercero.id if administradora.tercero else line.slip_id.employee_id.employee_address_home.id

            # print("y el valor por aqui")
            # print(credit_account_id)

            if debit_account_id: # If the rule has a debit account.
                debit = amount if amount > 0.0 else 0.0
                credit = -amount if amount < 0.0 else 0.0

                debit_line = next(self._get_existing_lines(
                    line_ids + new_lines, line, debit_account_id, debit, credit), False)

                if not debit_line:
                    debit_line = self._prepare_line_values(line, debit_account_id, date, debit, credit,partner_id_debit)
                    debit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_debit.tax_ids.ids]
                    new_lines.append(debit_line)
                else:
                    debit_line['debit'] += debit
                    debit_line['credit'] += credit

            if credit_account_id: # If the rule has a credit account.
                debit = -amount if amount < 0.0 else 0.0
                credit = amount if amount > 0.0 else 0.0
                credit_line = next(self._get_existing_lines(
                    line_ids + new_lines, line, credit_account_id, debit, credit), False)

                if not credit_line:
                    print(line.salary_rule_id.name)
                    print(credit_account_id)
                    print("habech")
                    credit_line = self._prepare_line_values(line, credit_account_id, date, debit, credit,partner_id_credit)
                    credit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_credit.tax_ids.ids]
                    new_lines.append(credit_line)
                else:
                    credit_line['debit'] += debit
                    credit_line['credit'] += credit
        return new_lines


    def _prepare_line_values(self, line, account_id, date, debit, credit,partner):
        if not self.company_id.batch_payroll_move_lines and line.code == "NET":
            partner = self.employee_id.work_contact_id.id
        # else:
        #     partner = line.partner_id
        return {
            'name': line.name,
            'partner_id': partner,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'analytic_distribution': (line.salary_rule_id.analytic_account_id and {line.salary_rule_id.analytic_account_id.id: 100}) or
                                     (line.slip_id.contract_id.analytic_account_id.id and {line.slip_id.contract_id.analytic_account_id.id: 100}),
            'tax_tag_ids': line.debit_tag_ids.ids if account_id == line.salary_rule_id.account_debit.id else line.credit_tag_ids.ids,
        }


class nomina_change(models.Model):
    _inherit = 'hr.salary.rule'

    origin_partner = fields.Many2one('res.partner', 'Origen empleado')
    partner_id_debit = fields.Many2one('res.partner', 'Tercero Deudor')
    partner_id_credit = fields.Many2one('res.partner', 'Tercero Acreedor')