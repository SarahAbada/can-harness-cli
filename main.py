import argparse

from serial.tools import list_ports
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Footer, Header, Input, RichLog

from protocol import HarnessCommand, parse_raw_command
from serial_manager import SerialManager


class SerialDataReceived(Message):
    """Event posted from the SerialManager thread to Textual when data arrives."""

    def __init__(self, line: str) -> None:
        self.line = line
        super().__init__()


class CanHarnessApp(App):
    """CLI telemetry and control interface for STMicroelectronics H7 Harness."""

    CSS = """
    #console_log {
        height: 1fr;
        border: solid green;
        background: $surface;
    }
    #input_container {
        height: auto;
        margin-top: 1;
    }
    #cmd_input {
        width: 4fr;
    }
    #dest_button {
        width: 1fr;
        margin-left: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "clear_log", "Clear Log"),
    ]

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 115200,
        available_ports: list[str] | None = None,
    ):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.available_ports = available_ports or []
        self.destination_mode = "head"

        self.serial_mgr = SerialManager(
            port=self.port,
            baudrate=self.baudrate,
            callback=self._handle_serial_callback,
        )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="console_log", highlight=True, markup=True, wrap=True)

        with Horizontal(id="input_container"):
            yield Input(
                placeholder="Enter command... (e.g. ping, send:can:123456, sniff:can:on)",
                id="cmd_input",
            )
            yield Button("Mode: HEAD", id="dest_button", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        """Runs when the application starts."""
        log = self.query_one("#console_log", RichLog)
        log.write("[bold cyan]===CAN Harness Control Interface ===[/bold cyan]")
        if self.available_ports:
            log.write("[bold cyan]Available serial ports:[/bold cyan]")
            for port in self.available_ports:
                log.write(f"[cyan] - {port}[/cyan]")
        log.write(f"Connecting to port [yellow]{self.port}[/yellow] at {self.baudrate} baud...")
        if self.serial_mgr.connect():
            log.write("[bold green]Connected successfully![/bold green]")
        else:
            log.write("[bold red]Failed to open serial port. (Running in disconnected mode)[/bold red]")

    def _handle_serial_callback(self, line: str) -> None:
        """Callback thread bridge: posts serial thread messages into Textual loop."""
        self.call_from_thread(self.post_message, SerialDataReceived(line))

    def on_serial_data_received(self, event: SerialDataReceived) -> None:
        """Handles inbound serial lines received from the thread message."""
        log = self.query_one("#console_log", RichLog)
        line = event.line

        log.write(f"[dim]RAW <--[/dim] {line}")

        if ":OK:" in line or ":INVALID:" in line:
            log.write(f"[bold green]ACK <--[/bold green] {line}")
        elif line.startswith("sniff:RESPONSE:") or line.upper().startswith("SNIFF:"):
            log.write(f"[bold magenta]DATA <--[/bold magenta] {line}")
        else:
            log.write(f"[blue]RX <--[/blue] {line}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Triggered when the user presses enter on the input field."""
        raw_text = event.value.strip()
        if not raw_text:
            return

        input_widget = self.query_one("#cmd_input", Input)
        log = self.query_one("#console_log", RichLog)
        input_widget.value = ""

        try:
            cmd = parse_raw_command(raw_text)
            cmd.validate(destination=self.destination_mode)
            if self.serial_mgr.send(cmd):
                log.write(f"[bold yellow]TX   -->[/bold yellow] {cmd.to_string().strip()}")
            else:
                log.write(f"[bold red]TX FAIL:[/bold red] Could not write to {self.port}")
        except ValueError as e:
            log.write(f"[bold red]INVALID COMMAND:[/bold red] {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Toggles destination mode between head and hub."""
        btn = self.query_one("#dest_button", Button)
        if self.destination_mode == "head":
            self.destination_mode = "hub"
            btn.label = "Mode: HUB"
            btn.variant = "warning"
        else:
            self.destination_mode = "head"
            btn.label = "Mode: HEAD"
            btn.variant = "primary"

    def action_clear_log(self) -> None:
        """Clears console log window."""
        self.query_one("#console_log", RichLog).clear()

    def on_unmount(self) -> None:
        """Runs when quitting the application."""
        self.serial_mgr.disconnect()


def _available_ports() -> list[str]:
    return [port.device for port in list_ports.comports()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CAN harness CLI")
    parser.add_argument("--port", help="Serial port to connect to")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports and exit")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    ports = _available_ports()

    if args.list_ports:
        print("Available serial ports:")
        if ports:
            for port in ports:
                print(f" - {port}")
        else:
            print(" - none found")
        raise SystemExit(0)

    selected_port = args.port or (ports[0] if ports else "/dev/ttyACM0")
    app = CanHarnessApp(port=selected_port, baudrate=args.baudrate, available_ports=ports)
    app.run()