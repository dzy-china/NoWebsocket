# websocket/protocol.py
import re
import base64
import hashlib
from .constants import WS_GUID

HEADER_REGEX = re.compile(rb'(?P<name>[^:\s]+):\s*(?P<value>.+?)\r\n')

def compute_accept_key(client_key):
    """计算WebSocket握手Accept Key"""
    sha1 = hashlib.sha1(client_key.encode() + WS_GUID.encode())
    return base64.b64encode(sha1.digest()).decode()

def parse_headers(data):
    """解析HTTP请求头"""
    headers = {}
    for match in HEADER_REGEX.finditer(data):
        name = match.group('name').decode('latin-1').lower()
        value = match.group('value').decode('latin-1').strip()
        headers[name] = value
    return headers