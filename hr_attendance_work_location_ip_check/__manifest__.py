{
    "name": "HR Attendance Work Location IP Check",
    "version": "16.0.1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "IP check for attendance check-in/out linked to work location CIDR ranges.",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-attendance",
    "license": "AGPL-3",
    "depends": ["hr_attendance", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/hr_work_location_views.xml",
        "views/hr_employee_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
    "development_status": "Beta",
}
