from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.model_create_multi
    def create(self, vals_list):
        """Validate IP before creating attendance records."""
        employees = self.env["hr.employee"].browse(
            [vals.get("employee_id") for vals in vals_list]
        )
        employee_by_id = {employee.id: employee for employee in employees}

        for vals in vals_list:
            employee = employee_by_id.get(vals.get("employee_id"))
            action = "check_in"
            employee._attendance_action_check(action)

        return super().create(vals_list)

    def write(self, vals):
        """Validate IP for check-in/out modifications."""
        if any(field in vals for field in ["check_in", "check_out"]):
            for attendance in self:
                if attendance.employee_id.work_location_id:
                    action = "check_out" if "check_out" in vals else "check_in"
                    # Use the hook method
                    attendance.employee_id._attendance_action_check(action)
        return super().write(vals)

    def _validate_location_ip(self, employee, action="check_in"):
        """Validate if IP is allowed for work location."""
        if not employee.work_location_id.check_ip:
            return True

        remote_ip = employee._get_remote_ip()
        if not remote_ip:
            raise ValidationError(_("Unable to determine IP address"))

        if not employee._is_ip_allowed(remote_ip):
            raise ValidationError(
                _("IP %(ip)s not allowed for %(location)s")
                % {
                    "ip": remote_ip,
                    "location": employee.work_location_id.name,
                }
            )
