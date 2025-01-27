import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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
                .get_param("hr_attendance_work_location_ip_check.ip_check_enabled")
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
