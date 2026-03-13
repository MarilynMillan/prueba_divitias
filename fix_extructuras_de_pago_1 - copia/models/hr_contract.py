# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class administradoras_contrato(models.Model):
    _inherit = 'hr.contract'
    _description = 'admin_colaborador'

    # name = fields.Char(string="Centro de costos")
    # company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    administradoras_ids = fields.Many2many("hr.administradoras", string="Administradoras",domain="[('colaborador', '=', True),('centro_costos', '=', False)]") ##('ccostos.id', '=', department_id.id),


    # MODELO hr.contract
    def get_admin_by_type(self, tipo):
        """Retorna la administradora del tipo solicitado."""
        self.ensure_one()
        admin = self.administradoras_ids.filtered(lambda r: r.type_entity == tipo)
        return admin[0] if admin else False

    def get_tarifa_by_type(self, tipo):
        """Devuelve la tarifa aplicable (un float) para el tipo de entidad.
        
        Busca la administradora asociada al contrato según el 'tipo' (ej: 'pension', 'salud') 
        y retorna el valor de su campo 'tarifa'.
        """
        self.ensure_one()
        
        # 1. Obtener la administradora utilizando el método ya existente en el contrato.
        # Se asume que get_admin_by_type(tipo) devuelve un único registro 'hr.administradoras' o False/None.
        admin = self.get_admin_by_type(tipo)
        
        # 2. Devolver la tarifa si se encuentra la administradora, de lo contrario, 0.0 o ''.
        # NOTA: Se recomienda devolver 0.0 si la columna en el Excel es numérica.
        # Si la tarifa no existe o es None, Odoo la tratará como 0.0 para campos Float, 
        # pero aquí forzamos el valor si el registro existe.
        if admin and hasattr(admin, 'tarifa'):
            return admin.tarifa
        
        # Siempre devuelva un valor escalar predecible.
        return 0.0