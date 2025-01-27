import ipaddress
import logging

from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request
from odoo.tools.safe_eval import const_eval

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    bypass_ip_check = fields.Boolean(
        string="Bypass IP Check",
        default=False,
        groups="hr.group_hr_manager",
    )

    def _attendance_action_check(self, action_type):
        """Hook method for attendance IP validation.
        Called from hr.attendance during create/write operations.

        Args:
            action_type: String indicating 'check_in' or 'check_out'
        Returns:
            True if validation passes
        Raises:
            ValidationError if IP check fails
        """
        self.ensure_one()
        action = "Check In" if action_type == "check_in" else "Check Out"

        if not self._is_ip_check_required():
            return True

        remote_ip = self._get_remote_ip()
        if not remote_ip:
            raise ValidationError(
                _("Unable to determine IP address for %(action)s operation")
                % {"action": action}
            )

        if not self._is_ip_allowed(remote_ip):
            raise ValidationError(
                _("IP %(ip)s not allowed for %(action)s")
                % {"ip": remote_ip, "action": action}
            )
        return True

    def _get_ip_check_enabled(self):
        """Get global IP check setting."""
        return const_eval(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_attendance_work_location_ip_check.ip_check_enabled", "False")
        )

    def _is_ip_check_required(self):
        """Determine if IP check is required for this employee."""
        self.ensure_one()

        # No work location means no IP check
        if not self.work_location_id:
            return False

        # Check if work location has IP check enabled
        if not self.work_location_id.check_ip:
            return False

        # Employee bypass takes precedence
        if self.bypass_ip_check:
            return False

        # Check if global IP check is enabled
        if not self._get_ip_check_enabled():
            return False

        return True

    def _is_ip_allowed(self, ip_addr):
        """Check if IP is allowed for this employee."""
        if not ip_addr:
            return False

        try:
            ip = ipaddress.ip_address(ip_addr)
            cidrs = self.work_location_id.allowed_cidr_ids.filtered("active")

            if not cidrs:
                raise ValidationError(
                    _("No active CIDR ranges defined for location %s")
                    % self.work_location_id.name
                )

            for cidr in cidrs:
                if ip in ipaddress.ip_network(cidr.cidr):
                    _logger.info(
                        "IP %s matched CIDR %s for location %s",
                        ip_addr,
                        cidr.cidr,
                        self.work_location_id.name,
                    )
                    return True

            return False

        except ValueError as e:
            _logger.error("Invalid IP address format: %s. Error: %s", ip_addr, e)
            return False

    def _get_remote_ip(self):
        """Get remote IP from request, considering proxy headers."""
        if not request:
            return None

        try:
            ip = request.httprequest.headers.get("X-Forwarded-For")
            if ip:
                return ip.split(",")[0].strip()

            ip = request.httprequest.headers.get("X-Real-IP")
            if ip:
                return ip.strip()

            return request.httprequest.remote_addr
        except Exception as e:
            _logger.error("Error getting remote address: %s", str(e))
            return None

    def write(self, vals):
        """Restrict bypass_ip_check modification to HR managers."""
        if "bypass_ip_check" in vals and not self.env.user.has_group(
            "hr.group_hr_manager"
        ):
            raise AccessError(
                _("Only HR Managers can modify the IP check bypass setting.")
            )
        return super().write(vals)
