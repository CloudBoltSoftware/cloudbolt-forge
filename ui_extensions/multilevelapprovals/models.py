'''
    Updated Models for multilevel approvals
'''

from django.utils.encoding import python_2_unicode_compatible
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.utils.html import escape
import cbhooks
from accounts.models import Role
from orders.models import Order, get_current_time
import orders.mail
from utilities.logger import ThreadLogger
from utilities.exceptions import CloudBoltException
from quota.exceptions import QuotaError
from quota.quota_set import QuotaSetError

logger = ThreadLogger(__name__)

@python_2_unicode_compatible
class CustomOrder(Order):
    class Meta:
        app_label = 'orders'

    def approve_my_grms(self, profile=None):
        '''
            in a multilevel approval, we need a user to partially (or fully)
            approve an order based on the GroupRoleMembership mappings (excluding)
            "approvers" (the default/single-level approval role)
        '''
        if self.status != 'PENDING':
            return
        if not profile:
            profile = self.owner

        oi = self.orderitem_set.first().cast()
        bpoi = oi.blueprintitemarguments_set.first()
        for grm in CustomOrder.get_my_grms(self, profile):
            grmcfv = bpoi.custom_field_values.get(field__name=f'{grm.role.name}_approver_id')
            if grmcfv and not grmcfv.int_value:
                grmcfv.int_value = grm.profile.user.id
                grmcfv.save()
                history_msg = _("The '{order}' order has been partially approved by {role_label}.").format(order=escape(self), role_label=grm.role.label)
                self.add_event('APPROVED', history_msg, profile=profile)

    def get_my_grms(self, profile=None):
        '''
            in a multilevel approval, we need a get the GroupRoleMembership mappings
            and exclude the default approvers role

            as well, if there's only one role.name == approvers
        '''
        if not profile:
            profile = self.owner

        owned_grms = profile.grouprolemembership_set.filter(group=self.group,
                                                            role__permissions__name='order.approve')
        if len(owned_grms) > 1:
            #multilevel approvals ignore the "approver" GRM
            owned_grms = owned_grms.exclude(role__name='approver')

        return owned_grms

    def is_multilevel_approval(self):
        """
            multilevel approvals need to display the roles that have order.approve permissions
            based on a BPOI custom_field_value where the field name has an "_approver_id" at the
            end, and a valid role exists on the Group for that cfv field name

            returns a dictionary of the roles or an empty dict
        """
        if not self.orderitem_set.first():
            return {}
        oi = self.orderitem_set.first().cast()
        if not oi or not hasattr(oi, 'blueprintitemarguments_set'):
            return {}

        bpoi = oi.blueprintitemarguments_set.first()
        approval_levels = {}
        if not bpoi:
            return {}
        for cfv in bpoi.custom_field_values.filter(field__name__endswith='_approver_id'):
            role_name = cfv.field.name.replace('_approver_id', '')
            ml_approver_role = Role.objects.get(name=role_name, permissions__name='order.approve')
            if ml_approver_role:
                approval_levels[ml_approver_role] = cfv.value
        return approval_levels

    def should_auto_approve(self):
        """
        Return True if this order should be automatically approved. An order
        should be auto approved if either it's group has auto approve enabled,
        if the submitter is also an approver on this group,
        or if all of its order items have environments with auto approve
        enabled.

        and now if the multi_level auto approval roles are granted to this user profile
        """
        if self.group and self.group.allow_auto_approval:
            return True

        # some orders (like those duplicated by CIT) will not have owners
        if self.is_multilevel_approval():
            if self.has_all_approver_roles(self.owner, self.group):
                return True
            return False

        else:
            if self.owner and self.owner.has_permission('order.approve', self.group):
                return True

        return False

    def has_all_approver_roles(self, profile, group):
        '''
            for multi_level approvals we want to know if we can approve the order
            as part of should_auto_approve()
        '''
        #Roles
        r_needed = Role.objects.filter(grouprolemembership__group=group,
                                       permissions__name='order.approve')
        if len(r_needed) > 1:
            r_needed = r_needed.exclude(name='approver').distinct()

        #GroupRoleMemberships
        r_owned = CustomOrder.get_my_grms(self, profile)

        if len(r_needed) == len(r_owned):
            #if the number of GRMs == the number of Roles for that group
            return True

        return False

    def start_approval_process(self, request=None):
        """
        This method determines what order process should be taken, and
        takes it.  By default, the process is to email the approvers, but
        this can be overriden by customers to instead call out to a hook,
        and that can be overridden by auto-approval (set on the group or
        env, or by the owner being an approver or a super admin).

        This method returns a message summarizing what action was taken.

        `request` is needed to determine the current portal URL; if not
        passed, default portal URL is used.
        """
        # done here to avoid circular import
        from cbhooks.models import HookPoint

        hook_point = HookPoint.objects.filter(name="order_approval").first()
        orch_actions = cbhooks._get_orchestration_actions_to_run(hook_point)
        if orch_actions:
            #the orchestration action NEEDs to be first in order to allow a hook
            # to model the approval process correctly and not have something
            # auto-approve before the hook is run
            logger.debug("Order Approval orchestration actions exist, so bypassing built-in approver emails.")
            try:
                cbhooks.run_hooks("order_approval", order=self)
            except cbhooks.exceptions.HookFailureException as e:
                msg = _("Failed to run hook for order approval. Status: {status},"
                        " Output: {output}, Errors: {errors}").format(status=e.status, output=e.output, errors=e.errors)
                raise CloudBoltException(msg)
            return ""

        #now that the hooks have run, check if it should be auto-approved
        profile = request.get_user_profile()
        if self.is_multilevel_approval():
            self.approve_my_grms(profile)

        if self.should_auto_approve():
            logger.debug("Order can be automatically approved, attempting approval by {}".format(self.owner))
            jobs, msg = self.approve(self.owner)
            if jobs:
                msg = render_to_string(
                    'orders/approved_msg.html', {
                        'order': self,
                        'autoapproved': True,
                        'num_jobs': len(jobs),
                        'extramsg': msg,
                    })
            return msg
        else:
            # No auto approval and no approval hooks, so go with
            # the default process of emailing a set of approvers, unless the
            # owner is an approver.
            msg = _("Order #{order_id} has been submitted for approval.  ").format(order_id=self.id)
            msg += orders.mail.email_approvers(self, request)
            logger.debug(msg)
            return msg

    def approve(self, approver=None, parent_job=None):
        """
        Sets this order to the "Active" status and kicks off the jobs needed
        to complete this order.

        One job of the appropriate type ('provision' or 'decom') is kicked
        off per OrderItem for this order.  An exception to this statement is
        if the "quantity" field on the OrderItem is set, then a set of
        identical jobs will be kicked off (however many are specified by
        quantity).

        Returns list of jobs and error messages from any cleanup of order
        items.
        """
        if self.status != 'PENDING':
            msg = _(
                "Only orders that are in 'PENDING' state can be approved. "
                "Current state of order is '{status}'."
            ).format(status=self.status)
            raise CloudBoltException(msg)

        approve_this_order = False
        if self.is_multilevel_approval():
            logger.info('models.approve is multilevel!')
            self.approve_my_grms(approver)
            logger.info(f'models.approve after approve_my_grms ({approver})!')
            if self.is_multilevel_approval():
                logger.info('models.approve ml approval complete!')
                approve_this_order = True
        else:
            logger.info('models.approve is NOT multilevel!')
            #single-level approval
            approve_this_order = True

        if not approve_this_order:
            #should only kick off if multilevel approvals
            msg = _(
                "Cannot fully approve this order.  Multilevel approvals not complete. "
                "Current state of order is '{status}'."
            ).format(status=self.status)
            return [], msg

        try:
            # Raise an error to bubble up specific reason as part of the exception
            self.group.quota_set.can_use(raise_error=True, **self.net_usage())
        except QuotaSetError as quota_set_error:
            raise QuotaError(_(
                "Cannot approve order #{order_id} because doing so would exceed the "
                "quota for group '{group}'.  {error}"
            ).format(order_id=self.id, group=self.group, error=quota_set_error))

        # Before we create job records, order the order items to make
        # sure decom jobs are queued before prov jobs.  the job engine
        # may still parallelize them, that's something we can revisit
        # later.  In the meantime, customers can set the concurrency
        # level to 1 to prevent this.
        # we're taking advantage of the fact that "decom" comes before
        # "prov" in the alphabet here.
        order_items = [oi.cast() for oi in self.top_level_items.order_by(
            "real_type", "add_date")]

        order_items, msg = self.__filter_illegal_order_items(order_items)
        if not order_items:
            msg = _("{message}  There are no valid order items left.  This order is "
                    "being marked as complete.").format(message=msg)
            self.complete("SUCCESS")
            return [], msg

        self.status = "ACTIVE"
        self.approved_by = approver
        self.approve_date = get_current_time()
        self.save()

        history_msg = _("The '{order}' order has been approved.").format(order=escape(self))
        self.add_event('APPROVED', history_msg, profile=self.owner)

        # run pre order execution hook
        try:
            cbhooks.run_hooks("pre_order_execution", order=self)
        except cbhooks.exceptions.HookFailureException as e:
            self.status = "FAILURE"
            self.save()
            msg = _("Failed to run hook for order approval. Status: {status},"
                    " Output: {output}, Errors: {errors}").format(status=e.status, output=e.output, errors=e.errors)

            history_msg = _("The '{order}' order has failed.").format(order=escape(self))
            self.add_event('FAILED', history_msg, profile=self.owner)
            raise CloudBoltException(msg)

        from jobs.models import Job
        # Saving job objects will cause them to be kicked off by the
        # job engine within a minute
        jobs = []

        for order_item in order_items:
            jobtype = getattr(order_item, 'job_type', None)
            if not jobtype:
                # the job type will default to the first word of the class type
                # ex. "provision", "decom"

                jobtype = str(order_item.real_type).split(" ", 1)[0]
            quantity = 1
            # quantity is a special field on order_items.  If an
            # order_item has the quantity field, kick off that many
            # jobs
            if hasattr(order_item, 'quantity') and \
                    order_item.quantity is not None and \
                    order_item.quantity != '':
                quantity = int(order_item.quantity)
            for i in range(quantity):
                job = Job(job_parameters=order_item,
                          type=jobtype,
                          owner=self.owner,
                          parent_job=parent_job)
                job.save()

                # Associate the job with any server(s)
                # This may seem unnecessary because it's done when most jobs
                # run, but it's needed at the very least for scheduled server
                # modification jobs (for changing resources) so they show up on
                # the server as scheduled before they actually run
                servers = []
                if hasattr(order_item, "server"):
                    servers = [order_item.server]
                elif hasattr(order_item, "servers"):
                    servers = order_item.servers.all()
                for server in servers:
                    server.jobs.add(job)

                jobs.append(job)

        # If it didn't make any jobs, just call it done
        if not jobs:
            self.complete("SUCCESS")

        return jobs, msg
