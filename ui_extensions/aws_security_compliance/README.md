# AWS Security Compliance Plugin

## Overview
When installed, this extension works in conjunction with the AWS Security Hub service to display the security compliance findings for a given AWS Resource Handler. Findings are separated by AWS Region.

## Prerequisites
To use this plugin, AWS Security Hub must be enabled for one or more regions. See the [AWS documentation for instructions](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-settingup.html).

## CloudBolt Setup
Security compliance findings are fetched as part of a scheduled Recurring Job that scans all regions in all AWS Resource Handlers for findings. Since this Job can be scheduled, it can be modified to run at any interval.

Compliance findings are displayed in a "Security Hub" tab for AWS Resource Handlers that have compliance data.
