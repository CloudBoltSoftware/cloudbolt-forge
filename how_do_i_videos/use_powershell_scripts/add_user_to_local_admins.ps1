$user = "{{user_upn}}"

# Add user to local admins group
Add-LocalGroupMember -Group "Administrators" -Member $user

Write-OutPut "User $user added to local admins group"
Write-OutPut "On server: {{server.hostname}}"