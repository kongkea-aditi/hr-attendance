from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceWorkflow(CommonAttendanceTest):
    """Test cases for attendance workflow and modifications."""

    def test_01_attendance_modification(self):
        """Test IP validation on attendance modification"""
        # Create initial attendance with valid IP
        self.mock_ip.return_value = "192.168.1.100"
        attendance = self._create_test_attendance()

        # Test modification with invalid IP
        self.mock_ip.return_value = "10.0.0.1"
        with self.assertRaises(ValidationError):
            attendance.write(
                {
                    "check_out": "2024-01-01 17:00:00",
                }
            )

        # Test modification with valid IP
        self.mock_ip.return_value = "192.168.1.100"
        attendance.write(
            {
                "check_out": "2024-01-01 17:00:00",
            }
        )
        check_out_str = "2024-01-01 17:00:00"
        self.assertEqual(
            attendance.check_out.strftime("%Y-%m-%d %H:%M:%S"),
            check_out_str,
        )

    def test_02_hook_inheritance(self):
        """Test attendance action check hook inheritance"""
        self.mock_ip.return_value = "192.168.1.100"

        # First test the hook directly
        self.employee._attendance_action_check("check_in")

        # Then verify it works through attendance_manual
        result = self.employee.attendance_manual({})
        self.assertTrue(result)  # Verify we got a response

        # Verify the attendance data in the result
        self.assertIn("action", result)
        self.assertIn("attendance", result["action"])
        attendance_data = result["action"]["attendance"]
        self.assertEqual(attendance_data["employee_id"][0], self.employee.id)

        # Verify check_out works through the hook too
        checkout_result = self.employee.attendance_manual({})
        self.assertTrue(checkout_result)
        self.assertIn("action", checkout_result)
        self.assertIn("attendance", checkout_result["action"])

    def test_03_attendance_create_edge_cases(self):
        """Test empty and multiple attendance creation."""
        result = self.env["hr.attendance"].create([])
        self.assertEqual(len(result), 0)

        self.mock_ip.return_value = "192.168.1.100"
        if self.employee.attendance_state == "checked_in":
            self.employee.attendance_ids.write({"check_out": fields.Datetime.now()})

        vals_list = [
            {
                "employee_id": self.employee.id,
                "check_in": "2024-01-01 08:00:00",
                "check_out": "2024-01-01 12:00:00",
            },
            {
                "employee_id": self.employee.id,
                "check_in": "2024-01-01 14:00:00",
                "check_out": "2024-01-01 17:00:00",
            },
        ]
        attendances = self.env["hr.attendance"].create(vals_list)
        self.assertEqual(len(attendances), 2)

    def test_04_multi_attendance_validation(self):
        """Test validation with multiple attendance records."""
        # First ensure employee is checked out
        if self.employee.attendance_state == "checked_in":
            self.employee.attendance_ids.write({"check_out": fields.Datetime.now()})

        vals_list = []
        check_in_time = fields.Datetime.from_string("2024-01-01 08:00:00")

        for i in range(3):
            vals_list.append(
                {
                    "employee_id": self.employee.id,
                    "check_in": check_in_time + timedelta(hours=i * 2),
                    "check_out": check_in_time + timedelta(hours=(i * 2) + 1),
                }
            )

        # Test with valid IP
        self.mock_ip.return_value = "192.168.1.100"
        attendances = self.env["hr.attendance"].create(vals_list)
        self.assertEqual(len(attendances), 3)

        # Test with invalid IP
        self.mock_ip.return_value = "10.0.0.1"
        with self.assertRaises(ValidationError) as context:
            self.env["hr.attendance"].create(vals_list)
        self.assertIn("not allowed for", str(context.exception))

    def test_05_validate_location_ip_direct(self):
        """Test direct validation of location IP."""
        self.mock_ip.return_value = "192.168.1.100"

        with self.with_user("hr_manager@test.com"):
            # Test with valid IP
            self.env["hr.attendance"]._validate_location_ip(self.employee, "check_in")

            # Test with no work location
            self.employee.work_location_id = False
            self.env["hr.attendance"]._validate_location_ip(self.employee, "check_in")

            # Test with disabled IP check
            self.employee.work_location_id = self.work_location
            self.work_location.check_ip = False
            self.env["hr.attendance"]._validate_location_ip(self.employee, "check_in")

    def test_06_attendance_state_transitions(self):
        """Test attendance state transitions and validations."""
        self.mock_ip.return_value = "192.168.1.100"
        attendance = self._create_test_attendance()

        # Test state transition validation
        with self.assertRaises(ValidationError) as context:
            # Try to check out before check in time
            attendance.write({"check_out": attendance.check_in - timedelta(hours=1)})
        self.assertIn(
            '"Check Out" time cannot be earlier than "Check In" time',
            str(context.exception),
        )

    def test_07_attendance_batch_operations(self):
        """Test batch operations on attendance records."""
        self.mock_ip.return_value = "192.168.1.100"

        # Create multiple attendance records
        attendances = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": fields.Datetime.now() - timedelta(hours=x),
                    "check_out": fields.Datetime.now() - timedelta(hours=x - 1),
                }
                for x in range(3, 0, -1)
            ]
        )

        self.assertEqual(len(attendances), 3)
        self.assertTrue(all(att.check_out > att.check_in for att in attendances))
