import ipaddress
import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, AccessError
from odoo.http import request
from odoo.tools.safe_eval import const_eval

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    bypass_ip_check = fields.Boolean(
        string='Bypass IP Check',
        default=False,
        readonly=True,
        groups='hr.group_hr_user',
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if not self.env.user.has_group('hr.group_hr_manager'):
            if 'bypass_ip_check' in res:
                res['bypass_ip_check']['readonly'] = True
        return res

    def write(self, vals):
        if 'bypass_ip_check' in vals and not self.env.user.has_group('hr.group_hr_manager'):
            raise AccessError(_('Only HR Managers can modify the IP check bypass setting.'))
        return super().write(vals)

    def attendance_manual(self, next_action, entered_pin=None):
        """Validate IP before processing manual attendance."""
        self.ensure_one()
        action_type = 'check_out' if self.attendance_state == 'checked_in' else 'check_in'
        self._validate_ip_address(action_type)
        return super().attendance_manual(next_action, entered_pin)

    def _get_ip_check_enabled(self):
        """Get global IP check setting."""
        return const_eval(
            self.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance.ip_check_enabled', 'False'
            )
        )

    def _validate_ip_address(self, action_type):
        """Validate current IP for attendance actions."""
        remote_ip = self._get_remote_ip()
        if not remote_ip:
            raise ValidationError(_(
                "Unable to determine IP address for %(action)s operation"
            ) % {'action': action_type})

        if not self._is_ip_allowed(remote_ip):
            raise ValidationError(_(
                "IP %(ip)s not allowed for %(action)s"
            ) % {'ip': remote_ip, 'action': action_type})

    def _is_ip_check_required(self):
        """Determine if IP check is required for this employee"""
        self.ensure_one()

        # Check if global IP check is enabled
        global_check = self._get_ip_check_enabled()
        if not global_check:
            return False

        # Employee bypass takes precedence
        if self.bypass_ip_check:
            return False

        # No work location means no IP check
        if not self.work_location_id:
            return False

        # Check if work location has IP check enabled
        return self.work_location_id.check_ip

    def _is_ip_allowed(self, ip_addr):
        """Check if IP is allowed for this employee"""
        if not self._is_ip_check_required():
            return True

        if not ip_addr:
            raise ValidationError(_("No IP address detected"))

        try:
            ip = ipaddress.ip_address(ip_addr)
            cidrs = self.work_location_id.allowed_cidr_ids.filtered('active').sorted('sequence')

            if not cidrs:
                _logger.error(
                    "No active CIDR ranges for location %s",
                    self.work_location_id.name
                )
                return False

            for cidr in cidrs:
                try:
                    if ip in ipaddress.ip_network(cidr.cidr):
                        _logger.info(
                            "IP %s matched CIDR %s for location %s",
                            ip_addr, cidr.cidr, self.work_location_id.name
                        )
                        return True
                except ValueError:
                    continue

            _logger.error(
                "IP %s not allowed for location %s",
                ip_addr,
                self.work_location_id.name
            )
            return False

        except ValueError:
            raise ValidationError(_("Invalid IP address format: %s") % ip_addr)

    def _get_remote_ip(self):
        """Get remote IP from request."""
        try:
            return request.httprequest.remote_addr if request else None
        except Exception as e:
            _logger.error("Error getting IP: %s", str(e))
            return None







