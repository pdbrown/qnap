from __future__ import print_function
import sys
import os
import json
import logging
from optparse import OptionParser

from qnap_client import QnapClient
from filestation import FileStation
from backup_manager import BackupManager

# Example usage
# Create creds.json (script looks in cwd by default), e.g.:
#   {"url": "https://me.myqnapcloud.com", "username": "admin", "password": "************"}
# Then:
#   python backup.py [-q] [-c creds.json] -n 5 ./documents.tgz /backups/phil/documents

logging.basicConfig()

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

parser = OptionParser(usage="usage: %prog [-q] [-c creds_file] -n <num_to_keep> local_file remote_backup_path")
parser.add_option("-n", type="int", dest="count", help="Number of old backups to keep")
parser.add_option("-c", type="string", dest="creds", help="Credentials json file.")
parser.add_option("-q", action="store_true", dest="quiet", help="Quiet")
(options, args) = parser.parse_args()
if len(args) < 2:
    parser.error("Must specify both local_file and remote_backup_path")
local_src_path = args[0]
remote_backup = args[1]

if not options.count:
    parser.error("Must specify number of backups to keep with -n")

if options.creds:
    creds = options.creds
else:
    creds = 'creds.json'

if not os.path.isfile(creds):
    eprint(creds + " file not found in current directory. Create one or specify an alternate location with -c.")
    sys.exit(1)

with open(creds) as creds_file:
    creds = json.load(creds_file)

qnap = QnapClient(creds['url'])
logged_in = qnap.login(creds['username'], creds['password'])
creds = None
if not logged_in:
    eprint("QNAP login failed.")
    sys.exit(1)

fs = FileStation(qnap)
backups = BackupManager(fs)

backups.upload_backup(local_src_path, remote_backup, options.count, options.quiet)
