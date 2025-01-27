=============
Configuration
=============

Prerequisites
-------------
* Odoo 16.0
* Administrator or HR Manager access rights

Global Settings
---------------

IP Check Activation
~~~~~~~~~~~~~~~~~~~
1. Navigate to Settings -> Human Resources -> Attendance
2. Locate "IP Attendance Check" section
3. Enable "IP-based Attendance Check"

Note: This is a company-wide setting affecting all locations.

Work Location Configuration
---------------------------

CIDR Range Setup
~~~~~~~~~~~~~~~~
1. Go to Settings -> Employees -> Work Locations
2. Select or create a work location
3. Enable "IP Check" option
4. Under "IP Attendance Check" section:
   * Add descriptive name (e.g., "Office Network")
   * Define CIDR range (e.g., "192.168.1.0/24")
   * Set sequence number for priority
   * Set active/inactive status

CIDR Configuration Rules
~~~~~~~~~~~~~~~~~~~~~~~~
* Each CIDR must be unique per work location and company
* CIDRs cannot overlap within same work location
* At least one active CIDR required when IP Check is enabled
* Use sequence numbers to control evaluation order

Employee Settings
-----------------

Bypass Configuration
~~~~~~~~~~~~~~~~~~~~
1. Access employee form -> HR Settings -> Attendance
2. Enable "Bypass IP Check" option
3. Requires HR Manager access rights
4. Allows check in/out from any IP address

Use Cases for Bypass:
* Remote workers
* Multi-location employees
* Special exceptions

Work Location Assignment
~~~~~~~~~~~~~~~~~~~~~~~~
* Assign appropriate work location to each employee
* IP validation based on location's CIDR ranges
* No work location = automatic bypass

Security Settings
-----------------

Access Rights
~~~~~~~~~~~~~
HR Manager:
* Full CIDR configuration access
* IP check management
* Employee bypass control
* Validation log access

HR User:
* Read-only CIDR access
* No IP check modifications
* No bypass management
* Company-specific records only

Multi-company Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* CIDR ranges are company-specific
* Work locations respect company boundaries
* Cross-company access prevented
* Separate configuration per company required
