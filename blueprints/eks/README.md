## AMAZON EKS
### Prerequisites
#### Role ARN
* A valid AWS role ARN (Amazon Resource Name), which allows EKS to manage clusters on your behalf.
    * Required AWS Managed policies:
        * AmazonEKSClusterPolicy
        * AmazonEKSServicePolicy
#### Networking
* Minimum 3 subnets in different AZs
* Limit of 4 resource VPC security groups per cluster
### Coding Conventions
 * Please comment your code well, with a docstring at the top of each Python module and on most methods.
 * Configure your editor to help keep your code [PEP8 compliant](https://www.python.org/dev/peps/pep-0008/).
### Action Inputs
It is recommended that you import this blueprint, which will use the JSON data to create the action inputs so all their metadata is set up properly. If you cannot do this, make sure:
 * The subnets and security groups action inputs allow multiple values
 * The Role ARN, subnets, and security groups action inputs have a regenerated options dependency on env_id
 * There may be other changes needed, see the .json files for complete details
### License
Contributions to this project are governed by the CONTRIBUTING file and the Apache License.
### Contact Us
We'd love to hear from you if you have any questions or ideas you'd like to discuss with us.
support@cloudbolt.io
http://cloudbolt.io/
