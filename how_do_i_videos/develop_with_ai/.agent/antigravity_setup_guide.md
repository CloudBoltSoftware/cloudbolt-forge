# Enabling Antigravity for CloudBolt Development

 This guide provides a step-by-step process for configuring Antigravity to be an expert CloudBolt developer. By following these instructions, you will replicate the setup used to build robust, standardized CloudBolt plugins.

 ## Prerequisites
 - **Antigravity Installed**: Ensure you have the Antigravity VS Code extension or standalone IDE installed.
 - **SSH Access**: You must have SSH access (root or sudo user) to your CloudBolt appliance.

 ---

 ## Step 1: Connect to CloudBolt
 1. Open Antigravity.
 2. Use the **Remote-SSH** feature to connect to your CloudBolt appliance.
    ```bash
    ssh root@<your-cloudbolt-ip>
    ```

 ---

 ## Step 2: Configure Workspaces
 You need to map the critical CloudBolt directories to Antigravity workspaces. This ensures the AI has access to both your customizations and the shared logic library.

 1. Open **File > Open Folder...** and select `/var/opt/cloudbolt/proserv`.
 2. (Optional) Add the Shared Modules directory to your workspace if you use them:
    - **Add Folder to Workspace**: `/var/www/html/cloudbolt/static/uploads/shared_modules`.

 ---

 ## Step 3: Import Intelligence
 To give Antigravity the specialized knowledge it needs, simply copy the standardized `.agent` configuration to your new system.
 
 1. **Locate the Source**: Find the `.agent` folder from your existing CloudBolt development environment (or download the standard package).
 2. **Copy to Target**: Place the `.agent` folder into the root of your `proserv` directory on the new system:
    ```bash
    cp -r /path/to/source/.agent /var/opt/cloudbolt/proserv/
    ```
 3. **Verify Integrity**: Ensure the following structure exists:
    ```text
    /var/opt/cloudbolt/proserv/.agent/
       ├── brain/
       │   └── development_context.md
       ├── skills/
       │   └── cloudbolt/
       │       └── SKILL.md
       ├── workflows/
       │   ├── create-blueprint.md
       │   ├── create-shared-module.md
       │   └── create-xui.md
       └── antigravity_setup_guide.md
    ```
 
 Antigravity will automatically detect these resources the next time you open the workspace.
