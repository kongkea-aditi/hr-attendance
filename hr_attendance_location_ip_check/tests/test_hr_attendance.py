from unittest.mock import patch

from odoo import fields
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
                    (6, 0, [cls.group_hr_manager.id, cls.group_attendance_manager.id])
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

    def setUp(self):
        super().setUp()
        # Setup IP patcher that can be used across all tests
        self.ip_patcher = patch(f"{self.patch_path}.HrEmployee._get_remote_ip")
        self.mock_ip = self.ip_patcher.start()

    def tearDown(self):
        self.ip_patcher.stop()
        super().tearDown()

    def _create_test_attendance(self, employee=None, check_in="2024-01-01 08:00:00"):
        """Helper method to create test attendance"""
        return self.env["hr.attendance"].create(
            {
                "employee_id": employee and employee.id or self.employee.id,
                "check_in": check_in,
            }
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
        """Test attendance with allowed IP using the hook"""
        self.mock_ip.return_value = "192.168.1.100"

        # Test the hook directly first
        self.employee._attendance_action_check("check_in")

        # Then test full attendance flow
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_05_attendance_blocked_ip(self):
        """Test attendance with blocked IP using the hook"""
        self.mock_ip.return_value = "10.0.0.1"

        # Test both hook and full attendance flow
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

        with self.assertRaises(ValidationError):
            self._create_test_attendance()

    def test_06_ip_check_disabled(self):
        """Test attendance when IP check is disabled"""
        with self.with_user("hr_manager@test.com"):
            self.work_location.check_ip = False

        self.mock_ip.return_value = "1.2.3.4"

        # Test the hook
        self.employee._attendance_action_check("check_in")

        # Test full attendance flow
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

        # Test modification
        attendance.write({"check_out": "2024-01-01 17:00:00"})
        self.assertEqual(
            attendance.check_out.strftime("%Y-%m-%d %H:%M:%S"),
            "2024-01-01 17:00:00",
        )

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
        self.mock_ip.return_value = "192.168.1.50"

        # Test hook directly
        self.employee._attendance_action_check("check_in")

        # Test full attendance flow
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
        self.mock_ip.return_value = "172.16.0.100"

        # Test hook directly for both employees
        employee2._attendance_action_check("check_in")
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

        # Test full attendance flow
        attendance = self._create_test_attendance(employee2)
        self.assertTrue(attendance.exists())

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

        self.mock_ip.return_value = "192.168.1.100"

        # Test hook directly
        with self.assertRaises(ValidationError):
            self.employee._attendance_action_check("check_in")

        # Test full attendance flow
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

        self.mock_ip.return_value = "172.16.0.50"

        # Test hook directly
        self.employee._attendance_action_check("check_in")

        # Test full attendance flow
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_11_attendance_modification(self):
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
            self.mock_ip.return_value = ip

            if expected == "error":
                with self.assertRaises(ValidationError):
                    self.employee._attendance_action_check("check_in")
            elif expected:
                self.employee._attendance_action_check("check_in")
                attendance = self._create_test_attendance()
                self.assertTrue(attendance.exists())
            else:
                with self.assertRaises(ValidationError):
                    self.employee._attendance_action_check("check_in")

    def test_13_config_changes(self):
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

    def test_14_bypass_features(self):
        """Test bypass feature functionality"""
        with self.with_user("hr_manager@test.com"):
            # Enable bypass
            self.employee.bypass_ip_check = True

        self.mock_ip.return_value = "1.2.3.4"

        # Test hook directly
        self.employee._attendance_action_check("check_in")

        # Test full attendance flow
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

    def test_16_hook_inheritance(self):
        """Test that the attendance action check hook works properly with inheritance"""
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

    def test_17_attendance_create_edge_cases(self):
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

    def test_18_employee_remote_ip_error(self):
        """Test error handling in remote IP retrieval."""
        # Configure the mock to return None
        self.mock_ip.return_value = None

        # Assert that _get_remote_ip returns None
        self.assertIsNone(self.employee._get_remote_ip())

        # Test that _attendance_action_check raises ValidationError when IP is None
        with self.assertRaises(ValidationError) as context:
            self.employee._attendance_action_check("check_in")

        self.assertIn(
            "Unable to determine IP address for check_in operation",
            str(context.exception),
        )

    def test_19_employee_fields_access(self):
        """Test field access rights for regular HR user."""
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

        with self.with_user(test_user.login):
            fields_data = self.employee.fields_get(["bypass_ip_check"])
            self.assertTrue(fields_data["bypass_ip_check"]["readonly"])

    def test_20_work_location_constraints(self):
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

        # Attempt to enable IP check without any active CIDRs
        with self.assertRaises(ValidationError) as context:
            location.sudo().write({"check_ip": True})

        # Verify that the correct error message is raised
        self.assertIn(
            "IP check enabled locations must have at least one active CIDR range.",
            str(context.exception),
        )

        # Reactivate all CIDRs and enable IP check
        cidrs.write({"active": True})
        location.sudo().write({"check_ip": True})
        self.env.invalidate_all()  # Refresh the environment to recognize changes
        self.assertTrue(location.check_ip)

    def test_21_employee_bypass_write_access(self):
        """Test bypass IP check write access restrictions."""
        test_user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Regular Employee 2",
                    "login": "regular.employee2@test.com",
                    "email": "regular.employee2@test.com",
                    "groups_id": [(6, 0, [self.group_hr_user.id])],
                }
            )
        )

        employee = self.employee.with_user(test_user)
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            employee.write({"bypass_ip_check": True})

    def test_22_cidr_validation_errors(self):
        """Test CIDR format validation."""
        with self.assertRaises(ValidationError), self.with_user("hr_manager@test.com"):
            self.env["hr.work.location.cidr"].create(
                {
                    "work_location_id": self.work_location.id,
                    "name": "Invalid Network",
                    "cidr": "256.256.256.256/24",
                }
            )

    def test_23_employee_ip_validation(self):
        """Test IP validation edge cases."""
        with patch("ipaddress.ip_address", side_effect=ValueError("Invalid IP")):
            with self.assertRaises(ValidationError):
                self.employee._is_ip_allowed("192.168.1.1")
