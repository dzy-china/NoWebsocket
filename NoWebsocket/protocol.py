import re
import base64
import hashlib
from .constants import WS_GUID

HEADER_REGEX = re.compile(rb'(?P<name>[^:\s]+):\s*(?P<value>.+?)\r\n')

class ProtocolHandler:
    """WebSocket协议处理器"""
    _WS_GUID_BYTES = WS_GUID.encode('utf-8')

    @classmethod
    def compute_accept_key(cls, client_key):
        combined = client_key.encode('utf-8') + cls._WS_GUID_BYTES
        return base64.b64encode(hashlib.sha1(combined).digest()).decode()

    @staticmethod
    def parse_headers(data):
        headers = {}
        headers.update(
            (match.group('name').decode('latin-1').lower(), 
             match.group('value').decode('latin-1').strip())
            for match in HEADER_REGEX.finditer(data)
        )
        return headers

    @classmethod
    def create_response_headers(cls, client_key):
        accept_key = cls.compute_accept_key(client_key)
        return (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )