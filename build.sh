#!/usr/bin/env bash
# Render 构建脚本：安装后端依赖 + 构建前端 + 复制静态文件
set -e

# 后端依赖
cd backend
pip install -r requirements.txt

# 前端构建
cd ../frontend
npm install
npm run build

# 把构建产物复制到后端 static/ 目录，由 FastAPI 提供服务
rm -rf ../backend/static
cp -r dist ../backend/static

echo "Build complete."
