# websocket/connection.py
import struct
import socket
from collections import deque
from .exceptions import WebSocketError
from .constants import (
    DEFAULT_CLOSE_TIMEOUT,
    DEFAULT_MAX_MESSAGE_SIZE,
    DEFAULT_READ_TIMEOUT
)

class WebSocketConnection:
    def __init__(self, request, max_message_size=DEFAULT_MAX_MESSAGE_SIZE,
                 read_timeout=DEFAULT_READ_TIMEOUT):
        self.request = request
        self.connected = True
        self.max_message_size = max_message_size
        self.read_timeout = read_timeout
        self._buffer = bytearray()
        self._fragments = deque()
        self._fragment_opcode = None
        self._current_length = 0

    def _read_into_buffer(self, size):
        while len(self._buffer) < size:
            try:
                chunk = self.request.recv(4096)
                if not chunk:
                    return False
                self._buffer.extend(chunk)
            except (socket.timeout, BlockingIOError):
                break
        return len(self._buffer) >= size

    def _read_bytes(self, size):
        if not self._read_into_buffer(size):
            return None
        data = self._buffer[:size]
        del self._buffer[:size]
        return bytes(data)

    def send_text(self, message):
        if not self.connected:
            raise ConnectionError("Connection closed")
        if not isinstance(message, str):
            raise TypeError("Message must be string")
        encoded = message.encode('utf-8')
        self._send_chunked(encoded, 0x1)

    def send_binary(self, data):
        if not self.connected:
            raise ConnectionError("Connection closed")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("Data must be bytes")
        self._send_chunked(data, 0x2)

    def _send_chunked(self, data, opcode):
        chunk_size = self.max_message_size
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            fin = (i + len(chunk)) >= len(data)
            current_opcode = opcode if i == 0 else 0x0
            frame = self._create_frame(current_opcode, chunk, fin)
            self._send_frame(frame)

    @staticmethod
    def _create_frame(opcode, payload, fin=True):
        header = bytearray()
        header.append((fin << 7) | opcode)
        payload_len = len(payload)
        if payload_len <= 125:
            header.append(payload_len)
        elif payload_len <= 65535:
            header.append(126)
            header.extend(struct.pack('!H', payload_len))
        else:
            header.append(127)
            header.extend(struct.pack('!Q', payload_len))
        return bytes(header + payload)

    def close(self, code=1000, reason=''):
        if self.connected:
            payload = struct.pack('!H', code) + reason.encode('utf-8', 'ignore')
            self._send_frame(self._create_frame(0x8, payload))
            self.connected = False
            self._wait_close_ack()

    def _wait_close_ack(self):
        try:
            original_timeout = self.request.gettimeout()
            self.request.settimeout(DEFAULT_CLOSE_TIMEOUT)
            while True:
                header = self._read_bytes(2)
                if not header or (header[0] & 0x0F) == 0x8:
                    break
        except (socket.timeout, OSError):
            pass
        finally:
            self.request.close()

    def _send_frame(self, frame):
        try:
            self.request.sendall(frame)
        except (BrokenPipeError, ConnectionResetError):
            self.connected = False

    def receive_message(self):
        original_timeout = self.request.gettimeout()
        try:
            self.request.settimeout(self.read_timeout)
            while self.connected:
                header = self._read_bytes(2)
                if not header:
                    return None

                byte1, byte2 = header[0], header[1]
                fin = (byte1 >> 7) & 0x01
                opcode = byte1 & 0x0F
                mask = (byte2 >> 7) & 0x01
                payload_len = byte2 & 0x7F

                self._validate_frame(opcode, payload_len)

                if payload_len == 126:
                    len_bytes = self._read_bytes(2)
                    if not len_bytes or len(len_bytes) != 2:
                        raise WebSocketError(1002, "Invalid length")
                    payload_len = struct.unpack('!H', len_bytes)[0]
                elif payload_len == 127:
                    len_bytes = self._read_bytes(8)
                    if not len_bytes or len(len_bytes) != 8:
                        raise WebSocketError(1002, "Invalid length")
                    payload_len = struct.unpack('!Q', len_bytes)[0]

                if payload_len > self.max_message_size:
                    raise WebSocketError(1009, "Message too large")

                mask_key = self._read_bytes(4) if mask else b''
                payload = self._read_bytes(payload_len)
                if not payload:
                    return None
                if mask:
                    payload = self._apply_mask(payload, mask_key)

                if opcode >= 0x8:
                    self._handle_control_frame(opcode, payload)
                    if opcode == 0x8:
                        return None
                    continue

                self._process_data_frame(opcode, payload, fin)
                if fin:
                    return self._finalize_message()
        except WebSocketError as e:
            self.close(e.code, e.reason)
        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            self.close(1006, "Connection closed")
        finally:
            self.request.settimeout(original_timeout)
        return None

    def _validate_frame(self, opcode, payload_len):
        if (opcode & 0x70) != 0:
            raise WebSocketError(1002, "Unsupported RSV bits")
        if opcode in (0x8, 0x9, 0xA) and payload_len > 125:
            raise WebSocketError(1002, "Control frame too large")

    def _apply_mask(self, data, mask_key):
        masked = bytearray(data)
        mask = (mask_key * (len(data) // 4 + 1))[:len(data)]
        for i in range(len(masked)):
            masked[i] ^= mask[i]
        return bytes(masked)

    def _process_data_frame(self, opcode, payload, fin):
        if opcode in (0x1, 0x2):
            if self._fragments:
                raise WebSocketError(1002, "Unexpected new message")
            self._fragment_opcode = opcode
            self._current_length = len(payload)
            self._fragments.append(payload)
        elif opcode == 0x0:
            if not self._fragments:
                raise WebSocketError(1002, "Unexpected continuation")
            self._current_length += len(payload)
            if self._current_length > self.max_message_size:
                raise WebSocketError(1009, "Message too large")
            self._fragments.append(payload)
        else:
            raise WebSocketError(1002, "Unexpected opcode")

    def _finalize_message(self):
        full_payload = b''.join(self._fragments)
        self._fragments.clear()
        self._current_length = 0
        if self._fragment_opcode == 0x1:
            try:
                return full_payload.decode('utf-8')
            except UnicodeDecodeError:
                raise WebSocketError(1007, "Invalid UTF-8")
        return bytes(full_payload)

    def _handle_control_frame(self, opcode, payload):
        if opcode == 0x8:
            code = 1005
            reason = ''
            if len(payload) >= 2:
                code = struct.unpack('!H', payload[:2])[0]
                reason = payload[2:].decode('utf-8', 'ignore')
            self.close(code, reason)
        elif opcode == 0x9:
            self._send_frame(self._create_frame(0xA, payload))
        elif opcode == 0xA:
            pass