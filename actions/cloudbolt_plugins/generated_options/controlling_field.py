"""
This is a working sample CloudBolt plug-in that will generate options for an action input defined within a Cloudbolt Plug-in. 

Attaching this as an action item on a blueprint will 

1. To utilize generate_options_for method, an action input must be created.
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


"""
    This plugin was developed to perform the following actions
      * pass a list from one generated parameter to another
      * pull the group ID from the list and construct a group object

      Setup:

      To configure this plugin:
      1. Create a parameter (admin > parameters > create) called 'client_secret'
      2. Assign the parameter to a group and give it a value
      3. Create a blueprint and add this code as a custom plugin action (admin > blueprints > create)
"""
import json
import logging

from accounts.models import Group
from common.methods import set_progress

"""Create Action Inputs for desired form fields"""
client_secret = "{{ client_secret }}"
dependant_variable = "{{ dependant_variable }}"


def generate_options_for_client_id(group, **kwargs):
    parameter = group.client_id

    return {"initial_value": parameter, "options": ""}


def construct_group(value):
    """
    Construct a group object from the value passed in
    """
    return Group.objects.get(id=int(value))


def generate_options_for_client_secret(group, control_value=None, *args, **kwargs):
    """
    This method will:
        - construct a list of options for the client_secret field
        - add group_id to the dict
        - return the list of options as a dictionary
    """

    # This class will simulate an object returned from an API
    class TempObject:
        def __init__(self, subscription_id, display_name):
            self.subscription_id = subscription_id
            self.display_name = display_name

    object_1 = TempObject("1", "first_option")
    object_2 = TempObject("2", "second_option")
    object_3 = TempObject("3", "third_option")

    raw = [object_1, object_2, object_3]
    entry = []
    for i in raw:
        prepared_dict = json.dumps(
            {
                "group_id": str(group.id),
                "subscription_id": i.subscription_id,
                "display_name": i.display_name,
            }
        )
        entry.append((prepared_dict, i.display_name))

    # Logging to the console to view the output for development purposes
    for i in entry:
        logging.info(i)
    # Parse the response into a dictionary to return
    dict_obj = {"group_id": str(group.id)}
    prepared_dict = json.dumps(dict_obj)

    return {"options": entry}


# By specifying control_values as an empty list, we will return the values from the controlling field
# as control_value and control_values, respectively.
def generate_options_for_dependant_variable(
    control_value=None, control_values=[], *args, **kwargs
):
    """
    :param control_valu:e The value returned from the controlling field
    :param control_values: The values returned from the controlling field as a list
    """
    if control_value is not None and control_value != "":
        dict_obj = json.loads(control_value)
        group = construct_group(dict_obj["group_id"])
        options = [(group.id, dict_obj["display_name"])]
        return {"options": options, "override": True}
    options = [("", "")]
    return {"options": options, "override": True}


def run(job, *args, **kwargs):
    set_progress(
        "Dictionary of keyword args passed to this plug-in: {}".format(kwargs.items())
    )

    set_progress()

    if True:
        return "SUCCESS", "Sample output message", ""
    else:
        return (
            "FAILURE",
            "Sample output message",
            "Sample error message, this is shown in red",
        )
