Usage
=====

Daily Operations
----------------
1. Employee Check-in/out Process:
   * Employees use standard attendance interface
   * System automatically validates IP address
   * Validation sequence:
     1. Checks if global IP check is enabled
     2. Verifies employee's work location configuration
     3. Validates current IP against allowed CIDR ranges
     4. Allows/denies attendance action based on validation

2. Validation Results:
   * Success: Check-in/out is recorded normally
   * Failure: Clear error message indicates the issue
   * Bypass: Employees with bypass enabled skip IP validation

Administrative Tasks
--------------------
1. IP Configuration Management (HR Managers):
   * Monitor and adjust CIDR ranges as needed
   * Review validation logs in system logs
   * Manage employee bypass permissions
   * Configure new work locations

2. Common IP Management Tasks:
   * Adding new office networks
   * Updating VPN ranges
   * Enabling/disabling ranges temporarily
   * Adjusting CIDR priorities

Example Configurations
----------------------
1. Standard Office Setup:
   * Name: "Main Office"
   * CIDR: 192.168.1.0/24 (seq=10)
   * All office workstations

2. VPN Access:
   * Name: "Corporate VPN"
   * CIDR: 10.0.0.0/8 (seq=20)
   * Remote workers via VPN

3. Branch Office:
   * Name: "Branch Office"
   * CIDR: 172.16.0.0/12 (seq=30)
   * Secondary location

4. Remote Working:
   * Disable IP Check for the location
   * Or enable bypass for specific employees

Troubleshooting Guide
---------------------
1. Common Issues and Solutions:

   a. Unable to Check In/Out:
      * Verify global IP check status
      * Check employee's work location assignment
      * Confirm bypass status if applicable
      * Verify network connectivity

   b. Network Configuration Issues:
      * Ensure work location has active CIDR ranges
      * Check if current IP falls within allowed ranges
      * Verify CIDR configuration is correct

2. Understanding Error Messages:
   * "Unable to determine IP address"
     - Check network connectivity
     - Verify client connection
     - Review proxy settings

   * "IP not allowed for location"
     - Verify current IP address
     - Check allowed CIDR ranges
     - Review work location settings

   * "No active CIDR ranges"
     - Add at least one active CIDR range
     - Check CIDR status
     - Review location configuration

Best Practices
--------------
1. Network Configuration:
   * Use descriptive names for CIDR ranges
   * Document network changes
   * Maintain sequence order logic
   * Regular review of active ranges

2. Employee Management:
   * Regular audit of bypass permissions
   * Document bypass justifications
   * Review work location assignments
   * Monitor attendance patterns

3. Security Considerations:
   * Regular review of access rights
   * Audit of bypass usage
   * Monitor validation logs
   * Document configuration changes
