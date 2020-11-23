INSTALL_WINDOWS_AGENT = """
# download the cloud endure agent
Invoke-WebRequest -Uri https://console.cloudendure.com/installer_win.exe -OutFile C:\installer_win.exe

# install the agent, and configure it using your account's agent installation token.
C:\installer_win.exe -t "{{ agent_installation_token }}" --no-prompt
"""

INSTALL_LINUX_AGENT = """
#download the cloudendure agent
wget -O ./installer_linux.py https://console.cloudendure.com/installer_linux.py

#install the agetn, using your account's agent installation token
sudo python ./installer_linux.py -t "{{ agent_installation_token }}" --no-prompt
"""
