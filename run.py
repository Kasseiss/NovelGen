#!/usr/bin/env python3
import os
import sys
import json
import time
import uuid
import hashlib
import sqlite3
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
DB_FILE = DATA_DIR / 'novelgen.db'
NODE_DIR = BASE_DIR / '.node'
NODE_VERSION = 'v20.18.0'

NODE_URLS = {
    'Linux-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-x64.tar.xz',
    'Linux-aarch64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-arm64.tar.xz',
    'Darwin-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-x64.tar.xz',
    'Darwin-arm64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-arm64.tar.xz',
    'Windows-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip',
}

db_lock = threading.Lock()
active_jobs = {}
cancel_events = {}

_db = None


def db_init():
    global _db
    DATA_DIR.mkdir(exist_ok=True)
    _db = sqlite3.connect(str(DB_FILE), check_same_thread=False)
    _db.row_factory = sqlite3.Row
    _db.execute('PRAGMA journal_mode=WAL')
    _db.execute('PRAGMA foreign_keys=ON')
    _db.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        api_config TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')
    _db.execute('''CREATE TABLE IF NOT EXISTS novels (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        theme TEXT NOT NULL,
        chapter_count INTEGER DEFAULT 0,
        words_per_chapter INTEGER DEFAULT 3000,
        status TEXT DEFAULT 'generating',
        error TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    _db.execute('''CREATE TABLE IF NOT EXISTS chapters (
        novel_id TEXT NOT NULL,
        chapter_id INTEGER NOT NULL,
        title TEXT DEFAULT '',
        content TEXT DEFAULT '',
        word_count INTEGER DEFAULT 0,
        plan TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        PRIMARY KEY (novel_id, chapter_id),
        FOREIGN KEY (novel_id) REFERENCES novels(id)
    )''')
    _db.execute('''CREATE TABLE IF NOT EXISTS tokens (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    _db.commit()
    return _db


def get_db():
    global _db
    if _db is None:
        db_init()
    return _db


def _hash_password(password, salt):
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()


def db_create_user(username, password):
    user_id = uuid.uuid4().hex[:16]
    salt = uuid.uuid4().hex
    password_hash = _hash_password(password, salt)
    now = now_str()
    with db_lock:
        try:
            get_db().execute(
                'INSERT INTO users (id, username, password_hash, salt, api_config, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, username, password_hash, salt, '{}', now, now)
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return None
    return user_id


def db_authenticate(username, password):
    with db_lock:
        row = get_db().execute('SELECT id, password_hash, salt FROM users WHERE username = ?', (username,)).fetchone()
    if not row:
        return None
    if _hash_password(password, row['salt']) != row['password_hash']:
        return None
    token = uuid.uuid4().hex
    now = now_str()
    with db_lock:
        get_db().execute('INSERT INTO tokens (token, user_id, created_at) VALUES (?, ?, ?)', (token, row['id'], now))
        get_db().commit()
    return token


def db_get_user_by_token(token):
    with db_lock:
        row = get_db().execute('SELECT user_id FROM tokens WHERE token = ?', (token,)).fetchone()
    return row['user_id'] if row else None


def db_get_username(user_id):
    with db_lock:
        row = get_db().execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    return row['username'] if row else None


def db_get_user_api_config(user_id):
    with db_lock:
        row = get_db().execute('SELECT api_config FROM users WHERE id = ?', (user_id,)).fetchone()
    if not row:
        return {}
    try:
        return json.loads(row['api_config'])
    except Exception:
        return {}


def db_save_user_api_config(user_id, api_config):
    now = now_str()
    with db_lock:
        get_db().execute('UPDATE users SET api_config = ?, updated_at = ? WHERE id = ?', (json.dumps(api_config, ensure_ascii=False), now, user_id))
        get_db().commit()


def db_delete_token(token):
    with db_lock:
        get_db().execute('DELETE FROM tokens WHERE token = ?', (token,))
        get_db().commit()


def db_create_novel(user_id, novel_data):
    novel_id = novel_data['id']
    now = now_str()
    with db_lock:
        get_db().execute(
            'INSERT INTO novels (id, user_id, theme, chapter_count, words_per_chapter, status, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (novel_id, user_id, novel_data['theme'], novel_data.get('chapterCount', 0),
             novel_data.get('wordsPerChapter', 3000), novel_data.get('status', 'generating'),
             novel_data.get('error', ''), now, now)
        )
        get_db().commit()
    return novel_id


def db_get_novel(novel_id, user_id):
    with db_lock:
        row = get_db().execute('SELECT * FROM novels WHERE id = ? AND user_id = ?', (novel_id, user_id)).fetchone()
    if not row:
        return None
    chapters = db_get_chapters(novel_id)
    return {
        'id': row['id'],
        'theme': row['theme'],
        'chapterCount': row['chapter_count'],
        'wordsPerChapter': row['words_per_chapter'],
        'status': row['status'],
        'error': row['error'],
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
        'chapters': chapters,
    }


def db_get_novel_no_check(novel_id):
    with db_lock:
        row = get_db().execute('SELECT * FROM novels WHERE id = ?', (novel_id,)).fetchone()
    if not row:
        return None
    chapters = db_get_chapters(novel_id)
    api_config = {}
    user_row = get_db().execute('SELECT api_config FROM users WHERE id = ?', (row['user_id'],)).fetchone()
    if user_row:
        try:
            api_config = json.loads(user_row['api_config'])
        except Exception:
            api_config = {}
    return {
        'id': row['id'],
        'user_id': row['user_id'],
        'theme': row['theme'],
        'chapterCount': row['chapter_count'],
        'wordsPerChapter': row['words_per_chapter'],
        'status': row['status'],
        'error': row['error'],
        'createdAt': row['created_at'],
        'updatedAt': row['updated_at'],
        'apiConfig': api_config,
        'chapters': chapters,
    }


def db_get_user_novels(user_id):
    with db_lock:
        rows = get_db().execute('SELECT * FROM novels WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    result = []
    for row in rows:
        chapter_metas = []
        with db_lock:
            crows = get_db().execute('SELECT chapter_id, title, status, word_count FROM chapters WHERE novel_id = ? ORDER BY chapter_id', (row['id'],)).fetchall()
        for cr in crows:
            chapter_metas.append({
                'id': cr['chapter_id'],
                'title': cr['title'],
                'status': cr['status'],
                'wordCount': cr['word_count'],
            })
        result.append({
            'id': row['id'],
            'theme': row['theme'],
            'chapterCount': row['chapter_count'],
            'wordsPerChapter': row['words_per_chapter'],
            'status': row['status'],
            'error': row['error'],
            'createdAt': row['created_at'],
            'updatedAt': row['updated_at'],
            'chapterMeta': chapter_metas,
        })
    return result


def db_get_chapters(novel_id):
    with db_lock:
        rows = get_db().execute('SELECT * FROM chapters WHERE novel_id = ? ORDER BY chapter_id', (novel_id,)).fetchall()
    return [
        {
            'id': r['chapter_id'],
            'title': r['title'],
            'content': r['content'],
            'wordCount': r['word_count'],
            'plan': r['plan'],
            'status': r['status'],
        }
        for r in rows
    ]


def db_update_novel_meta(novel_id, **kwargs):
    sets = []
    vals = []
    field_map = {
        'theme': 'theme',
        'chapterCount': 'chapter_count',
        'wordsPerChapter': 'words_per_chapter',
        'status': 'status',
        'error': 'error',
        'updatedAt': 'updated_at',
    }
    for k, v in kwargs.items():
        col = field_map.get(k)
        if col:
            sets.append(f'{col} = ?')
            vals.append(v)
    if not sets:
        return
    vals.append(novel_id)
    with db_lock:
        get_db().execute(f'UPDATE novels SET {", ".join(sets)} WHERE id = ?', vals)
        get_db().commit()


def db_save_chapter(novel_id, chapter_data):
    with db_lock:
        get_db().execute(
            'INSERT OR REPLACE INTO chapters (novel_id, chapter_id, title, content, word_count, plan, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (novel_id, chapter_data['id'], chapter_data.get('title', ''),
             chapter_data.get('content', ''), chapter_data.get('wordCount', 0),
             chapter_data.get('plan', ''), chapter_data.get('status', 'pending'))
        )
        get_db().commit()


def db_delete_novel(novel_id, user_id):
    with db_lock:
        get_db().execute('DELETE FROM chapters WHERE novel_id = ?', (novel_id,))
        get_db().execute('DELETE FROM novels WHERE id = ? AND user_id = ?', (novel_id, user_id))
        get_db().commit()


def db_delete_novel_no_check(novel_id):
    with db_lock:
        get_db().execute('DELETE FROM chapters WHERE novel_id = ?', (novel_id,))
        get_db().execute('DELETE FROM novels WHERE id = ?', (novel_id,))
        get_db().commit()


def db_reset_chapter(novel_id, chapter_id):
    with db_lock:
        get_db().execute(
            'UPDATE chapters SET content = ?, word_count = ?, status = ? WHERE novel_id = ? AND chapter_id = ?',
            ('', 0, 'pending', novel_id, chapter_id)
        )
        get_db().commit()


def db_set_chapter_writing(novel_id, chapter_id, title='', plan=''):
    with db_lock:
        get_db().execute(
            'UPDATE chapters SET title = ?, content = ?, word_count = ?, plan = ?, status = ? WHERE novel_id = ? AND chapter_id = ?',
            (title, '', 0, plan, 'writing', novel_id, chapter_id)
        )
        get_db().commit()


def db_get_pending_chapters(novel_id):
    with db_lock:
        rows = get_db().execute(
            "SELECT * FROM chapters WHERE novel_id = ? AND status != 'completed' ORDER BY chapter_id LIMIT 1",
            (novel_id,)
        ).fetchall()
    if not rows:
        return None
    r = rows[0]
    return {
        'id': r['chapter_id'],
        'title': r['title'],
        'content': r['content'],
        'wordCount': r['word_count'],
        'plan': r['plan'],
        'status': r['status'],
    }


def db_get_completed_chapters(novel_id, exclude_id=None):
    with db_lock:
        if exclude_id is not None:
            rows = get_db().execute(
                "SELECT * FROM chapters WHERE novel_id = ? AND status = 'completed' AND chapter_id != ? ORDER BY chapter_id",
                (novel_id, exclude_id)
            ).fetchall()
        else:
            rows = get_db().execute(
                "SELECT * FROM chapters WHERE novel_id = ? AND status = 'completed' ORDER BY chapter_id",
                (novel_id,)
            ).fetchall()
    return [
        {
            'id': r['chapter_id'],
            'title': r['title'],
            'content': r['content'],
            'wordCount': r['word_count'],
            'plan': r['plan'],
            'status': r['status'],
        }
        for r in rows
    ]


def db_count_completed(novel_id):
    with db_lock:
        row = get_db().execute("SELECT COUNT(*) as cnt FROM chapters WHERE novel_id = ? AND status = 'completed'", (novel_id,)).fetchone()
    return row['cnt']


def db_count_chapters(novel_id):
    with db_lock:
        row = get_db().execute('SELECT COUNT(*) as cnt FROM chapters WHERE novel_id = ?', (novel_id,)).fetchone()
    return row['cnt']


def db_ensure_chapter(novel_id, chapter_id):
    with db_lock:
        row = get_db().execute('SELECT 1 FROM chapters WHERE novel_id = ? AND chapter_id = ?', (novel_id, chapter_id)).fetchone()
    if not row:
        with db_lock:
            get_db().execute(
                'INSERT INTO chapters (novel_id, chapter_id, title, content, word_count, plan, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (novel_id, chapter_id, '', '', 0, '', 'pending')
            )
            get_db().commit()


def db_all_chapters_generating(novel_id):
    with db_lock:
        rows = get_db().execute('SELECT * FROM chapters WHERE novel_id = ? ORDER BY chapter_id', (novel_id,)).fetchall()
    return [
        {
            'id': r['chapter_id'],
            'title': r['title'],
            'content': r['content'],
            'wordCount': r['word_count'],
            'plan': r['plan'],
            'status': r['status'],
        }
        for r in rows
    ]


def db_get_generating_novels():
    with db_lock:
        rows = get_db().execute("SELECT * FROM novels WHERE status = 'generating'").fetchall()
    return rows


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


def start_job(novel_id):
    with db_lock:
        if novel_id in cancel_events:
            cancel_events[novel_id].set()
        active_jobs.pop(novel_id, None)
        cancel_events[novel_id] = threading.Event()
        thread = threading.Thread(target=run_generation_job, args=(novel_id,), daemon=True)
        active_jobs[novel_id] = thread
        thread.start()


def run_generation_job(novel_id):
    try:
        db_update_novel_meta(novel_id, status='generating', updatedAt=now_str(), error='')
        while True:
            with db_lock:
                evt = cancel_events.get(novel_id)
            if evt and evt.is_set():
                return

            novel = db_get_novel_no_check(novel_id)
            if not novel or novel.get('status') != 'generating':
                break

            chapters = novel.get('chapters', [])
            chapter_count = novel.get('chapterCount', 0)
            target = chapter_count if chapter_count and chapter_count > 0 else 500

            completed = [c for c in chapters if c.get('status') == 'completed']
            if len(completed) >= target:
                db_update_novel_meta(novel_id, status='completed', updatedAt=now_str())
                break

            non_completed = [c for c in chapters if c.get('status') != 'completed']
            if not non_completed:
                db_update_novel_meta(novel_id, status='completed', updatedAt=now_str())
                break

            chapter_num = non_completed[0]['id']

            if not any(c.get('id') == chapter_num for c in chapters):
                db_ensure_chapter(novel_id, chapter_num)

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

                with db_lock:
                    evt = cancel_events.get(novel_id)
                if evt and evt.is_set():
                    return

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

                with db_lock:
                    novel_check = db_get_novel_no_check(novel_id)
                    if not novel_check or novel_check.get('status') != 'generating':
                        return
                db_save_chapter(novel_id, {
                    'id': chapter_num,
                    'title': title,
                    'content': '',
                    'wordCount': 0,
                    'plan': plan,
                    'status': 'writing',
                })
                db_update_novel_meta(novel_id, updatedAt=now_str())

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

                with db_lock:
                    evt = cancel_events.get(novel_id)
                if evt and evt.is_set():
                    return

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

                with db_lock:
                    novel_check = db_get_novel_no_check(novel_id)
                    if not novel_check or novel_check.get('status') != 'generating':
                        return

                if not final_content or len(final_content.strip()) < 10:
                    db_save_chapter(novel_id, {
                        'id': chapter_num,
                        'title': final_title,
                        'content': final_content or '',
                        'wordCount': final_word_count,
                        'plan': plan,
                        'status': 'error',
                    })
                else:
                    db_save_chapter(novel_id, {
                        'id': chapter_num,
                        'title': final_title,
                        'content': final_content,
                        'wordCount': final_word_count,
                        'plan': plan,
                        'status': 'completed',
                    })
                db_update_novel_meta(novel_id, updatedAt=now_str())

            except Exception as exc:
                db_update_novel_meta(novel_id, status='error', updatedAt=now_str(), error=str(exc))
                return
    finally:
        with db_lock:
            active_jobs.pop(novel_id, None)


def run_chapter_regen_job(novel_id, chapter_id):
    try:
        novel = db_get_novel_no_check(novel_id)
        if not novel:
            return

        api_url = novel.get('apiConfig', {}).get('baseUrl', '')
        api_key = novel.get('apiConfig', {}).get('apiKey', '')
        model = novel.get('apiConfig', {}).get('model', '')
        system_prompt = novel.get('apiConfig', {}).get('systemPrompt', '')
        theme = novel.get('theme', '')
        words_per_chapter = novel.get('wordsPerChapter', 3000)
        chapter_count = novel.get('chapterCount', 0)
        target = chapter_count if chapter_count and chapter_count > 0 else 500

        completed = db_get_completed_chapters(novel_id, exclude_id=chapter_id)
        previous_summary = '\n\n'.join(
            [f"第{c['id']}章「{c.get('title', '')}」：{c.get('content', '')[-500:]}" for c in completed[-3:]]
        )

        db_update_novel_meta(novel_id, status='generating', updatedAt=now_str(), error='')
        db_set_chapter_writing(novel_id, chapter_id, '', '')

        plan_prompt = (
            f'【小说主题】\n{theme}\n\n'
            f'【任务】\n这是第 {chapter_id} 章重新生成，总共 {target} 章。\n\n'
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
            title = f'第{chapter_id}章'

        db_save_chapter(novel_id, {
            'id': chapter_id,
            'title': title,
            'content': '',
            'wordCount': 0,
            'plan': plan,
            'status': 'writing',
        })
        db_update_novel_meta(novel_id, updatedAt=now_str())

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

        if not final_content or len(final_content.strip()) < 10:
            db_save_chapter(novel_id, {
                'id': chapter_id,
                'title': final_title,
                'content': final_content or '',
                'wordCount': final_word_count,
                'plan': plan,
                'status': 'error',
            })
        else:
            db_save_chapter(novel_id, {
                'id': chapter_id,
                'title': final_title,
                'content': final_content,
                'wordCount': final_word_count,
                'plan': plan,
                'status': 'completed',
            })
        db_update_novel_meta(novel_id, status='completed', updatedAt=now_str())

    except Exception as exc:
        db_update_novel_meta(novel_id, status='error', updatedAt=now_str(), error=str(exc))
    finally:
        with db_lock:
            active_jobs.pop(f'{novel_id}_ch{chapter_id}', None)


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f'[HTTP] {args[0]}', flush=True)

    def add_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Connection', 'keep-alive')

    def json_ok(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.add_cors()
        self.end_headers()
        self.wfile.write(body)

    def json_error(self, code, message):
        body = json.dumps({'error': message}, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.add_cors()
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def get_auth_user(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
            user_id = db_get_user_by_token(token)
            return user_id
        return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.add_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path == '/api/auth/me':
            user_id = self.get_auth_user()
            if not user_id:
                return self.json_error(401, 'unauthorized')
            username = db_get_username(user_id)
            return self.json_ok({'user_id': user_id, 'username': username})

        if path == '/api/user/config':
            user_id = self.get_auth_user()
            if not user_id:
                return self.json_error(401, 'unauthorized')
            config = db_get_user_api_config(user_id)
            return self.json_ok(config)

        if path == '/api/novels':
            user_id = self.get_auth_user()
            if not user_id:
                return self.json_error(401, 'unauthorized')
            return self.json_ok(db_get_user_novels(user_id))

        if path.startswith('/api/novels/') and len(path.split('/')) == 4:
            novel_id = path.split('/')[3]
            if len(novel_id) > 100:
                return self.json_error(404, 'not found')
            user_id = self.get_auth_user()
            if not user_id:
                return self.json_error(401, 'unauthorized')
            novel = db_get_novel(novel_id, user_id)
            if novel:
                return self.json_ok(novel)
            return self.json_error(404, 'novel not found')

        return self.serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path == '/api/auth/register':
            body = self.read_json()
            username = (body.get('username') or '').strip()
            password = body.get('password') or ''
            if not username or not password:
                return self.json_error(400, 'username and password required')
            if len(password) < 6:
                return self.json_error(400, 'password must be at least 6 characters')
            user_id = db_create_user(username, password)
            if not user_id:
                return self.json_error(409, 'username already exists')
            token = db_authenticate(username, password)
            return self.json_ok({'token': token, 'username': username}, 201)

        if path == '/api/auth/login':
            body = self.read_json()
            username = (body.get('username') or '').strip()
            password = body.get('password') or ''
            token = db_authenticate(username, password)
            if not token:
                return self.json_error(401, 'invalid credentials')
            return self.json_ok({'token': token, 'username': username})

        if path == '/api/auth/logout':
            auth = self.headers.get('Authorization', '')
            if auth.startswith('Bearer '):
                db_delete_token(auth[7:])
            return self.json_ok({'ok': True})

        user_id = self.get_auth_user()
        if not user_id:
            return self.json_error(401, 'unauthorized')

        if path == '/api/user/config':
            body = self.read_json()
            db_save_user_api_config(user_id, body)
            return self.json_ok({'ok': True})

        if path == '/api/novels':
            body = self.read_json()
            theme = (body.get('theme') or '').strip()
            if not theme:
                return self.json_error(400, 'theme required')
            api_config = db_get_user_api_config(user_id)
            if not api_config.get('apiKey'):
                return self.json_error(400, 'please configure your API key first')
            novel_config = body.get('novelConfig') or {}
            novel_id = uuid.uuid4().hex[:16]
            novel_data = {
                'id': novel_id,
                'theme': theme,
                'chapterCount': int(novel_config.get('chapterCount', 0) or 0),
                'wordsPerChapter': max(1, int(novel_config.get('wordsPerChapter', 3000) or 3000)),
                'status': 'generating',
                'error': '',
            }
            db_create_novel(user_id, novel_data)
            db_ensure_chapter(novel_id, 1)
            start_job(novel_id)
            return self.json_ok({'id': novel_id, 'status': 'generating', 'theme': theme}, 201)

        if path == '/api/novels/delete':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            db_delete_novel(novel_id, user_id)
            with db_lock:
                if novel_id in cancel_events:
                    cancel_events[novel_id].set()
                active_jobs.pop(novel_id, None)
            return self.json_ok({'ok': True})

        if path == '/api/novels/stop':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            novel = db_get_novel(novel_id, user_id)
            if not novel:
                return self.json_error(404, 'not found')
            for ch in novel.get('chapters', []):
                if ch.get('status') in ('writing', 'planning'):
                    db_reset_chapter(novel_id, ch['id'])
            db_update_novel_meta(novel_id, status='paused', updatedAt=now_str(), error='')
            with db_lock:
                if novel_id in cancel_events:
                    cancel_events[novel_id].set()
            return self.json_ok({'ok': True})

        if path == '/api/novels/continue':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            novel = db_get_novel(novel_id, user_id)
            if not novel:
                return self.json_error(404, 'not found')
            for ch in novel.get('chapters', []):
                if ch.get('status') in ('error', 'writing', 'planning'):
                    db_reset_chapter(novel_id, ch['id'])
            db_update_novel_meta(novel_id, status='generating', updatedAt=now_str(), error='')
            start_job(novel_id)
            return self.json_ok({'ok': True})

        if path == '/api/novels/regenerate':
            body = self.read_json()
            novel_id = body.get('id')
            if not novel_id:
                return self.json_error(400, 'id required')
            novel = db_get_novel(novel_id, user_id)
            if not novel:
                return self.json_error(404, 'not found')
            with db_lock:
                get_db().execute('DELETE FROM chapters WHERE novel_id = ?', (novel_id,))
                get_db().commit()
            db_ensure_chapter(novel_id, 1)
            db_update_novel_meta(novel_id, status='generating', updatedAt=now_str(), error='')
            start_job(novel_id)
            return self.json_ok({'ok': True})

        if path == '/api/novels/regenerate-chapter':
            body = self.read_json()
            novel_id = body.get('novelId')
            chapter_id = body.get('chapterId')
            if not novel_id or not chapter_id:
                return self.json_error(400, 'novelId and chapterId required')
            novel = db_get_novel(novel_id, user_id)
            if not novel:
                return self.json_error(404, 'not found')
            job_key = f'{novel_id}_ch{chapter_id}'
            with db_lock:
                if job_key in active_jobs:
                    return self.json_error(409, 'already regenerating')
            thread = threading.Thread(target=run_chapter_regen_job, args=(novel_id, chapter_id), daemon=True)
            with db_lock:
                active_jobs[job_key] = thread
            thread.start()
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

        ext = file_path.suffix.lower()
        content_types = {
            '.html': 'text/html',
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.json': 'application/json',
            '.svg': 'image/svg+xml',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.ico': 'image/x-icon',
        }
        content_type = content_types.get(ext, 'application/octet-stream')

        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.add_cors()
            if ext in ('.js', '.css', '.svg', '.png', '.jpg', '.ico'):
                self.send_header('Cache-Control', 'public, max-age=31536000')
            elif ext == '.html':
                self.send_header('Cache-Control', 'public, max-age=0, must-revalidate')
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.json_error(404, 'not found')


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    request_queue_size = 128


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)


def restore_generating_jobs():
    try:
        rows = db_get_generating_novels()
        for row in rows:
            novel_id = row['id']
            print(f'恢复生成任务: {novel_id}', flush=True)
            start_job(novel_id)
    except Exception as e:
        print(f'恢复任务失败: {e}', flush=True)


def run_server(host, port):
    db_init()
    ensure_dirs()
    restore_generating_jobs()
    print(f'服务启动: http://{host}:{port}', flush=True)
    try:
        server = ThreadedHTTPServer((host, port), AppHandler)
    except OSError as e:
        print(f'端口 {port} 被占用: {e}', flush=True)
        sys.exit(1)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run_server('0.0.0.0', port)