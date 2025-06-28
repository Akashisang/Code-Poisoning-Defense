"""
Basic implementation Nexpose API
Full API guide take a look in https://community.rapid7.com/docs/DOC-1896

What implemented:
- Login/Logout
- Report
    - Get report listing
    - Get report config
    - Get template listing
    - Get specific report from URI

- Exceptions
    - Create vulnerability exception
    - Approve vulnerability exception

- Vulnerability
    - Get vulnerability listing
    - Get vulnerability details

Example of using:
```
with NexposeClient('localhost', 3780, "username", "password") as client:
    listing = client.report_listing()
    for report in listing:
        config = client.report_config(report.get('cfg-id'))

```
"""