#!/bin/bash
# 私人摄影团队 MVP - 启动脚本
# 使用相对路径，可在任意目录运行

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="/tmp/ecommerce_mvp.pid"
LOG_DIR="$SCRIPT_DIR/logs"

# 加载 .env 文件（如果存在）
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# 优先使用项目虚拟环境（启动前由 ensure_backend_env 保证可用）
PYTHON=python3

_venv_python_ok() {
    local py="$1"
    [ -n "$py" ] && [ -x "$py" ] && "$py" -c 'import sys' > /dev/null 2>&1
}

ensure_backend_env() {
    if [ -x "$SCRIPT_DIR/.venv/bin/python" ] && ! _venv_python_ok "$SCRIPT_DIR/.venv/bin/python"; then
        echo "      检测到无效虚拟环境（可能由 rsync 从其他系统同步），正在重建..."
        rm -rf "$SCRIPT_DIR/.venv"
    fi
    if ! _venv_python_ok "$SCRIPT_DIR/.venv/bin/python"; then
        echo "      创建 Python 虚拟环境 (.venv)..."
        if ! python3 -m venv "$SCRIPT_DIR/.venv"; then
            echo "      ✗ 无法创建虚拟环境，请确认已安装 python3-venv"
            exit 1
        fi
    fi
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
    if ! "$PYTHON" -m uvicorn --version > /dev/null 2>&1; then
        echo "      安装后端依赖..."
        if ! "$PYTHON" -m pip install -q -r "$SCRIPT_DIR/backend/requirements.txt"; then
            echo "      ✗ 后端依赖安装失败，请检查 network 或 requirements.txt"
            exit 1
        fi
    fi
}

FRONTEND_DIR="$SCRIPT_DIR/frontend"

_frontend_deps_ok() {
    [ -f "$FRONTEND_DIR/package.json" ] || return 1
    [ -f "$FRONTEND_DIR/node_modules/vite/dist/node/cli.js" ] || return 1
    (cd "$FRONTEND_DIR" && ./node_modules/.bin/vite --version > /dev/null 2>&1)
}

ensure_frontend_deps() {
    if _frontend_deps_ok; then
        return 0
    fi

    if [ -d "$FRONTEND_DIR/node_modules" ]; then
        echo "      检测到无效前端依赖（可能由 rsync 从其他系统同步），正在重装..."
        rm -rf "$FRONTEND_DIR/node_modules"
    else
        echo "      安装前端依赖 (frontend/)..."
    fi

    cd "$FRONTEND_DIR" || { echo "      ✗ 前端目录不存在: $FRONTEND_DIR"; exit 1; }

    if [ -f package-lock.json ]; then
        if ! npm ci --no-audit --no-fund 2>&1 | tail -8; then
            echo "      npm ci 失败，尝试 npm install..."
            rm -rf node_modules
            if ! npm install --no-audit --no-fund 2>&1 | tail -8; then
                echo "      ✗ 前端依赖安装失败，请在 frontend/ 目录执行 npm install"
                exit 1
            fi
        fi
    else
        if ! npm install --no-audit --no-fund 2>&1 | tail -8; then
            echo "      ✗ 前端依赖安装失败，请在 frontend/ 目录执行 npm install"
            exit 1
        fi
    fi

    if ! _frontend_deps_ok; then
        echo "      ✗ 前端依赖仍不可用，请检查 Node.js 版本与磁盘空间"
        exit 1
    fi
}

if [ -f "$SCRIPT_DIR/.venv/bin/activate" ] && _venv_python_ok "$SCRIPT_DIR/.venv/bin/python"; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "======================================"
echo "  私人摄影团队 MVP - 服务管理"
echo "======================================"
echo "  项目目录: $SCRIPT_DIR"
echo "======================================"

# 检查服务是否已在运行
check_running() {
    if [ -f "$PID_FILE" ]; then
        while read -r line; do
            PID=$(echo "$line" | cut -d':' -f2)
            if ps -p "$PID" > /dev/null 2>&1; then
                return 0
            fi
        done < "$PID_FILE"
    fi
    return 1
}

# 停止服务
stop_services() {
    echo "[1/3] 停止已有服务..."
    
    if [ -f "$PID_FILE" ]; then
        while read -r line; do
            PID=$(echo "$line" | cut -d':' -f2)
            NAME=$(echo "$line" | cut -d':' -f1)
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "      停止 $NAME (PID: $PID)"
                kill "$PID" 2>/dev/null
                sleep 1
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    pkill -f "uvicorn main:app" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    sleep 2
    echo "      ✓ 服务已停止"
}

# 启动服务
start_services() {
    echo "[2/3] 启动服务..."
    
    > "$PID_FILE"
    
    ensure_backend_env
    
    # 启动后端
    echo "      启动后端服务 (端口: 8155)..."
    cd "$SCRIPT_DIR/backend" || { echo "      ✗ 后端目录不存在: $SCRIPT_DIR/backend"; exit 1; }
    
    # 初始化数据库
    $PYTHON -c "from database import engine, Base; from models import *; from models import LookbookStudioTask; Base.metadata.create_all(bind=engine)" 2>/dev/null
    
    nohup $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8155 > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "backend:$BACKEND_PID" >> "$PID_FILE"
    
    BACKEND_OK=false
    for _ in 1 2 3 4 5 6 7 8; do
        sleep 1
        if curl -s http://127.0.0.1:8155/ > /dev/null 2>&1; then
            BACKEND_OK=true
            break
        fi
    done
    if [ "$BACKEND_OK" = true ]; then
        echo "      ✓ 后端服务启动成功 (PID: $BACKEND_PID)"
    else
        echo "      ✗ 后端服务启动失败"
        echo "      日志: $LOG_DIR/backend.log"
        tail -5 "$LOG_DIR/backend.log" 2>/dev/null | sed 's/^/        /'
    fi
    
    # 启动前端
    echo "      启动前端服务 (端口: 8150)..."
    ensure_frontend_deps
    cd "$FRONTEND_DIR" || { echo "      ✗ 前端目录不存在: $FRONTEND_DIR"; exit 1; }

    nohup npm run dev -- --host --port 8150 > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "frontend:$FRONTEND_PID" >> "$PID_FILE"

    FRONTEND_OK=false
    for _ in 1 2 3 4 5 6 7 8 10 12; do
        sleep 1
        if curl -s http://127.0.0.1:8150/ > /dev/null 2>&1; then
            FRONTEND_OK=true
            break
        fi
    done
    if [ "$FRONTEND_OK" = true ]; then
        echo "      ✓ 前端服务启动成功 (PID: $FRONTEND_PID)"
    else
        echo "      ✗ 前端服务启动失败"
        echo "      日志: $LOG_DIR/frontend.log"
        tail -8 "$LOG_DIR/frontend.log" 2>/dev/null | sed 's/^/        /'
    fi
}

# 显示状态
show_status() {
    echo "[3/3] 服务状态检查"
    echo ""
    
    BACKEND_RUNNING=false
    FRONTEND_RUNNING=false
    
    if curl -s http://127.0.0.1:8155/ > /dev/null 2>&1; then
        echo "      ✓ 后端服务: 运行中 (http://localhost:8155)"
        BACKEND_RUNNING=true
    else
        echo "      ✗ 后端服务: 未运行"
    fi
    
    if curl -s http://127.0.0.1:8150/ > /dev/null 2>&1; then
        echo "      ✓ 前端服务: 运行中 (http://localhost:8150)"
        FRONTEND_RUNNING=true
    else
        echo "      ✗ 前端服务: 未运行"
    fi
    
    echo ""
    echo "======================================"
    if [ "$BACKEND_RUNNING" = true ] && [ "$FRONTEND_RUNNING" = true ]; then
        echo "  所有服务运行正常"
        echo "======================================"
        echo "  前端访问: http://localhost:8150"
        echo "  后端API:  http://localhost:8155"
        echo "======================================"
        return 0
    else
        echo "  部分服务未启动"
        echo "======================================"
        echo "  查看日志:"
        echo "    后端: tail -f $LOG_DIR/backend.log"
        echo "    前端: tail -f $LOG_DIR/frontend.log"
        echo "======================================"
        return 1
    fi
}

# 主逻辑
case "${1:-start}" in
    start)
        if check_running; then
            echo "服务已在运行中..."
            show_status
        else
            stop_services
            start_services
            show_status
        fi
        ;;
    stop)
        stop_services
        echo "服务已停止"
        ;;
    restart)
        stop_services
        start_services
        show_status
        ;;
    status)
        show_status
        ;;
    logs)
        echo "查看日志 (按 Ctrl+C 退出)..."
        tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" 2>/dev/null
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看实时日志"
        exit 1
        ;;
esac
