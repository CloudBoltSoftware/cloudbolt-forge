from urllib.parse import urlparse

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.template import loader
from django.urls import reverse
from django.utils.translation import ugettext as _, ungettext

from accounts.models import UserProfile
from accounts.templatetags import account_tags
from cbhooks.exceptions import HookFailureException
from common.views import clear_cached_submenu
from costs.utils import (
    is_rates_feature_enabled,
)
from cscv.models import CITConf, can_order_be_tested, CITTest
from orders.forms import DenyOrderForm
from orders.models import Order
from orders.templatetags.order_tags import order_pictograph, order_status_icon
from quota.exceptions import QuotaError
from servicecatalog.models import ServiceBlueprint
from utilities.decorators import json_view, dialog_view
from utilities.exceptions import (
    InvalidCartException, InvalidConfigurationException,
    CloudBoltException
)
from utilities.cb_http import django_sort_cols_from_datatable_request
from utilities.logger import ThreadLogger
from utilities.templatetags.helper_tags import link_or_label, how_long_ago
from utilities.views import access_denied

from .models import CustomOrder


from extensions.views import admin_extension



#@admin_extension(title='Multilevel Approvals Extension')
logger = ThreadLogger(__name__)

# Intentionally not protected at view level
@admin_extension(title='Multilevel Approvals Extension')
def order_list(request, message=""):
    profile = request.get_user_profile()

    # NOTE: order info will be sent via AJAX
    return render(request, 'multilevelapprovals/templates/list.html', {
        'pagetitle': _("Order List"),
        'message': message,
        'profile': profile,
        'enable_rates_feature': is_rates_feature_enabled(),
    })

# Intentionally not protected at view level
@json_view
def order_list_json(request, extra_context={}):
    profile = request.get_user_profile()

    # List of orders the user has permissions to view:
    orders = Order.objects_for_profile(profile)
    num_total_records = orders.count()

    search = request.GET.get('sSearch')
    if search:
        orders = orders.search(search)

    num_filtered_records = orders.count()

    # Sorting: client passes column # which must be translated to model field
    sort_cols = django_sort_cols_from_datatable_request(request, [
        'id',
        None,
        'status',
        'group',
        # order by first & last which is how it's presented
        ['owner__user__first_name', 'owner__user__last_name'],
        'create_date',
        None,  # Actions column is not sortable
    ])
    orders = orders.order_by(*sort_cols)

    # Pagination:
    start = int(request.GET.get('iDisplayStart', None))
    if start is not None:
        end = int(start) + int(request.GET.get('iDisplayLength', 0))
        orders = orders[start:end]

    # Cache links to objects (since generating each requires a database hit):
    _group_link_or_label_cache = {}
    _owner_link_or_label_cache = {}
    profiles_visible_to_this_profile = UserProfile.objects_for_profile(profile)

    def cached_group_link_or_label(group):
        try:
            return _group_link_or_label_cache[group]
        except KeyError:
            rendered = link_or_label(group, profile)
            _group_link_or_label_cache[group] = rendered
            return rendered

    def cached_owner_link_or_label(owner):
        """
        Ensure that owner avatar and link-or-label is only constructed once
        per page view.
        """
        if not owner or not owner.user:
            return ""
        try:
            rendered = _owner_link_or_label_cache[owner]
        except KeyError:
            rendered = account_tags.rich_gravatar(
                owner,
                size=20,
                link=(owner in profiles_visible_to_this_profile),
                full_name=True
            )

            _owner_link_or_label_cache[owner] = rendered
        return rendered

    actions_template = loader.get_template('multilevelapprovals/templates/actions.html')
    rows = []
    for order in orders:
        # Render the actions column value as HTML:
        actions_html = actions_template.render(context={
            'order': order,
            'profile': profile,
            'is_owner': order.owner == profile,
            'can_approve': profile.has_permission('order.approve', order),
            'can_cancel': order.can_cancel(profile),
            'can_save_to_catalog': order.can_save_to_catalog(profile),
        }, request=request)

        #approval_str = "" #SRM
        #for dict in is_multilevel_approval(order):
        #    for key in dict.keys():
        #        strng = UserProfile.objects.get(id=dict[key]).user.username
        #        if not approval_str:
        #            approval_str = key + ":", strng
        #        else:
        #            approval_str += "<BR>" + key + ":", strng

        row = [
            # We know that the user has access to view this order already,
            # so show URL instead of link_or_label:
            '<a href="%s">%s</a>' % (order.get_absolute_url(),
                                     order.nickname()),
            order_pictograph(order),
            order_status_icon(order),
            cached_group_link_or_label(order.group),
            cached_owner_link_or_label(order.owner),
            how_long_ago(order.create_date),
            actions_html,
        ]
        rows.append(row)

    return {
        # unaltered from client-side value, but cast to int to avoid XSS
        # http://datatables.net/usage/server-side
        "sEcho": int(request.GET.get('sEcho', 1)),
        "iTotalRecords": num_total_records,
        "iTotalDisplayRecords": num_filtered_records,
        "aaData": rows,  # Orders for the current page only
    }

def modify(request, order_id):
    """
    POST requests from the order list and detail views go here.
    """
    order = get_object_or_404(Order, pk=order_id)
    profile = request.get_user_profile()

    # action matches the button values in order_actions templatetag.
    action = request.POST.get('action', [''])
    logger.info(f'SRM:  in modify: action == {action}')

    if action in ['approve', 'deny']:
        if not profile.has_permission('order.approve', order):
            return access_denied(
                request, _("You do not have permission to approve this item."))

    msg = ""
    redirect_url = request.META['HTTP_REFERER']

    if action == 'submit':
        if not profile.has_permission('order.submit', order):
            return access_denied(
                request, _("You do not have permission to submit this order."))
        try:
            order.submit()
            msg += order.start_approval_process(request)
            messages.info(request, msg)
        except QuotaError as e:  # could happen if order is auto-approved
            messages.error(request, e)
        except InvalidConfigurationException as e:
            messages.error(request, e)
        except HookFailureException as e:
            messages.error(request, e)
        redirect_url = reverse('order_detail', args=[order.id])

    elif action == 'approve':
        logger.info('SRM:  in modify: action == approve (should work) -- b4 approve_my_grms')
        logger.info(f'SRM:  order = {order}')
        logger.info(f'SRM:  profile = {profile}')
        if CustomOrder.is_multilevel_approval(order):
            logger.info(f'SRM:  is multilevel -- approving GRMs')
            CustomOrder.approve_my_grms(order, profile)
            if all(CustomOrder.is_multilevel_approval(order).values()):
                logger.info(f'SRM:  all values return true - can approve')
            else:
                logger.info(f'SRM:  not all values return true - cant approve')
                messages.info(request, "partial approval processed")
                return HttpResponseRedirect(reverse('order_detail', args=[order.id]))

        try:
            jobs, extramsg = order.approve(profile)
            if jobs:
                # template tweaks the message based on where we are going next
                redirect_parsed = urlparse(redirect_url)
                msg = loader.render_to_string('orders/approved_msg.html', {
                    'order': order,
                    'autoapproved': False,
                    'num_jobs': len(jobs),
                    'extramsg': extramsg,
                    'request': request,
                    'redirect_url': redirect_parsed.path,
                })
            else:
                msg = extramsg
            messages.info(request, msg)
        except QuotaError as e:
            messages.error(request, e)
        except CloudBoltException as e:
            messages.warning(request, e)
        except:
            raise

    elif action == 'cancel':
        if not order.can_cancel(profile):
            return access_denied(
                request, _("You do not have permission to cancel this order."))
        order.cancel()

        if order.owner:
            clear_cached_submenu(order.owner.user_id, 'orders')

        msg = _("Order #{order_id} has been canceled.").format(order_id=order.id)
        messages.info(request, msg)

    elif action == 'clear':
        order.group = None
        order.blueprint = None
        order.save()
        for order_item in order.orderitem_set.all():
            order_item.delete()

        if order.owner:
            clear_cached_submenu(order.owner.user_id, 'orders')

        messages.success(request, _("Your current order has been cleared."))

    elif action == 'remind':
        logger.info(_("User requested order approval reminder for order {order_id}").format(order_id=order_id))
        try:
            msg = order.send_reminder(request)
            logger.debug(msg)
            messages.info(request, msg)
        except InvalidConfigurationException as e:
            messages.error(request, e)

    elif action == 'duplicate':
        # Global Viewers are a special case where objects_for_profile will
        # return True since they can view all orders, but we don't want them to
        # be able to do anything like duplicate it (unless they have additional
        # permissions)

        duplicable, reason = order.can_duplicate(profile)
        if not duplicable:
            if reason == 'permission':
                return access_denied(
                    request, _("You do not have permission to duplicate this order."))
            elif reason == 'group':
                messages.error(request, _("Orders with no group cannot be duplicated."))
                return HttpResponseRedirect(reverse('order_detail', args=[order.id]))
        try:
            profile = request.get_user_profile()
            cart = profile.get_current_order()
            cart = order.duplicate(cart)
            items_duplicated = cart.items_duplicated
            hostnames_updated = cart.hostnames_updated

            msg = ungettext("Duplicated {num_items} order item under "
                            "<a href='{url}'>your current order</a>.",
                            "Duplicated {num_items} order items under "
                            "<a href='{url}'>your current order</a>.",
                            items_duplicated).format(num_items=items_duplicated,
                                                     url=cart.get_absolute_url())
            if hostnames_updated:
                uniq_msg = ungettext("{updated_count} order item was updated to "
                                     "avoid creating identical hostnames.",
                                     "{updated_count} order items were updated to "
                                     "avoid creating identical hostnames.",
                                     hostnames_updated).format(updated_count=hostnames_updated)
                msg += uniq_msg

            clear_cached_submenu(profile.user_id, 'orders')

            messages.success(request, msg)
            return HttpResponseRedirect(reverse('current_order'))

        except InvalidCartException as e:
            messages.error(request, e)

    elif action == 'save_as_blueprint':
        profile = request.get_user_profile()
        if order.group and not profile.has_permission('blueprint.manage', order.group):
            return access_denied(
                request, _("You need to have blueprint management permission for "
                           "group '{group}' to create a blueprint from this order.").format(group=order.group))

        bp = ServiceBlueprint.from_order(order)

        clear_cached_submenu(profile.user_id, 'catalog')

        messages.success(
            request,
            _("Successfully saved the <a href='{order_url}'>order</a> "
              "as blueprint <a href='{blueprint_url}'>{blueprint_name}</a>").format(
                  order_url=order.get_absolute_url(),
                  blueprint_url=bp.get_absolute_url(),
                  blueprint_name=bp.name))
        redirect_url = bp.get_absolute_url()

    elif action == 'add_to_cit':
        if can_order_be_tested(order):
            cit_test = CITTest.objects.create(
                name=order.name,
                order=order,
                cit_conf=CITConf.objects.first(),
                expected_status=order.status,
            )
            messages.success(
                request,
                _('Created CIT test "{}". It will be automatically tested during '
                  'the text text run.'.format(link_or_label(cit_test, profile)))
            )
        else:
            messages.error(request, "This order could not be added to CIT.")

    return HttpResponseRedirect(redirect_url)
