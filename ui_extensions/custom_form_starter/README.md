# Custom Form XUI Starter 
This is the a barebones custom form XUI that will render a custom form and complete an action.

The implementation defined here will render different forms based on a JSON definition file using the surveyjs library.  The form data will be sent via POST request and processed by the functionality defined in forms.py. 

At the point of implementing a custom form, it entails you are giving up generated options in favor of generating the options yourself. All parameters defined in CMP are still valid and usable in a custom form.

While this form is utilizing surveyjs, it is not a requirement to utilize it.  The current implementation assumes JSON form descriptions in a [form](forms) directory of the XUI.  To make your own custom forms utilizing SurveyJS, utilize the [SurveyJS designer tool](https://surveyjs.io/create-free-survey) 

It is important to note that the build actions in the blueprint step will be ignored, for this reason there is an included build action set to disabled to allow the form to be ordered.  All logic will be dictated from the views.py page upon processing the order submission.

When this form is ordered, it will submit a job to the custom_form_starter plugin and set the owner to the requester.  After submitting the form, you will be redirected to the job page and should see the parameters that were passed through displayed in the progress box and/or logs. 


## Quick Start

1. From the quickstart folder, download the custom_form_starter.zip and custom_form_blueprint.zip.
2. Navigate to admin > ui extensions
3. Upload UI extension and select the [custom_form_starter.zip](packages/custom_form_starter.zip) file
4. Restart your web server so it loads the new URL(s) in the UI extension
5. Navigate to catalog 
6. Select upload blueprint and upload the [custom_form_blueprint.zip](packages/custom_form_blueprint.zip) custom_form_blueprint.zip file

## Structure
A custom form consists of several elements:
- form.html
- urls.py
- views.py 

### form.html

[form.html](templates/form.html) template page will control the rendering of your form.  This is where you can make all of the visual edits that will render your form.  Often, you can and will include javascript in here to add advanced functionality. 

## urls.py
[urls.py](urls.py) will dictate the routing logic.  Core functionality for rendering will require that a get_custom_form function is mapped from the [views.py](views.py)

## views.py
[views.py](views.py) will control the logic of what happens within our application, this will declare methods that are used within itself and expose logic via [urls.py](urls.py) for ajax calls to make the form more dynamic. 

Within [views.py](views.py) are several special methods that control the custom form. 

### FormDelegate class
The FormDelegate adds the should_display logic for a custom form, this will dictate when the [form.html](templates/form.html) should be rendered on the custom form, preventing it from replacing the content of every blueprint in the catalog.  The implementation logic of this starter defines checks for the existence of a parameter called "custom_form".

### get_custom_form
This method will map the custom form to the logic and provide any initial context values that need to be rendered by the [form.html](templates/form.html) 

## Development Tips

During development, any changes to *.py files will require an HTTPD restart to reload into the CMP system.   If you are editing strictly the visual elements in form.html, then no restart will be required.


### Run a plugin programatically

To trigger a pre-existing plugin, you can utilize the following-code, which will register the action in the job-queue.  This logic can be used to make use of existing plugin modules, while leveraging the GUI customization of forms. 

    from import ResourceAction
    ra = ResourceAction.objects.get(id=id)
    ra.run_hook_as_job()

    from cbhooks.models import OrchestrationHook
    oh = OrchestrationHook.objecst.get(name="plugin_name")
    oh.run_hook_as_job()
