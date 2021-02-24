# kumo-integration-kit
Kumolus Integration Kit for CloudBolt CMP

## Getting started with Development

This repo contains a set of XUI extensions that can be developed on a live CloudBolt instance. To get started, on your CloudBolt host, simply clone this repo to the /var/opt/cloudbolt/proserv/xui/ directory. 

```
$ cd /var/opt/cloudbolt/proserv/xui/
$ git clone https://github.com/CloudBoltSoftware/kumo_integration_kit.git
```

Once this is done, you should see the kumo_integration_kit listed under Admin > Manage UI Extensions.

## Setup
To configure the KIK, add the following lines to ```/var/opt/cloudbolt/proserv/customer_settings.py``` 
and set ```KUMO_API_KEY``` accordingly to the API key generated from a Kumolus user account.

```
from settings import STATICFILES_DIRS
STATICFILES_DIRS += PROSERV_DIR + "/xui/kumo_integration_kit/static",

KUMO_API_KEY = ''
```

Also be sure to run ```npm i``` inside the static folder!

## Notes
* The AWS Account ID is currently hard-coded to 336101051063 in the source code for development
purposes. Once we've added the ability to retrieve this ID from a given AWS resource handler 
in CB, we'll be able to properly link the RH to its corresponding Account ID in Kumolus.



