from NoWebsocket.application import WebSocketApplication
from NoWebsocket.router import Blueprint

chat_bp = Blueprint(prefix='/chat')

@chat_bp.route("/youmi")
class User(WebSocketApplication):
    def on_open(self):
        """连接建立时触发"""
        pass

    def on_message(self, message):
        print(message)
        self.connection.send_text(f"你好，我是悠米系统服务，收到了你的信息：\'{message}\'")

    def on_binary(self, data):
        """收到二进制消息时触发"""
        print(data)

    def on_close(self):
        """连接关闭时触发"""
        print("on_close")