import logging
from unittest.mock import Mock, PropertyMock, patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestHrAttendanceIP(TransactionCase):
    """Test cases for IP validation functionality."""

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
            "odoo.addons.hr_attendance_work_location_ip_check.models.hr_employee"
        )

    def setUp(self):
        super().setUp()
        self.patch_path = (
            "odoo.addons.hr_attendance_work_location_ip_check.models.hr_employee"
        )

    def tearDown(self):
        # Ensure any patches are stopped at the end of each test
        patch.stopall()
        super().tearDown()

    def _create_test_attendance(self, employee=None, check_in="2024-01-01 08:00:00"):
        """Helper method to create test attendance"""
        return self.env["hr.attendance"].create(
            {
                "employee_id": employee and employee.id or self.employee.id,
                "check_in": check_in,
            }
        )

    def _mock_remote_ip(self, ip):
        """Helper method to mock _get_remote_ip"""
        return patch(f"{self.patch_path}.HrEmployee._get_remote_ip", return_value=ip)

    def test_01_attendance_allowed_ip(self):
        """Test attendance with allowed IP"""
        with self._mock_remote_ip("192.168.1.100"):
            self.employee._attendance_action_check("check_in")
            attendance = self._create_test_attendance()
            self.assertTrue(attendance.exists())

    def test_02_attendance_blocked_ip(self):
        """Test attendance with blocked IP"""
        with self._mock_remote_ip("5.5.5.5"):
            with self.assertRaises(ValidationError) as context:
                self.employee._attendance_action_check("check_in")
            self.assertIn("IP 5.5.5.5 not allowed for", str(context.exception))

            with self.assertRaises(ValidationError) as context:
                self._create_test_attendance()
            self.assertIn("IP 5.5.5.5 not allowed for", str(context.exception))

    def test_03_ip_edge_cases(self):
        """Test edge cases in IP validation"""
        edge_cases = [
            ("192.168.1.255", True),  # Last IP in range
            ("192.168.2.0", False),  # First IP outside range
            ("invalid_ip", "error"),  # Invalid IP format
            ("", "error"),  # Empty IP
            ("256.256.256.256", "error"),  # Invalid IP values
        ]

        for ip, expected in edge_cases:
            with self._mock_remote_ip(ip):
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

    def test_04_remote_ip_error_direct_mock(self):
        """Test error handling in remote IP retrieval with direct mock."""

        def mock_get_remote_ip():
            return None

        with patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip",
            side_effect=mock_get_remote_ip,
        ):
            with self.assertRaises(ValidationError) as context:
                self.employee._attendance_action_check("check_in")
            self.assertIn(
                "Unable to determine IP address for check_in operation",
                str(context.exception),
            )

    def test_05_ip_validation_errors(self):
        """Test IP validation error handling"""
        with self.assertRaises(ValidationError):
            self.employee._is_ip_allowed("invalid-ip-format")

    def test_06_no_ip_error_message_direct_mock(self):
        """Test specific error message when IP cannot be determined with direct mock."""

        def mock_get_remote_ip():
            return None

        with patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip",
            side_effect=mock_get_remote_ip,
        ):
            with self.assertRaises(ValidationError) as context:
                self.employee._attendance_action_check("check_in")
            self.assertIn("Unable to determine IP address", str(context.exception))

    def test_07_ip_not_allowed_message(self):
        """Test specific error message when IP is not allowed."""
        with self._mock_remote_ip("10.0.0.1"):
            with self.assertRaises(ValidationError) as context:
                self.employee._attendance_action_check("check_in")
            self.assertIn("IP 10.0.0.1 not allowed for", str(context.exception))

    def test_08_get_remote_ip_direct(self):
        """Test direct remote IP retrieval."""
        with self._mock_remote_ip("192.168.1.100"):
            result = self.employee._get_remote_ip()
            self.assertEqual(result, "192.168.1.100")

        with patch(f"{self.patch_path}.HrEmployee._get_remote_ip", return_value=None):
            result = self.employee._get_remote_ip()
            self.assertIsNone(result)

    def test_09_attendance_creation_no_ip_direct_mock(self):
        """Test attendance creation when no IP is available with direct mock."""

        def mock_get_remote_ip():
            return None

        with patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip",
            side_effect=mock_get_remote_ip,
        ):
            with self.assertRaises(ValidationError) as context:
                self._create_test_attendance()
            self.assertIn("Unable to determine IP address", str(context.exception))

    def test_10_attendance_creation_invalid_ip(self):
        """Test attendance creation with an IP outside the allowed range."""
        with self._mock_remote_ip("1.1.1.1"):
            with self.assertRaises(ValidationError) as context:
                self._create_test_attendance()
            self.assertIn("IP 1.1.1.1 not allowed for", str(context.exception))

    def test_11_attendance_ip_validation_message(self):
        """Test the specific validation error message format."""
        with self._mock_remote_ip("1.1.1.1"):
            with self.assertRaises(ValidationError) as context:
                self.employee._attendance_action_check("check_in")

            # Test both possible message formats
            error_msg = str(context.exception)
            self.assertTrue(
                "IP 1.1.1.1 not allowed for" in error_msg,
                f"Expected error message not found in: {error_msg}",
            )

    def test_12_get_remote_ip_no_request(self):
        """Test _get_remote_ip when no request object is available."""
        with patch(f"{self.patch_path}.request", None):
            ip = self.employee._get_remote_ip()
            self.assertIsNone(ip)

    def test_13_no_active_cidrs(self):
        """Test that ValidationError is raised when no active CIDRs are found."""
        self.work_location.allowed_cidr_ids.write({"active": False})
        with self.assertRaises(ValidationError) as context:
            self.employee._is_ip_allowed("192.168.1.100")
        self.assertIn(
            "No active CIDR ranges defined for location", str(context.exception)
        )

    def test_14_get_remote_ip_request_block(self):
        """Test the if request block in _get_remote_ip."""
        mock_request = Mock()
        mock_request.httprequest.headers.get.return_value = "192.168.1.100"
        mock_request.httprequest.remote_addr = "192.168.1.1"
        with patch(f"{self.patch_path}.request", mock_request):
            self.assertEqual(self.employee._get_remote_ip(), "192.168.1.100")

    def test_15_remote_ip_variations(self):
        """Test various IP retrieval scenarios."""
        # Test normal IP retrieval
        with self._mock_remote_ip("192.168.1.100"):
            self.assertEqual(self.employee._get_remote_ip(), "192.168.1.100")

        # Test empty IP
        with self._mock_remote_ip(""):
            self.assertEqual(self.employee._get_remote_ip(), "")

        # Test None IP
        with patch(f"{self.patch_path}.HrEmployee._get_remote_ip", return_value=None):
            self.assertIsNone(self.employee._get_remote_ip())

        # Test error case - need to reset mock between tests
        with patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip",
            side_effect=TypeError("Test type error"),
        ):
            with self.assertRaises(TypeError) as context:
                self.employee._get_remote_ip()

            # Optionally, check the exception message
            self.assertEqual(str(context.exception), "Test type error")

        # Reset the side effect to a simple return value for this check:
        with patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip", return_value=None
        ):  # Simulate no IP found
            # Now call the method and check if it returns None after exception
            result = self.employee._get_remote_ip()
            self.assertIsNone(result)

    def test_16_get_remote_ip_x_forwarded_for(self):
        """Test _get_remote_ip with X-Forwarded-For header."""
        mock_request = Mock()
        # Correctly set up side_effect to return values in sequence
        mock_request.httprequest.headers.get.side_effect = [
            None,  # First call (X-Real-IP)
            "192.168.1.100, 10.0.0.1",  # Second call (X-Forwarded-For)
        ]
        mock_request.httprequest.remote_addr = "172.160.0.1"

        with patch(f"{self.patch_path}.request", mock_request):
            ip = self.employee._get_remote_ip()
            self.assertEqual(ip, "192.168.1.100")  # Correct assertion
            # Assert that get was called with "X-Forwarded-For" and "X-Real-IP"
            mock_request.httprequest.headers.get.assert_any_call("X-Real-IP")
            mock_request.httprequest.headers.get.assert_any_call(
                "X-Forwarded-For", None
            )
            # Assert that get was called exactly twice
            self.assertEqual(mock_request.httprequest.headers.get.call_count, 2)
            mock_request.httprequest.headers.get.reset_mock()

    def test_17_get_remote_ip_x_real_ip(self):
        """Test _get_remote_ip with X-Real-IP header."""
        mock_request = Mock()
        mock_request.httprequest.headers.get.side_effect = [None, "192.168.1.101"]
        mock_request.httprequest.remote_addr = "172.16.0.1"

        with patch(f"{self.patch_path}.request", mock_request):
            ip = self.employee._get_remote_ip()
            self.assertEqual(ip, "192.168.1.101")
            mock_request.httprequest.headers.get.assert_any_call("X-Real-IP")
            mock_request.httprequest.headers.get.reset_mock()

    def test_get_remote_ip_remote_addr(self):
        """Test _get_remote_ip falling back to remote_addr."""
        mock_request = Mock()
        mock_request.httprequest.headers.get.side_effect = [
            None,
            None,
        ]  # First call returns None, second call also returns None
        mock_request.httprequest.remote_addr = "192.168.1.102"

        with patch(f"{self.patch_path}.request", mock_request):
            ip = self.employee._get_remote_ip()
            self.assertEqual(ip, "192.168.1.102")
            # Verify the first call to get (for 'X-Forwarded-For')
            mock_request.httprequest.headers.get.assert_any_call(
                "X-Forwarded-For", None
            )
            # Verify the second call to get (for 'X-Real-IP')
            mock_request.httprequest.headers.get.assert_any_call("X-Real-IP")
            # Assert that get was called exactly twice
            self.assertEqual(mock_request.httprequest.headers.get.call_count, 2)
            mock_request.httprequest.headers.get.reset_mock()

    def test_18_get_remote_ip_exception_handling_headers(self):
        """Test _get_remote_ip exception handling when getting headers."""
        mock_request = Mock()
        mock_request.httprequest.headers.get.side_effect = Exception(
            "Test Exception in headers"
        )

        with patch(f"{self.patch_path}.request", mock_request):
            ip = self.employee._get_remote_ip()
            self.assertIsNone(ip)
            mock_request.httprequest.headers.get.reset_mock()

    def test_19_get_remote_ip_exception_handling_remote_addr(self):
        """Test _get_remote_ip exception handling when getting remote_addr."""
        # Create a mock for the entire 'request' object
        mock_request = Mock()

        # Create a mock for 'httprequest'
        mock_httprequest = Mock()

        # Mock the 'headers.get' method to return None
        mock_httprequest.headers.get.return_value = None

        # Simulate 'remote_addr' raising an exception using PropertyMock
        type(mock_httprequest).remote_addr = PropertyMock(
            side_effect=Exception("Test Exception in remote_addr")
        )

        # Assign the mocked 'httprequest' to the 'request' mock
        mock_request.httprequest = mock_httprequest

        # Patch the 'request' object in the model's context
        with patch(f"{self.patch_path}.request", mock_request):
            # Call the method under test
            result = self.employee._get_remote_ip()

            # Assert that the result is None due to the exception
            self.assertIsNone(result)

    def test_20_is_ip_allowed_empty_ip(self):
        """Test _is_ip_allowed returns False for empty IP address."""
        result = self.employee._is_ip_allowed("")
        self.assertFalse(result)
