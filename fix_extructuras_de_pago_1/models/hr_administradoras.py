# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class administradoras(models.Model):
    _name = 'hr.administradoras'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Administradoras'

    name = fields.Char(string="Nombre Comercial" ,tracking=True)
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    ccostos = fields.Many2one("hr.centrocostos", string="Centro de costos" ,tracking=True)
    administradora = fields.Many2one("hr.tipo", string="Tipo" ,tracking=True)
    tercero = fields.Many2one("res.partner", string="Tercero")
    porcentaje = fields.Float(string="Porcentaje" ,tracking=True)
    compania = fields.Boolean(string="Compañia")
    colaborador = fields.Boolean(string="Colaborador")
    centro_costos = fields.Boolean(string="Centro de costos" ,tracking=True)
    cuenta_debito = fields.Many2one("account.account", string="Cuenta debito" ,tracking=True)
    cuenta_credito = fields.Many2one("account.account", string="Cuenta crédito" ,tracking=True)

    @api.onchange('centro_costos')
    def _onchange_centro_costos(self):
        pass 
