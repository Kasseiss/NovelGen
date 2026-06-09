#!/usr/bin/env python3
import json
import random
import sys
import time
import uuid
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:3000')
TEST_API_KEY = 'test-stress-key-00000000'
TEST_THEME = '__stress_test_theme__'

TEST_USERNAME = f'test_stress_{random.randint(10000, 99999)}'
TEST_PASSWORD = 'test123456'
_auth_token = None

created_novel_ids = []
ids_lock = threading.Lock()


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


def api_get(path, timeout=10):
    url = BASE_URL + path
    req = urllib.request.Request(url, headers=auth_header(), method='GET')
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            elapsed = time.monotonic() - start
            return resp.status, elapsed, None
    except urllib.error.HTTPError as e:
        e.read()
        elapsed = time.monotonic() - start
        return e.code, elapsed, str(e.code)
    except Exception as e:
        elapsed = time.monotonic() - start
        return 0, elapsed, type(e).__name__


def api_post(path, data=None, timeout=10):
    url = BASE_URL + path
    body = json.dumps(data or {}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url, data=body,
        headers=auth_header(),
        method='POST',
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode('utf-8')
            elapsed = time.monotonic() - start
            resp_data = json.loads(resp_body) if resp_body else {}
            return resp.status, elapsed, None, resp_data
    except urllib.error.HTTPError as e:
        e.read()
        elapsed = time.monotonic() - start
        return e.code, elapsed, str(e.code), {}
    except Exception as e:
        elapsed = time.monotonic() - start
        return 0, elapsed, type(e).__name__, {}


def check_server():
    try:
        req = urllib.request.Request(BASE_URL + '/', method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def percentile(sorted_data, p):
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def analyze_results(task_name, latencies, errors, total_time):
    if not latencies:
        print(f'\n  [{task_name}] 无成功请求')
        return

    sorted_lat = sorted(latencies)
    total_req = len(latencies) + len(errors)
    success = len(latencies)
    fail = len(errors)

    avg_lat = sum(latencies) / len(latencies)
    max_lat = max(latencies)
    min_lat = min(latencies)
    p50 = percentile(sorted_lat, 50)
    p95 = percentile(sorted_lat, 95)
    p99 = percentile(sorted_lat, 99)
    qps = success / total_time if total_time > 0 else 0

    error_dist = {}
    for e in errors:
        error_dist[e] = error_dist.get(e, 0) + 1

    print(f'\n  {"=" * 60}')
    print(f'  {task_name}')
    print(f'  {"=" * 60}')
    print(f'  总请求数:       {total_req}')
    print(f'  成功:           {success}')
    print(f'  失败:           {fail}')
    print(f'  成功率:         {success / total_req * 100:.1f}%' if total_req else '  成功率: N/A')
    print(f'  总耗时:         {total_time:.2f}s')
    print(f'  QPS:            {qps:.2f}')
    print(f'  {"-" * 60}')
    print(f'  平均响应时间:   {avg_lat * 1000:.1f}ms')
    print(f'  最小响应时间:   {min_lat * 1000:.1f}ms')
    print(f'  最大响应时间:   {max_lat * 1000:.1f}ms')
    print(f'  P50:            {p50 * 1000:.1f}ms')
    print(f'  P95:            {p95 * 1000:.1f}ms')
    print(f'  P99:            {p99 * 1000:.1f}ms')
    if error_dist:
        print(f'  {"-" * 60}')
        print(f'  错误分布:')
        for err_type, count in sorted(error_dist.items(), key=lambda x: -x[1]):
            print(f'    {err_type}: {count}')
    print(f'  {"=" * 60}')


def make_novel_payload(theme_suffix=''):
    return {
        'theme': f'{TEST_THEME}_{uuid.uuid4().hex[:8]}{theme_suffix}',
        'novelConfig': {
            'chapterCount': 0,
            'wordsPerChapter': 100,
        },
    }


def cleanup():
    print('\n[INFO] 清理临时数据...')
    for nid in created_novel_ids:
        try:
            api_post('/api/novels/delete', {'id': nid})
        except Exception:
            pass
    print('[INFO] 清理完成')


def test_concurrent_reads(concurrency):
    latencies = []
    errors = []
    lock = threading.Lock()

    def do_read(_):
        status, elapsed, err = api_get('/api/novels')
        with lock:
            if err:
                errors.append(err)
            else:
                latencies.append(elapsed)

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(do_read, i) for i in range(concurrency)]
        for f in as_completed(futures):
            f.result()
    total_time = time.monotonic() - start

    analyze_results(f'并发读取 — {concurrency} 个并发 GET /api/novels', latencies, errors, total_time)


def test_concurrent_writes(concurrency):
    latencies = []
    errors = []
    ids = []
    lock = threading.Lock()

    def do_write(_):
        payload = make_novel_payload(f'_cw{concurrency}')
        status, elapsed, err, data = api_post('/api/novels', payload)
        with lock:
            if err:
                errors.append(err)
            else:
                latencies.append(elapsed)
                if isinstance(data, dict) and 'id' in data:
                    ids.append(data['id'])

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(do_write, i) for i in range(concurrency)]
        for f in as_completed(futures):
            f.result()
    total_time = time.monotonic() - start

    with ids_lock:
        created_novel_ids.extend(ids)

    analyze_results(f'并发写入 — {concurrency} 个并发 POST /api/novels', latencies, errors, total_time)


def test_mixed_load(total_requests=200, concurrency=20, read_ratio=0.7):
    read_latencies = []
    read_errors = []
    write_latencies = []
    write_errors = []
    write_ids = []
    lock = threading.Lock()
    counter = {'i': 0}

    def do_request(_):
        with lock:
            idx = counter['i']
            counter['i'] += 1
        is_read = (idx % 100) < int(read_ratio * 100)

        if is_read:
            status, elapsed, err = api_get('/api/novels')
            with lock:
                if err:
                    read_errors.append(err)
                else:
                    read_latencies.append(elapsed)
        else:
            payload = make_novel_payload('_mixed')
            status, elapsed, err, data = api_post('/api/novels', payload)
            with lock:
                if err:
                    write_errors.append(err)
                else:
                    write_latencies.append(elapsed)
                    if isinstance(data, dict) and 'id' in data:
                        write_ids.append(data['id'])

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(do_request, i) for i in range(total_requests)]
        for f in as_completed(futures):
            f.result()
    total_time = time.monotonic() - start

    with ids_lock:
        created_novel_ids.extend(write_ids)

    all_lat = sorted(read_latencies + write_latencies)
    all_errors = read_errors + write_errors

    print(f'\n  {"=" * 60}')
    print(f'  混合负载 — {total_requests} 请求 ({int(read_ratio*100)}% 读 + {100-int(read_ratio*100)}% 写)')
    print(f'  {"=" * 60}')

    total_req = len(all_lat) + len(all_errors)
    success = len(all_lat)
    avg_lat = sum(all_lat) / len(all_lat) if all_lat else 0
    max_lat = max(all_lat) if all_lat else 0
    p50 = percentile(all_lat, 50)
    p95 = percentile(all_lat, 95)
    p99 = percentile(all_lat, 99)
    qps = success / total_time if total_time > 0 else 0

    error_dist = {}
    for e in all_errors:
        error_dist[e] = error_dist.get(e, 0) + 1

    print(f'  总请求数:       {total_req}')
    print(f'  成功:           {success}')
    print(f'  失败:           {len(all_errors)}')
    print(f'  成功率:         {success / total_req * 100:.1f}%' if total_req else '')
    print(f'  总耗时:         {total_time:.2f}s')
    print(f'  QPS:            {qps:.2f}')
    print(f'  {"-" * 60}')
    print(f'  读请求: {len(read_latencies)} 成功, {len(read_errors)} 失败')
    print(f'  写请求: {len(write_latencies)} 成功, {len(write_errors)} 失败')
    print(f'  {"-" * 60}')
    print(f'  平均响应时间:   {avg_lat * 1000:.1f}ms')
    print(f'  最大响应时间:   {max_lat * 1000:.1f}ms')
    print(f'  P50:            {p50 * 1000:.1f}ms')
    print(f'  P95:            {p95 * 1000:.1f}ms')
    print(f'  P99:            {p99 * 1000:.1f}ms')
    if error_dist:
        print(f'  {"-" * 60}')
        print(f'  错误分布:')
        for err_type, count in sorted(error_dist.items(), key=lambda x: -x[1]):
            print(f'    {err_type}: {count}')
    print(f'  {"=" * 60}')


def test_sustained_load(duration_sec=60, concurrency=10):
    latencies = []
    errors = []
    stop_flag = threading.Event()
    lock = threading.Lock()
    write_ids = []

    def worker(_):
        while not stop_flag.is_set():
            status, elapsed, err = api_get('/api/novels', timeout=30)
            with lock:
                if err:
                    errors.append(err)
                else:
                    latencies.append(elapsed)

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker, i) for i in range(concurrency)]
        time.sleep(duration_sec)
        stop_flag.set()
        for f in as_completed(futures):
            f.result()
    total_time = time.monotonic() - start

    analyze_results(f'长连接 — 持续 {duration_sec}s 请求轰炸 ({concurrency} 并发)', latencies, errors, total_time)


def test_large_novel_reads(concurrency=10):
    print(f'\n  创建包含大量章节的小说用于读取测试...')
    novel = None
    payload = make_novel_payload('_large')
    payload['novelConfig']['chapterCount'] = 0
    status, elapsed, err, data = api_post('/api/novels', payload)
    if status == 201 and isinstance(data, dict) and 'id' in data:
        novel = data
        created_novel_ids.append(data['id'])

    if not novel:
        print('  [WARN] 无法创建测试小说，跳过此测试')
        return

    nid = novel['id']
    print(f'  已创建小说 id={nid}，等待生成一些章节...')
    time.sleep(5)

    code, detail_elapsed, detail_err = api_get(f'/api/novels/{nid}')
    latencies = []
    errors = []
    lock = threading.Lock()

    def do_read(_):
        status, elapsed, err = api_get(f'/api/novels/{nid}')
        with lock:
            if err:
                errors.append(err)
            else:
                latencies.append(elapsed)

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(do_read, i) for i in range(concurrency)]
        for f in as_completed(futures):
            f.result()
    total_time = time.monotonic() - start

    analyze_results(f'大文件读取 — {concurrency} 并发读取单本小说', latencies, errors, total_time)


def print_summary(all_results):
    print('\n' + '=' * 80)
    print('  压力测试总结')
    print('=' * 80)
    print(f'  测试时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  服务器地址: {BASE_URL}')
    print('=' * 80)
    print()


def main():
    print('=' * 80)
    print('  无限生成小说 — 压力测试')
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
    print('[INFO] API 配置已保存，开始压力测试...\n')

    try:
        print('\n[TEST 1/5] 并发读取测试')
        print('-' * 60)
        for c in [10, 50, 100, 500]:
            test_concurrent_reads(c)

        print('\n\n[TEST 2/5] 并发写入测试')
        print('-' * 60)
        for c in [10, 50, 100]:
            test_concurrent_writes(c)

        print('\n\n[TEST 3/5] 混合负载测试')
        print('-' * 60)
        test_mixed_load(total_requests=200, concurrency=20, read_ratio=0.7)

        print('\n\n[TEST 4/5] 长连接测试 (30s)')
        print('-' * 60)
        test_sustained_load(duration_sec=30, concurrency=10)

        print('\n\n[TEST 5/5] 大文件读取测试')
        print('-' * 60)
        test_large_novel_reads(concurrency=10)

    finally:
        cleanup()

    print_summary([])

    print('=' * 80)
    print('  压力测试完成')
    print('=' * 80)


if __name__ == '__main__':
    main()
