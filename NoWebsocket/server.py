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

class WebSocketHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.conn = WebSocketConnection(
            self.request,
            config={
                'max_message_size': self.server.max_message_size,
                'read_timeout': self.server.read_timeout
            },
            client_address=self.client_address  # 传递客户端地址
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

    def __init__(self, server_address, router, **kwargs):
        super().__init__(server_address, WebSocketHandler)
        self.router = router
        self.max_header_size = kwargs.get('max_header_size', DEFAULT_MAX_HEADER_SIZE)
        self.max_message_size = kwargs.get('max_message_size', DEFAULT_MAX_MESSAGE_SIZE)
        self.read_timeout = kwargs.get('read_timeout', DEFAULT_READ_TIMEOUT)

    @classmethod
    def create_with_blueprints(cls, host, port, blueprint_package='blueprints'):
        router = WebSocketRouter()
        Blueprint.auto_discover(router, blueprint_package)
        return cls((host, port), router)