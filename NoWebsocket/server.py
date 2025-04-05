import socketserver
import logging
from urllib.parse import urlparse
from .connection import WebSocketConnection
from .exceptions import WebSocketError
from .protocol import ProtocolHandler
from .router import WebSocketRouter, Blueprint
from .constants import *
from .utils import validate_handshake_headers

logger = logging.getLogger(__name__)

from typing import override


class WebSocketHandler(socketserver.BaseRequestHandler):
    server: 'WebSocketServer'

    @override
    def setup(self):
        self.conn = WebSocketConnection(
            self.request,
            config={
                'max_message_size': self.server.max_message_size,
                'read_timeout': self.server.read_timeout
            },
            client_address=self.client_address
        )
        self.app = None

    def handle(self):
        if not self._perform_handshake():
            return

        try:
            self.app.on_open()
            while self.conn.connected:
                message = self.conn._receive_message()
                if message is None:
                    break
                self._dispatch_message(message)
        except Exception as e:
            logger.error("Handler error: %s", e)
            self.conn.close(1011, str(e))
        finally:
            self._cleanup()

    def _perform_handshake(self):
        try:
            request_data = self._read_handshake_data()
            path = self._parse_request_path(request_data)
            handler_class, params = self.server.router.match(path)
            if not handler_class:
                self._send_404()
                return False

            headers = ProtocolHandler.parse_headers(request_data)
            if not validate_handshake_headers(headers):
                return False

            self._send_handshake_response(headers['sec-websocket-key'])
            self.app = handler_class(connection=self.conn)
            self.app.path_params = params
            return True
        except Exception as e:
            logger.error("Handshake failed: %s", e)
            return False

    def _read_handshake_data(self):
        data = bytearray()
        while True:
            chunk = self.request.recv(1024)
            if not chunk:
                break
            data.extend(chunk)
            if b'\r\n\r\n' in data:
                break
            if len(data) > self.server.max_header_size:
                raise WebSocketError(400, "Header too large")
        return data

    def _parse_request_path(self, data):
        try:
            request_line = data.split(b'\r\n')[0].decode()
            return urlparse(request_line.split()[1]).path
        except (IndexError, UnicodeDecodeError) as e:
            raise WebSocketError(400, "Invalid request") from e

    def _send_handshake_response(self, client_key):
        response = ProtocolHandler.create_response_headers(client_key)
        self.request.sendall(response.encode())

    def _send_404(self):
        self.request.sendall(b'HTTP/1.1 404 Not Found\r\n\r\n')

    def _dispatch_message(self, message):
        try:
            if isinstance(message, str):
                self.app.on_message(message)
            else:
                self.app.on_binary(message)
        except Exception as e:
            logger.error("Message handling error: %s", e)
            raise

    def _cleanup(self):
        try:
            self.app.on_close()
        except Exception as e:
            logger.error("on_close error: %s", e)
        finally:
            self.conn.close()


class WebSocketServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    # 显式声明服务器配置属性
    max_header_size: int = DEFAULT_MAX_HEADER_SIZE
    max_message_size: int = DEFAULT_MAX_MESSAGE_SIZE
    read_timeout: float = DEFAULT_READ_TIMEOUT
    router: WebSocketRouter

    def __init__(
            self,
            server_address,
            router,
            enable_logging=False,
            log_level=logging.INFO,
            max_header_size=DEFAULT_MAX_HEADER_SIZE,
            max_message_size=DEFAULT_MAX_MESSAGE_SIZE,
            read_timeout=DEFAULT_READ_TIMEOUT,
            **kwargs
    ):
        super().__init__(server_address, WebSocketHandler)
        self.router = router
        self.max_header_size = max_header_size
        self.max_message_size = max_message_size
        self.read_timeout = read_timeout

        if enable_logging:
            from .utils import setup_logging
            setup_logging(log_level)
        else:
            # 完全禁用日志配置
            logging.getLogger().handlers = []
            logging.getLogger().propagate = False

    @classmethod
    def create_with_blueprints(
            cls,
            host,
            port,
            blueprint_package='blueprints',
            enable_logging=True,
            log_level=logging.INFO,
            max_header_size=DEFAULT_MAX_HEADER_SIZE,
            max_message_size=DEFAULT_MAX_MESSAGE_SIZE,
            read_timeout=DEFAULT_READ_TIMEOUT
    ):
        """创建服务器实例并自动注册蓝图"""
        if enable_logging:
            from .utils import setup_logging
            setup_logging(log_level)
        else:
            # 完全禁用日志配置
            logging.getLogger().handlers = []
            logging.getLogger().propagate = False
        router = WebSocketRouter()
        Blueprint.auto_discover(router, blueprint_package)
        return cls(
            (host, port),
            router,
            enable_logging=False,
            log_level=logging.NOTSET if not enable_logging else log_level,
            max_header_size=max_header_size,
            max_message_size=max_message_size,
            read_timeout=read_timeout
        )
