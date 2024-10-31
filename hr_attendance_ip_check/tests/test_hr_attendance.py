from odoo.tests.common import TransactionCase, tagged
from unittest.mock import patch
import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestHrAttendance(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
        })

        # Define test IPs
        self.ALLOWED_IP = '192.168.1.1'
        self.BLOCKED_IP = '192.168.1.2'
        self.WHITELIST = f'{self.ALLOWED_IP}, 10.0.0.1'

        # Configure system parameters
        self._set_config_params()

    def _set_config_params(self):
        """Set configuration parameters."""
        param_obj = self.env['ir.config_parameter'].sudo()
        param_obj.set_param('hr_attendance.ip_check_enabled', 'True')
        param_obj.set_param('hr_attendance.whitelist_ips', self.WHITELIST)

    def _check_warning_format(self, result, message_contains=None):
        """Helper method to check warning format"""
        self.assertTrue(isinstance(result, dict))
        self.assertTrue('warning' in result)
        if message_contains:
            self.assertTrue(message_contains in result['warning'])

    def test_01_blocked_ip(self):
        """Test attendance with blocked IP."""
        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value=self.BLOCKED_IP):
            result = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self._check_warning_format(result, message_contains=self.BLOCKED_IP)

    def test_02_empty_whitelist(self):
        """Test when whitelist is empty."""
        self.env['ir.config_parameter'].sudo().set_param('hr_attendance.whitelist_ips', '')

        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value=self.ALLOWED_IP):
            result = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self._check_warning_format(result, message_contains='No IP addresses are whitelisted')

    def test_03_allowed_ip(self):
        """Test attendance with allowed IP."""
        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value=self.ALLOWED_IP):
            result = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self.assertTrue(result.get('action'))  # Should proceed with normal attendance flow

    def test_04_ip_check_disabled(self):
        """Test when IP checking is disabled."""
        self.env['ir.config_parameter'].sudo().set_param('hr_attendance.ip_check_enabled', 'False')

        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value=self.BLOCKED_IP):
            result = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self.assertTrue(result.get('action'))  # Should proceed regardless of IP

    def test_05_failed_ip_detection(self):
        """Test when IP detection fails."""
        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value=None):
            result = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self._check_warning_format(result, message_contains='Unable to determine your IP address')

    def test_06_whitelist_with_spaces(self):
        """Test IP validation with whitespace in whitelist."""
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_attendance.whitelist_ips', ' 192.168.1.1,  10.0.0.1 , 192.168.1.3')

        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value='192.168.1.3'):
            result = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self.assertTrue(result.get('action'))

    def test_07_check_in_out_sequence(self):
        """Test check-in/out sequence with IP validation."""
        with patch('odoo.addons.hr_attendance_ip_check.models.hr_employee.HrEmployee._get_current_ip',
                   return_value=self.ALLOWED_IP):
            # Check-in
            result1 = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self.assertTrue(result1.get('action'))
            self.assertEqual(self.employee.attendance_state, 'checked_in')

            # Check-out
            result2 = self.employee.attendance_manual('hr_attendance.hr_attendance_action_my_attendances')
            self.assertTrue(result2.get('action'))
            self.assertEqual(self.employee.attendance_state, 'checked_out')