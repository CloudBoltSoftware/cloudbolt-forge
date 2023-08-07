"""
Display Condition Plugin intended to prevent server action from
appearing on the bulk servers page.

To use this plugin, set it under 'Display Condition'
on the server action page.  (/actions/server_actions/)

Reference:
https://docs.cloudbolt.io/articles/#!cloudbolt-latest-docs/server-actions/

"""


def should_display(request, **kwargs):
    # Check the enviroment variable for the path info
    path_info = str(request.environ["PATH_INFO"])
    # Split the path info into a list, based on the forward slash
    path_list = path_info.split("/")

    # Check if the path list contains the string "batch_server_actions"
    if "batch_server_actions" in path_list:
        # If it does, return False, which will prevent the action from displaying
        return False
    else:
        # Otherwise, return True, which will allow the action to display
        return True
