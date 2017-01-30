import logging
import os
import json
import re
import time
from qnap_client import QnapClient
from filestation import FileStation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_TOTAL_BACKUPS = 10000

def cmp_backup_names(x, y):
    """
    Comparator for backup file names with date and possible ordinal suffix:
    "abc.2016-01-01" < "abc.2016-01-02.2" < "abc.2016-01-02.10"
    Behavior is undefined if file names differ other than their suffixes.
    """
    xs = x.split(".")
    ys = y.split(".")
    max_len = max(len(xs), len(ys))
    if len(xs) < max_len:
        x_ord = 0
        x_date = xs[-1]
    else:
        x_ord = int(xs[-1])
        x_date = xs[-2]
    if len(ys) < max_len:
        y_ord = 0
        y_date = ys[-1]
    else:
        y_ord = int(ys[-1])
        y_date = ys[-2]

    if x_date == y_date:
        return x_ord - y_ord
    else:
        return cmp(x_date, y_date)

class BackupManager():

    def __init__(self, fs):
        self.fs = fs

    def load_backup_names(self, remote_path):
        """
        Retrive existing backup names for backup at remote_path sorted from oldest to newest.
        """
        backup_basename = os.path.basename(remote_path)
        remote_dirname = os.path.dirname(remote_path)
        remote_listing = self.fs.list(remote_dirname, MAX_TOTAL_BACKUPS)
        if remote_listing is None:
            logging.error("Failed to load list of existing backups")
            return None
        remote_listing = remote_listing['datas']
        if len(remote_listing) >= MAX_TOTAL_BACKUPS:
            logging.error("Found more than limit of %d possible backups, aborting." % MAX_TOTAL_BACKUPS)
            return None

        remote_backups = [f['filename'] for f in remote_listing
                          if f['isfolder'] == 0 and
                          re.match("^%s\.\d{4}-\d{2}-\d{2}(\.\d+)?$" % backup_basename, f['filename'])]
        remote_backups.sort(cmp_backup_names)
        return remote_backups

    def delete_oldest_backups(self, remote_path, num_to_keep):
        if num_to_keep <= 0:
            raise RuntimeError("Must keep at least one backup.")
        remote_dirname = os.path.dirname(remote_path)
        backups = self.load_backup_names(remote_path)
        if backups is None:
            raise RuntimeError("Failed to load old backup names for old backup cleanup.")
        for i in range(num_to_keep):
            if not backups:
                break
            backups.pop() # remove backups we want to keep
        for backup in backups:
            if not self.fs.delete(os.path.join(remote_dirname, backup)):
                raise RuntimeError("Failed to delete old backup " + os.path.join(remote_dirname, backup))

    @staticmethod
    def get_conflicts(remote_backups, timestamped_name):
        return filter(lambda x: re.match("^%s(\.\d+)?$" % timestamped_name, x), remote_backups)

    def upload_backup(self, local_src_path, remote_path, num_to_keep, quiet=False):
        remote_dirname = os.path.dirname(remote_path)
        remote_basename = os.path.basename(remote_path)
        remote_backups = self.load_backup_names(remote_path)
        if remote_backups is None:
            raise RuntimeError("Failed to load old backup names for backup rotation.")
        timestamped_name = remote_basename + "." + time.strftime("%Y-%m-%d")
        if BackupManager.get_conflicts(remote_backups, timestamped_name):
            timestamped_name += "." + str(int(time.time()))
        upload_path = os.path.join(remote_dirname, timestamped_name)
        logger.info("Uploading new backup to " + upload_path)
        if self.fs.upload(local_src_path, upload_path, False, quiet) is None:
            raise RuntimeError("Failed to upload backup.")
        self.delete_oldest_backups(remote_path, num_to_keep)
