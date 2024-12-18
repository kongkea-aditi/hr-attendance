==============================================
HR Attendance IP Check with Work Location CIDR
==============================================

This module extends HR Attendance to validate check-in/out operations based on work locations' IP configuration.
It ensures employees can only record attendance when connected from authorized IP ranges, with support for
individual bypass permissions and multi-company environments.

Key Features
------------
* IP-based attendance validation using CIDR ranges
* Employee-level IP check bypass with strict access control (HR Manager only)
* Prioritized evaluation of IP ranges using sequence numbers
* Multi-company security with proper access rules
* Flexible configuration at global and per-location levels
* Active/inactive network range management
* HR Manager/User permission separation
* Detailed validation messages and logging
* Scalable IP validation for enterprises with multiple work locations
* CIDR overlap detection and validation
* Comprehensive error handling and logging

Technical Features
------------------
* Extends hr.attendance for IP validation
* Implements hr.work.location.cidr for network management
* Advanced CIDR validation with overlap detection
* Extensive logging for troubleshooting
* Multi-company security enforcement
* Proper access control implementation
* Comprehensive test coverage including:
  * Access control tests
  * CIDR validation and overlap detection
  * Multi-user scenarios
  * Bypass feature validation
  * Edge case handling
  * Configuration changes
  * Multi-company isolation

Why Work Location-Based Validation?
-----------------------------------
This module adopts a work location-based approach for IP validation by associating CIDR ranges with work locations.
This architectural decision offers several advantages:

* Scalability: Efficiently handles enterprises with multiple locations and complex network setups
* Centralized Management: Simplifies configuration and maintenance through work location grouping
* Flexible Application: Supports various deployment scenarios:
  * Global policies through system settings
  * Location-specific rules via work location configuration
  * Individual exceptions through employee bypass settings
* Multi-company Support: Built-in isolation and security for multi-company environments
* Audit Capabilities: Comprehensive logging and tracking of attendance validations

This design particularly benefits organizations with:
* Distributed teams across multiple locations
* Complex work location structures
* Mixed office and remote work policies
* Multi-company operations
* Strict attendance compliance requirements
