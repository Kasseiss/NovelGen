#!/usr/bin/env python3
"""
墨流小说生成器 - Python 启动脚本
用法: python run.py [--port 3000] [--host 0.0.0.0] [--build]
"""

import os
import sys
import subprocess
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DIST_DIR = BASE_DIR / 'dist'

class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory or str(DIST_DIR), **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path) and not os.path.exists(os.path.join(path, 'index.html')):
            self.path = '/index.html'
        return super().do_GET()

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def check_node():
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    return False


def run_npm_install():
    print("正在安装依赖...")
    result = subprocess.run(['npm', 'install'], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"安装失败: {result.stderr}")
        sys.exit(1)
    print("依赖安装完成")


def run_build():
    print("正在构建...")
    result = subprocess.run(['npm', 'run', 'build'], cwd=BASE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"构建失败: {result.stderr}")
        sys.exit(1)
    print("构建完成")


def main():
    parser = argparse.ArgumentParser(description='墨流小说生成器')
    parser.add_argument('--port', type=int, default=3000, help='端口号 (默认: 3000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument('--build', action='store_true', help='强制重新构建')
    parser.add_argument('--no-build', action='store_true', help='跳过构建，直接启动')
    args = parser.parse_args()

    if args.build:
        if not check_node():
            print("错误: 未找到 Node.js，请先安装 Node.js")
            sys.exit(1)
        run_npm_install()
        run_build()
    elif not args.no_build:
        if not DIST_DIR.exists():
            if not check_node():
                print("错误: 未找到 Node.js，请先安装 Node.js 或使用 --no-build 跳过构建")
                sys.exit(1)
            run_npm_install()
            run_build()
        else:
            print(f"检测到 dist 目录，跳过构建")

    if not DIST_DIR.exists():
        print("错误: dist 目录不存在，请先执行构建")
        sys.exit(1)

    handler = partial(SPAHandler, directory=str(DIST_DIR))
    server = HTTPServer((args.host, args.port), handler)

    print(f"")
    print(f"  墨流小说生成器")
    print(f"  http://localhost:{args.port}")
    print(f"  http://0.0.0.0:{args.port}")
    print(f"")
    print(f"  按 Ctrl+C 停止服务")
    print(f"")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == '__main__':
    main()
