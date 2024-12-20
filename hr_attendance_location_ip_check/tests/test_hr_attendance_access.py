from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceAccess(CommonAttendanceTest):
    """Test cases for HR Attendance IP Check access rights."""

    def test_01_hr_user_access_rights(self):
        """Test HR User access rights for IP check features"""
        with self.with_user("hr_user@test.com"):
            self.env.clear()

            # Should be able to read work location basic info
            self.assertTrue(self.work_location.name)
            self.assertTrue(self.work_location.address_id)

            # Should not be able to modify IP check settings
            with self.assertRaises(AccessError):
                self.work_location.with_user(self.hr_user).write({"check_ip": False})

            # Should not be able to read CIDR records at all
            with self.assertRaises(AccessError):
                self.env["hr.work.location.cidr"].with_user(self.hr_user).search([])

            # Verify HR user cannot read or write bypass_ip_check
            employee = self.employee.with_user(self.hr_user)
            with self.assertRaises(AccessError):
                employee.read(["bypass_ip_check"])
            with self.assertRaises(AccessError):
                employee.write({"bypass_ip_check": True})

    def test_02_hr_manager_access_rights(self):
        """Test HR Manager access rights for IP check features"""
        with self.with_user("hr_manager@test.com"):
            # Should have full access to IP check settings
            self.work_location.check_ip = False
            self.assertFalse(self.work_location.check_ip)

            # Should be able to create CIDR records
            cidr = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Test Network",
                    "cidr": "172.16.0.0/24",
                }
            )
            self.created_cidrs.append(cidr)
            self.assertTrue(cidr.exists())

            # Should be able to modify bypass_ip_check
            self.employee.write({"bypass_ip_check": True})
            self.assertTrue(self.employee.bypass_ip_check)
