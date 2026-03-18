from odoo import models, fields, api

class HrWorkerSubtype(models.Model):
    _name = 'hr.worker.subtype'
    _description = 'Subtipo de Trabajador (PILA)'

    code = fields.Char(string='Código', required=True)
    name = fields.Char(string='Descripción', required=True)
    active = fields.Boolean(default=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}" if record.code else record.name

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}" if record.code else record.name
            result.append((record.id, name))
        return result
