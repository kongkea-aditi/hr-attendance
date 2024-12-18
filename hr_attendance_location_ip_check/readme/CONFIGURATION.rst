Configuration
=============

System Requirements
------------------
* Odoo 16.0
* No additional Python packages required

Global Settings
---------------
1. Enable IP-based attendance check:
   * Navigate to Settings -> Human Resources -> Attendance
   * Locate the "IP Attendance Check" section
   * Activate "Enable IP-based Attendance Check"
   * Note: This is a company-wide setting affecting all locations

Work Location Setup
-------------------
1. Configure locations (requires HR Manager rights):
   * Go to Settings -> Employees -> Work Locations
   * Select or create a work location
   * Enable "IP Check" option where needed
   * Under "IP Attendance Check" section, add allowed IP ranges:
     * Set a descriptive name (e.g., "Office Network")
     * Define CIDR range (e.g., "192.168.1.0/24")
     * Arrange priority using sequence handle (lower numbers = higher priority)
     * Set active/inactive status as needed

   Note: When IP Check is enabled for a location, at least one active CIDR range is required.

2. CIDR Configuration Guidelines:
   * Each CIDR must be unique per work location and company
   * CIDRs cannot overlap within the same work location
   * Invalid CIDR formats will be rejected
   * Use sequence numbers to control evaluation order
   * Inactive CIDRs are ignored during validation

Employee Configuration
----------------------
1. Individual Bypass Settings:
   * Navigate to employee form -> HR Settings -> Attendance/Point of Sale
   * Enable "Bypass IP Check" option (requires HR Manager access rights)
   * When enabled, the employee can check in/out from any IP address
   * Useful for:
     * Remote workers
     * Employees working across multiple locations
     * Special cases requiring IP check exemption

2. Work Location Assignment:
   * Assign appropriate work location to each employee
   * IP validation is based on the assigned work location's CIDR ranges
   * Employees without work location assignment bypass IP validation

Security Configuration
----------------------
Access rights are automatically configured but can be reviewed:

1. HR Manager Rights:
   * Full access to CIDR configuration
   * Can enable/disable IP checks
   * Can manage employee bypass settings
   * Can view all validation logs

2. HR User Rights:
   * Can view CIDR configurations
   * Cannot modify IP check settings
   * Cannot modify bypass settings
   * Limited to company-specific records

3. Multi-company Considerations:
   * CIDR ranges are company-specific
   * Work locations respect company boundaries
   * Cross-company access is prevented by security rules

Configuration Validation
------------------------
The system performs several validations during configuration:

1. CIDR Validation:
   * Format checking of IP ranges
   * Overlap detection between ranges
   * Uniqueness verification per location
   * Active status confirmation

2. Location Settings:
   * IP Check enablement status
   * Presence of active CIDR ranges
   * Work location assignments
   * Multi-company boundaries

3. Employee Settings:
   * Bypass permission verification
   * Work location assignment check
   * Access right validation
