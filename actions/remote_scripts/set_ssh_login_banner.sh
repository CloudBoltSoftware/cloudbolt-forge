#!/bin/bash
#
# Display Welcome or Warning message for SSH users before login. We use issue.net file to display a banner massages.
cat >> /etc/issue.net << EOF
#########################################
#                                       #
#    ALL YOUR CASE ARE BELONG TO US     #
#                                       #
#########################################
EOF
echo Banner /etc/issue.net >> /etc/ssh/sshd_config
service sshd reload
