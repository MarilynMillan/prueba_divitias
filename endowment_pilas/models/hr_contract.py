
from odoo import fields, models, api
from datetime import date

class HrContract(models.Model):
    _inherit = 'hr.contract'

    pila_novelty_ids = fields.One2many(
        'hr.contract.novelty.line',
        'contract_id',
        string='Novedades Aplicadas')

    date_wage_change = fields.Date(
        string='Último Cambio Sueldo',
        help="Fecha en la que el campo Salario ('wage') fue modificado por última vez."
    ,tracking=True, readonly="1")

    wage_integral = fields.Boolean(string='Salario Integral',tracking=True)
    wage_variable = fields.Boolean(string='Salario Variable',tracking=True)

    auxilio_de_transporte = fields.Float("Auxilio de transporte",tracking=True)
    uvt =  fields.Float("UVT",tracking=True)
    salario_minimo = fields.Float("Salario Minimo",tracking=True)
    tipo_contrato = fields.Selection([
        ('1', 'Término Fijo'),
        ('2', 'Término Indefinido'),
        ('3', 'Obra o Labor'),
        ('4', 'Aprendizaje'),
        ('5', 'Practicas'),
    ], string='Tipo Contrato',tracking=True)
    
    tipo_trabajador = fields.Selection([
        ('01', '1.Dependiente'),
        ('02', 'Servicio domestico'),
        ('03', 'Independiente'),
        ('04', 'Madre comunitaria'),
        ('12', 'Aprendices del Sena en etapa lectiva'),
        ('16', 'Independiente agremiado o asociado'),
        ('18', 'Funcionarios públicos sin tope máximo de ibc'),
        ('19', 'Aprendices del SENA en etapa productiva'),
        ('20', 'Estudiantes (régimen especial ley 789 de 2002)'),
        ('21', 'Estudiantes de postgrado en salud'),
        ('22', 'Profesor de establecimiento particular'),
        ('23', 'Estudiantes aportes solo riesgos laborales'),
        ('30', 'Dependiente entidades o universidades públicas con régimen especial en salud'),
        ('31', 'Cooperados o pre cooperativas de trabajo asociado'),
        ('32', 'Cotizante miembro de la carrera diplomática o consular de un país extranjero o funcionario de organismo multilateral'),
        ('33', 'Beneficiario del fondo de solidaridad pensional'),
        ('34', 'Concejal municipal o distrital o edil de junta administrativa local que percibe honorarios amparado por póliza de salud'),
        ('35', 'Concejal municipal o distrital que percibe honorarios no amparado con póliza de salud'),
        ('36', 'Concejal municipal o distrital que percibe honorarios no amparado con póliza de salud beneficiario del fondo de solidaridad pensional'),
        ('40', 'Beneficiario upc adicional'),
        ('41', 'Beneficiario sin ingresos con pago por tercero'),
        ('42', 'Cotizante pago solo salud articulo 2 ley 1250 de 2008 (independientes de bajos ingresos)'),
        ('43', 'Cotizante voluntario a pensiones con pago por tercero'),
        ('44', 'Cotizante dependiente de empleo de emergencia con duración mayor o igual a un mes'),
        ('45', 'Cotizante dependiente de empleo de emergencia con duración menor a un mes'),
        ('47', 'Trabajador dependiente de entidad beneficiaria del sistema general de participaciones - aportes patronales'),
        ('51', 'Trabajador de tiempo parcial'),
        ('52', 'Beneficiario del mecanismo de protección al cesante'),
        ('53', 'Afiliado participe'),
        ('54', 'Pre pensionado de entidad en liquidación.'),
        ('55', 'Afiliado participe - dependiente'),
        ('56', 'Pre pensionado con aporte voluntario a salud'),
        ('57', 'Independiente voluntario al sistema de riesgos laborales'),
        ('58', 'Estudiantes de prácticas laborales en el sector público'),
        ('59', 'Independiente con contrato de prestación de servicios superior a 1 mes'),
        ('61', 'Beneficiario programa de reincorporación'),
        ], string='Tipo Trabajador',tracking=True)
    sub_tipo_trabajador = fields.Selection([
        ('00', 'Ninguna'),
        ('01', '1.Dependiente pensionado por vejez activo'),
        # ('02', 'Independiente pensionado por vejez activo'),
        # ('03', 'Cotizante no obligado a cotizar a pensión por edad'),
        # ('04', 'Cotizante con requisitos cumplidos para pensión'),
        # ('12', 'Cotizante a quien se le ha reconocido indemnización sustitutiva o devolución de saldos'),
        # ('16', 'Cotizante perteneciente a un régimen de exceptuado de pensiones a entidades autorizadas para recibir aportes exclusivamente de un grupo de sus propios'),
        # ('18', 'Cotizante pensionado con mesada superior a 25 smlmv'),
        # ('19', 'Residente en el exterior afiliado voluntario al sistema general de pensiones y/o afiliado'),
        # ('20', 'Conductores del servicio público de transporte terrestre automotor individual de pasajeros en vehículos taxi decreto 1047 de 2014'),
        # ('21', 'Conductores servicio taxi no aporte pensión dec. 1047'),
        ], string='Subtipo de Trabajador',tracking=True)
    AltoRiegoPension = fields.Selection([
        ('false', 'NO'),
        ('true', 'SI'),
        ], string='Alto Riego Pension',default='false',tracking=True)
    SalarioIntegral = fields.Selection([
        ('false', 'NO'),
        ('true', 'SI'),
        ], string='Salario Integral',default='false',tracking=True)
    banco = fields.Char("Banco",tracking=True)
    tipo_cuenta = fields.Char("Tipo cuenta",tracking=True)
    numero_cuenta = fields.Char("Numero de cuenta",tracking=True)
    metodo_pago = fields.Selection([
        ('1', 'Instrumento no definido'),
        ('2', 'Crédito ACH'),
        ('3', 'Débito ACH'),
        ('4', 'Reversión débito de demanda ACH'),
        ('5', 'Reversión crédito de demanda ACH'),
        ('6', 'Crédito de demanda ACH'),
        ('7', 'Débito de demanda ACH'),
        ('8', 'Mantener'),
        ('9', 'Clearing Nacional o Regional'),
        ('10', 'Efectivo'),
        ('11', 'Reversión Crédito Ahorro'),
        ('12', 'Reversión Débito Ahorro'),
        ('13', 'Crédito Ahorro'),
        ('14', 'Débito Ahorro'),
        ('15', 'Bookentry Crédito'),
        ('16', 'Bookentry Débito'),
        ('17', 'Concentración de la demanda en efectivo Desembolso Crédito (CCD)'),
        ('18', 'Concentración de la demanda en efectivo Desembolso (CCD) débito'),
        ('19', 'Crédito Pago negocio corporativo (CTP)'),
        ('20', 'Cheque'),
        ('21', 'Proyecto bancario'),
        ('22', 'Proyecto bancario certificado'),
        ('23', 'Cheque bancario'),
        ('24', 'Nota cambiaria esperando aceptación'),
        ('25', 'Cheque certificado'),
        ('26', 'Cheque Local'),
        ('27', 'Débito Pago Negocio Corporativo (CTP)'),
        ('28', 'Crédito Negocio Intercambio Corporativo (CTX)'),
        ('29', 'Débito Negocio Intercambio Corporativo (CTX)'),
        ('30', 'Transferencia Crédito'),
        ('31', 'Transferencia Débito'),
        ('32', 'Concentración Efectivo / Desembolso Crédito plus (CCD+)'),
        ('33', 'Concentración Efectivo / Desembolso Débito plus (CCD+)'),
        ('34', 'Pago y depósito pre acordado (PPD)'),
        ('35', 'Concentración efectivo ahorros / Desembolso Crédito (CCD)'),
        ('36', 'Concentración efectivo ahorros / Desembolso Crédito (CCD)'),
        ('37', 'Pago Negocio Corporativo Ahorros Crédito (CTP)'),
        ('38', 'Pago Negocio Corporativo Ahorros Débito (CTP)'),
        ('39', 'Crédito Negocio Intercambio Corporativo (CTX)'),
        ('40', 'Débito Negocio Intercambio Corporativo (CTX)'),
        ('41', 'Concentración efectivo/Desembolso Crédito plus (CCD+)'),
        ('42', 'Consignación bancaria'),
        ('43', 'Concentración efectivo / Desembolso Débito plus (CCD+)'),
        ('44', 'Nota cambiaria'),
        ('45', 'Transferencia Crédito Bancario'),
        ('46', 'Transferencia Débito Interbancario'),
        ('47', 'Transferencia Débito Bancaria'),
        ('48', 'Tarjeta Crédito'),
        ('49', 'Tarjeta Débito'),
        ('50', 'Postgiro'),         
        ('51', 'Telex estándar bancario francés'),
        ('52', 'Pago comercial urgente'),
        ('53', 'Pago Tesorería Urgente'),
        ('60', 'Nota promisoria'),
        ('61', 'Nota promisoria firmada por el acreedor'),
        ('62', 'Nota promisoria firmada por el acreedor, avalada por el banco'),
        ('63', 'Nota promisoria firmada por el acreedor, avalada por un tercero'),
        ('64', 'Nota promisoria firmada por el banco'),
        ('65', 'Nota promisoria firmada por un banco avalada por otro banco'),
        ('66', 'Nota promisoria firmada'),
        ('67', 'Nota promisoria firmada por un tercero avalada por un banco'),
        ('70', 'Retiro de nota por el por el acreedor'),
        ('71', 'Bonos'),
        ('72', 'Vales'),
        ('74', 'Retiro de nota por el por el acreedor sobre un banco'),
        ('75', 'Retiro de nota por el acreedor, avalada por otro banco'),
        ('76', 'Retiro de nota por el acreedor, sobre un banco avalada por un tercero'),
        ('77', 'Retiro de una nota por el acreedor sobre un tercero'),
        ('78', 'Retiro de una nota por el acreedor sobre un tercero avalada por un banco'),
        ('91', 'Nota bancaria transferible'),
        ('92', 'Cheque local trasferible'),
        ('93', 'Giro referenciado'),
        ('94', 'Giro urgente'),
        ('95', 'Giro formato abierto'),
        ('96', 'Método de pago solicitado no usado'),
        ('97', 'Clearing entre partners'),
        ('ZZZ', 'Acuerdo mutuo'),
        ], string='Metodo de pago',default='10',tracking=True) 

    alto_riesgo = fields.Selection([
        ('1', 'Actividades alto riesgos'),
        ('2', 'Senadores'),
        ('3', 'CTI'),
        ('4', 'Aviadores'),
        ('5', 'Sin riesgo'),
    ], string='Indicador alto riesgo',default='5',tracking=True)

    clase = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Clase ',tracking=True)


    economic_activitity = fields.Integer( string='Actividad economica ',tracking=True)
    work_center_id = fields.Many2one(
        'hr.work.center', 
        string="Centro de Trabajo (PILA)",
        help="Seleccione el centro de trabajo para el reporte de seguridad social."
    )

    pila_ingreso_concepto_id = fields.Many2one(
        'hr.contract.concept', 
        string="Concepto ingreso",
        domain=[('type', '=', 'ingreso')]
    )
    
    pila_retiro_concepto_id = fields.Many2one(
        'hr.contract.concept', 
        string="Concepto egreso",
        domain=[('type', '=', 'egreso')]
    )

    @api.model
    def write(self, vals):
        # Usamos write para capturar cambios desde el formulario o por código.
        # Si 'wage' está siendo modificado Y el nuevo valor es diferente al actual
        if 'wage' in vals:
            for contract in self:
                # Comparamos solo si el contrato ya existe (self.exists()) y el valor es distinto
                if contract.exists() and contract.wage != vals['wage']:
                    vals['date_wage_change'] = fields.Date.today()
                    # Salimos del bucle si solo hay un contrato para evitar doble asignación de hoy()
                    break 

        return super(HrContract, self).write(vals)



