# Sample Order Approval Workflows

As of version 8.8, CloudBolt offers more robust support for custom order approval workflows. These workflows, which can be enabled for specific groups, allow CloudBolt admins to completely overhaul CloudBolt's standard order approval process, enabling features such as multiple user approvals, multiple group approvals in both parallel and serial, conditional approvals based on internal or external threshold validation, and more!

After upgrading to version 8.8, you will find that one Order Approval workflow ships out-of-the-box, entitled "Two Approvers", which can be found under _Admin > Actions > Orchestration Actions > Order Trigger Points_. Other, more complicated workflows, can be imported from the Content Library. Currently, there are four sample workflows, including the out-of-the-box option, to get you started. All of these workflows are included for demonstration purposes, and while functional, are meant to exemplify different levels complexity supported by this feature. These sample workflows are designed to be copied, modified, and extended to suit your needs!

Some workflows require two Orchestration Actions to be enabled to work properly. Actions in the "Order Submission" trigger point are executed immediately after an order is submitted, whereas actions in the "Post-Order Approval" trigger point are executed when a user approves an order. These trigger points serve very different purposes, and you can read all about them in [CloudBolt's documentation on Order Approval Plug-ins](http://docs.cloudbolt.io/advanced/orchestration-actions/cloudbolt-plugins/index.html#special-case-plug-ins).

The four sample workflows are explained below, starting simple and getting progressively more complex:

## Two Approvers

> This workflow requires that two users approve an Order before it becomes Active.

The "Two Approvers" workflow requires only one Orchestration Action, a single "Post-Order Approval" action, because we're only changing the behavior of the "Approve" button. In this plugin, we check to see if there are two users in `order.approvers`, which only returns unique users by design. As mentioned in the documentation linked above, the default behavior of a "Post-Order Approval" plug-in is to approve the order -- therefore, if the condition we're requiring (the number of approvers is at least two) is not met, we return the order back to the queue via the `order.set_pending()` method. This method, in addition to sending the order back to the queue, prevents the same user from approving the order twice, and adds the approval action to an order's Order History, which can be viewed on the order's detail page.

_Ideas for extending this plug-in:_ require a different number of users approve an order, or check that at least one of the approvers is a specific user.

The "Post-Order Approval" trigger point is especially powerful -- this plug-in demonstrates that, with only four lines of Python, we can completely change CloudBolt's order approval workflow.

## Multiple Group Approval

> This workflow requires users from two separate Groups approve an Order (e.g. in parallel) before it becomes Active.

Similar to the previous example, the "Multiple Group Approval" workflow only requires a single "Post-Order Approval" action. This plugin is the next step in complexity, requiring not only that two users approve the order, but that those users are in two specified groups, neither of which is the group that placed the order. To use this plug-in without modifications, some minor configuration on the groups in your CloudBolt is required. Namely, this plug-in leverages the new "Approval Permission" relationship that's present on a group's detail page in CloudBolt version 8.8+. This relationship gives Approvers in a group (e.g. "Finance") approval permission over another group's orders (e.g. "Workers"), even the latter group is not a sub-group of the former. Additionally, this plug-in makes use of the `order.all_groups_approved()` method, which verifies that all of the groups passed to the method have approved the order. It is by passing two groups to this method that we allow the approvals to effectively happen in parallel, meaning that we're not concerned with the sequence in which different groups approve the order.

_Ideas for extending this plug-in:_ require that _two_ users from the "IT" group and one user from "Finance" group approve the order.

## Hierarchical, Multiple Group Approval

> This workflow requires that users from two separate Groups approve an Order in a specified order (e.g. in series) before it becomes Active.

With the next step up in complexity, the "Hierarchical, Multiple Group Approval" workflow is the first to require two Orchestration Actions. This workflow, in contrast to the former "Multiple Group Approval", specifies that an order must be approved by groups in a specified sequence (e.g. in series). To do so, we'll use the `order.groups_for_approval` attribute. If this attribute is set to a specific group, the order can be approved by that group only, whereas if the the attribute is set to `None`, the order can be approved all groups that have approval permission over the requesting group. This workflow uses an action at the "Order Submission" trigger point to assign the order to the "Finance" group immediately after the order is submitted, which is why we need two Orchestration Actions. The "Post-Order Approval" action, on the other hand, verifies that the first approval came from the "Finance" group and assigns the "IT" group to approve the order, again by using `order.groups_for_approval` -- then, after a second user from the "IT" group approves the order, the order is executed.

_Ideas for extending this plug-in:_ require that a second user from the "Finance" group approve the order after it's been approved by one user from "Finance" and one user from "IT".

## Threshold Check

> This workflow checks if an Order crosses specified quota limits, and requires different number of approvals depending on the cost.  
> 
> If no threshold is exceeded, the Order is automatically approved. If any of the configured values exceed 50%, but less than 90%, of the Group's quota, we required one approver. If the configured values exceed 90% of the Group's quota, we require that one user from the IT Group _and_ one user from the Finance Group approve the order.

The code for this final workflow _initially_ looks a lot more complex that the previous three examples, but we'll see that the actual order approval logic is even simpler than the last workflow. Looking at the description of what this workflow does, we can see why two actions are needed -- one action is used to automatically approve the order if a condition is met when it's submitted, and the second is used to conditionally change the behavior of the approve button. If we open the two `threshold_check_*.py` scripts and scroll down to the `run()` functions, we see that the order approval logic uses methods that we're comfortable with at this point in the tutorial. The complexity of this workflow, therefore, comes from the two other functions (which are identical between the two scripts), which allow us to question how the order is effecting our group's quota limits.

While group quotas in CloudBolt are a very effective tool, this sort of validation is just the tip of the iceberg for threshold-based approval. This workflow can be extended to, for example, reach out to an external service that checks how much space remains on the server your users are provisioning to and modify the approval workflow based on that information.

---

## Conclusion

We hope that these four sample order approval workflows serve as a useful introduction into the power and extensibility of this area of CloudBolt. We encourage users to add their custom workflows to this repository, and to reach out to our Professional Services team if you would like any assistance creating the custom approval workflow of your dreams. Thank you for reading, and happy CloudBolting!
