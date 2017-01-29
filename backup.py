import json
# from qnap_client import QnapQlient

# from filestation import FileStation

with open('creds.json') as creds_file:
    creds = json.load(creds_file)

qnap = QnapClient(creds['url'])
logged_in = qnap.login(creds['username'], creds['password'])
creds = None
if not logged_in:
    raise RuntimeError('Failed to login.')

fs = FileStation(qnap)

def pprint(jsn):
    print json.dumps(jsn, indent=4, separators=(',', ': '))

test_file = "/Multimedia/Music/David's Music/MP3/ABBA/Abba - Dancing queen.mp3"


#shares = filestation.list_share()
#file_list = filestation.list('/')
#print file_list
#search_results = filestation.search('/Multimedia/Sample/picture', 'sample')
#file_contents = filestation.download('/Multimedia/Sample/picture/sample001.jpg')
