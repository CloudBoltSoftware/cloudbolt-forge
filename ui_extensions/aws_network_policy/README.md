# AWS Inspector Plugin

## Overview
When installed, this custom extension works in conjunction with the AWS Inspector service to display server security findings on the server details page for which findings have been generated.


## Prerequisites
To use this plugin, the Inspector Service must be enabled from the AWS Security Hub page at https://aws.amazon.com/security-hub/. Inspector is enabled on a region-by-region basis. 

Once enabled, Inspector assessments can be defined and run manually or on a scheduled basis from the
AWS Console.


## CloudBolt Setup
Inspector findings are fetched as part of a scheduled Recurring Job that scans all regions in all AWS Resource Handlers for findings. Since this Job can be scheduled, it can be modified to run at any interval. It's recommended that it be run no less than every five minutes. By default, CloudBolt updates findings at the top of every hour.



