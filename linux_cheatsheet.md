# Linux Cheatsheet

This cheatsheet provides examples of common Linux commands for general usage.

## Navigating around Linux

### CD (Change Directory)

`cd` is used to change the current working directory.

```bash
cd /path/to/directory
```

The CloudBolt operating folder where the manage.py is stored is located at /opt/cloudbolt.
```bash
cd /opt/cloudbolt
```

The Proserv directory, which is upgrade save and contains your customizations, is located at /opt/proserv.
```bash
cd /var/opt/cloudbolt/proserv
```
### VI (Text Editor)

vi is a command-line text editor. You can open a file with the following command:

```bash

vi filename.txt
```
### Quit

Press ESC to exit the "insert" mode, then type :q and press Enter to quit without saving.
Save

Press ESC to exit the "insert" mode, then type :w and press Enter to save the file.

To save and quit, type :wq and press Enter.


### Viewing files

ls -la is used to display detailed information about files and directories in the current directory.

The ls command shows a list of files and directories with additional information such as permissions, ownership, size, and modification date.
What the letters mean
```bash
ls -la

total 24
drwxr-xr-x  5 user group 4096 Mar 24 12:34 .
drwxr-xr-x  7 user group 4096 Mar 24 11:11 ..
-rw-r--r--  1 user group  164 Mar 24 12:00 .bashrc
drwxr-xr-x  2 user group 4096 Mar 24 12:01 Documents
drwxr-xr-x  2 user group 4096 Mar 24 12:02 Downloads
-rw-r--r--  1 user group   43 Mar 24 12:34 example.txt
```
    -: Regular file
    d: Directory
    l: Symbolic link

### File permissions

The first column of the ls -la output represents the file permissions, which are grouped into three sets of three characters:

    Owner permissions
    Group permissions
    Other permissions

Each set has three characters that represent read (r), write (w), and execute (x) permissions.

For example, drwxr-xr-x means:

    d: Directory
    rwx: Read, write, and execute permissions for the owner
    r-x: Read and execute permissions for the group
    r-x: Read and execute permissions for others

cat

cat is used to display the contents of a file.

```bash

cat filename.txt
```
