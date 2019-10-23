# Resource Health Checks

This feature enables you to configure basic HTTP health checks for resources. 

This rule consists of a condition: `Perform Resource Health Checks` and an action: `Alert Channels of Health Report`.
The condition will send HTTP requests to urls specified for resources and the action will send alerts when health
checks fail, to configured Alert Channels. 

## Set Up

* Configure one or more [alert channels](http://docs.cloudbolt.io/multi-channel-alerts.html). 
This is required in order for the alerting to work in the action. 
* List the alert channels you would like to use and add them to `resource_health_checks.py`
under the list `ALERT_CHANNELS`. 
* Add the `health_check_config` parameter to one or more resources. 
The rule will run for any resource with a valid value.
The value must be valid JSON, and it must specify a url to send an HTTP request to for a health check, 
and may include some additional optional parameters. 
Here is an example of a valid `health_check_config` parameter value: 
 ```
 {
     'failure_threshold': 2,                       # Optional. The default is 1.
     'health_checks': [
         {
             'name': 'Check01',                    # Required. For reporting purposes. 
             'url': 'https://google.com',          # Required. This is where we will send an HTTP GET request to.
             'accepted_status_codes': [200, 201],  # Optional, will accept *any* if not specified.
             'timeout_seconds': 5,                 # Optional, default is 3
         }
     ],
 }
 ```
* The rule will automatically execute anytime the recurring job `Execute All Rules` is run, which is set by a cron schedule. 
If you would like to have the health checks run more or less often, you may create a recurring job to run this individual rule. 
