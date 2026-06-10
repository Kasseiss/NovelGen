#!/usr/bin/env python3
import json
import random
import sys
import time
import uuid
import urllib.request
import urllib.error

import os
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:3000')
TEST_API_KEY = 'test-boundary-key-00000000'
TEST_THEME = '__boundary_test_theme__'

TEST_USERNAME = f'test_boundary_{random.randint(10000, 99999)}'
TEST_PASSWORD = 'test123456'
_auth_token = None


def register_and_login():
    global _auth_token
    data = json.dumps({'username': TEST_USERNAME, 'password': TEST_PASSWORD}).encode()
    req = urllib.request.Request(
        BASE_URL + '/api/auth/register', data=data,
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read())
        _auth_token = result['token']
    return _auth_token


def auth_header():
    return {'Content-Type': 'application/json', 'Authorization': f'Bearer {_auth_token}'}


def save_user_config():
    body = json.dumps({
        'baseUrl': 'https://api.openai.com/v1',
        'apiKey': TEST_API_KEY,
        'model': 'gpt-4',
        'systemPrompt': '',
    }).encode()
    req = urllib.request.Request(
        BASE_URL + '/api/user/config', data=body,
        headers=auth_header(), method='PUT')
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


results = []
created_novel_ids = []


def api_get(path):
    url = BASE_URL + path
    req = urllib.request.Request(url, headers=auth_header(), method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body
    except Exception as e:
        return 0, str(e)


def api_post(path, data=None):
    url = BASE_URL + path
    body = json.dumps(data or {}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url, data=body,
        headers=auth_header(),
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode('utf-8')
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(resp_body)
        except Exception:
            return e.code, resp_body
    except Exception as e:
        return 0, str(e)


def api_put(path, data=None):
    url = BASE_URL + path
    body = json.dumps(data or {}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url, data=body,
        headers=auth_header(),
        method='PUT',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode('utf-8')
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(resp_body)
        except Exception:
            return e.code, resp_body
    except Exception as e:
        return 0, str(e)


def raw_get(path, headers=None):
    url = BASE_URL + path
    req = urllib.request.Request(url, headers=headers or {}, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body
    except Exception as e:
        return 0, str(e)


def raw_post(path, data=None, headers=None):
    url = BASE_URL + path
    body = json.dumps(data or {}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url, data=body,
        headers=headers or {'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode('utf-8')
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(resp_body)
        except Exception:
            return e.code, resp_body
    except Exception as e:
        return 0, str(e)


def record(test_id, scenario, precondition, steps, expected, actual, passed):
    results.append({
        'id': test_id,
        'scenario': scenario,
        'precondition': precondition,
        'steps': steps,
        'expected': expected,
        'actual': actual,
        'passed': passed,
    })
    tag = '\033[32mPASS\033[0m' if passed else '\033[31mFAIL\033[0m'
    print(f'  [{tag}] {test_id}: {scenario}')


def check_server():
    try:
        req = urllib.request.Request(BASE_URL + '/', method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def cleanup():
    code, data = api_get('/api/novels')
    if code == 200 and isinstance(data, list):
        for novel in data:
            nid = novel.get('id')
            if nid:
                try:
                    api_post('/api/novels/delete', {'id': nid})
                except Exception:
                    pass


def make_novel_payload(theme=None, chapter_count=None, words_per_chapter=None):
    return {
        'theme': theme if theme is not None else f'{TEST_THEME}_{uuid.uuid4().hex[:8]}',
        'novelConfig': {
            'chapterCount': chapter_count if chapter_count is not None else 1,
            'wordsPerChapter': words_per_chapter if words_per_chapter is not None else 100,
        },
    }


def create_temp_novel(**kwargs):
    payload = make_novel_payload(**kwargs)
    code, data = api_post('/api/novels', payload)
    if code == 201 and isinstance(data, dict) and 'id' in data:
        created_novel_ids.append(data['id'])
        return data
    return None


def wait_for_status(novel_id, target_status, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, data = api_get(f'/api/novels/{novel_id}')
        if code == 200 and isinstance(data, dict):
            st = data.get('status', '')
            if st == target_status:
                return data
            if st == 'error':
                return data
        time.sleep(0.5)
    return None


def wait_for_any_chapter(novel_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, data = api_get(f'/api/novels/{novel_id}')
        if code == 200 and isinstance(data, dict):
            chapters = data.get('chapters', [])
            if chapters:
                return data
        time.sleep(0.5)
    return None


def t01_get_novels_empty():
    code, data = api_get('/api/novels')
    passed = code == 200 and isinstance(data, list)
    record('T01', 'GET /api/novels — 返回列表类型',
           '服务器运行中',
           'GET /api/novels',
           '返回 200 且 body 为数组',
           f'code={code}, type={type(data).__name__}',
           passed)


def t02_get_novels_normal():
    novel = create_temp_novel()
    if not novel:
        record('T02', 'GET /api/novels — 包含新创建小说',
               '成功创建临时小说', 'GET /api/novels',
               '列表中包含新小说', '创建失败', False)
        return
    code, data = api_get('/api/novels')
    found = any(item.get('id') == novel['id'] for item in data) if isinstance(data, list) else False
    record('T02', 'GET /api/novels — 包含新创建小说',
           '已创建临时小说',
           'GET /api/novels，检查列表是否包含新小说',
           '列表中包含刚创建的小说',
           f'code={code}, found={found}',
           passed=code == 200 and found)


def t03_get_novel_valid_id():
    novel = create_temp_novel()
    if not novel:
        record('T03', 'GET /api/novels/{id} — 有效 id',
               '创建临时小说', 'GET /api/novels/{id}',
               '返回 200 和小说数据', '创建失败', False)
        return
    code, data = api_get(f'/api/novels/{novel["id"]}')
    passed = code == 200 and isinstance(data, dict) and data.get('id') == novel['id']
    record('T03', 'GET /api/novels/{id} — 有效 id',
           f'已创建小说 id={novel["id"]}',
           f'GET /api/novels/{novel["id"]}',
           '返回 200 且 id 匹配',
           f'code={code}, id_match={data.get("id") if isinstance(data, dict) else "N/A"}',
           passed)


def t04_get_novel_invalid_id():
    code, data = api_get('/api/novels/nonexistent_id_12345')
    passed = code == 404
    record('T04', 'GET /api/novels/{id} — 无效 id',
           '无此 id 的小说',
           'GET /api/novels/nonexistent_id_12345',
           '返回 404',
           f'code={code}',
           passed)


def t05_get_novel_long_id():
    long_id = 'a' * 10000
    code, data = api_get(f'/api/novels/{long_id}')
    passed = code == 404
    record('T05', 'GET /api/novels/{id} — 超长 id (10000 字符)',
           '无此 id 的小说',
           f'GET /api/novels/{"a" * 10000}',
           '返回 404',
           f'code={code}',
           passed)


def t06_get_novel_special_char_id():
    special_ids = [
        '../../../etc/passwd',
        '<script>alert(1)</script>',
        'id; DROP TABLE--',
        '中文id测试',
        'id%00null',
    ]
    all_ok = True
    for sid in special_ids:
        code, data = api_get(f'/api/novels/{urllib.request.quote(sid)}')
        if code != 404:
            all_ok = False
            break
    record('T06', 'GET /api/novels/{id} — 特殊字符 id',
           '无这些 id 的小说',
           f'尝试 {len(special_ids)} 种特殊字符 id',
           '全部返回 404',
           f'all_404={all_ok}',
           all_ok)


def t07_post_novel_empty_body():
    code, data = api_post('/api/novels', {})
    passed = code == 400
    record('T07', 'POST /api/novels — 空 body',
           '无',
           'POST /api/novels body={}',
           '返回 400，提示 theme required',
           f'code={code}, data={data}',
           passed)


def t08_post_novel_missing_theme():
    code, data = api_post('/api/novels', {
        'novelConfig': {'chapterCount': 1, 'wordsPerChapter': 100},
    })
    passed = code == 400
    record('T08', 'POST /api/novels — 缺少 theme',
           '无',
           'POST /api/novels 不含 theme 字段',
           '返回 400，提示 theme required',
           f'code={code}',
           passed)


def t09_post_novel_missing_apikey():
    code2, _ = api_put('/api/user/config', {
        'baseUrl': 'https://api.openai.com/v1',
        'model': 'gpt-4',
    })
    code, data = api_post('/api/novels', {
        'theme': f'{TEST_THEME}_nokey',
        'novelConfig': {'chapterCount': 1, 'wordsPerChapter': 100},
    })
    passed = code == 400
    record('T09', 'POST /api/novels — 缺少 apiKey',
           '用户配置中无 apiKey',
           'POST /api/novels 不含 apiKey',
           '返回 400，提示 apiKey required',
           f'code={code}',
           passed)
    save_user_config()


def t10_post_novel_negative_chapter_count():
    novel = create_temp_novel(chapter_count=-5)
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
        code, detail = api_get(f'/api/novels/{novel["id"]}')
        actual_count = detail.get('chapterCount', '?') if isinstance(detail, dict) else '?'
        passed = code == 200 and actual_count == 0
        record('T10', 'POST /api/novels — 负数 chapterCount',
               '无',
               'POST /api/novels chapterCount=-5',
               'chapterCount 被修正为 0',
               f'code={code}, chapterCount={actual_count}',
               passed)
    else:
        record('T10', 'POST /api/novels — 负数 chapterCount',
               '无', 'POST /api/novels chapterCount=-5',
               'chapterCount 被修正为 0', '创建失败', False)


def t11_post_novel_negative_words():
    novel = create_temp_novel(words_per_chapter=-100)
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
        code, detail = api_get(f'/api/novels/{novel["id"]}')
        actual_words = detail.get('wordsPerChapter', '?') if isinstance(detail, dict) else '?'
        passed = code == 200 and actual_words == 1
        record('T11', 'POST /api/novels — 负数 wordsPerChapter',
               '无',
               'POST /api/novels wordsPerChapter=-100',
               'wordsPerChapter 被修正为 1',
               f'code={code}, wordsPerChapter={actual_words}',
               passed)
    else:
        record('T11', 'POST /api/novels — 负数 wordsPerChapter',
               '无', 'POST /api/novels wordsPerChapter=-100',
               'wordsPerChapter 被修正为 1', '创建失败', False)


def t12_post_novel_huge_values():
    novel = create_temp_novel(chapter_count=999999, words_per_chapter=999999)
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
        code, detail = api_get(f'/api/novels/{novel["id"]}')
        passed = code == 200
        record('T12', 'POST /api/novels — 超大 chapterCount 和 wordsPerChapter',
               '无',
               'POST /api/novels chapterCount=999999, wordsPerChapter=999999',
               '服务器接受并正确存储',
               f'code={code}, chapterCount={detail.get("chapterCount")}, wordsPerChapter={detail.get("wordsPerChapter")}',
               passed)
    else:
        record('T12', 'POST /api/novels — 超大值',
               '无', 'POST /api/novels 超大值',
               '服务器接受', '创建失败', False)


def t13_post_novel_empty_strings():
    code, data = api_post('/api/novels', {
        'theme': '',
        'novelConfig': {'chapterCount': 1, 'wordsPerChapter': 100},
    })
    passed = code == 400
    record('T13', 'POST /api/novels — 空字符串 theme',
           '无',
           'POST /api/novels theme=""',
           '返回 400',
           f'code={code}',
           passed)


def t14_post_novel_unicode_theme():
    theme = '测试主题🎭✨「日本語」한국어 العربية'
    novel = create_temp_novel(theme=theme)
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
        code, detail = api_get(f'/api/novels/{novel["id"]}')
        actual_theme = detail.get('theme', '') if isinstance(detail, dict) else ''
        passed = code == 200 and actual_theme == theme
        record('T14', 'POST /api/novels — Unicode 主题',
               '无',
               f'POST /api/novels theme="{theme}"',
               '正确存储 Unicode 主题',
               f'code={code}, theme_match={actual_theme == theme}',
               passed)
    else:
        record('T14', 'POST /api/novels — Unicode 主题',
               '无', 'POST /api/novels Unicode theme', '正确存储', '创建失败', False)


def t15_stop_missing_id():
    code, data = api_post('/api/novels/stop', {})
    passed = code == 400
    record('T15', 'POST /api/novels/stop — 缺少 id',
           '无',
           'POST /api/novels/stop body={}',
           '返回 400，提示 id required',
           f'code={code}',
           passed)


def t16_stop_invalid_id():
    code, data = api_post('/api/novels/stop', {'id': 'nonexistent_99999'})
    passed = code == 404
    record('T16', 'POST /api/novels/stop — 无效 id',
           '无此 id 的小说',
           'POST /api/novels/stop id=nonexistent_99999',
           '返回 404',
           f'code={code}',
           passed)


def t17_stop_paused_novel():
    novel = create_temp_novel(chapter_count=1)
    if not novel:
        record('T17', 'POST /api/novels/stop — 已暂停的小说', '创建小说', 'stop', '返回 200', '创建失败', False)
        return
    nid = novel['id']
    created_novel_ids.append(nid)
    time.sleep(1)
    api_post('/api/novels/stop', {'id': nid})
    time.sleep(0.5)
    code, data = api_post('/api/novels/stop', {'id': nid})
    passed = code == 200
    record('T17', 'POST /api/novels/stop — 已暂停的小说',
           f'小说已暂停 id={nid}',
           '再次 POST /api/novels/stop',
           '返回 200（幂等操作）',
           f'code={code}',
           passed)


def t18_continue_missing_id():
    code, data = api_post('/api/novels/continue', {})
    passed = code == 400
    record('T18', 'POST /api/novels/continue — 缺少 id',
           '无',
           'POST /api/novels/continue body={}',
           '返回 400，提示 id required',
           f'code={code}',
           passed)


def t19_continue_invalid_id():
    code, data = api_post('/api/novels/continue', {'id': 'nonexistent_88888'})
    passed = code == 404
    record('T19', 'POST /api/novels/continue — 无效 id',
           '无此 id 的小说',
           'POST /api/novels/continue id=nonexistent_88888',
           '返回 404',
           f'code={code}',
           passed)


def t20_continue_completed_novel():
    novel = create_temp_novel(chapter_count=1)
    if not novel:
        record('T20', 'POST /api/novels/continue — 已完成的小说', '创建小说', 'continue', '行为合理', '创建失败', False)
        return
    nid = novel['id']
    created_novel_ids.append(nid)
    wait_for_status(nid, 'completed', timeout=30)
    code, data = api_post('/api/novels/continue', {'id': nid})
    passed = code == 200
    record('T20', 'POST /api/novels/continue — 已完成的小说',
           f'小说已完成 id={nid}',
           'POST /api/novels/continue',
           '返回 200，重新开始生成',
           f'code={code}',
           passed)


def t21_regenerate_missing_id():
    code, data = api_post('/api/novels/regenerate', {})
    passed = code == 400
    record('T21', 'POST /api/novels/regenerate — 缺少 id',
           '无',
           'POST /api/novels/regenerate body={}',
           '返回 400，提示 id required',
           f'code={code}',
           passed)


def t22_regenerate_invalid_id():
    code, data = api_post('/api/novels/regenerate', {'id': 'nonexistent_77777'})
    passed = code == 404
    record('T22', 'POST /api/novels/regenerate — 无效 id',
           '无此 id 的小说',
           'POST /api/novels/regenerate id=nonexistent_77777',
           '返回 404',
           f'code={code}',
           passed)


def t23_regenerate_generating_novel():
    novel = create_temp_novel(chapter_count=50)
    if not novel:
        record('T23', 'POST /api/novels/regenerate — 正在生成的小说', '创建小说', 'regenerate', '返回 200', '创建失败', False)
        return
    nid = novel['id']
    created_novel_ids.append(nid)
    time.sleep(0.5)
    code, data = api_post('/api/novels/regenerate', {'id': nid})
    passed = code == 200
    record('T23', 'POST /api/novels/regenerate — 正在生成的小说',
           f'小说正在生成 id={nid}',
           'POST /api/novels/regenerate',
           '返回 200，重新开始生成',
           f'code={code}',
           passed)


def t24_regenerate_chapter_missing_params():
    code, data = api_post('/api/novels/regenerate-chapter', {})
    passed = code == 400
    record('T24', 'POST /api/novels/regenerate-chapter — 缺少参数',
           '无',
           'POST /api/novels/regenerate-chapter body={}',
           '返回 400，提示 novelId and chapterId required',
           f'code={code}',
           passed)


def t25_regenerate_chapter_invalid_params():
    code, data = api_post('/api/novels/regenerate-chapter', {
        'novelId': 'nonexistent',
        'chapterId': 999,
    })
    passed = code == 404
    record('T25', 'POST /api/novels/regenerate-chapter — 无效参数',
           '无此小说',
           'POST /api/novels/regenerate-chapter novelId=nonexistent, chapterId=999',
           '返回 404（小说不存在）',
           f'code={code}',
           passed)


def t26_delete_missing_id():
    code, data = api_post('/api/novels/delete', {})
    passed = code == 400
    record('T26', 'POST /api/novels/delete — 缺少 id',
           '无',
           'POST /api/novels/delete body={}',
           '返回 400，提示 id required',
           f'code={code}',
           passed)


def t27_delete_invalid_id():
    code, data = api_post('/api/novels/delete', {'id': 'nonexistent_66666'})
    passed = code == 200
    record('T27', 'POST /api/novels/delete — 无效 id',
           '无此 id 的小说',
           'POST /api/novels/delete id=nonexistent_66666',
           '返回 200（幂等删除）',
           f'code={code}',
           passed)


def t28_delete_valid_novel():
    novel = create_temp_novel()
    if not novel:
        record('T28', 'POST /api/novels/delete — 删除有效小说', '创建小说', 'delete', '返回 200 且小说消失', '创建失败', False)
        return
    nid = novel['id']
    code, data = api_post('/api/novels/delete', {'id': nid})
    code2, data2 = api_get(f'/api/novels/{nid}')
    passed = code == 200 and code2 == 404
    record('T28', 'POST /api/novels/delete — 删除有效小说',
           f'已创建小说 id={nid}',
           'POST /api/novels/delete，然后 GET 验证',
           '删除返回 200，再次 GET 返回 404',
           f'delete_code={code}, get_code={code2}',
           passed)


def t29_concurrent_create():
    import concurrent.futures
    count = 5
    ids_created = []

    def do_create(i):
        payload = make_novel_payload(theme=f'{TEST_THEME}_concurrent_{i}')
        return api_post('/api/novels', payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(do_create, i) for i in range(count)]
        for f in concurrent.futures.as_completed(futures):
            code, data = f.result()
            if code == 201 and isinstance(data, dict) and 'id' in data:
                ids_created.append(data['id'])

    created_novel_ids.extend(ids_created)
    passed = len(ids_created) == count
    record('T29', '并发请求 — 同时创建多个小说',
           '无',
           f'同时发送 {count} 个 POST /api/novels',
           f'全部成功创建（{count}/{count}）',
           f'created={len(ids_created)}/{count}',
           passed)


def t30_concurrent_delete_and_create():
    import concurrent.futures
    novel = create_temp_novel()
    if not novel:
        record('T30', '并发请求 — 同时删除和创建', '创建小说', '并发操作', '无崩溃', '创建失败', False)
        return
    nid = novel['id']

    results_pool = []

    def do_delete():
        return api_post('/api/novels/delete', {'id': nid})

    def do_create():
        payload = make_novel_payload(theme=f'{TEST_THEME}_concurrent_mix')
        return api_post('/api/novels', payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_del = pool.submit(do_delete)
        f_cre = pool.submit(do_create)
        r1 = f_del.result()
        r2 = f_cre.result()
        results_pool = [r1, r2]

    if r2[0] == 201 and isinstance(r2[1], dict) and 'id' in r2[1]:
        created_novel_ids.append(r2[1]['id'])

    no_crash = all(r[0] in (200, 201, 400, 404, 409) for r in results_pool)
    record('T30', '并发请求 — 同时删除和创建',
           f'已创建小说 id={nid}',
           '同时发送 delete 和 create 请求',
           '服务器无崩溃，返回合理状态码',
           f'delete={r1[0]}, create={r2[0]}',
           no_crash)


def t31_large_payload_long_theme():
    long_theme = 'A' * 100000
    code, data = api_post('/api/novels', make_novel_payload(theme=long_theme))
    passed = code in (200, 201, 400, 413)
    if code in (200, 201) and isinstance(data, dict) and 'id' in data:
        created_novel_ids.append(data['id'])
    record('T31', '大 payload — 超长主题 (100KB)',
           '无',
           'POST /api/novels theme=100000 个字符',
           '服务器不崩溃，返回合理状态码',
           f'code={code}',
           passed)


def t32_large_payload_long_system_prompt():
    long_prompt = '你是一个作家。' * 10000
    code2, _ = api_put('/api/user/config', {
        'baseUrl': 'https://api.openai.com/v1',
        'apiKey': TEST_API_KEY,
        'model': 'gpt-4',
        'systemPrompt': long_prompt,
    })
    novel = create_temp_novel()
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
    record('T32', '大 payload — 超长系统提示词',
           '无',
           'POST /api/novels systemPrompt=超长字符串',
           '服务器不崩溃',
           f'created={novel is not None}',
           passed)
    save_user_config()


def t33_config_page_zero_values():
    novel = create_temp_novel(chapter_count=0, words_per_chapter=0)
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
        code, detail = api_get(f'/api/novels/{novel["id"]}')
        wc = detail.get('wordsPerChapter', 0) if isinstance(detail, dict) else 0
        passed = code == 200 and wc >= 1
        record('T33', '配置页面 — 章节数=0, 字数=0',
               '无',
               'POST /api/novels chapterCount=0, wordsPerChapter=0',
               'wordsPerChapter 至少为 1',
               f'code={code}, wordsPerChapter={wc}',
               passed)
    else:
        record('T33', '配置页面 — 零值', '无', 'POST 零值', '合理处理', '创建失败', False)


def t34_config_page_very_large():
    novel = create_temp_novel(chapter_count=10000, words_per_chapter=100000)
    passed = novel is not None
    if novel:
        created_novel_ids.append(novel['id'])
    record('T34', '配置页面 — 超大章节数和字数',
           '无',
           'POST /api/novels chapterCount=10000, wordsPerChapter=100000',
           '服务器接受（前端应做限制）',
           f'created={novel is not None}',
           passed)


def t35_shelf_empty():
    cleanup()
    code, data = api_get('/api/novels')
    passed = code == 200 and isinstance(data, list) and len(data) == 0
    record('T35', '书架页面 — 空书架',
           '已清理所有小说',
           'GET /api/novels',
           '返回 200 且为空数组',
           f'code={code}, count={len(data) if isinstance(data, list) else "N/A"}',
           passed)


def t36_shelf_many_novels():
    import concurrent.futures
    count = 20
    ids = []

    def do_create(i):
        return api_post('/api/novels', make_novel_payload(theme=f'{TEST_THEME}_shelf_{i}', chapter_count=0))

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(do_create, i) for i in range(count)]
        for f in concurrent.futures.as_completed(futures):
            code, data = f.result()
            if code == 201 and isinstance(data, dict) and 'id' in data:
                ids.append(data['id'])

    created_novel_ids.extend(ids)
    code, data = api_get('/api/novels')
    total = len(data) if isinstance(data, list) else 0
    passed = code == 200 and total >= count
    record('T36', f'书架页面 — 创建 {count} 本小说后查询',
           '无',
           f'创建 {count} 本小说，然后 GET /api/novels',
           f'返回列表长度 >= {count}',
           f'code={code}, total={total}, created={len(ids)}',
           passed)


def t37_unauth_access():
    code, data = raw_get('/api/novels')
    passed = code == 401
    record('T37', '未认证访问 /api/novels → 401',
           '无 token',
           'GET /api/novels 不带 Authorization',
           '返回 401',
           f'code={code}',
           passed)


def t38_invalid_token():
    code, data = raw_get('/api/novels', {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer invalid_token_abcdef123456',
    })
    passed = code == 401
    record('T38', '无效 token 访问 → 401',
           '使用伪造 token',
           'GET /api/novels 带无效 Bearer token',
           '返回 401',
           f'code={code}',
           passed)


def t39_register_duplicate():
    code, data = raw_post('/api/auth/register', {
        'username': TEST_USERNAME,
        'password': TEST_PASSWORD,
    })
    passed = code == 409
    record('T39', '注册重复用户名 → 409',
           f'用户名 {TEST_USERNAME} 已存在',
           'POST /api/auth/register 相同用户名',
           '返回 409',
           f'code={code}',
           passed)


def t40_login_wrong_password():
    code, data = raw_post('/api/auth/login', {
        'username': TEST_USERNAME,
        'password': 'wrong_password_123',
    })
    passed = code == 401
    record('T40', '登录错误密码 → 401',
           f'用户名 {TEST_USERNAME} 存在',
           'POST /api/auth/login 错误密码',
           '返回 401',
           f'code={code}',
           passed)


def t41_token_invalidated_after_logout():
    result = raw_post('/api/auth/register', {
        'username': f'test_logout_{random.randint(10000, 99999)}',
        'password': 'test123456',
    })
    code0, data0 = result
    if code0 != 201:
        record('T41', '登出后 token 失效 → 401',
               '注册临时用户', '登出后用 token 访问',
               '返回 401', f'register_code={code0}', False)
        return
    tmp_token = data0['token']
    code_logout, _ = raw_post('/api/auth/logout', {}, {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {tmp_token}',
    })
    code, data = raw_get('/api/novels', {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {tmp_token}',
    })
    passed = code == 401
    record('T41', '登出后 token 失效 → 401',
           f'已登出，logout_code={code_logout}',
           'GET /api/novels 用已登出的 token',
           '返回 401',
           f'code={code}',
           passed)


def print_report():
    total = len(results)
    passed_count = sum(1 for r in results if r['passed'])
    failed_count = total - passed_count

    print('\n' + '=' * 80)
    print('  边界测试报告')
    print('=' * 80)
    print(f'  总计: {total}  |  通过: {passed_count}  |  失败: {failed_count}')
    print(f'  通过率: {passed_count / total * 100:.1f}%' if total else '  无测试用例')
    print('=' * 80)

    if failed_count > 0:
        print('\n  失败用例:')
        for r in results:
            if not r['passed']:
                print(f'    [{r["id"]}] {r["scenario"]}')
                print(f'           预期: {r["expected"]}')
                print(f'           实际: {r["actual"]}')

    print('\n  详细结果:')
    print(f'  {"ID":<6} {"状态":<6} {"场景":<50}')
    print('  ' + '-' * 70)
    for r in results:
        tag = 'PASS' if r['passed'] else 'FAIL'
        print(f'  {r["id"]:<6} {tag:<6} {r["scenario"][:50]}')

    print('\n' + '=' * 80)


def main():
    print('=' * 80)
    print('  无限生成小说 — 边界测试')
    print(f'  服务器地址: {BASE_URL}')
    print(f'  时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 80)

    if not check_server():
        print('\n[ERROR] 无法连接服务器，请先启动: python run.py')
        sys.exit(1)

    print('\n[INFO] 服务器连接成功，注册测试用户...')
    try:
        register_and_login()
        print(f'[INFO] 注册成功: {TEST_USERNAME}')
    except Exception as e:
        print(f'\n[ERROR] 注册失败: {e}')
        sys.exit(1)

    print('[INFO] 保存 API 配置...')
    save_user_config()
    print('[INFO] API 配置已保存，开始测试...\n')

    tests = [
        t37_unauth_access,
        t38_invalid_token,
        t39_register_duplicate,
        t40_login_wrong_password,
        t41_token_invalidated_after_logout,
        t01_get_novels_empty,
        t02_get_novels_normal,
        t03_get_novel_valid_id,
        t04_get_novel_invalid_id,
        t05_get_novel_long_id,
        t06_get_novel_special_char_id,
        t07_post_novel_empty_body,
        t08_post_novel_missing_theme,
        t09_post_novel_missing_apikey,
        t10_post_novel_negative_chapter_count,
        t11_post_novel_negative_words,
        t12_post_novel_huge_values,
        t13_post_novel_empty_strings,
        t14_post_novel_unicode_theme,
        t15_stop_missing_id,
        t16_stop_invalid_id,
        t17_stop_paused_novel,
        t18_continue_missing_id,
        t19_continue_invalid_id,
        t20_continue_completed_novel,
        t21_regenerate_missing_id,
        t22_regenerate_invalid_id,
        t23_regenerate_generating_novel,
        t24_regenerate_chapter_missing_params,
        t25_regenerate_chapter_invalid_params,
        t26_delete_missing_id,
        t27_delete_invalid_id,
        t28_delete_valid_novel,
        t29_concurrent_create,
        t30_concurrent_delete_and_create,
        t31_large_payload_long_theme,
        t32_large_payload_long_system_prompt,
        t33_config_page_zero_values,
        t34_config_page_very_large,
        t35_shelf_empty,
        t36_shelf_many_novels,
    ]

    try:
        for test_fn in tests:
            try:
                test_fn()
            except Exception as e:
                record(test_fn.__name__.upper(), test_fn.__name__, '', '', '无异常', str(e), False)
    finally:
        print('\n[INFO] 清理临时数据...')
        cleanup()
        print('[INFO] 清理完成\n')

    print_report()

    failed_count = sum(1 for r in results if not r['passed'])
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == '__main__':
    main()
