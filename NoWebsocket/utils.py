import logging
from .constants import WS_VERSION

logger = logging.getLogger(__name__)

def validate_handshake_headers(headers):
    """验证握手头合规性"""
    required = {'host', 'upgrade', 'connection',
               'sec-websocket-key', 'sec-websocket-version'}
    if not required.issubset(headers.keys()):
        logger.warning("Missing required headers: %s", required - headers.keys())
        return False
    return (
        headers['upgrade'].lower() == 'websocket' and
        'upgrade' in headers['connection'].lower().split(', ') and
        headers['sec-websocket-version'] == WS_VERSION
    )

def setup_logging(level=logging.INFO):
    """配置日志系统"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level
    )