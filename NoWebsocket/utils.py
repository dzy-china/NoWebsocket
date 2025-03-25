# websocket/utils.py
from .constants import WS_VERSION

def validate_handshake_headers(headers):
    """验证WebSocket握手头"""
    required = {'host', 'upgrade', 'connection',
               'sec-websocket-key', 'sec-websocket-version'}
    if not required.issubset(headers.keys()):
        return False
    return (
        headers['upgrade'].lower() == 'websocket' and
        'upgrade' in headers['connection'].lower().split(', ') and
        headers['sec-websocket-version'] == WS_VERSION
    )