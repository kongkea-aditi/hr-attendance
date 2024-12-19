Employee Check-in/out Process
-----------------------------
* Use standard attendance interface
* System validates IP address based on:
  1. Global IP check status
  2. Employee's work location configuration
  3. Allowed CIDR ranges

* Results:
  - Success: Check-in/out recorded
  - Failure: Error message shown
  - Bypass: Skips validation for authorized employees

Administrative Tasks
--------------------
* Configure CIDR ranges and priorities
* Manage bypass permissions
* Update or disable network ranges as needed
