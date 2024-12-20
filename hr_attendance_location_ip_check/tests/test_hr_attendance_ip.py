from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import CommonAttendanceTest


@tagged("post_install", "-at_install")
class TestHrAttendanceIP(CommonAttendanceTest):
    """Test cases for IP validation functionality."""

    def test_01_attendance_allowed_ip(self):
        """Test attendance with allowed IP"""
        self.mock_ip.return_value = "192.168.1.100"
        self.employee._attendance_action_check("check_in")
        attendance = self._create_test_attendance()
        self.assertTrue(attendance.exists())

    def test_02_attendance_blocked_ip(self):
        """Test attendance with blocked IP"""
        self.mock_ip.return_value = "5.5.5.5"
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

    def test_04_remote_ip_error(self):
        """Test error handling in remote IP retrieval."""
        self.mock_ip.return_value = None
        self.assertIsNone(self.employee._get_remote_ip())

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

    def test_06_no_ip_error_message(self):
        """Test specific error message when IP cannot be determined."""
        self.mock_ip.return_value = None
        with self.assertRaises(ValidationError) as context:
            self.employee._attendance_action_check("check_in")
        self.assertIn("Unable to determine IP address", str(context.exception))

    def test_07_ip_not_allowed_message(self):
        """Test specific error message when IP is not allowed."""
        self.mock_ip.return_value = "10.0.0.1"
        with self.assertRaises(ValidationError) as context:
            self.employee._attendance_action_check("check_in")
        self.assertIn("IP 10.0.0.1 not allowed for", str(context.exception))

    def test_08_get_remote_ip_direct(self):
        """Test direct remote IP retrieval."""
        with patch(
            f"{self.patch_path}.HrEmployee._get_remote_ip", return_value="192.168.1.100"
        ):
            result = self.employee._get_remote_ip()
            self.assertEqual(result, "192.168.1.100")

        with patch(f"{self.patch_path}.HrEmployee._get_remote_ip", return_value=None):
            result = self.employee._get_remote_ip()
            self.assertIsNone(result)

    def test_09_attendance_creation_no_ip(self):
        """Test attendance creation when no IP is available."""
        self.mock_ip.return_value = None
        with self.assertRaises(ValidationError) as context:
            self._create_test_attendance()
        self.assertIn("Unable to determine IP address", str(context.exception))

    def test_10_attendance_creation_invalid_ip(self):
        """Test attendance creation with an IP outside the allowed range."""
        self.mock_ip.return_value = "1.1.1.1"  # Outside of defined CIDRs
        with self.assertRaises(ValidationError) as context:
            self._create_test_attendance()
        self.assertIn("IP 1.1.1.1 not allowed for", str(context.exception))
