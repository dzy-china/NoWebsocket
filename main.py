# 主文件
from NoWebsocket.server import WebSocketServer

if __name__ == "__main__":
    server = WebSocketServer.create_with_blueprints(
        host='0.0.0.0',
        port=8765,
        enable_logging=True,    # 启用日志
    )
    print("Server running → ws://0.0.0.0:8765")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\n🛑 Server stopped")