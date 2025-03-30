import re
import base64
import hashlib
from .constants import WS_GUID

HEADER_REGEX = re.compile(rb'(?P<name>[^:\s]+):\s*(?P<value>.+?)\r\n')

class ProtocolHandler:
    """WebSocket协议处理器"""
    @staticmethod
    def compute_accept_key(client_key):
        sha1 = hashlib.sha1(client_key.encode() + WS_GUID.encode())
        return base64.b64encode(sha1.digest()).decode()

    @staticmethod
    def parse_headers(data):
        headers = {}
        for match in HEADER_REGEX.finditer(data):
            name = match.group('name').decode('latin-1').lower()
            value = match.group('value').decode('latin-1').strip()
            headers[name] = value
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