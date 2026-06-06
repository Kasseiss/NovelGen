#!/usr/bin/env python3
import os
import sys
import json
import time
import uuid
import threading
import platform
import shutil
import urllib.request
import urllib.error
import urllib.parse
import zipfile
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DIST_DIR = BASE_DIR / 'dist'
DATA_DIR = BASE_DIR / 'data'
HISTORY_FILE = DATA_DIR / 'history.json'
NOVELS_DIR = DATA_DIR / 'novels'
API_KEYS_FILE = BASE_DIR / 'api_keys.json'
NODE_DIR = BASE_DIR / '.node'
NODE_VERSION = 'v20.18.0'

NODE_URLS = {
    'Linux-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-x64.tar.xz',
    'Linux-aarch64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-arm64.tar.xz',
    'Darwin-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-x64.tar.xz',
    'Darwin-arm64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-arm64.tar.xz',
    'Windows-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip',
}

store_lock = threading.RLock()
active_jobs = {}


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    NOVELS_DIR.mkdir(exist_ok=True)


def get_novel_file(novel_id):
    return NOVELS_DIR / f'{novel_id}.json'


def load_api_keys():
    if API_KEYS_FILE.exists():
        try:
            return json.loads(API_KEYS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_api_keys(keys):
    API_KEYS_FILE.write_text(json.dumps(keys, ensure_ascii=False, indent=2), encoding='utf-8')


def load_novel(novel_id):
    file = get_novel_file(novel_id)
    if file.exists():
        try:
            novel = json.loads(file.read_text(encoding='utf-8'))
        except Exception:
            return None
        api_keys = load_api_keys()
        if novel_id in api_keys:
            novel['apiConfig'] = api_keys[novel_id]
        return novel
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
            for item in history:
                if item.get('id') == novel_id and 'chapters' in item:
                    novel = dict(item)
                    api_keys = load_api_keys()
                    if novel_id in api_keys:
                        novel['apiConfig'] = api_keys[novel_id]
                    save_novel(novel)
                    return novel
        except Exception:
            pass
    return None


def save_novel(novel):
    novel_id = novel['id']
    file = get_novel_file(novel_id)
    data = {k: v for k, v in novel.items() if k != 'apiConfig'}
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    if 'apiConfig' in novel:
        api_keys = load_api_keys()
        api_keys[novel_id] = novel['apiConfig']
        save_api_keys(api_keys)


def delete_novel_file(novel_id):
    file = get_novel_file(novel_id)
    if file.exists():
        file.unlink()
    api_keys = load_api_keys()
    if novel_id in api_keys:
        api_keys.pop(novel_id, None)
        save_api_keys(api_keys)


def extract_chapter_meta(chapters):
    return [
        {'id': c['id'], 'title': c.get('title', ''), 'status': c.get('status', ''), 'wordCount': c.get('wordCount', 0)}
        for c in chapters
    ]


def novel_to_history_item(novel):
    return {
        'id': novel['id'],
        'theme': novel.get('theme', ''),
        'status': novel.get('status', ''),
        'chapterCount': novel.get('chapterCount', 0),
        'wordsPerChapter': novel.get('wordsPerChapter', 3000),
        'createdAt': novel.get('createdAt', ''),
        'updatedAt': novel.get('updatedAt', ''),
        'error': novel.get('error', ''),
        'chapterMeta': extract_chapter_meta(novel.get('chapters', [])),
    }


def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []


def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')


def get_history():
    with store_lock:
        return load_history()


def replace_history(data):
    with store_lock:
        save_history(data)


def find_novel(novel_id):
    novel = load_novel(novel_id)
    history = load_history()
    for i, item in enumerate(history):
        if item.get('id') == novel_id:
            return history, i, novel if novel else item
    return history, -1, novel


def update_novel(novel_id, updater):
    with store_lock:
        history, idx, novel = find_novel(novel_id)
        if idx == -1 or novel is None:
            return None
        updater(novel)
        save_novel(novel)
        history[idx] = novel_to_history_item(novel)
        save_history(history)
        return novel


def start_job(novel):
    novel_id = novel['id']
    with store_lock:
        if novel_id in active_jobs:
            return
        thread = threading.Thread(target=run_generation_job, args=(novel_id,), daemon=True)
        active_jobs[novel_id] = thread
        thread.start()


def now_str():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def api_request(api_url, api_key, model, messages, max_tokens=2048, temperature=0.8, timeout=120):
    body = json.dumps({
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False,
    }).encode('utf-8')

    url = api_url.rstrip('/') + '/chat/completions'
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        return data['choices'][0]['message']['content']


def run_generation_job(novel_id):
    try:
        update_novel(novel_id, lambda n: n.update({'status': 'generating', 'updatedAt': now_str(), 'error': ''}))
        while True:
            with store_lock:
                _, _, novel = find_novel(novel_id)
            if not novel or novel.get('status') != 'generating':
                break

            chapters = novel.get('chapters', [])
            chapter_count = novel.get('chapterCount', 0)
            target = chapter_count if chapter_count and chapter_count > 0 else 500

            chapters = [c for c in chapters if c.get('status') != 'error']
            update_novel(novel_id, lambda n: n.update({'chapters': chapters}))

            completed = [c for c in chapters if c.get('status') == 'completed']
            if len(completed) >= target:
                update_novel(novel_id, lambda n: n.update({'status': 'completed', 'updatedAt': now_str()}))
                break

            chapter_num = len(chapters) + 1
            previous_summary = '\n\n'.join(
                [
                    f"第{c['id']}章「{c.get('title', '')}」：{c.get('content', '')[-500:]}"
                    for c in completed[-3:]
                ]
            )

            api_url = novel.get('apiConfig', {}).get('baseUrl', '')
            api_key = novel.get('apiConfig', {}).get('apiKey', '')
            model = novel.get('apiConfig', {}).get('model', '')
            system_prompt = novel.get('apiConfig', {}).get('systemPrompt', '')
            theme = novel.get('theme', '')
            words_per_chapter = novel.get('wordsPerChapter', 3000)

            try:
                plan_prompt = (
                    f'【小说主题】\n{theme}\n\n'
                    f'【任务】\n这是第 {chapter_num} 章，总共 {target} 章。\n\n'
                )
                if previous_summary:
                    plan_prompt += f'【前文摘要】\n{previous_summary}\n\n'
                plan_prompt += (
                    '请用最简短、最直接的话，写出这一章要写什么。\n'
                    '不要废话，不要绕弯子，直接说清楚：\n'
                    '- 这一章的核心事件是什么\n'
                    '- 主角要干什么、遇到什么、怎么解决\n'
                    '- 章节标题是什么\n\n'
                    '严格按以下格式输出：\n'
                    '标题：xxx\n'
                    '内容：xxx'
                )

                plan_text = api_request(
                    api_url,
                    api_key,
                    model,
                    [
                        {'role': 'system', 'content': '你是一个小说大纲策划师。你的任务是用最简短直接的话规划每一章的内容。不要废话，不要文学性描述，只要说清楚这一章写什么。'},
                        {'role': 'user', 'content': plan_prompt},
                    ],
                    max_tokens=800,
                    temperature=0.7,
                )

                title = ''
                plan = plan_text.strip()
                for line in plan_text.splitlines():
                    line = line.strip()
                    if line.startswith('标题：') or line.startswith('标题:'):
                        title = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                    if line.startswith('内容：') or line.startswith('内容:'):
                        plan = line.split('：', 1)[-1].split(':', 1)[-1].strip()

                if not title:
                    title = f'第{chapter_num}章'

                with store_lock:
                    _, _, novel = find_novel(novel_id)
                    if not novel or novel.get('status') != 'generating':
                        return
                    chapters = novel.get('chapters', [])
                    chapters = [c for c in chapters if c.get('id') != chapter_num]
                    chapters.append({
                        'id': chapter_num,
                        'title': title,
                        'content': '',
                        'wordCount': 0,
                        'plan': plan,
                        'status': 'writing',
                    })
                    update_novel(novel_id, lambda n: n.update({'chapters': chapters, 'updatedAt': now_str()}))

                content_prompt = (
                    f'【小说主题】\n{theme}\n\n'
                    f'【本章任务】\n这是第 {chapter_num} 章，总共 {target} 章。\n'
                    f'本章要求字数：{words_per_chapter} 字以上。\n\n'
                    f'【本章大纲】\n{plan}\n\n'
                )
                if previous_summary:
                    content_prompt += f'【前文摘要】（确保剧情连贯）\n{previous_summary[-1500:]}\n\n'
                content_prompt += (
                    '请严格按照上面的大纲创作本章正文。\n'
                    '要求：\n'
                    '1. 先输出章节标题，格式：第X章：标题\n'
                    '2. 然后换行输出正文\n'
                    '3. 正文必须紧扣大纲内容\n'
                    '4. 情节紧凑、描写生动、对话自然\n'
                    f'5. 字数必须达到 {words_per_chapter} 字以上，只多不少'
                )

                content_text = api_request(
                    api_url,
                    api_key,
                    model,
                    [
                        {
                            'role': 'system',
                            'content': system_prompt or (
                                '你是一位专业的中文网络小说作家。\n\n'
                                '【核心规则】\n'
                                '1. 严格按照提供的大纲创作，不要偏离主题\n'
                                '2. 每章字数必须达到要求，只多不少\n'
                                '3. 情节紧凑、描写生动、对话自然\n'
                                '4. 章节间剧情必须连贯\n'
                                '5. 不要在章节开头重复小说标题\n\n'
                                '【输出格式】\n'
                                '第X章：章节标题\n\n'
                                '（正文内容，段落分明）'
                            ),
                        },
                        {'role': 'user', 'content': content_prompt},
                    ],
                    max_tokens=max(2048, int(words_per_chapter * 2)),
                    temperature=0.85,
                )

                final_title = title
                final_content = content_text.strip()
                for line in content_text.splitlines():
                    line = line.strip()
                    if line.startswith('第') and '章' in line and '：' in line:
                        final_title = line.split('：', 1)[-1].strip()
                        final_content = content_text.split('\n', 1)[-1].strip()
                        break
                    if line.startswith('第') and '章' in line and ':' in line:
                        final_title = line.split(':', 1)[-1].strip()
                        final_content = content_text.split('\n', 1)[-1].strip()
                        break

                final_word_count = len(final_content.replace(' ', '').replace('\n', ''))

                with store_lock:
                    _, _, novel = find_novel(novel_id)
                    if not novel or novel.get('status') != 'generating':
                        return
                    chapters = novel.get('chapters', [])
                    new_chapters = []
                    for c in chapters:
                        if c.get('id') == chapter_num:
                            new_chapters.append({
                                'id': chapter_num,
                                'title': final_title,
                                'content': final_content,
                                'wordCount': final_word_count,
                                'plan': plan,
                                'status': 'completed',
                            })
                        else:
                            new_chapters.append(c)
                    update_novel(novel_id, lambda n: n.update({'chapters': new_chapters, 'updatedAt': now_str()}))

            except Exception as exc:
                update_novel(novel_id, lambda n: n.update({'status': 'error', 'updatedAt': now_str(), 'error': str(exc)}))
                return
    finally:
        with store_lock:
            active_jobs.pop(novel_id, None)


def run_chapter_regen_job(novel_id, chapter_id):
    try:
        with store_lock:
            _, _, novel = find_novel(novel_id)
        if not novel:
            return

        api_url = novel.get('apiConfig', {}).get('baseUrl', '')
        api_key = novel.get('apiConfig', {}).get('apiKey', '')
        model = novel.get('apiConfig', {}).get('model', '')
        system_prompt = novel.get('apiConfig', {}).get('systemPrompt', '')
        theme = novel.get('theme', '')
        words_per_chapter = novel.get('wordsPerChapter', 3000)
        chapters = novel.get('chapters', [])
        chapter_count = novel.get('chapterCount', 0)
        target = chapter_count if chapter_count and chapter_count > 0 else 500

        completed = [c for c in chapters if c.get('status') == 'completed' and c.get('id') != chapter_id]
        previous_summary = '\n\n'.join(
            [f"第{c['id']}章「{c.get('title', '')}」：{c.get('content', '')[-500:]}" for c in completed[-3:]]
        )

        update_novel(novel_id, lambda n: n.update({
            'status': 'generating',
            'updatedAt': now_str(),
            'error': '',
            'chapters': [
                {**c, 'status': 'writing', 'content': '', 'wordCount': 0} if c.get('id') == chapter_id else c
                for c in n.get('chapters', [])
            ],
        }))

        try:
            plan_prompt = (
                f'【小说主题】\n{theme}\n\n'
                f'【任务】\n这是第 {chapter_id} 章，总共 {target} 章。请重新规划这一章的内容。\n\n'
            )
            if previous_summary:
                plan_prompt += f'【前文摘要】\n{previous_summary}\n\n'
            plan_prompt += (
                '请用最简短、最直接的话，写出这一章要写什么。\n'
                '不要废话，不要绕弯子，直接说清楚：\n'
                '- 这一章的核心事件是什么\n'
                '- 主角要干什么、遇到什么、怎么解决\n'
                '- 章节标题是什么\n\n'
                '严格按以下格式输出：\n'
                '标题：xxx\n'
                '内容：xxx'
            )

            plan_text = api_request(
                api_url, api_key, model,
                [
                    {'role': 'system', 'content': '你是一个小说大纲策划师。你的任务是用最简短直接的话规划每一章的内容。不要废话，不要文学性描述，只要说清楚这一章写什么。'},
                    {'role': 'user', 'content': plan_prompt},
                ],
                max_tokens=800,
                temperature=0.7,
            )

            title = ''
            plan = plan_text.strip()
            for line in plan_text.splitlines():
                line = line.strip()
                if line.startswith('标题：') or line.startswith('标题:'):
                    title = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                if line.startswith('内容：') or line.startswith('内容:'):
                    plan = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            if not title:
                title = f'第{chapter_id}章'

            update_novel(novel_id, lambda n: n.update({
                'chapters': [
                    {**c, 'title': title, 'plan': plan} if c.get('id') == chapter_id else c
                    for c in n.get('chapters', [])
                ],
                'updatedAt': now_str(),
            }))

            content_prompt = (
                f'【小说主题】\n{theme}\n\n'
                f'【本章任务】\n这是第 {chapter_id} 章，总共 {target} 章。\n'
                f'本章要求字数：{words_per_chapter} 字以上。\n\n'
                f'【本章大纲】\n{plan}\n\n'
            )
            if previous_summary:
                content_prompt += f'【前文摘要】（确保剧情连贯）\n{previous_summary[-1500:]}\n\n'
            content_prompt += (
                '请严格按照上面的大纲创作本章正文。\n'
                '要求：\n'
                '1. 先输出章节标题，格式：第X章：标题\n'
                '2. 然后换行输出正文\n'
                '3. 正文必须紧扣大纲内容\n'
                '4. 情节紧凑、描写生动、对话自然\n'
                f'5. 字数必须达到 {words_per_chapter} 字以上，只多不少'
            )

            content_text = api_request(
                api_url, api_key, model,
                [
                    {
                        'role': 'system',
                        'content': system_prompt or (
                            '你是一位专业的中文网络小说作家。\n\n'
                            '【核心规则】\n'
                            '1. 严格按照提供的大纲创作，不要偏离主题\n'
                            '2. 每章字数必须达到要求，只多不少\n'
                            '3. 情节紧凑、描写生动、对话自然\n'
                            '4. 章节间剧情必须连贯\n'
                            '5. 不要在章节开头重复小说标题\n\n'
                            '【输出格式】\n'
                            '第X章：章节标题\n\n'
                            '（正文内容，段落分明）'
                        ),
                    },
                    {'role': 'user', 'content': content_prompt},
                ],
                max_tokens=max(2048, int(words_per_chapter * 2)),
                temperature=0.85,
            )

            final_title = title
            final_content = content_text.strip()
            for line in content_text.splitlines():
                line = line.strip()
                if line.startswith('第') and '章' in line and '：' in line:
                    final_title = line.split('：', 1)[-1].strip()
                    final_content = content_text.split('\n', 1)[-1].strip()
                    break
                if line.startswith('第') and '章' in line and ':' in line:
                    final_title = line.split(':', 1)[-1].strip()
                    final_content = content_text.split('\n', 1)[-1].strip()
                    break

            final_word_count = len(final_content.replace(' ', '').replace('\n', ''))

            with store_lock:
                _, _, novel = find_novel(novel_id)
                if not novel:
                    return
                new_chapters = []
                for c in novel.get('chapters', []):
                    if c.get('id') == chapter_id:
                        new_chapters.append({
                            'id': chapter_id,
                            'title': final_title,
                            'content': final_content,
                            'wordCount': final_word_count,
                            'plan': plan,
                            'status': 'completed',
                        })
                    else:
                        new_chapters.append(c)
                all_completed = all(c.get('status') == 'completed' for c in new_chapters)
                new_status = 'completed' if all_completed else novel.get('status', 'generating')
                update_novel(novel_id, lambda n: n.update({'chapters': new_chapters, 'status': new_status, 'updatedAt': now_str()}))

        except Exception as exc:
            update_novel(novel_id, lambda n: n.update({
                'status': 'error',
                'updatedAt': now_str(),
                'error': f'重新生成第{chapter_id}章失败: {exc}',
            }))
    finally:
        with store_lock:
            active_jobs.pop(f'{novel_id}_ch{chapter_id}', None)


class AppHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        self.add_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path == '/api/novels':
            return self.json_ok(get_history())
        if path.startswith('/api/novels/') and len(path.split('/')) == 4:
            novel_id = path.split('/')[3]
            novel = load_novel(novel_id)
            if novel:
                return self.json_ok(novel)
            return self.json_error(404, 'novel not found')

        return self.serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path == '/api/novels':
            body = self.read_json()
            theme = (body.get('theme') or '').strip()
            api_config = body.get('apiConfig') or {}
            novel_config = body.get('novelConfig') or {}
            if not theme:
                return self.json_error(400, 'theme required')
            if not api_config.get('apiKey'):
                return self.json_error(400, 'apiKey required')

            novel_id = uuid.uuid4().hex[:16]
            novel = {
                'id': novel_id,
                'theme': theme,
                'apiConfig': {
                    'baseUrl': api_config.get('baseUrl', 'https://api.openai.com/v1'),
                    'apiKey': api_config.get('apiKey', ''),
                    'model': api_config.get('model', 'gpt-4'),
                    'systemPrompt': api_config.get('systemPrompt', ''),
                },
                'chapterCount': int(novel_config.get('chapterCount', 0) or 0),
                'wordsPerChapter': int(novel_config.get('wordsPerChapter', 3000) or 3000),
                'status': 'generating',
                'createdAt': now_str(),
                'updatedAt': now_str(),
                'error': '',
                'chapters': [],
            }

            history = get_history()
            history.insert(0, novel_to_history_item(novel))
            replace_history(history)
            save_novel(novel)
            start_job(novel)
            return self.json_ok(novel, 201)

        if path == '/api/novels/delete':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            with store_lock:
                history = load_history()
                new_history = [h for h in history if h.get('id') != novel_id]
                save_history(new_history)
                delete_novel_file(novel_id)
            return self.json_ok({'ok': True})

        if path == '/api/novels/regenerate-chapter':
            body = self.read_json()
            novel_id = body.get('novelId')
            chapter_id = body.get('chapterId')
            if not novel_id or not chapter_id:
                return self.json_error(400, 'novelId and chapterId required')
            job_key = f'{novel_id}_ch{chapter_id}'
            with store_lock:
                if job_key in active_jobs:
                    return self.json_error(409, 'already regenerating')
            thread = threading.Thread(target=run_chapter_regen_job, args=(novel_id, chapter_id), daemon=True)
            with store_lock:
                active_jobs[job_key] = thread
            thread.start()
            return self.json_ok({'ok': True, 'jobKey': job_key})

        if path == '/api/novels/regenerate':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            with store_lock:
                novel = load_novel(novel_id)
                if not novel:
                    return self.json_error(404, 'not found')
                novel['chapters'] = []
                novel['status'] = 'generating'
                novel['updatedAt'] = now_str()
                novel['error'] = ''
                save_novel(novel)
                history = load_history()
                for i, h in enumerate(history):
                    if h.get('id') == novel_id:
                        history[i] = novel_to_history_item(novel)
                        break
                save_history(history)
            start_job(novel)
            return self.json_ok({'ok': True})

        if path == '/api/novels/continue':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            with store_lock:
                novel = load_novel(novel_id)
                if not novel:
                    return self.json_error(404, 'not found')
                for c in novel.get('chapters', []):
                    if c.get('status') in ('writing', 'planning'):
                        c['status'] = 'error'
                        c['content'] = c.get('content', '') or ''
                        c['wordCount'] = len(c.get('content', '').replace(' ', '').replace('\n', ''))
                novel['status'] = 'generating'
                novel['updatedAt'] = now_str()
                novel['error'] = ''
                save_novel(novel)
                history = load_history()
                for i, h in enumerate(history):
                    if h.get('id') == novel_id:
                        history[i] = novel_to_history_item(novel)
                        break
                save_history(history)
            start_job(novel)
            return self.json_ok({'ok': True})

        return self.json_error(404, 'not found')

    def serve_static(self, path):
        if not DIST_DIR.exists():
            return self.json_error(500, 'dist not found')

        if path.startswith('/api/'):
            return self.json_error(404, 'api not found')

        file_path = DIST_DIR / path.lstrip('/')
        if file_path.is_dir():
            file_path = file_path / 'index.html'
        if not file_path.exists():
            file_path = DIST_DIR / 'index.html'
        if not file_path.exists():
            return self.json_error(404, 'not found')

        self.send_response(200)
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        if file_path.suffix == '.html':
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            content = file_path.read_bytes()
            import time
            ver = str(int(time.time())).encode()
            content = content.replace(b'.js"', b'.js?v=' + ver + b'"')
            content = content.replace(b'.css"', b'.css?v=' + ver + b'"')
            self.send_header('Content-Length', str(len(content)))
            self.add_cors()
            self.end_headers()
            self.wfile.write(content)
            return
        elif file_path.suffix == '.js':
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
        elif file_path.suffix == '.css':
            self.send_header('Content-Type', 'text/css; charset=utf-8')
        elif file_path.suffix == '.svg':
            self.send_header('Content-Type', 'image/svg+xml')
        elif file_path.suffix == '.json':
            self.send_header('Content-Type', 'application/json; charset=utf-8')
        else:
            self.send_header('Content-Type', 'application/octet-stream')
        data = file_path.read_bytes()
        self.send_header('Content-Length', str(len(data)))
        self.add_cors()
        self.end_headers()
        self.wfile.write(data)

    def json_ok(self, data, code=200):
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.add_cors()
        self.end_headers()
        self.wfile.write(payload)

    def json_error(self, code, message):
        return self.json_ok({'error': message}, code)

    def read_json(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length) if length > 0 else b'{}'
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {}

    def add_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')

    def log_message(self, fmt, *args):
        sys.stderr.write(f'[HTTP] {fmt % args}\n')
        sys.stderr.flush()


def platform_key():
    return f'{platform.system()}-{platform.machine()}'


def node_bin_path():
    if platform.system() == 'Windows':
        return NODE_DIR / 'node.exe'
    return NODE_DIR / 'bin' / 'node'


def npm_bin_path():
    if platform.system() == 'Windows':
        return NODE_DIR / 'npm' / 'npm-cli.js'
    return NODE_DIR / 'bin' / 'npm'


def ensure_node():
    if shutil.which('node'):
        return shutil.which('node'), shutil.which('npm')
    if node_bin_path().exists():
        return str(node_bin_path()), str(npm_bin_path())

    key = platform_key()
    url = NODE_URLS.get(key)
    if not url:
        raise RuntimeError(f'Unsupported platform: {key}')

    NODE_DIR.mkdir(exist_ok=True)
    filename = url.split('/')[-1]
    archive_path = BASE_DIR / filename
    urllib.request.urlretrieve(url, archive_path)
    if filename.endswith('.tar.xz'):
        subprocess.run(['tar', '-xf', str(archive_path), '-C', str(NODE_DIR), '--strip-components=1'], check=True)
    else:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            top = zf.namelist()[0].split('/')[0] + '/'
            for m in zf.namelist():
                if not m.startswith(top):
                    continue
                rel = m[len(top):]
                target = NODE_DIR / rel
                if m.endswith('/'):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(m) as src, open(target, 'wb') as dst:
                        dst.write(src.read())
    archive_path.unlink(missing_ok=True)
    return str(node_bin_path()), str(npm_bin_path())


def npm_build_if_needed():
    if DIST_DIR.exists():
        return
    node_path, npm_path = ensure_node()
    subprocess.run([node_path, npm_path, 'install'], cwd=BASE_DIR, check=True)
    subprocess.run([node_path, npm_path, 'run', 'build'], cwd=BASE_DIR, check=True)


def migrate_data():
    if not HISTORY_FILE.exists():
        return
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
    except Exception:
        return
    needs_migration = any('chapters' in item or 'apiConfig' in item for item in history)
    if not needs_migration:
        return
    NOVELS_DIR.mkdir(exist_ok=True)
    api_keys = load_api_keys()
    new_history = []
    for item in history:
        novel_id = item.get('id')
        if not novel_id:
            continue
        novel_file = get_novel_file(novel_id)
        if not novel_file.exists() and ('chapters' in item or 'apiConfig' in item):
            full_novel = dict(item)
            if 'apiConfig' in full_novel:
                api_keys[novel_id] = full_novel.pop('apiConfig')
            data = {k: v for k, v in full_novel.items() if k != 'apiConfig'}
            novel_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        if 'apiConfig' in item and novel_id not in api_keys:
            api_keys[novel_id] = item['apiConfig']
        if 'chapterMeta' not in item:
            if novel_file.exists():
                try:
                    novel_data = json.loads(novel_file.read_text(encoding='utf-8'))
                    meta = novel_to_history_item(novel_data)
                except Exception:
                    meta = novel_to_history_item(item)
            else:
                meta = novel_to_history_item(item)
            new_history.append(meta)
        else:
            clean = {k: v for k, v in item.items() if k not in ('chapters', 'apiConfig')}
            new_history.append(clean)
    save_history(new_history)
    if api_keys:
        save_api_keys(api_keys)


def restore_generating_jobs():
    history = get_history()
    for item in history:
        if item.get('status') == 'generating':
            item['status'] = 'pending'
            item['updatedAt'] = now_str()
            item['error'] = ''
    replace_history(history)
    history = get_history()
    for item in history:
        if item.get('status') == 'pending':
            start_job(item)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def run_server(host, port):
    try:
        server = ThreadedHTTPServer((host, port), AppHandler)
    except OSError as e:
        print(f'端口 {port} 被占用，请先关闭占用进程或换一个端口: {e}', flush=True)
        sys.exit(1)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    ensure_dirs()
    print('初始化完成', flush=True)
    migrate_data()
    print('数据迁移检查完成', flush=True)
    npm_build_if_needed()
    print('构建检查完成', flush=True)
    restore_generating_jobs()
    print('恢复任务完成', flush=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    print(f'服务启动: http://localhost:{port}', flush=True)
    run_server('0.0.0.0', port)
