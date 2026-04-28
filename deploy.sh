#!/bin/bash
set -e

echo "🚀 Content Aggregator 部署脚本"
echo ""
echo "支持平台: Render / Railway / Replit / 本地服务器"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    exit 1
fi

# 安装依赖
echo "📦 安装后端依赖..."
cd backend
pip install -r requirements.txt

# 初始化数据库
echo "🗄️ 初始化数据库..."
python3 -c "from app.database import init_db; init_db()"

# 启动服务
echo "🏁 启动服务..."
echo "访问地址: http://localhost:8000"
python3 run.py
