# Summary
This is a 'Server Action' with a Wedhook that sends server details to a [Slack](https://slack.com) channel.

# Setup
* zip slack_server_details.zip slack_server_details.json
* rm slack_server_details.json
* zip slack_my_details.zip slack_my_details/slack_my_details.json slack_my_details/slack_server_details/slack_server_details.zip
* Import slack_my_details.zip into CloudBolt server
* Update Webhook url for the desired Slack channel [Webhook integration](https://my.slack.com/services/new/incoming-webhook/)
* If desired, modify the JSON data

# Refs
[API documentation](https://api.slack.com/incoming-webhooks)
[Message Builder](https://api.slack.com/docs/messages/builder)
[Webhook integration](https://my.slack.com/services/new/incoming-webhook/)
