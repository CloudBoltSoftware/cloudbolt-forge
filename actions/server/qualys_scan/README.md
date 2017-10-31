# qualys_scan
This action will launch an Authenticated Qualys Scan against a single server or list of servers.
The Job will report a summary of all findings and will email a PDF report to the requestor.
CC List value allow you to send the PDF report(s) to additional email addresses
Email_Extra_Body lets you add custom text to the bottom of the email

## Prerequisies
Install qualysapi (https://github.com/paragbaxi/qualysapi) on your Cloudbolt server
Create a .qcrc file per the example in the qualysapi documentation. Problably want to create the file in root's home directory with 0600 permissions.
Determine which Qualys Report Template(s) to use and update the generate_options_for_Scan_Type section of qualys_scanner.py
Create a qualys_scanner perameter in each Cloudbolt Environment you want to Scan. Set the value to the appropriate on-prem scanner.

