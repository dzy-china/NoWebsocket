class WebSocketError(Exception):
    """WebSocket协议异常基类"""
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket Error {code}: {reason}")