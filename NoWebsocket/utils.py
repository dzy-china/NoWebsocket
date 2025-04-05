# utils.py
import logging
from .constants import WS_VERSION
import os

logger = logging.getLogger(__name__)

# 预定义握手头常量
REQUIRED_HEADERS = {'host', 'upgrade', 'connection', 'sec-websocket-key', 'sec-websocket-version'}


def validate_handshake_headers(headers):
    """验证握手头合规性"""
    if not REQUIRED_HEADERS.issubset(headers.keys()):
        logger.warning("Missing required headers: %s", REQUIRED_HEADERS - headers.keys())
        return False
    return (
        headers['upgrade'].lower() == 'websocket' and
        'upgrade' in headers['connection'].lower().split(', ') and
        headers['sec-websocket-version'] == WS_VERSION
    )




def setup_logging(level=logging.INFO, enable_logging=True):
    """配置日志系统（支持数字级别）"""
    if not enable_logging:
        return

    # 初始化formatter和root_logger
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    
    # 设置日志级别
    level_mapping = {
        1: logging.DEBUG,
        2: logging.INFO,
        3: logging.WARNING,
        4: logging.ERROR,
        5: logging.CRITICAL
    }
    if isinstance(level, int) and level in level_mapping:
        level = level_mapping[level]
    root_logger.setLevel(level)

    # 控制台处理器配置（修正顺序）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 移除所有现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 添加处理器
    root_logger.addHandler(console_handler)

    # 添加调试输出以确认配置
    root_logger.info("日志系统配置完成，级别设置为: %s", logging.getLevelName(level))

