"""NexusForge 后端 PyInstaller 入口点

接收端口号作为命令行参数，启动 uvicorn serving FastAPI app。
在 PyInstaller 冻结模式下，自动设置工作目录和 sys.path。
"""
import os
import sys


def _setup_frozen_paths():
    """PyInstaller 冻结模式下设置路径"""
    if getattr(sys, "frozen", False):
        # 可执行文件所在目录（onedir 模式下是 dist/nexusforge-backend/）
        base_dir = os.path.dirname(sys.executable)
        os.chdir(base_dir)
        # 确保 _internal 目录在 sys.path 中（PyInstaller 6.x 的依赖目录）
        internal_dir = os.path.join(base_dir, "_internal")
        if os.path.isdir(internal_dir):
            sys.path.insert(0, internal_dir)


def main():
    _setup_frozen_paths()

    # 解析端口号
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    # 启动 uvicorn
    import uvicorn

    uvicorn.run(
        "interfaces.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
