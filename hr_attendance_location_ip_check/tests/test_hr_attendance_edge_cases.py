from odoo import fields
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceEdgeCases(CommonAttendanceTest):
    """Test cases for edge cases and error scenarios."""

    def setUp(self):
        super().setUp()
        # Create a test partner for address requirement
        self.test_partner2 = self.env["res.partner"].create(
            {
                "name": "Test Location Address 2",
                "street": "Test Street 2",
                "city": "Test City 2",
            }
        )

    def test_01_attendance_create_error_handling(self):
        """Test error handling in attendance creation."""
        # Test with invalid check_in format
        with self.assertRaises(UserError):
            self.env["hr.attendance"].create(
                {"employee_id": self.employee.id, "check_in": "not-a-date"}
            )

        # Test with non-existent employee - should raise UserError
        max_id = self.env["hr.employee"].search([], order="id desc", limit=1).id
        with self.assertRaises(UserError):
            self.env["hr.attendance"].with_context(no_check_access=True).create(
                {"employee_id": max_id + 1, "check_in": "2024-01-01 08:00:00"}
            )

    def test_02_employee_ip_validation_errors(self):
        """Test IP validation error scenarios."""
        # Test with None IP
        self.mock_ip.return_value = None
        with self.assertRaises(ValidationError) as context:
            self.employee._attendance_action_check("check_in")
        self.assertIn("Unable to determine IP", str(context.exception))

        # Test with empty IP
        self.mock_ip.return_value = ""
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

    def test_03_work_location_ip_validation(self):
        """Test work location IP validation edge cases."""
        # Test with no active CIDRs
        self.work_location.allowed_cidr_ids.write({"active": False})
        self.assertFalse(self.work_location.check_ip_allowed("192.168.1.100"))

        # Test with invalid IP format
        self.assertFalse(self.work_location.check_ip_allowed("invalid_ip"))

        # Test with empty IP
        self.assertFalse(self.work_location.check_ip_allowed(""))

    def test_04_cidr_range_validation(self):
        """Test CIDR range validation edge cases."""
        # Create work location with a different CIDR range
        work_location2 = self.env["hr.work.location"].create(
            {
                "name": "Test Location 2",
                "address_id": self.test_partner2.id,
                "check_ip": False,
            }
        )

        cidr = self.env["hr.work.location.cidr"].create(
            {
                "work_location_id": work_location2.id,
                "name": "Test Network",
                "cidr": "10.0.0.0/24",  # Different range to avoid overlap
            }
        )
        self.created_cidrs.append(cidr)

        # Test IP validations
        self.assertFalse(cidr.with_context(test_mode=True).ip_in_range("invalid_ip"))
        self.assertFalse(cidr.with_context(test_mode=True).ip_in_range(""))
        self.assertFalse(cidr.with_context(test_mode=True).ip_in_range("192.168.1.1"))
        self.assertTrue(cidr.ip_in_range("10.0.0.1"))

    def test_05_attendance_write_error_handling(self):
        """Test error handling in attendance write operations."""
        from datetime import datetime, timedelta

        from pytz import UTC

        self.mock_ip.return_value = "192.168.1.100"

        # Create a base attendance
        base_time = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": base_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        # Test invalid checkout time (before check-in)
        before_checkin = (base_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaises(ValidationError):
            attendance.write({"check_out": before_checkin})

        # Test valid checkout time
        valid_checkout = (base_time + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        attendance.write({"check_out": valid_checkout})
        self.assertEqual(
            attendance.check_out.strftime("%Y-%m-%d %H:%M:%S"), valid_checkout
        )

    def test_06_work_location_constraints(self):
        """Test work location constraints and validation."""
        work_location = self.env["hr.work.location"].create(
            {
                "name": "Test Location 2",
                "address_id": self.test_partner2.id,
                "check_ip": False,
            }
        )

        # Try to enable IP check without CIDRs
        with self.assertRaises(ValidationError):
            work_location.write({"check_ip": True})

        # Add inactive CIDR
        cidr = self.env["hr.work.location.cidr"].create(
            {
                "work_location_id": work_location.id,
                "name": "Test Network",
                "cidr": "172.16.0.0/24",
                "active": False,
            }
        )
        self.created_cidrs.append(cidr)

        # Should still fail with inactive CIDR
        with self.assertRaises(ValidationError):
            work_location.write({"check_ip": True})

    def test_07_cidr_validation_edge_cases(self):
        """Test CIDR validation edge cases."""
        invalid_cidrs = [
            "256.256.256.256/24",  # Invalid IP
            "192.168.1.0/33",  # Invalid prefix
            "192.168.1/24",  # Incomplete IP
            "invalid/24",  # Invalid format
            "",  # Empty string
        ]

        for invalid_cidr in invalid_cidrs:
            with self.assertRaises(ValidationError):
                self.env["hr.work.location.cidr"].create(
                    {
                        "work_location_id": self.work_location.id,
                        "name": "Test Network",
                        "cidr": invalid_cidr,
                    }
                )

    def test_08_ip_check_bypass(self):
        """Test IP check bypass functionality."""
        # First ensure IP check is enabled
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_attendance.ip_check_enabled", "True"
        )

        # Enable bypass for employee using HR manager
        self.env.user.groups_id = [(4, self.group_hr_manager.id)]
        self.employee.sudo().write({"bypass_ip_check": True})

        # Should work with any IP when bypassed
        self.mock_ip.return_value = "1.1.1.1"
        self.employee._attendance_action_check("check_in")

        # Disable bypass
        self.employee.sudo().write({"bypass_ip_check": False})

        # Should fail with invalid IP
        self.mock_ip.return_value = "1.1.1.1"
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

    def test_09_attendance_creation_edge_cases(self):
        """Test edge cases in attendance creation process."""
        # Test empty vals_list
        result = self.env["hr.attendance"].create([])
        self.assertEqual(len(result), 0)

        # Get a valid test employee
        test_employee = self.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "work_location_id": self.work_location.id,  # Important: Use existing location
            }
        )

        # Set valid IP for attendance creation
        self.mock_ip.return_value = "192.168.1.100"  # Valid IP from CIDR range

        # Test valid attendance creation first (baseline)
        attendance = self.env["hr.attendance"].create(
            [{"employee_id": test_employee.id, "check_in": fields.Datetime.now()}]
        )
        self.assertTrue(attendance.exists())

        # Now test max ID scenario (non-existent employee)
        max_id = self.env["hr.employee"].search([], order="id desc", limit=1).id
        with self.assertRaises(MissingError):
            self.env["hr.attendance"].create(
                [
                    {
                        "employee_id": max_id + 999,  # Non-existent ID
                        "check_in": fields.Datetime.now(),
                    }
                ]
            )

        # Cleanup
        attendance.unlink()
        test_employee.unlink()
