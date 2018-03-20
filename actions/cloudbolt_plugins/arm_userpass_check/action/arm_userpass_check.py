# This performs regex matching in the order form validation hook
# Since we can return pretty errors here, instead of showing the user regexes
# in regex contraints of parameters.
#
#
# Copyright 2018 Aves-IT B.V.
# 
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re

def validate_order_form(requestor, group, env, quantity, hostname, cfvs, pcvss, 
                        os_build=None):
    errors_by_field_id = {}

    password = None
    username = None

    for cfv in cfvs:
        if cfv.field.name == 'password':
            password = cfv.pwd_value
        elif cfv.field.name == 'username':
            username = cfv.str_value

    if password is not None:
        # See https://blogs.technet.microsoft.com/poshchap/2016/10/14/regex-for-password-complexity-validation/
        pattern = r"^((?=.*[a-z])(?=.*[A-Z])(?=.*\d)|(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9])|(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z0-9])|(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]))([A-Za-z\d@#$%^&£*\-_+=[\]{}|\\:',?/`~\"();!]|\.(?!@)){8,123}$"
        if not re.match(pattern, password):
            error_str = 'Please provide a complex password (8-123 chars, upper/lowercase, numbers, special characters)'
            errors_by_field_id['password'] = error_str

    if username is not None:
        # Construct regex to cover: "not root, not administrator, cannot be more than 20 characters long, end with a period(.), or contain the following characters: \ / " [ ] : | < > + = ; , ? * @."
        # TODO: Figure out how much of https://docs.microsoft.com/en-us/azure/virtual-machines/windows/faq/#what-are-the-username-requirements-when-creating-a-vm is actually enforced by the API
        pattern = r"[^\\\/\"\[\]\:\|\<\>\+\=\;\,\?\*]{1,19}[^\\\/\"\[\]\:\|\<\>\+\=\;\,\?\*\.]$"
        if not re.match(pattern, username):
            error_str = 'Please provide a valid username (2-20 chars, cannot end with a (.) or contain \/"[]:|<>+=;,?*@ )'
            errors_by_field_id['username'] = error_str
       
    return errors_by_field_id

# vim: set ts=2 et tw=78 ff=unix ft=python:
