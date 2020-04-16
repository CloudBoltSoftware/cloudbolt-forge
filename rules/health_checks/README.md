# Resource Health Checks

This feature enables you to configure basic HTTP health checks for resources. 

This rule consists of a condition: `Perform Resource Health Checks` and an action: `Alert Channels of Health Report`.
The condition will send HTTP requests to urls specified for resources and the action will send alerts when health
checks fail, to configured Alert Channels. 

## Set Up

* Copy the entire `health_checks' directory into your `/proserv/ directory, then run it, via
`python create.py`. This file will create necessary objects for configuring and running the health checks rule. 
This will only work from the proserv directory.  
* Configure one or more [alert channels](http://docs.cloudbolt.io/multi-channel-alerts.html). 
This is required in order for the alerting to work in the action. 
  * Use alert category, "health_check" in your comma-delimited list of alert categories for any
  and all alert channels you wish to use for health checks
* List the alert channels you would like to use and add them to `health_alerts.py`
under the list `ALERT_CHANNELS`. 
* Add the `health_check_config` parameter to one or more resources. 
The rule will run for any resource with a valid value.
The value must be valid JSON, and it must specify a url to send an HTTP request to for a health check, 
and may include some additional optional parameters. 
Here is an example of a valid `health_check_config` parameter value: 
 ```
 {                   
     "health_checks": [
         {
             "name": "Teapot",                   
             "url": "https://google.com",        
             "accepted_status_codes": [418],  
             "timeout_seconds": 5,               
             "max_retries": 4,
             "retry_interval_seconds": 10
         }
     ],
 }
 ```

* The rule will automatically execute anytime the recurring job `Execute All Rules` is run, which is set by a cron schedule. 
If you would like to have the health checks run more or less often, you may create a recurring job to run this individual rule. 

Here is a more detailed breakdown of the supported parameters:

* health_checks: Required. Must be a list of JSON objects with the following required parameters.
* name: Required. Specify for referencing health checks in logging and reporting. 
* url: Required. Needed to send a request to do a health check.
* accepted_status_codes: Optional. Must be a list of integers for HTTP status codes. The default is to accept any status code. 
* timeout_seconds: Optional. The default is 3. Must be an integer. This specifies the number of seconds to wait before timing out the request.
* max_retries: Optional. The default is 3. This specifies the number of retry attempts allowed before reporting the cloud resource as unavailable. 
* retry_interval_seconds: Optional. The default is 1 second. This specifies how many seconds to wait between retry attempts. 
