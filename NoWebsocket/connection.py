import struct
import socket
import logging
import time
from collections import deque
from .exceptions import WebSocketError

logger = logging.getLogger(__name__)

class WebSocketConnection:
    """WebSocket连接管理类"""
    def __init__(self, sock, config, client_address):
        self.sock = sock
        self.client_address = client_address
        self.connected_time = time.time()
        self.connected = True
        self.config = config
        self._buffer = bytearray()
        self._fragments = deque()
        self._fragment_opcode = None
        self._current_length = 0
        self.close_code = 1000
        self.close_reason = ''

    def _receive_message(self):
        try:
            while self.connected:
                frame = self._receive_frame()
                if frame is None:
                    return None
                if frame['opcode'] in (0x1, 0x2):
                    return self._process_data_frame(frame)
                elif frame['opcode'] == 0x8:
                    self._handle_close_frame(frame)
                    return None
                elif frame['opcode'] == 0x9:
                    self._send_pong(frame['payload'])
                elif frame['opcode'] == 0xA:
                    pass
        except WebSocketError as e:
            self.close(e.code, e.reason)
        except (socket.timeout, ConnectionError) as e:
            logger.warning("Connection error: %s", e)
            self.close(1006, "Connection closed")
        return None

    def send_text(self, message):
        self._send(message.encode('utf-8'), opcode=0x1)

    def send_binary(self, data):
        self._send(data, opcode=0x2)

    def close(self, code=1000, reason=''):
        if not self.connected:
            return
        self.close_code = code
        self.close_reason = reason
        payload = struct.pack('!H', code) + reason.encode('utf-8')
        self._send(payload, opcode=0x8)
        self.connected = False
        self._cleanup()

    def _send(self, payload, opcode):
        frames = self._create_frames(payload, opcode)
        for frame in frames:
            try:
                self.sock.sendall(frame)
            except (BrokenPipeError, ConnectionResetError):
                self.connected = False
                raise

    def _create_frames(self, payload, opcode):
        max_size = self.config['max_message_size']
        frames = []
        for i in range(0, len(payload), max_size):
            chunk = payload[i:i+max_size]
            fin = (i + len(chunk)) >= len(payload)
            frame_opcode = opcode if i == 0 else 0x0
            frames.append(self._create_single_frame(frame_opcode, chunk, fin))
        return frames

    def _create_single_frame(self, opcode, payload, fin=True):
        header = bytearray()
        header.append((fin << 7) | opcode)
        payload_len = len(payload)
        if payload_len <= 125:
            header.append(payload_len)
        elif payload_len <= 65535:
            header.extend([126, *struct.pack('!H', payload_len)])
        else:
            header.extend([127, *struct.pack('!Q', payload_len)])
        return bytes(header + payload)

    def _receive_frame(self):
        header = self._read_bytes(2)
        if not header:
            return None

        byte1, byte2 = header
        fin = (byte1 >> 7) & 0x01
        opcode = byte1 & 0x0F
        mask = (byte2 >> 7) & 0x01
        payload_len = byte2 & 0x7F

        if payload_len == 126:
            payload_len = struct.unpack('!H', self._read_bytes(2))[0]
        elif payload_len == 127:
            payload_len = struct.unpack('!Q', self._read_bytes(8))[0]

        mask_key = self._read_bytes(4) if mask else b''
        payload = self._read_bytes(payload_len)
        if mask:
            payload = self._apply_mask(payload, mask_key)

        return {'fin': fin, 'opcode': opcode, 'payload': payload}

    def _read_bytes(self, size):
        while len(self._buffer) < size:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self._buffer.extend(chunk)
        data = self._buffer[:size]
        del self._buffer[:size]
        return bytes(data)

    @staticmethod
    def _apply_mask(data, mask_key):
        return bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))

    def _cleanup(self):
        self._buffer.clear()
        self._fragments.clear()
        try:
            self.sock.close()
        except OSError:
            pass

    def _handle_close_frame(self, frame):
        code = 1005
        reason = ''
        if len(frame['payload']) >= 2:
            code = struct.unpack('!H', frame['payload'][:2])[0]
            reason = frame['payload'][2:].decode('utf-8', 'ignore')
        self.close(code, reason)

    def _send_pong(self, payload):
        self._send(payload, opcode=0xA)

    def _process_data_frame(self, frame):
        if frame['opcode'] == 0x1:
            try:
                return frame['payload'].decode('utf-8')
            except UnicodeDecodeError:
                raise WebSocketError(1007, "Invalid UTF-8")
        return frame['payload']