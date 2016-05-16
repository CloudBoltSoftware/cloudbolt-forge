This CB Plugin should be enabled as a pre-delete service action (from Admin >
Orchestration Actions). It will look for a parameter on the service called "AWS
Stack Name" and delete the Stack with that name in AWS.

Note that this is a sample to start from, and not yet produciton-ready. There
are still some hard-coded items in this action including the region. Also, the
first AWS handler is always used.
