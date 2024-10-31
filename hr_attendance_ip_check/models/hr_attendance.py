import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to validate IP before creating attendance records."""
        if not vals_list:
            return {'warning': _('No valid attendance records to create')}

        valid_vals = []
        for vals in vals_list:
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            validation_result = employee._validate_ip_address('check_in')

            if isinstance(validation_result, dict):
                return validation_result
            valid_vals.append(vals)

        return super().create(valid_vals)

    def write(self, vals):
        """Override write to validate IP before updating attendance records."""
        if 'check_out' in vals:
            for attendance in self:
                validation_result = attendance.employee_id._validate_ip_address('check_out')
                if isinstance(validation_result, dict):
                    return validation_result

        return super().write(vals)
