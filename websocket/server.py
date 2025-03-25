# websocket/server.py
import socketserver
from urllib.parse import urlparse
from .connection import WebSocketConnection
from .protocol import parse_headers, compute_accept_key
from .constants import *
from .utils import validate_handshake_headers

class WebSocketHandler(socketserver.BaseRequestHandler):
    def handle_handshake(self):
        buffer = bytearray()
        header_end = b'\r\n\r\n'

        while True:
            chunk = self.request.recv(1024)
            if not chunk:
                return False
            buffer.extend(chunk)
            if header_end in buffer:
                break
            if len(buffer) > self.server.max_header_size:
                return False

        try:
            request_line = buffer.split(b'\r\n')[0].decode('latin-1')
            method, path, _ = request_line.split()[:3]
            path = urlparse(path).path
        except Exception:
            return False

        handler_class, params = self.server.router.match(path)
        if not handler_class:
            self.request.sendall(b'HTTP/1.1 404 Not Found\r\n\r\n')
            return False

        headers = parse_headers(buffer)
        if not validate_handshake_headers(headers):
            return False

        accept_key = compute_accept_key(headers['sec-websocket-key'])
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        self.request.sendall(response.encode())
        self.app_class = handler_class
        self.path_params = params
        return True

    def handle(self):
        if not self.handle_handshake():
            self.request.close()
            return

        conn = WebSocketConnection(
            self.request,
            max_message_size=self.server.max_message_size,
            read_timeout=self.server.read_timeout
        )
        app = self.app_class()
        app.connection = conn
        app.path_params = self.path_params

        try:
            app.on_open()
        except Exception as e:
            conn.close(1011, f"Internal error: {str(e)}")
            return

        try:
            while conn.connected:
                message = conn.receive_message()
                if message is None:
                    break
                try:
                    if isinstance(message, str):
                        app.on_message(message)
                    else:
                        app.on_binary(message)
                except Exception as e:
                    conn.close(1011, f"Handler error: {str(e)}")
                    break
        except Exception as e:
            conn.close(1011, f"Unexpected error: {str(e)}")
        finally:
            try:
                app.on_close()
            except Exception:
                pass
            conn.close()

class WebSocketServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, router,
                 max_header_size=DEFAULT_MAX_HEADER_SIZE,
                 max_message_size=DEFAULT_MAX_MESSAGE_SIZE,
                 read_timeout=DEFAULT_READ_TIMEOUT):
        super().__init__(server_address, WebSocketHandler)
        self.router = router
        self.max_header_size = max_header_size
        self.max_message_size = max_message_size
        self.read_timeout = read_timeout