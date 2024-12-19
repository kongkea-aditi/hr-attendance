from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestHrAttendanceIPCheck(TransactionCase):
    """
    Test cases for HR Attendance IP Check module.
    Tests include access rights, CIDR validation, and attendance controls.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create users with different access levels
        cls.group_hr_user = cls.env.ref("hr.group_hr_user")
        cls.group_hr_manager = cls.env.ref("hr.group_hr_manager")
        cls.attendance_user_ref = "hr_attendance.group_hr_attendance_user"
        cls.attendance_manager_ref = "hr_attendance.group_hr_attendance_manager"
        cls.group_attendance_user = cls.env.ref(cls.attendance_user_ref)
        cls.group_attendance_manager = cls.env.ref(cls.attendance_manager_ref)

        # Create test users
        user_vals = {
            "hr_user": {
                "name": "HR User",
                "login": "hr_user@test.com",
                "email": "hr_user@test.com",
                "groups_id": [
                    (6, 0, [cls.group_hr_user.id, cls.group_attendance_user.id])
                ],
            },
            "hr_manager": {
                "name": "HR Manager",
                "login": "hr_manager@test.com",
                "email": "hr_manager@test.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.group_hr_manager.id,
                            cls.group_attendance_manager.id,
                        ],
                    )
                ],
            },
        }

        cls.users = {}
        for user_key, vals in user_vals.items():
            cls.users[user_key] = (
                cls.env["res.users"].with_context(no_reset_password=True).create(vals)
            )

        cls.hr_user = cls.users["hr_user"]
        cls.hr_manager = cls.users["hr_manager"]

        # Create test partner address
        cls.test_partner = cls.env["res.partner"].create(
            {
                "name": "Test Location Address",
                "street": "Test Street",
                "city": "Test City",
            }
        )

        # Create work location first without IP check
        cls.work_location = (
            cls.env["hr.work.location"]
            .sudo()
            .create(
                {
                    "name": "Test Location",
                    "check_ip": False,
                    "address_id": cls.test_partner.id,
                    "company_id": cls.env.company.id,
                }
            )
        )

        # Create initial CIDR
        cls.env["hr.work.location.cidr"].sudo().create(
            {
                "work_location_id": cls.work_location.id,
                "name": "Office Network",
                "cidr": "192.168.1.0/24",
                "sequence": 10,
                "company_id": cls.env.company.id,
            }
        )

        # Enable IP check after CIDR is created
        cls.work_location.sudo().write({"check_ip": True})

        # Create regular employee
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Test Employee",
                "work_location_id": cls.work_location.id,
                "company_id": cls.env.company.id,
                "user_id": cls.hr_user.id,
            }
        )

        # Set up test config parameter
        param = "hr_attendance.ip_check_enabled"
        cls.env["ir.config_parameter"].sudo().set_param(param, "True")

        # Store common patch path
        cls.patch_path = (
            "odoo.addons.hr_attendance_location_ip_check.models.hr_employee"
        )

    def _create_test_attendance(self, employee=None, check_in="2024-01-01 08:00:00"):
        """Helper method to create test attendance"""
        return self.env["hr.attendance"].create(
            {
                "employee_id": employee and employee.id or self.employee.id,
                "check_in": check_in,
            }
        )

    def _patch_ip(self, ip_address):
        """Helper method to create IP address patch"""
        return patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip", return_value=ip_address
        )

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
            self.assertTrue(cidr.exists())

            # Should be able to modify bypass_ip_check
            self.employee.write({"bypass_ip_check": True})
            self.assertTrue(self.employee.bypass_ip_check)

    def test_03_cidr_validation(self):
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
            self.assertTrue(cidr.exists())

    def test_04_attendance_allowed_ip(self):
        """Test attendance creation with allowed IP"""
        with self._patch_ip("192.168.1.100"):
            attendance = self._create_test_attendance()
            self.assertTrue(attendance.exists())

    def test_05_attendance_blocked_ip(self):
        """Test attendance creation with blocked IP"""
        with self._patch_ip("10.0.0.1"):
            with self.assertRaises(ValidationError):
                self._create_test_attendance()

    def test_06_ip_check_disabled(self):
        """Test attendance when IP check is disabled for work location"""
        # Disable IP check with manager rights
        with self.with_user("hr_manager@test.com"):
            self.work_location.check_ip = False

        with self._patch_ip("1.2.3.4"):
            attendance = self._create_test_attendance()
            self.assertTrue(attendance.exists())

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

        # Re-enable IP check with manager rights
        with self.with_user("hr_manager@test.com"):
            self.work_location.check_ip = True

        with self._patch_ip("1.2.3.4"):
            with self.assertRaises(ValidationError):
                self._create_test_attendance()

    def test_07_multiple_cidrs(self):
        """Test with multiple CIDR ranges"""
        with self.with_user("hr_manager@test.com"):
            # Create second CIDR range
            self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Secondary Network",
                    "cidr": "10.0.0.0/8",
                    "sequence": 20,
                }
            )

        # Test IP from first range
        with self._patch_ip("192.168.1.50"):
            attendance = self._create_test_attendance()
            self.assertTrue(attendance.exists())

    def test_08_multi_company(self):
        """Test CIDR restrictions respect company boundaries"""
        company2 = self.env["res.company"].create({"name": "Company 2"})

        # Create location and CIDR with manager rights
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
            self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": location2.id,
                    "name": "Company 2 Network",
                    "cidr": "172.16.0.0/12",
                    "sequence": 10,
                    "company_id": company2.id,
                }
            )

            # Enable IP check
            location2.check_ip = True

        employee2 = self.env["hr.employee"].create(
            {
                "name": "Employee 2",
                "work_location_id": location2.id,
                "company_id": company2.id,
            }
        )

        # Test cross-company IP validation
        with self._patch_ip("172.16.0.100"):
            # Should work for company 2 employee
            attendance = self._create_test_attendance(employee2)
            self.assertTrue(attendance.exists())

            # Should fail for company 1 employee
            with self.assertRaises(ValidationError):
                self._create_test_attendance(self.employee)

    def test_09_inactive_cidr(self):
        """Test IP validation with inactive CIDR"""
        with self.with_user("hr_manager@test.com"):
            # First deactivate the existing CIDR
            cidrs = self.env["hr.work.location.cidr"].search(
                [("work_location_id", "=", self.work_location.id)]
            )
            cidrs.write({"active": False})

            # Should fail with all CIDRs inactive
            with self._patch_ip("192.168.1.100"):
                with self.assertRaises(ValidationError):
                    self._create_test_attendance()

        # Should fail with inactive CIDR
        with self._patch_ip("192.168.1.100"):
            with self.assertRaises(ValidationError):
                self._create_test_attendance()

    def test_10_cidr_sequence(self):
        """Test CIDR sequence priorities"""
        with self.with_user("hr_manager@test.com"):
            self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Specific Network",
                    "cidr": "172.16.0.0/24",
                    "sequence": 5,  # Higher priority than existing
                }
            )

        # Test IP in the more specific range
        with self._patch_ip("172.16.0.50"):
            attendance = self._create_test_attendance()
            self.assertTrue(attendance.exists())

    def test_11_attendance_modification(self):
        """Test IP validation on attendance modification"""
        # Create initial attendance with valid IP
        with self._patch_ip("192.168.1.100"):
            attendance = self._create_test_attendance()

        # Test modification with invalid IP
        with self._patch_ip("10.0.0.1"):
            with self.assertRaises(ValidationError):
                attendance.write(
                    {
                        "check_out": "2024-01-01 17:00:00",
                    }
                )

        # Test modification with valid IP
        with self._patch_ip("192.168.1.100"):
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

    def test_12_ip_edge_cases(self):
        """Test edge cases in IP validation"""
        edge_cases = [
            ("192.168.1.255", True),  # Last IP in range
            ("192.168.2.0", False),  # First IP outside range
            ("invalid_ip", "error"),  # Invalid IP format
            ("", "error"),  # Empty IP
            ("256.256.256.256", "error"),  # Invalid IP values
        ]

        for ip, expected in edge_cases:
            with self._patch_ip(ip):
                if expected == "error":
                    with self.assertRaises(ValidationError):
                        self._create_test_attendance()
                elif expected:
                    attendance = self._create_test_attendance()
                    self.assertTrue(attendance.exists())
                else:
                    with self.assertRaises(ValidationError):
                        self._create_test_attendance()

    def test_13_config_changes(self):
        """Test impact of configuration changes"""
        param = "hr_attendance.ip_check_enabled"
        # Disable IP check globally
        self.env["ir.config_parameter"].sudo().set_param(param, "False")

        with self._patch_ip("1.2.3.4"):
            attendance = self._create_test_attendance()
            self.assertTrue(attendance.exists())

        # Re-enable IP check
        self.env["ir.config_parameter"].sudo().set_param(param, "True")

        with self._patch_ip("1.2.3.4"):
            with self.assertRaises(ValidationError):
                self._create_test_attendance()

    def test_14_bypass_features(self):
        """Test bypass feature functionality"""
        with self.with_user("hr_manager@test.com"):
            # Enable bypass
            self.employee.bypass_ip_check = True

            # Should work with any IP when bypassed
            with self._patch_ip("1.2.3.4"):
                attendance = self._create_test_attendance()
                self.assertTrue(attendance.exists())

    def test_15_multi_user_scenarios(self):
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
            self.assertTrue(cidr.exists())
