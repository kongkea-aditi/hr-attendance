from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceConfig(CommonAttendanceTest):
    """Test cases for attendance configuration settings."""

    def test_01_ip_check_disabled(self):
        """Test attendance when IP check is disabled"""
        with self.with_user("hr_manager@test.com"):
            self.work_location.check_ip = False
            self.assertFalse(self.work_location.check_ip)

        self.mock_ip.return_value = "1.2.3.4"
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

        attendance.write({"check_out": "2024-01-01 17:00:00"})
        self.assertEqual(
            attendance.check_out.strftime("%Y-%m-%d %H:%M:%S"),
            "2024-01-01 17:00:00",
        )

    def test_02_config_changes(self):
        """Test impact of configuration changes"""
        param = "hr_attendance.ip_check_enabled"
        # Disable IP check globally
        self.env["ir.config_parameter"].sudo().set_param(param, "False")

        self.mock_ip.return_value = "1.2.3.4"
        # Should work when disabled
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

        # Re-enable IP check
        self.env["ir.config_parameter"].sudo().set_param(param, "True")

        # Should fail when re-enabled
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")
        with self.assertRaises(ValidationError):
            self._create_test_attendance()

    def test_03_work_location_constraints(self):
        """Test work location CIDR constraints."""
        location = self.work_location

        # Deactivate all existing CIDRs for the work location
        cidrs = (
            self.env["hr.work.location.cidr"]
            .sudo()
            .search([("work_location_id", "=", location.id)])
        )
        cidrs.write({"active": False})

        # Set check_ip to False to allow changes without constraints
        location.sudo().write({"check_ip": False})
        self.assertFalse(self.work_location.check_ip)

        # Attempt to enable IP check without any active CIDRs
        with self.assertRaises(ValidationError) as context:
            location.sudo().write({"check_ip": True})

        self.assertIn(
            "IP check enabled locations must have at least one active CIDR range.",
            str(context.exception),
        )

        # Reactivate all CIDRs and enable IP check
        cidrs.write({"active": True})
        location.sudo().write({"check_ip": True})
        self.env.invalidate_all()  # Refresh the environment
        self.assertTrue(location.check_ip)

    def test_04_work_location_ip_check_disabled(self):
        """Test behavior when IP check is disabled at work location level."""
        with self.with_user("hr_manager@test.com"):
            self.work_location.check_ip = False
            self.assertFalse(self.work_location.check_ip)
        self.mock_ip.return_value = "5.5.5.5"
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_05_no_work_location(self):
        """Test scenario where employee has no work location."""
        self.employee.work_location_id = False
        self.mock_ip.return_value = "5.5.5.5"
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_06_global_ip_check(self):
        """Test global IP check configuration."""
        # Test when disabled globally
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_attendance.ip_check_enabled", "False"
        )
        result = self.employee._get_ip_check_enabled()
        self.assertFalse(result)

        # Test when enabled globally
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_attendance.ip_check_enabled", "True"
        )
        result = self.employee._get_ip_check_enabled()
        self.assertTrue(result)

    def test_07_location_cidr_constraints(self):
        """Test work location CIDR constraints and validation."""
        location = self.work_location

        # Create a new CIDR first before deactivating others
        new_cidr = self.env["hr.work.location.cidr"].create(
            {
                "work_location_id": location.id,
                "name": "Test CIDR",
                "cidr": "10.0.0.0/24",
                "active": True,
            }
        )
        self.created_cidrs.append(new_cidr)

        # Now deactivate all CIDRs
        location.allowed_cidr_ids.write({"active": False})

        # Try to enable IP check without active CIDRs
        with self.assertRaises(ValidationError) as context:
            location.write({"check_ip": True})
        self.assertIn(
            "must have at least one active CIDR range", str(context.exception)
        )

        # Reactivate one CIDR and verify IP check can be enabled
        new_cidr.write({"active": True})
        location.write({"check_ip": True})
        self.assertTrue(location.check_ip)

    def test_08_ip_allowed_validation(self):
        """Test IP validation for work locations."""
        location = self.work_location

        # Test with valid IP
        self.assertTrue(
            location.check_ip_allowed("192.168.1.100"), "Should allow IP in CIDR range"
        )

        # Test with invalid IP
        self.assertFalse(
            location.check_ip_allowed("10.0.0.1"),
            "Should not allow IP outside CIDR range",
        )

        # Test with invalid IP format
        self.assertFalse(
            location.check_ip_allowed("invalid_ip"), "Should handle invalid IP format"
        )

    def test_09_ip_check_required_global_disabled(self):
        """Test _is_ip_check_required when global IP check is off."""
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_attendance.ip_check_enabled", "False"
        )
        self.assertFalse(self.employee._is_ip_check_required())

    def test_10_work_location_ip_check(self):
        """Test work location IP check with various scenarios."""
        # Deactivate existing CIDRs first
        existing_cidrs = self.work_location.allowed_cidr_ids
        existing_cidrs.write({"active": False})

        # Create new CIDR with different range
        cidr = (
            self.env["hr.work.location.cidr"]
            .sudo()
            .create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Test CIDR",
                    "cidr": "10.0.0.0/24",  # Different range to avoid overlap
                    "active": True,
                }
            )
        )
        self.created_cidrs.append(cidr)

        # Test with active CIDR
        self.assertTrue(self.work_location.check_ip_allowed("10.0.0.100"))

        # Test with no active CIDRs
        cidr.write({"active": False})
        self.assertFalse(self.work_location.check_ip_allowed("10.0.0.100"))

        # Test with invalid IP
        self.assertFalse(self.work_location.check_ip_allowed("invalid_ip"))

        # Reactivate CIDR and test again
        cidr.write({"active": True})
        self.assertTrue(self.work_location.check_ip_allowed("10.0.0.100"))

    def test_11_work_location_ip_disabled(self):
        """Test check_ip_allowed method when check_ip is False"""
        work_location = self.env["hr.work.location"].create(
            {
                "name": "Test Location no IP Check",
                "address_id": self.test_partner.id,
                "check_ip": False,
            }
        )
        self.assertTrue(work_location.check_ip_allowed("192.168.1.100"))