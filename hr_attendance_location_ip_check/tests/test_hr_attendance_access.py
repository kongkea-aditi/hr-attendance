from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceAccess(CommonAttendanceTest):
    """Test cases for HR Attendance IP Check access rights."""

    def test_01_hr_user_access_rights(self):
        """Test HR User access rights for IP check features"""
        with self.with_user("hr_user@test.com"):
            # Clear any potential access caches
            self.env.clear()

            # Should be able to read work location basic info
            self.assertTrue(self.work_location.name)
            self.assertTrue(self.work_location.address_id)

            # Should not be able to modify IP check settings
            with self.assertRaises(AccessError):
                (self.work_location.with_user(self.hr_user).write({"check_ip": False}))

            # Should not be able to read CIDR records at all
            with self.assertRaises(AccessError):
                (self.env["hr.work.location.cidr"].with_user(self.hr_user).search([]))

            # Should be able to read but not modify bypass_ip_check
            self.assertIsNotNone(self.employee.bypass_ip_check)

            # Should not be able to modify bypass_ip_check
            with self.assertRaises(AccessError):
                (self.employee.with_user(self.hr_user).write({"bypass_ip_check": True}))

    def test_02_hr_manager_access_rights(self):
        """Test HR Manager access rights for IP check features"""
        with self.with_user("hr_manager@test.com"):
            # Should have full access to IP check settings
            self.work_location.check_ip = False
            self.assertFalse(self.work_location.check_ip)

            # Should be able to create and modify CIDR records
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

    def test_03_employee_bypass_write_access(self):
        """Test bypass IP check write access restrictions."""
        test_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Regular Employee",
                    "login": "regular.employee@test.com",
                    "email": "regular.employee@test.com",
                    "groups_id": [(6, 0, [self.group_hr_user.id])],
                }
            )
        )

        employee = self.employee.with_user(test_user)
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            employee.write({"bypass_ip_check": True})

        with self.with_user("hr_manager@test.com"):
            self.assertTrue(self.employee.write({"name": "Updated Employee Name"}))

    def test_04_fields_get_return(self):
        """Test the return value of fields_get and write permissions."""
        test_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Regular Employee",
                    "login": "regular.employee@test.com",
                    "email": "regular.employee@test.com",
                    "groups_id": [(6, 0, [self.group_hr_user.id])],
                }
            )
        )

        # Regular user - should see readonly field and not be able to write
        with self.with_user(test_user.login):
            fields_data = self.employee.fields_get(["bypass_ip_check"])
            self.assertTrue(fields_data["bypass_ip_check"]["readonly"])
            with self.assertRaises(AccessError):
                self.employee.with_user(test_user).write({"bypass_ip_check": True})

        # HR manager - should see readonly field but able to write
        with self.with_user("hr_manager@test.com"):
            fields_data = self.employee.fields_get(["bypass_ip_check"])
            self.assertTrue(fields_data["bypass_ip_check"]["readonly"])
            # Should be able to write despite readonly UI
            self.employee.write({"bypass_ip_check": True})

    def test_05_multi_user_scenarios(self):
        """Test various user scenarios"""
        with self.with_user("hr_user@test.com"), self.assertRaises(AccessError):
            self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "HR User Network",
                    "cidr": "192.168.2.0/24",
                }
            )

        with self.with_user("hr_manager@test.com"):
            cidr = self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "HR Manager Network",
                    "cidr": "192.168.2.0/24",
                }
            )
            self.created_cidrs.append(cidr)
            self.assertTrue(cidr.exists())

    def test_06_employee_field_access_details(self):
        """Test detailed field access controls and restrictions."""
        # Test fields_get with different permissions (covers lines 119-123)
        # As regular user
        with self.with_user("hr_user@test.com"):
            fields_data = self.employee.fields_get(["bypass_ip_check"])
            self.assertTrue(
                fields_data["bypass_ip_check"]["readonly"],
                "Bypass IP check should be readonly for HR user",
            )

        # As HR manager
        with self.with_user("hr_manager@test.com"):
            fields_data = self.employee.fields_get(["bypass_ip_check"])
            self.assertIn(
                "bypass_ip_check",
                fields_data,
                "HR manager should see bypass_ip_check field",
            )

    def test_07_employee_write_restrictions(self):
        """Test write access restrictions for employee fields."""
        test_user = self.env["res.users"].create(
            {
                "name": "Test Regular User",
                "login": "test.regular@test.com",
                "email": "test.regular@test.com",
                "groups_id": [(6, 0, [self.group_hr_user.id])],
            }
        )

        with self.assertRaises(AccessError):
            self.employee.with_user(test_user).write({"bypass_ip_check": True})
