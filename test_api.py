import urllib.request
import json
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/orders', 
        data=json.dumps({"notes": "", "items": [], "table_number": 2}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    r = urllib.request.urlopen(req)
    print(r.read())
except Exception as e:
    print(e.read().decode('utf-8'))
