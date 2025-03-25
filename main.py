from NoWebsocket import WebSocketServer
from NoWebsocket.router import WebSocketRouter, Blueprint


def create_app():
    router = WebSocketRouter()

    # 自动注册所有蓝图
    Blueprint.auto_register(
        router,
        package_path='blueprints',
        bp_suffix='_bp'
    )

    return WebSocketServer(("0.0.0.0", 9000), router)


if __name__ == "__main__":
    server = create_app()
    print("WebSocket server running on ws://localhost:9000")
    try:
        server.serve_forever()  # 启动服务
    except KeyboardInterrupt:
        server.shutdown()  # 优雅关闭
        print("\n🛑 Server stopped")