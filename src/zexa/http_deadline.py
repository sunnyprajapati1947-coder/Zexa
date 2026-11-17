"""Total-deadline reader for one inbound HTTP request."""

from __future__ import annotations

import socket
import time


class DeadlineSocketReader:
    """Read request bytes under one monotonic deadline, not a resettable idle timeout.

    The handler calls begin_request() before BaseHTTPRequestHandler parses the
    request line. Its header and optional body reads therefore share one
    deadline. end_request() restores the ordinary idle timeout before response
    handling or the next keep-alive request.
    """

    def __init__(
        self,
        connection: socket.socket,
        *,
        request_timeout: float = 10.0,
        idle_timeout: float = 5.0,
    ) -> None:
        if request_timeout <= 0 or idle_timeout <= 0:
            raise ValueError("Request and idle timeouts must be positive.")
        self.connection = connection
        self.request_timeout = float(request_timeout)
        self.idle_timeout = float(idle_timeout)
        self._deadline: float | None = None
        self._buffer = bytearray()
        self._closed = False
        self._timed_out = False

    @property
    def timed_out(self) -> bool:
        return self._timed_out

    def begin_request(self) -> None:
        self._deadline = time.monotonic() + self.request_timeout
        self._timed_out = False

    def end_request(self) -> None:
        self._deadline = None
        try:
            self.connection.settimeout(self.idle_timeout)
        except OSError:
            pass

    def _recv(self, size: int) -> bytes:
        if self._closed:
            return b""
        if self._deadline is None:
            timeout = self.idle_timeout
        else:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                self._timed_out = True
                raise socket.timeout("Total HTTP request read deadline exceeded.")
            timeout = min(self.idle_timeout, remaining)
        self.connection.settimeout(timeout)
        try:
            return self.connection.recv(size)
        except socket.timeout:
            self._timed_out = True
            raise

    def readline(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        while True:
            newline = self._buffer.find(b"\n")
            if newline >= 0 and (size < 0 or newline + 1 <= size):
                return self._take(newline + 1)
            if size >= 0 and len(self._buffer) >= size:
                return self._take(size)
            amount = 4096 if size < 0 else min(4096, size - len(self._buffer))
            chunk = self._recv(max(1, amount))
            if not chunk:
                return self._take(len(self._buffer))
            self._buffer.extend(chunk)

    def read(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        if size < 0:
            chunks = [self._take(len(self._buffer))]
            while True:
                chunk = self._recv(4096)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        output = bytearray(self._take(min(size, len(self._buffer))))
        while len(output) < size:
            chunk = self._recv(size - len(output))
            if not chunk:
                break
            output.extend(chunk)
        return bytes(output)

    def _take(self, size: int) -> bytes:
        result = bytes(self._buffer[:size])
        del self._buffer[:size]
        return result

    def close(self) -> None:
        self._closed = True
        self._buffer.clear()
