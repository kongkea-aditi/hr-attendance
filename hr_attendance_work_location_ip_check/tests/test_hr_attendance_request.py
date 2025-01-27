from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceRequest(CommonAttendanceTest):
    """Test cases for request handling and system integration."""

    def setUp(self):
        """Set up test cases."""
        super().setUp()
        # Ensure employee starts checked out
        if self.employee.attendance_state == "checked_in":
            last_attendance = self.env["hr.attendance"].search(
                [("employee_id", "=", self.employee.id)], order="check_in desc", limit=1
            )
            if last_attendance:
                last_attendance.write(
                    {"check_out": fields.Datetime.now() - timedelta(hours=1)}
                )

    def test_01_request_ip_scenarios(self):
        """Test various IP request scenarios."""
        # Test valid IP
        self.mock_ip.return_value = "192.168.1.100"
        attendance = self._create_test_attendance(check_in="2024-01-01 08:00:00")
        self.assertTrue(attendance.exists())
        attendance.write({"check_out": "2024-01-01 12:00:00"})

        # Test None IP
        self.mock_ip.return_value = None
        with self.assertRaises(ValidationError) as context:
            self._create_test_attendance(check_in="2024-01-01 13:00:00")
        self.assertIn("Unable to determine IP address", str(context.exception))

    def test_02_request_error_handling(self):
        """Test error handling in request processing."""
        # Test error logging in _get_remote_ip
        self.mock_ip.return_value = None
        ip = self.employee._get_remote_ip()
        self.assertIsNone(ip)

        with self.assertRaises(ValidationError) as context:
            self._create_test_attendance(check_in="2024-01-01 08:00:00")
        self.assertIn("Unable to determine IP address", str(context.exception))

    def test_03_multiple_attendance_requests(self):
        """Test handling of multiple attendance requests."""
        self.mock_ip.return_value = "192.168.1.100"

        # First attendance
        attendance1 = self._create_test_attendance(check_in="2024-01-01 08:00:00")
        self.assertTrue(attendance1.exists())
        attendance1.write({"check_out": "2024-01-01 12:00:00"})

        # Second attendance
        attendance2 = self._create_test_attendance(check_in="2024-01-01 13:00:00")
        self.assertTrue(attendance2.exists())
        attendance2.write({"check_out": "2024-01-01 17:00:00"})

        # Verify both attendances
        attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "=", self.employee.id),
                ("check_in", ">=", "2024-01-01 00:00:00"),
                ("check_in", "<=", "2024-01-01 23:59:59"),
            ]
        )
        self.assertEqual(len(attendances), 2)

    def test_04_request_with_different_contexts(self):
        """Test request handling with different contexts."""
        # Test without IP check
        self.work_location.check_ip = False
        attendance1 = self._create_test_attendance(check_in="2024-01-01 08:00:00")
        self.assertTrue(attendance1.exists())
        attendance1.write({"check_out": "2024-01-01 12:00:00"})

        # Re-enable IP check
        self.work_location.check_ip = True

        # Test with bypass for employee
        self.employee.sudo().write({"bypass_ip_check": True})
        attendance2 = self._create_test_attendance(check_in="2024-01-01 13:00:00")
        self.assertTrue(attendance2.exists())
        attendance2.write({"check_out": "2024-01-01 17:00:00"})

    def test_05_request_ip_changes(self):
        """Test handling of changing IP addresses."""
        # Initial check-in with valid IP
        self.mock_ip.return_value = "192.168.1.100"
        attendance = self._create_test_attendance(check_in="2024-01-01 08:00:00")
        self.assertTrue(attendance.exists())

        # Attempt check-out with different IP
        self.mock_ip.return_value = "10.0.0.1"
        with self.assertRaises(ValidationError):
            attendance.write({"check_out": "2024-01-01 12:00:00"})

        # Successful check-out with valid IP
        self.mock_ip.return_value = "192.168.1.100"
        attendance.write({"check_out": "2024-01-01 12:00:00"})
        self.assertEqual(
            attendance.check_out.strftime("%Y-%m-%d %H:%M:%S"), "2024-01-01 12:00:00"
        )

    def test_06_employee_initially_checked_in(self):
        """Test scenario where employee is initially checked in."""
        # Set a valid return value for the mocked _get_remote_ip method
        self.mock_ip.return_value = "192.168.1.100"

        # Create an initial attendance record to simulate checked-in state
        attendance = self._create_test_attendance(
            employee=self.employee, check_in="2024-01-01 08:00:00"
        )

        # Check out the employee
        attendance.write({"check_out": fields.Datetime.now() - timedelta(hours=1)})

        # Assert that the employee is now checked out
        self.assertEqual(self.employee.attendance_state, "checked_out")

    def test_07_initial_checkin_state(self):
        """Test setup with initial checked-in state."""
        self.mock_ip.return_value = "192.168.1.100"
        # Create initial attendance to simulate checked-in state
        initial_attendance = self._create_test_attendance(
            check_in="2024-01-01 08:00:00"
        )
        self.assertEqual(self.employee.attendance_state, "checked_in")
        # Now run a dummy test to invoke the setUp method with an initial checked_in state
        self.assertTrue(initial_attendance.exists())

    def test_08_employee_initial_state_handling(self):
        """Test handling of employee's initial attendance state."""
        # First create a checked-in state
        self.mock_ip.return_value = "192.168.1.100"
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": fields.Datetime.now() - timedelta(hours=2),
            }
        )
        self.assertEqual(self.employee.attendance_state, "checked_in")

        # Then test the checkout process
        attendance.write({"check_out": fields.Datetime.now() - timedelta(hours=1)})
        self.assertEqual(self.employee.attendance_state, "checked_out")
