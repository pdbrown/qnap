Backups
=======

The included `backup_cli.py` script uploads date-stamped files to a QNAP host and ensures
it only keeps the n most recent copies.

Ensure the destination directory is accessible on the QNAP host, in this case `/backups`. Then:

```bash
# Add creds.json to cwd, (or elsewhere and use optional -c path/to/creds.json flag) e.g.:
echo '{"url": "https://me.myqnapcloud.com",
       "username": "admin",
       "password": "************"}' > creds.json
echo 'back me up' > important.txt
python backup_cli.py -n 5 important-file.txt /backups/important-file.txt
```

You should now see a copy of important-file.txt at
`/backups/important-file.txt.2017-01-29`. Note that the current date is appended
to the file name. If run more than once a day, the current unix epoch is
appended too. The `-n 5` switch means the script will keep the 5 most recent
copies, and will delete older ones.

QNAP API
========

The backup script uses the QNAP "Filestation" API, for which this repo contains python bindings to:

- List shares
- List a directory
- Stat file
- Rename file
- Delete file
- Download file
- Upload file

This library worked once with Python 2.7.9 on debian 8, and QNAP QTS 4.2.2.
See also the outdated http://download.qnap.com/dev/QNAP_QTS_File_Station_API_v4.1.pdf

Sample usage:

```python
url = 'https://me.myqnapcloud.com'
user = 'qnap'
password = 'qnap'

qnap_client = QnapClient(url)
if not qnap_client.login(user, passord):
    raise RuntimeError("Login failed.")
fs = FileStation(qnap_client)
shares = fs.list_shares()
file_list = fs.list('/Multimedia')
file_contents = fs.download('/Multimedia/Sample/picture/sample001.jpg')
fs.upload('/home/phil/silentmovie.txt', '/Multimedia/silentmovie.txt')
```
