import logging
from odoo import models, _
from odoo.http import request
from werkzeug.exceptions import HTTPException

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_current_ip(self):
        """Get the current IP address from the request."""
        try:
            if request and request.httprequest:
                return request.httprequest.remote_addr
        except (AttributeError, HTTPException) as e:
            _logger.error("Error getting IP address: %s", str(e), exc_info=True)
        return None

    def _validate_ip_address(self, action_type='attendance'):
        """Validate if current IP is allowed for attendance actions."""
        if not self.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance.ip_check_enabled', 'False').lower() == 'true':
            return True

        current_ip = self._get_current_ip()
        if not current_ip:
            return {
                'warning': _('Unable to determine your IP address')
            }

        whitelist_ips = [
            ip.strip()
            for ip in self.env['ir.config_parameter'].sudo()
            .get_param('hr_attendance.whitelist_ips', '').split(',')
            if ip.strip()
        ]

        if not whitelist_ips:
            return {
                'warning': _('No IP addresses are whitelisted')
            }

        if current_ip not in whitelist_ips:
            return {
                'warning': _('You are not allowed to %(action)s from current IP address (%(ip)s)') % {
                    'action': action_type.replace('_', ' '),
                    'ip': current_ip
                }
            }

        return True

    def attendance_manual(self, next_action, entered_pin=None):
        """Handle manual attendance with IP validation."""
        self.ensure_one()

        # Determine action type based on current state
        action_type = 'check_out' if self.attendance_state == 'checked_in' else 'check_in'

        # Validate IP first
        ip_validation = self._validate_ip_address(action_type)
        if isinstance(ip_validation, dict):
            return ip_validation

        # Let hr_attendance handle the rest (PIN check, etc)
        return super().attendance_manual(next_action, entered_pin)
