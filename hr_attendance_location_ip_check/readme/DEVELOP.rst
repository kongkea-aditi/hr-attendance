Development
===========

Module Structure
----------------
1. Models:
   * hr_attendance.py: Attendance validation
   * hr_employee.py: Employee IP check logic and bypass control
   * hr_work_location.py: Location configuration and IP check settings
   * hr_work_location_cidr.py: CIDR management and overlap validation

2. Security:
   * ir.model.access.csv: Access rights
   * security.xml: Record rules

3. Views:
   * hr_employee_views.xml: Employee form extension
   * hr_work_location_views.xml: Location configuration
   * res_config_settings_views.xml: Global settings

Error Handling & Logging
------------------------
1. Error Types and Messages:

   a. IP Validation Errors:
      * "Unable to determine IP address"
      * "IP {ip} not allowed for {location}"
      * "Invalid IP address format: {ip}"
      * "No active CIDR ranges for location {location}"

   b. CIDR Configuration Errors:
      * "CIDR must be unique per work location and company"
      * "CIDR {new} overlaps with existing {old}"
      * "Invalid CIDR for {location}: {cidr}"

   c. Access Control Errors:
      * "Only HR Managers can modify the IP check bypass setting"

2. Logging Implementation:
   * Module Logger: 'hr_attendance_ip_check'
   * Log Levels:
     * ERROR: Validation failures and configuration errors
     * INFO: Successful validations and configuration changes
     * DEBUG: Detailed CIDR matching attempts
   * Log Categories:
     * IP validation results
     * CIDR matching attempts
     * Configuration changes
     * Access attempts
     * Error conditions
   * Implementation Guidelines:
     * Use structured logging format
     * Include relevant context (user, location, IP)
     * Maintain consistent error codes
     * Enable trace logging for debugging

Test Coverage
-------------
1. Access Rights:
   * test_01_hr_user_access_rights: Tests that HR Users can read but not modify IP check settings
   * test_02_hr_manager_access_rights: Tests HR Manager's full access to IP settings and CIDR

2. CIDR & IP Validation:
   * test_03_cidr_validation: Validates CIDR format and creation rules
   * test_04_attendance_allowed_ip: Tests attendance creation from allowed IP
   * test_05_attendance_blocked_ip: Tests attendance blocking from unauthorized IP

3. Configuration Tests:
   * test_06_ip_check_disabled: Verifies behavior when IP check is disabled
   * test_07_multiple_cidrs: Tests handling of multiple CIDR ranges
   * test_08_multi_company: Tests CIDR restrictions across different companies
   * test_09_inactive_cidr: Tests behavior with inactive CIDR ranges

4. Advanced Features:
   * test_10_cidr_sequence: Tests CIDR priority ordering
   * test_11_attendance_modification: Tests IP validation during attendance updates
   * test_12_ip_edge_cases: Tests edge cases (last IP, invalid IPs, etc.)
   * test_13_config_changes: Tests global configuration parameter changes
   * test_14_bypass_features: Tests employee IP check bypass functionality
   * test_15_multi_user_scenarios: Tests different user access scenarios

Each test focuses on a specific aspect of the module's functionality, ensuring
comprehensive coverage of features, security, and edge cases.

Development Guidelines
----------------------
1. IP Validation:
   * Use ipaddress module for CIDR validation
   * Handle network overlaps
   * Validate IP format
   * Consider edge cases

2. Security:
   * Implement proper access controls
   * Follow least privilege principle
   * Use appropriate security groups
   * Validate multi-company access

3. Testing:
   * Cover all use cases
   * Test edge cases
   * Validate security rules
   * Check multi-company scenarios

4. Error Handling:
   * Use consistent error message format
   * Implement proper exception classes
   * Handle all edge cases
   * Provide clear user feedback

5. Logging:
   * Follow Odoo logging conventions
   * Use appropriate log levels
   * Include necessary context
   * Enable debugging information

Bug Tracker
-----------
Bugs are tracked on `GitHub Issues <https://github.com/OCA/hr/issues>`_.
In case of trouble, please check there if your issue has already been reported.

