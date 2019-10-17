Prerequisites:
 * Set up export of Net Flow logs from EC2 to CloudWatch. This can be set up using these instructions from AWS: https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html.
 * The account used in your AWS resource handler must have permission to perform logs:FilterLogEvents on the chosen group and log stream (see the instructions in the previous item).
 * Requires CloudBolt version 9.0.1 or greater.
 * Add AWS_NET_FLOW_LOG_GROUP_NAME to customer_settings.py.
