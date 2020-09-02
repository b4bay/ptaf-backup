# Copy backup from PT AF to external storage

## Copy to local folder
```
pt@ptaf-vm:~/ptaf-backup$ sudo /opt/waf/python/bin/python ./ptaf-copy-backup-to-local-dir.py -h
usage: ptaf-copy-backup-to-local-dir.py [-h] [-t SCHEDULE] [-f FOLDER]

Copy backup from PT AF to local directory

optional arguments:
  -h, --help            show this help message and exit
  -t SCHEDULE, --task-schedule SCHEDULE
                        Name of Task Schedule to check, e.g. "Main settings".
                        Default is "All settings"
  -f FOLDER, --folder FOLDER
                        Full path to store backup, e.g. /folder1/subfolder/.
                        Default is /backup/
```

## Copy to SMB share
```
pt@ptaf-vm:~/ptaf-backup$ /opt/waf/python/bin/python ./ptaf-copy-backup-to-smb.py -h
usage: ptaf-copy-backup-to-smb.py [-h] [-t SCHEDULE] [-s HOST] [-f FOLDER]
                                  [-d DOMAIN] [-l LOGIN] [-p PASSWORD]

Export backup from PT AF

optional arguments:
  -h, --help            show this help message and exit
  -t SCHEDULE, --task-schedule SCHEDULE
                        Name of Task Schedule to check, e.g. "Main settings"
  -s HOST, --server HOST
                        Server name or IP to store backup, e.g. MYSERVER or
                        192.16.0.1
  -f FOLDER, --folder FOLDER
                        Path to share excluding root, e.g. folder1
  -d DOMAIN, --domain DOMAIN
                        Domain for login, e.g. MYDOMAIN
  -l LOGIN, --login LOGIN
                        Username for share, e.g. Administrator
  -p PASSWORD, --password PASSWORD
                        Password for share, e.g. P@ssw0rd

```