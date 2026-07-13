#!/usr/bin/env python3
"""星渊笔一键启动脚本
运行后会自动启动后端服务器并打开浏览器。
用法: python start.py
"""
import subprocess
import sys
import os
import time
import secrets
import urllib.request
import webbrowser
import shutil
import signal

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
LOG_DIR = os.path.join(BACKEND_DIR, "logs")
PORT = 8000
HEALTH_URL = f"http://127.0.0.1:{PORT}/health"
APP_URL = f"http://localhost:{PORT}"
FRONTEND_DEV_URL = "http://localhost:5173"

# 优先使用项目自带的虚拟环境，避免依赖缺失
VENV_PYTHON = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


def print_banner():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║          ✦  星 渊 笔  ✦              ║")
    print("  ║      AI 驱动的小说创作系统            ║")
    print("  ╚══════════════════════════════════════╝")
    print()


def check_port_in_use():
    """检查端口是否已被占用（服务可能已在运行）"""
    try:
        urllib.request.urlopen(HEALTH_URL, timeout=1)
        return True
    except:
        return False


def wait_for_server(max_wait=30):
    """等待服务器启动就绪"""
    for i in range(max_wait):
        try:
            urllib.request.urlopen(HEALTH_URL, timeout=2)
            return True
        except:
            time.sleep(1)
    return False


def _check_dependencies():
    """检查后端依赖是否已安装"""
    try:
        subprocess.run(
            [PYTHON, "-c", "import fastapi, uvicorn"],
            cwd=BACKEND_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _mask_key(key: str) -> str:
    """对 API Key 进行脱敏，仅显示首尾片段。"""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def _is_development(env: dict) -> bool:
    """开发模式：未设置 APP_ENV 或明确为 development/dev/test 时视为开发环境。"""
    app_env = env.get("APP_ENV", "").lower()
    return not app_env or app_env in ("development", "dev", "test")


def _is_production(env: dict) -> bool:
    """生产模式：必须显式设置 APP_ENV=production。"""
    return env.get("APP_ENV", "").lower() == "production"


def _start_frontend_dev_server(env: dict):
    """启动前端 Vite 开发服务器，并将 API Key 通过 VITE_ 前缀注入。"""
    npm = shutil.which("npm")
    if not npm:
        print("  ⚠️  未找到 npm，无法自动启动前端开发服务器。")
        print("     请在前端目录手动执行: npm run dev")
        return None

    if not os.path.isdir(os.path.join(FRONTEND_DIR, "node_modules")):
        print("  ⚠️  前端依赖未安装，无法自动启动前端开发服务器。")
        print("     请在前端目录执行: npm install")
        return None

    print("  🚀 正在启动前端开发服务器...")
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(
        [npm, "run", "dev"],
        cwd=FRONTEND_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs,
    )


def _wait_for_frontend_dev_server(url: str, max_wait: int = 30) -> bool:
    """等待前端开发服务器就绪"""
    for i in range(max_wait):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except:
            time.sleep(1)
    return False


def _terminate_process(proc):
    """安全终止子进程及其进程树（Windows 下使用 Ctrl+Break 事件）。"""
    if proc is None or proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        else:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main():
    print_banner()

    if not _check_dependencies():
        print("  ✗ 检测到后端依赖未安装或虚拟环境异常。")
        print(f"     请检查: {VENV_PYTHON}")
        print("     或在 backend 目录执行: python -m pip install -r requirements.txt")
        sys.exit(1)

    # 如果服务已经在运行，直接打开浏览器
    if check_port_in_use():
        print("  ✓ 检测到服务已在运行，直接打开浏览器...")
        try:
            webbrowser.open(APP_URL)
        except:
            pass
        print(f"\n  🌐 访问地址: {APP_URL}")
        print("\n  按 Ctrl+C 退出。\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return

    # 准备日志目录
    os.makedirs(LOG_DIR, exist_ok=True)
    # M-01 修复：日志文件改为追加模式（"a"），避免每次启动丢失历史日志。
    # 旧实现使用 "w" 模式会清空文件，导致问题排查时无法回溯历史。
    log_file = open(os.path.join(LOG_DIR, "server.log"), "a", encoding="utf-8")

    # 启动后端服务
    print(f"  🚀 正在启动后端服务 (端口 {PORT})...")

    env = os.environ.copy()
    env["PYTHONPATH"] = BACKEND_DIR

    # API Key 安全处理：
    # - 生产环境（APP_ENV=production）必须由外部显式设置 API_KEY，否则拒绝启动。
    # - 开发环境可自动生成，但只保留在环境变量中，不再写入前端静态目录。
    if env.get("API_KEY"):
        print(f"  🔑 使用外部 API Key: {_mask_key(env['API_KEY'])}")
    elif _is_production(env):
        print("  ✗ 生产环境必须显式设置 API_KEY 环境变量。")
        print("     Windows: set API_KEY=your-secret-api-key")
        print("     Linux/macOS: export API_KEY=your-secret-api-key")
        log_file.close()
        sys.exit(1)
    else:
        generated_key = secrets.token_urlsafe(32)
        env["API_KEY"] = generated_key
        os.environ["API_KEY"] = generated_key
        print(f"  🔑 已自动生成 API Key: {_mask_key(generated_key)}")
        print(f"  ⚠️  请妥善保管此 API Key，前端请求需在 Header 中携带 X-API-Key")

    # 将 key 通过 VITE_ 前缀注入前端开发服务器，避免落盘到前端静态目录。
    env["VITE_API_KEY"] = env["API_KEY"]

    # M-01 修复：默认绑定 127.0.0.1，避免桌面用户启动后服务暴露在局域网。
    # 用户若需外部访问，设置 APP_HOST=0.0.0.0 环境变量即可。
    bind_host = env.get("APP_HOST", "127.0.0.1")

    print(f"  🐍 使用 Python: {PYTHON}")

    proc = subprocess.Popen(
        [
            PYTHON, "-m", "uvicorn",
            "interfaces.main:app",
            "--host", bind_host,
            "--port", str(PORT),
            "--log-level", "warning",
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    # 等待服务就绪
    print("  ⏳ 等待服务启动", end="", flush=True)
    for i in range(30):
        print(".", end="", flush=True)
        try:
            urllib.request.urlopen(HEALTH_URL, timeout=2)
            print(" 就绪!", flush=True)
            break
        except:
            time.sleep(1)
    else:
        print(" 超时!", flush=True)
        print("\n  ✗ 服务启动失败，请查看日志: backend/logs/server.log", flush=True)
        proc.terminate()
        log_file.close()
        sys.exit(1)

    frontend_proc = None
    open_url = APP_URL

    if _is_development(env):
        frontend_proc = _start_frontend_dev_server(env)
        if frontend_proc is not None:
            print("  ⏳ 等待前端开发服务器就绪", end="", flush=True)
            if _wait_for_frontend_dev_server(FRONTEND_DEV_URL):
                print(" 就绪!", flush=True)
                open_url = FRONTEND_DEV_URL
            else:
                print(" 超时!", flush=True)
                print("\n  ⚠️ 前端开发服务器启动超时，请检查 frontend 目录依赖是否完整。", flush=True)

    # 打开浏览器
    print(f"\n  🌐 正在打开浏览器: {open_url}", flush=True)
    try:
        webbrowser.open(open_url)
    except:
        pass

    print(f"\n  ✅ 星渊笔已启动！", flush=True)
    print(f"     访问地址: {open_url}", flush=True)
    print(f"     日志文件: backend/logs/server.log", flush=True)
    print(f"\n  按 Ctrl+C 停止服务并退出。\n", flush=True)

    # 保持运行，等待用户退出
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n  🛑 正在停止服务...")
        _terminate_process(frontend_proc)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()
        log_file.close()
        print("  ✅ 服务已停止，再见！\n")


if __name__ == "__main__":
    main()
