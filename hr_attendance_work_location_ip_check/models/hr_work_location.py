import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import const_eval

_logger = logging.getLogger(__name__)


class HrWorkLocation(models.Model):
    _inherit = "hr.work.location"

    allowed_cidr_ids = fields.One2many(
        "hr.work.location.cidr",
        "work_location_id",
        string="Allowed Networks",
        groups="hr.group_hr_manager",
    )
    check_ip = fields.Boolean(
        string="Enable IP Check",
        default=False,
        groups="hr.group_hr_manager",
    )

    global_check_ip = fields.Boolean(
        string="IP Check Enabled Globally",
        compute="_compute_ip_check_enabled",
    )

    def _compute_ip_check_enabled(self):
        for record in self:
            record.global_check_ip = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hr_attendance.ip_check_enabled")
            )

    @api.constrains("check_ip", "allowed_cidr_ids")
    def _check_ip_cidrs(self):
        for record in self:
            if record.check_ip and not record.allowed_cidr_ids.filtered("active"):
                raise ValidationError(
                    _(
                        "IP check enabled locations must have at least one active CIDR range."
                    )
                )

    def check_ip_allowed(self, ip_addr):
        """Check if IP is allowed for this location."""
        self.ensure_one()
        if not const_eval(str(self.check_ip)):
            return True

        cidrs = self.allowed_cidr_ids.filtered("active")
        if not cidrs:
            return False

        return any(cidr.ip_in_range(ip_addr) for cidr in cidrs)
