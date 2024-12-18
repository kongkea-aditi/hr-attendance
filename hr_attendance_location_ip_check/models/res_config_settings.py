from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ip_check_enabled = fields.Boolean(
        string='Enable IP Attendance Check for Work Locations',
        config_parameter='hr_attendance.ip_check_enabled',
    )




