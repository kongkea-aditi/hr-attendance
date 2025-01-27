from odoo import api, models


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
                action = "check_out" if "check_out" in vals else "check_in"
                attendance.employee_id._attendance_action_check(action)
        return super().write(vals)
