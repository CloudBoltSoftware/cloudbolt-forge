from common.methods import set_progress

from connectors.ansible.models import AnsibleConf, AnsiblePlaybook


def run(job, *args, **kwargs):
    set_progress("Importing and/or updating Ansible Playbooks")

    for a in AnsibleConf.objects.all():
        set_progress("Looking for playbooks in ansible configuration '{}'".format(a))
        ci = a.connection_info
        possible_playbooks = ci.execute_script(
            script_contents="find {{ base_path }} -iregex '.*\.yml'").split('\n')
        for path in possible_playbooks:
            if path:
                ap = AnsiblePlaybook.objects.filter(path=path, conf=a).first()
                if ap:
                    set_progress("...{} already added, skipping...".format(ap))
                else:
                    name = path.replace("{{ base_path }}", "")
                    ap = AnsiblePlaybook.objects.create(name=name, path=path, conf=a)
                    set_progress("...added new playbook {}".format(ap))
    
        playbooks_to_delete = AnsiblePlaybook.objects.exclude(path__in=possible_playbooks, conf=a)
        if playbooks_to_delete.count() == 0:
            set_progress("...there are no playbooks to remove, exiting job")
        else:        
            set_progress("...removing deleted playbooks")
            for ap in playbooks_to_delete:
                set_progress("...deleting {} playbook".format(ap))
                ap.delete()
                #TBD If a playbook was used, what happens with the delete
