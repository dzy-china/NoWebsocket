# blueprints/EchoBp.py
from NoWebsocket.router import Blueprint
from NoWebsocket.application import WebSocketApplication

echo_bp = Blueprint('/echo')

@echo_bp.route('/{message:str}')
class EchoBp(WebSocketApplication):
    def on_open(self):
        # 正确获取路径参数（类型为 str，无需转换）
        initial_message = self.path_params.get('message', '')
        self.connection.send_text(f"初始消息: {initial_message}")

    def on_message(self, message):
        print(message)
        self.connection.send_text(f"{message}")

    def on_close(self):
        # 正确获取关闭状态码和原因
        code = self.connection.close_code
        reason = self.connection.close_reason or "未知原因"
        print(f"连接关闭 → 状态码: {code}, 原因: {reason}")