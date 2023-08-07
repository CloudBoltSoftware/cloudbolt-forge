"""
This is a working sample CloudBolt plug-in that will generate options for an action input defined within a Cloudbolt Plug-in. 

Attaching this as an action item on a blueprint will 

1. To utilize generate_otpions_for method, an action input must be created.
2. After the action input is created, the generate options method can be created. 

For further reading, consult the documentation:
https://docs.cloudbolt.io/articles/#!cloudbolt-latest-docs/advanced-option-returns
"""
# Importing set_progress allows us to view output of the job while it is running
from common.methods import set_progress

# First we declare the action input
action_input = "{{ action_input }}"

# Second we declare the method to generate the options to be returned, **kwargs is required
def generate_options_for_action_input(**kwargs):
    # The generate_options methods expect a list of tuples to be returned.
    # The first item in the tuple is the item that will be assigned
    # The second item in the tuple will be displayed visually at time of selection
    # When ordering this blueprint, you will see "First, Second, Third" in the dropdown
    options = [(1, "First"), (2, "Second"), (3, "Third")]
    return {"initial_value": "value", "options": options}


# In a cloudbolt plug-in, the run method will execute all the code inside the method once the item is ordered.
def run(job, *args, **kwargs):

    # Log the value of the selection for action_input
    # The output will be either 1, 2, 3 as referenced above as the first item in the option tuple
    set_progress(action_input)

    # the run method expects a return of three items:
    # status message, output message, error message
    # Items in the third return will display as red.
    if True:
        # This is an example of a message and sucess text on successful completion
        # note the output message contains text and the error message is empty
        return "SUCCESS", "Success message text", ""
    else:
        # This is a sample of a failure message, note the output message is empty
        # and the error message is populted
        return "FAILURE", "", "Failure message text"
