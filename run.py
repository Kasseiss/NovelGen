#!/usr/bin/env python3
"""
墨流小说生成器 - 一键启动
用法: python3 run.py [--port 3000] [--host 0.0.0.0]
"""

import os
import sys
import subprocess
import argparse
import platform
import shutil
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DIST_DIR = BASE_DIR / 'dist'
NODE_DIR = BASE_DIR / '.node'
NODE_BIN = NODE_DIR / 'bin' / 'node' if platform.system() != 'Windows' else NODE_DIR / 'node.exe'
NPM_BIN = NODE_DIR / 'bin' / 'npm' if platform.system() != 'Windows' else NODE_DIR / 'npm' / 'npm-cli.js'

NODE_VERSION = 'v20.18.0'

NODE_URLS = {
    'Linux-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-x64.tar.xz',
    'Linux-aarch64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-arm64.tar.xz',
    'Darwin-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-x64.tar.xz',
    'Darwin-arm64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-arm64.tar.xz',
    'Windows-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip',
}


class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory or str(DIST_DIR), **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or (os.path.isdir(path) and not os.path.exists(os.path.join(path, 'index.html'))):
            self.path = '/index.html'
        return super().do_GET()

    def log_message(self, format, *args):
        pass


def get_platform_key():
    system = platform.system()
    machine = platform.machine()
    return f'{system}-{machine}'


def get_node_from_system():
    path = shutil.which('node')
    if path:
        return path, shutil.which('npm')
    return None, None


def get_bundled_node():
    if NODE_BIN.exists():
        return str(NODE_BIN), str(NPM_BIN)
    return None, None


def install_node():
    key = get_platform_key()
    url = NODE_URLS.get(key)
    if not url:
        print(f'  不支持的平台: {key}')
        sys.exit(1)

    print(f'  平台: {key}')
    print(f'  下载 Node.js {NODE_VERSION}...')

    filename = url.split('/')[-1]
    download_path = BASE_DIR / filename

    try:
        urllib.request.urlretrieve(url, download_path)
    except Exception as e:
        print(f'  下载失败: {e}')
        sys.exit(1)

    print('  解压中...')
    NODE_DIR.mkdir(exist_ok=True)

    if filename.endswith('.tar.xz'):
        subprocess.run(['tar', '-xf', str(download_path), '-C', str(NODE_DIR), '--strip-components=1'], check=True)
    elif filename.endswith('.zip'):
        import zipfile
        with zipfile.ZipFile(download_path, 'r') as zf:
            members = zf.namelist()
            prefix = members[0].split('/')[0] + '/'
            for m in members:
                if m.startswith(prefix):
                    target = NODE_DIR / m[len(prefix):]
                    if m.endswith('/'):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(m) as src, open(target, 'wb') as dst:
                            dst.write(src.read())

    download_path.unlink(missing_ok=True)
    print('  Node.js 安装完成')


def get_node_and_npm():
    system_node, system_npm = get_node_from_system()
    if system_node:
        return system_node, system_npm

    bundled_node, bundled_npm = get_bundled_node()
    if bundled_node:
        return bundled_node, bundled_npm

    print('')
    print('  未检测到 Node.js，正在自动安装...')
    install_node()

    bundled_node, bundled_npm = get_bundled_node()
    if bundled_node:
        return bundled_node, bundled_npm

    print('  Node.js 安装失败')
    sys.exit(1)


def npm_install(node_path, npm_path):
    print('  安装依赖...')
    if npm_path and npm_path.endswith('npm-cli.js'):
        cmd = [node_path, npm_path, 'install']
    else:
        cmd = [npm_path or 'npm', 'install']

    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'  安装失败: {result.stderr[:200]}')
        sys.exit(1)


def npm_build(node_path, npm_path):
    print('  构建项目...')
    if npm_path and npm_path.endswith('npm-cli.js'):
        cmd = [node_path, npm_path, 'run', 'build']
    else:
        cmd = [npm_path or 'npm', 'run', 'build']

    env = os.environ.copy()
    env['PATH'] = str(NODE_DIR / 'bin') + os.pathsep + env.get('PATH', '')
    env['NODE'] = str(node_path)

    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f'  构建失败: {result.stderr[:500]}')
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='墨流小说生成器')
    parser.add_argument('--port', type=int, default=3000, help='端口号')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    args = parser.parse_args()

    print('')
    print('  ╔══════════════════════════════╗')
    print('  ║       墨流小说生成器          ║')
    print('  ╚══════════════════════════════╝')
    print('')

    if not DIST_DIR.exists():
        node_path, npm_path = get_node_and_npm()
        npm_install(node_path, npm_path)
        npm_build(node_path, npm_path)
        print('')
    else:
        print('  已有构建文件，跳过构建')

    if not DIST_DIR.exists():
        print('  构建失败: dist 目录不存在')
        sys.exit(1)

    handler = partial(SPAHandler, directory=str(DIST_DIR))
    server = HTTPServer((args.host, args.port), handler)

    print(f'  服务已启动')
    print(f'  本机访问: http://localhost:{args.port}')
    print(f'  局域网访问: http://0.0.0.0:{args.port}')
    print(f'')
    print(f'  Ctrl+C 停止')
    print(f'')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  服务已停止')
        server.server_close()


if __name__ == '__main__':
    main()
