import time
import os
import pty
import random
import select
from typing import Optional
from dataclasses import dataclass

DELIMITER = ":"
TERMINATOR = "\n"

@dataclass
class HarnessCommand:
    action: str
    target: Optional[str] = None
    parameter: Optional[str] = None

    @classmethod
    def from_raw(cls, raw_input: str) -> "HarnessCommand":
        cleaned = raw_input.strip()
        if not cleaned:
            raise ValueError("Empty command")
        parts = cleaned.split(DELIMITER, 2)
        action = parts[0].strip()
        target = parts[1].strip() if len(parts) > 1 else None
        parameter = parts[2].strip() if len(parts) > 2 else None
        return cls(action=action, target=target, parameter=parameter)

    def raw_formatted(self) -> str:
        parts = [self.action]
        if self.target:
            parts.append(self.target)
        if self.parameter:
            parts.append(self.parameter)
        return DELIMITER.join(parts)


class HarnessDeviceSimulator:
    def __init__(self, device_type: str = "head"):
        self.device_type = device_type.lower()
        self.sniff_active = False
        self.sniff_busses = []
        self.last_sniff_time = 0.0

    def get_timestamp(self) -> str:
        """Returns epoch timestamp in milliseconds."""
        return f"{int(time.time() * 1000)}"

    def handle_command(self, raw_str: str) -> str:
        """Parses incoming command and returns formatted response."""
        try:
            cmd = HarnessCommand.from_raw(raw_str)
            cmd_prefix = cmd.raw_formatted()
        except ValueError:
            return [ f"UNKNOWN:ERR:{self.get_timestamp()}{TERMINATOR}" ]

        # 1. Handle Sniff State
        if cmd.action == "sniff":
            if cmd.parameter == "on":
                self.sniff_active = True
                self.sniff_busses.append(cmd.target)
                return [ f"{cmd.action}:OK:{self.get_timestamp()}{TERMINATOR}" ]
            elif cmd.parameter == "off":
                self.sniff_active = len(self.sniff_busses) > 0
                self.sniff_busses.remove(cmd.target)
                return [ f"{cmd.action}:OK:{self.get_timestamp()}{TERMINATOR}" ]

        # 2. Handle Status Query
        elif cmd.action == "status":
            uptime = int(time.process_time())
            temp = random.randint(35, 52)
            # Example response: status:head:OK:<ts>:temp=42C,uptime=120s
            return [f"{cmd.action}:OK:{self.get_timestamp()}{TERMINATOR}", f"temp={temp}C,uptime={uptime}s{TERMINATOR}"]

        # 3. Handle Bus Query
        elif cmd.action == "bus":
            status = random.choice(["OK", "BUS_HEAVY", "NO_ACK"])
            err_count = random.randint(0, 5)
            return [ f"{cmd.action}:OK:{self.get_timestamp()}{TERMINATOR}", f"status={status},errs={err_count}{TERMINATOR}" ]

        # 4. Handle Ping / Send / Reset
        elif cmd.action in {"ping", "send", "reset"}:
            return [ f"{cmd.action}:OK:{self.get_timestamp()}{TERMINATOR}" ]

        # Fallback for unrecognized action
        return [ f"{cmd.action}:ERR:UNKNOWN_ACTION:{self.get_timestamp()}{TERMINATOR}" ]

    def generate_sniff_stream(self) -> str:
        """Generates mock telemetry payload at ~1Hz."""
        res = []
        for b in self.sniff_busses:
            can_id = hex(random.randint(0x100, 0x7FF))
            payload = "".join(f"{random.randint(0, 255):02X}" for _ in range(8))
            res.append(f"SNIFF:{b}:{can_id}:{payload}:{self.get_timestamp()}{TERMINATOR}")
        return res


def run_simulator():
    master, slave = pty.openpty()
    port_name = os.ttyname(slave)

    sim = HarnessDeviceSimulator(device_type="head")

    print(f"==================================================")
    print(f" Virtual Serial Port Active: {port_name}")
    print(f" Point your Python sender application to this port")
    print(f"==================================================")

    rx_buffer = ""

    try:
        while True:
            # Non-blocking check for incoming commands or timeouts (100ms slice)
            r, _, _ = select.select([master], [], [], 0.1)

            if r:
                data = os.read(master, 1024).decode("utf-8", errors="ignore")
                rx_buffer += data

                while TERMINATOR in rx_buffer:
                    line, rx_buffer = rx_buffer.split(TERMINATOR, 1)
                    if line.strip():
                        print(f"[RX ← App]: {line}")
                        responses = sim.handle_command(line)
                        for res in responses:
                            os.write(master, res.encode("utf-8"))
                            print(f"[TX → App]: {res.strip()}")

            # Stream Sniff data at ~1Hz (1.0 sec interval)
            current_time = time.time()
            if sim.sniff_active and (current_time - sim.last_sniff_time >= 1.0):
                sniff_pkt = sim.generate_sniff_stream()
                for s in sniff_pkt:
                    os.write(master, s.encode("utf-8"))
                    print(f"[STREAM → App]: {s.strip()}")
                sim.last_sniff_time = current_time

    except KeyboardInterrupt:
        print("\nStopping Simulator...")
    finally:
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    run_simulator()
sim.py