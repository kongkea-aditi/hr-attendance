import logging
from unittest.mock import patch

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class CommonAttendanceTest(TransactionCase):
    """Common test class for HR Attendance IP Check tests."""

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
        # Setup IP patcher
        self.ip_patcher = patch(f"{self.patch_path}.HrEmployee._get_remote_ip")
        self.mock_ip = self.ip_patcher.start()
        self.addCleanup(self.ip_patcher.stop)  # Add cleanup method

        # Create a list to track created CIDR records for cleanup
        self.created_cidrs = []

    def _create_test_attendance(self, employee=None, check_in="2024-01-01 08:00:00"):
        """Helper method to create test attendance"""
        return self.env["hr.attendance"].create(
            {
                "employee_id": employee and employee.id or self.employee.id,
                "check_in": check_in,
            }
        )
