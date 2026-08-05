import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from serial_manager import SerialManager


class FakeSerial:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.is_open = True

    @property
    def in_waiting(self):
        return len(self._chunks[0]) if self._chunks else 0

    def read(self, size):
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        return chunk


def test_read_loop_handles_cr_terminated_lines():
    events = []
    serial = FakeSerial([b"ping:OK:123\r"])

    manager = SerialManager("dummy", 115200, callback=events.append)
    manager._serial = serial
    manager._running = True

    def stop_after_first_event(line):
        events.append(line)
        manager._running = False

    manager.callback = stop_after_first_event
    manager._read_loop()

    assert events == ["ping:OK:123"]
