import logging

from NoWebsocket.server import WebSocketServer
from NoWebsocket.utils import setup_logging


# 初始化日志系统（INFO 级别）
setup_logging(logging.INFO)

if __name__ == "__main__":
    # 自动注册蓝图（扫描 blueprints 目录）
    server = WebSocketServer.create_with_blueprints(
        host='0.0.0.0',  # 监听所有网络接口
        port=8765  # 绑定端口
    )
    print("Server running → ws://0.0.0.0:8765")
    try:
        server.serve_forever()  # 启动服务
    except KeyboardInterrupt:
        server.shutdown()  # 优雅关闭
        print("\n🛑 Server stopped")