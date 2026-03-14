# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class administradoras_contrato(models.Model):
    _inherit = 'hr.contract'
    _description = 'admin_colaborador'

    # name = fields.Char(string="Centro de costos")
    # company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    administradoras_ids = fields.Many2many("hr.administradoras", string="Administradoras",domain="[('colaborador', '=', True),('centro_costos', '=', False)]") ##('ccostos.id', '=', department_id.id),

