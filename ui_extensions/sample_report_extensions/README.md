# Sample UI extension package of reports

To install:
  * Download or create an extension package folder from the forge
  * Zip it up **including the folder name**.
  * Go to *Admin > Manage UI Extensions* and **upload** the zip file
  * (for now) restart Apache via `service httpd restart`

To customize:
  * Go to Admin > Manage UI Extensions and download the package
  * Unzip it and modify views as needed
  * Re-install it

Installed extension packages are located in /var/opt/cloudbolt/proserv/xui/<package_name>.  Any changes to those files take effect in the UI after Apache is restarted.
