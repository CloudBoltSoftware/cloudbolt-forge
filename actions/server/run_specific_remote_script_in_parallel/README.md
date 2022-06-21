This plug-in can be used as a server action for the case when you want to run a particular remote script on the server list page on many servers in parallel. By default, CB (at least in 2022.2.4 and prior) runs these remote scripts in serial, but this little plug-in works around that.

After uploading this and setting it up as a server action, modify the code to have it fetch the server action for the remote script you want it to run.

I would recommend marking the remote script server action that it runs as disabled so that the remote script does not appear as a separate button on the server details page.
