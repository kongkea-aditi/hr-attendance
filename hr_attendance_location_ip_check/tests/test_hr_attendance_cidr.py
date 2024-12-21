import logging
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestHrAttendanceCIDR(CommonAttendanceTest):
    """Test cases for CIDR validation and management."""

    def test_01_cidr_validation(self):
        """Test CIDR format validation"""
        with self.with_user("hr_manager@test.com"):
            # Invalid CIDR should raise ValidationError
            with self.assertRaises(ValidationError):
                self.env["hr.work.location.cidr"].create(
                    {
                        "work_location_id": self.work_location.id,
                        "name": "Invalid CIDR",
                        "cidr": "invalid_cidr",
                    }
                )

            # Valid CIDR should work
            cidr = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Primary Network",
                    "cidr": "10.0.0.0/8",
                    "sequence": 20,
                }
            )
            self.created_cidrs.append(cidr)
            self.assertTrue(cidr.exists())

    def test_02_multiple_cidrs(self):
        """Test with multiple CIDR ranges"""
        with self.with_user("hr_manager@test.com"):
            # Create second CIDR range
            cidr = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Secondary Network",
                    "cidr": "10.0.0.0/8",
                    "sequence": 20,
                }
            )
            self.created_cidrs.append(cidr)

        # Test IP from first range
        self.mock_ip.return_value = "192.168.1.50"
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_03_multi_company_cidrs(self):
        """Test CIDR restrictions respect company boundaries"""
        company2 = self.env["res.company"].create({"name": "Company 2"})

        with self.with_user("hr_manager@test.com"):
            # Switch to Company 2 context
            self.env.user.company_ids = [(4, company2.id)]
            self.env.user.company_id = company2.id

            # Create location without IP check
            location2 = self.env["hr.work.location"].create(
                {
                    "name": "Location 2",
                    "check_ip": False,
                    "company_id": company2.id,
                    "address_id": self.test_partner.id,
                }
            )

            # Create CIDR
            cidr = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": location2.id,
                    "name": "Company 2 Network",
                    "cidr": "172.16.0.0/12",
                    "sequence": 10,
                    "company_id": company2.id,
                }
            )
            self.created_cidrs.append(cidr)
            location2.check_ip = True

        employee2 = self.env["hr.employee"].create(
            {
                "name": "Employee 2",
                "work_location_id": location2.id,
                "company_id": company2.id,
            }
        )

        self.mock_ip.return_value = "172.16.0.100"
        employee2._attendance_action_check("check_in")
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

    def test_04_inactive_cidr(self):
        """Test IP validation with inactive CIDR"""
        with self.with_user("hr_manager@test.com"):
            cidrs = self.env["hr.work.location.cidr"].search(
                [("work_location_id", "=", self.work_location.id)]
            )
            cidrs.write({"active": False})

        self.mock_ip.return_value = "192.168.1.100"
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

    def test_05_cidr_sequence(self):
        """Test CIDR sequence priorities"""
        with self.with_user("hr_manager@test.com"):
            cidr = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Specific Network",
                    "cidr": "172.16.0.0/24",
                    "sequence": 5,  # Higher priority than existing
                }
            )
            self.created_cidrs.append(cidr)

        self.mock_ip.return_value = "172.16.0.50"
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_06_overlapping_cidrs(self):
        """Test handling of overlapping CIDRs."""
        with self.with_user("hr_manager@test.com"):
            with self.assertRaises(ValidationError) as context:
                self.env["hr.work.location.cidr"].create(
                    {
                        "work_location_id": self.work_location.id,
                        "name": "Overlapping Network",
                        "cidr": "192.168.1.128/25",  # Overlaps with 192.168.1.0/24
                        "sequence": 30,
                        "active": True,
                    }
                )
            self.assertIn("overlaps with existing", str(context.exception))

    def test_07_cidr_cleanup(self):
        """Test CIDR cleanup handling."""
        with self.with_user("hr_manager@test.com"):
            cidrs = []
            for i in range(1, 4):
                cidr = self.env["hr.work.location.cidr"].create(
                    {
                        "work_location_id": self.work_location.id,
                        "name": f"Test CIDR {i}",
                        "cidr": f"172.16.{i}.0/24",
                        "sequence": i,
                    }
                )
                cidrs.append(cidr)
                self.created_cidrs.append(cidr)

            self.assertEqual(len(cidrs), 3)
            cidrs[0].unlink()
            self.assertFalse(cidrs[0].exists())
            self.assertTrue(cidrs[1].exists())

    def test_08_is_ip_allowed_no_active_cidrs(self):
        """Test that ValidationError is raised when no active CIDRs are found."""
        self.work_location.allowed_cidr_ids.write({"active": False})
        with self.assertRaises(ValidationError) as context:
            self.employee._is_ip_allowed("192.168.1.100")
        self.assertIn(
            "No active CIDR ranges defined for location", str(context.exception)
        )

    def test_09_cidr_cleanup_error(self):
        """Test error handling during CIDR cleanup."""
        with patch.object(_logger, "exception") as mock_logger, patch(
            "odoo.models.Model.exists", return_value=True
        ), patch("odoo.models.Model.sudo") as mock_sudo:
            mock_unlink = mock_sudo.return_value.unlink
            mock_unlink.side_effect = Exception("Mock unlink error")

            # Trigger tearDown logic
            self.cidrs = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Test CIDR",
                    "cidr": "192.168.100.0/24",
                    "sequence": 30,
                    "company_id": self.env.company.id,
                }
            )
            self.created_cidrs.append(self.cidrs)

            # Call tearDown to trigger the cleanup logic
            self.tearDown()

            # Assert that the logger.exception method was called
            mock_logger.assert_called_once()

    def tearDown(self):
        """Tear down test cases."""
        # Clean up created CIDR records
        for cidr in self.created_cidrs:
            if cidr.exists():
                try:
                    cidr.sudo().unlink()
                except Exception as e:
                    _logger.exception(
                        "Unexpected error during cleanup of CIDR %s: %s", cidr.id, e
                    )
        super().tearDown()
