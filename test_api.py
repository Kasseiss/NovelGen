import urllib.request, json

# 测试 1: GET /api/novels 正常
r = urllib.request.urlopen('http://127.0.0.1:3000/api/novels', timeout=5)
d = json.loads(r.read())
print('1. GET /api/novels: OK, count=', len(d))

# 测试 2: POST /api/novels/stop 缺少 id
try:
    data = json.dumps({}).encode()
    req = urllib.request.Request('http://127.0.0.1:3000/api/novels/stop', data=data, headers={'Content-Type': 'application/json'}, method='POST')
    r = urllib.request.urlopen(req, timeout=5)
except urllib.error.HTTPError as e:
    print('2. POST /api/novels/stop (no id):', e.code, 'OK' if e.code == 400 else 'FAIL')

# 测试 3: POST /api/novels/stop 不存在的 id
try:
    data = json.dumps({'id': 'nonexistent'}).encode()
    req = urllib.request.Request('http://127.0.0.1:3000/api/novels/stop', data=data, headers={'Content-Type': 'application/json'}, method='POST')
    r = urllib.request.urlopen(req, timeout=5)
except urllib.error.HTTPError as e:
    print('3. POST /api/novels/stop (bad id):', e.code, 'OK' if e.code == 404 else 'FAIL')

print('All tests passed!')