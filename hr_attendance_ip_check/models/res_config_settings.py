from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ip_check_enabled = fields.Boolean(
        string='Enable IP-based Attendance Check',
        config_parameter='hr_attendance.ip_check_enabled',
        help="Enable IP address validation for attendance check-in/check-out"
    )
    whitelist_ips = fields.Char(
        string='Whitelist IP Addresses',
        config_parameter='hr_attendance.whitelist_ips',
        help="Comma-separated list of allowed IP addresses")
