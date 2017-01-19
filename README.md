<img src="https://www.cloudbolt.io/wp-content/uploads/CloudBolt_hlogo_blue_cloud_w_text2-1.png" width="500">

# CloudBolt Forge
Welcome to the CloudBolt Forge, a public github repository used for sharing powerful content in CloudBolt.  Initially, this holds CloudBolt actions (AKA hooks), but will soon store Blueprints and other content.

If you have interesting hooks that you have developed, please share them! Even if they are rough-hewn, others may admire your work, improve on it, and re-share those improvements back with you.

## Importing and Exporting Actions
*New in 5.2*
 * There are import and export scripts located in c2_api/c2_api_samples/python_client/samples/.
 * To import an action into CB, use the import_action.py script and provide the username, password, host, port, and protocol arguments, as well as either a zip file or directory.
 * To export an action from CB, you can use the Export button on the Action Details page or use the export_action.py script and provide the username, password, host, port, protocol, and action ID arguments.
 * Some actions may have placeholder fields that you need to fill in manually, either in the JSON file before importing or in the UI after importing.

## File & Directory Naming Conventions
 * Each importable piece of content should have its own directory.
 * Use no spaces or special characters in file & directory names other than underscores.

## Coding Conventions
 * Please comment your code well, with a docstring at the top of each Python module and on most methods.
 * Configure your editor to help keep your code [PEP8 compliant](https://www.python.org/dev/peps/pep-0008/).

## Contribution Process
 * First, fork the cloudbolt-forge repository.
 * Make your changes in your forked repository.
 * Then, submit a pull request to merge your changes into the CloudBoltSoftware repository.
 * By submitting a pull request for this project, you agree to license your contribution under the Apache License to this project.

## License
Contributions to this project are governed by the CONTRIBUTING file and the Apache License.

## Contact Us
We'd love to hear from you if you have any questions or ideas you'd like to discuss with us.

support@cloudbolt.io

http://cloudbolt.io/
