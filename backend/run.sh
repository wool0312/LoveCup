#!/usr/bin/env bash
# 启动后端开发服务器（含自动建表、自动锁定兜底任务）
set -e
cd "$(dirname "$0")"
exec .venv/bin/python -m uvicorn app.main:app --reload --port 8000
