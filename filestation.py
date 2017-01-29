import logging
import json
import os
import urllib
import re
import time
from requests_toolbelt.multipart import encoder

class FileStation():
    """
    Access QNAP FileStation.
    """

    def __init__(self, qnap_client):
        self.qnap_client = qnap_client

    def post_form(self, func, params):
        path = '/cgi-bin/filemanager/utilRequest.cgi?func=' + func
        return self.qnap_client.post_form(path, params)

    @staticmethod
    def decode_response(res, failure_msg):
        if res is None:
            logging.error(failure_msg)
            return None
        return json.loads(res.text)


    def list_shares(self):
        """
        List all shares.
        """
        res = self.post_form('get_tree', {'node': 'share_root'})
        return FileStation.decode_response(res, 'Failed to list shares')

    def list(self, path, limit=10000):
        """
        List files in a directory.
        """
        res = self.post_form('get_list', {'path': path, 'limit': limit})
        return FileStation.decode_response(res, 'Failed to list path')

    def stat(self, path):
        """
        Get file information.
        """
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)

        res = self.post_form('stat', {'path': dirname, 'file_name': basename})
        return FileStation.decode_response(res, 'Failed to stat file')

    def rename(self, path, new_filename):
        """
        Rename without overwrite.
        """
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)

        res = self.post_form('rename', {'path': dirname,
                                        'source_name': basename,
                                        'dest_name': new_filename})
        res = FileStation.decode_response(res, 'Failed to rename file')
        if res is None:
            return None
        if res['status'] == 2:
            logging.error('Failed to rename file because renaming would have overwritten an existing file.')
            return None
        elif res['status'] != 1:
            logging.error('Failed to rename file for unknown reason.')
            return None
        else:
            return res

    def delete(self, path):
        """
        Delete without recyle bin.
        """
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)

        res = self.post_form('delete', {'path': dirname,
                                        'file_name': basename,
                                        'file_total': 1,
                                        'v': 1,      # verbose response
                                        'force': 1}) # no recycle bin
        return FileStation.decode_response(res, 'Failed to delete file')

    def download(self, path):
        """
        Download file. Returns response object for use with:

        with open(filename, 'wb') as fd:
          for chunk in response.iter_content(chunk_size=128):
            fd.write(chunk)
        """
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        basename_encoded = urllib.quote(basename)

        request_path = '/cgi-bin/filemanager/utilRequest.cgi/' + basename_encoded
        res = self.qnap_client.post_form(
            request_path,
            {'func': 'download',
             'isfolder': 0,
             'source_total': 1,
             'source_path': dirname,
             'source_file': basename})

        if res is None:
            logging.error('Failed to download ' + path)
            return None
        return res


    class ProgressReporter():

        def __init__(self, total_size_bytes):
            self.total_size_bytes = total_size_bytes
            self.total_size_mb = total_size_bytes / 1024.0 / 1024
            self.bytes_uploaded = 0
            self.last_update_epoch_seconds = 0
            self.time_started_epoch_seconds = time.time()

        def report(self, monitor):
            # monitor.bytes_read reports size including multipart form headers. It's ok to ignore this
            # as long as part_body.len sufficiently > part_headers.len
            self.bytes_uploaded = min(monitor.bytes_read, self.total_size_bytes)
            now_epoch_sec = time.time()
            if now_epoch_sec > self.last_update_epoch_seconds + 5:
                self.last_update_epoch_seconds = now_epoch_sec
                mb_uploaded = self.bytes_uploaded / 1024.0 / 1024
                print "Uploaded %f of %f MB at %f MB/s" % (
                    mb_uploaded,
                    self.total_size_mb,
                    mb_uploaded / (now_epoch_sec - self.time_started_epoch_seconds))

        def finish(self):
            print "Finished uploading %f MB in %f seconds." % (
                self.total_size_mb,
                time.time() - self.time_started_epoch_seconds)

    def upload(self, local_src_path, remote_dest_path, overwrite=False):
        """
        Upload file.
        """
        if remote_dest_path[0] != '/':
            logging.error("remote_dest_path must be absolute and begin with /")
            return None

        remote_dirname = os.path.dirname(remote_dest_path)
        remote_basename = os.path.basename(remote_dest_path)

        # From docs:
        # Where to put tmp (If you used share root path(/Download, /Public, ...)
        # as the value of parameter “upload_root_dir” , it will be auto cleaned in period of 7 days later.
        if remote_dirname.count("/") <= 1:
            upload_root_dir = remote_dirname
        else:
            upload_root_dir = "/" + re.split("\/", remote_dirname)[0]

        start_res = self.post_form('start_chunked_upload', {'upload_root_dir': upload_root_dir})
        start_res = FileStation.decode_response(start_res, 'Failed to start chunked upload')
        if start_res['status'] != 0:
            logging.error('Failed to start chunked upload with error code %d' % start_res['status'])
            return None

        upload_id = start_res['upload_id']

        params = {'func': 'chunked_upload',
                  'upload_id': upload_id,
                  'dest_path': remote_dirname,
                  'upload_root_dir': upload_root_dir,
                  'upload_name': remote_basename,
                  'overwrite': 1 if overwrite else 0,
                  'offset': 0,
                  'filesize': os.stat(local_src_path).st_size}

        request_path = '/cgi-bin/filemanager/utilRequest.cgi?' + urllib.urlencode(params)

        progress_reporter = FileStation.ProgressReporter(params['filesize'])
        with open(local_src_path, 'rb') as src_file:
            e = encoder.MultipartEncoder(
                fields=([('fileName', remote_basename),
                         ('file', ('blob', src_file, 'application/octet-stream'))]))
            m = encoder.MultipartEncoderMonitor(e, progress_reporter.report)
            res = self.qnap_client.post_multipart(request_path, m)

        progress_reporter.finish()
        return res
