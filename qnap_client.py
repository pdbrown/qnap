import logging
import requests
import xml.etree.ElementTree as ET
import urlparse
import urllib

from get_sid import ezEncode

class QnapClient():
    def __init__(self, url):
        urlparse.urlparse(url)
        self.base_url = url
        self.sid = None

    def login(self, user, passwd):
        url = urlparse.urljoin(self.base_url, '/cgi-bin/authLogin.cgi')
        res = requests.post(url, {'user': user.replace('\\', '+'),
                                  'pwd': ezEncode(passwd)})
        if res.status_code != 200:
            return False

        qdoc_root = ET.fromstring(res.text)
        if qdoc_root is None:
            return False

        auth_passed = qdoc_root.find('authPassed').text
        if auth_passed is None or int(auth_passed) != 1:
            return False

        self.sid = qdoc_root.find('authSid').text
        return True

    def post_form(self, path, params):
        url = urlparse.urljoin(self.base_url, path)
        params_auth = params.copy()
        if self.sid:
            params_auth['sid'] = self.sid
        res = requests.post(url, params_auth)
        if res.status_code != 200:
            logging.error('Request for %s failed with %d:' % [path, res.status_code])
            return None
        return res

    def post_multipart(self, path, data):
        url = urlparse.urljoin(self.base_url, path)
        if self.sid:
            if "?" in path:
                url = url + "&sid=" + urllib.quote(self.sid)
            else:
                url = url + "?sid=" + urllib.quote(self.sid)
        res = requests.post(url, data, headers={'content-type': 'multipart/form-data;'})
        if res.status_code != 200:
            logging.error('Request for %s failed with status %d' % (path, res.status_code))
            return None
        return res
