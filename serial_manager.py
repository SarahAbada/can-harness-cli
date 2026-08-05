import serial
import threading
import time
from typing import Callable, Optional
from protocol import HarnessCommand

class SerialManager:
    def __init__(self, port: str, baudrate: int, callback: Optional[Callable[[str], None]]=None ):
        self.port = port
        self.baudrate = baudrate # communication speed
        self.callback = callback # a function provided to receive decoded inbout strings

        self._serial: Optional[serial.Serial] = None # the pySerial instance 
        self._read_thread: Optional[threading.Thread] = None # background thread listening for responses
        self._running: bool = False # used to signal to the thread loop to stop when disconnecting
        
    def connect(self) -> bool:
        """Open serial port and launch background thread"""
        try:

            self._serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0,
                write_timeout=1.0,
            )
            self._running = True # set its state variable to indicate that it is running 
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True) # create the background thread used to continuously monitor the connection, and daemon=True keeps it running in the background
            self._read_thread.start() # start the thread
            return True # indicates that everything was successful 
        except serial.SerialException as e:
            print(f"failed to connect to {self.port}: {e}") # print log to show that it failed to connect and inform user of the exact error
            self._running = False # set the state variable to accurately reflect that the thread is not running, because it could not even be created
            self._serial = None # there is no serial connection
            return False # indicates failure to establish serial connection

    def _read_loop(self) -> None:
        """Continuously read lines from serial and forward them to the UI callback."""
        buffer = b""
        while self._running and self._serial and self._serial.is_open:
            try:
                waiting = self._serial.in_waiting
                if not waiting:
                    time.sleep(0.01)
                    continue

                chunk = self._serial.read(waiting)
                if not chunk:
                    continue

                buffer += chunk

                while True:
                    if b"\n" in buffer:
                        raw_line, buffer = buffer.split(b"\n", 1)
                    elif b"\r" in buffer:
                        raw_line, buffer = buffer.split(b"\r", 1)
                    else:
                        break

                    line = raw_line.rstrip(b"\r").decode("utf-8", errors="ignore").strip()
                    if line and self.callback:
                        self.callback(line)
            except (serial.SerialException, OSError) as e:
                print(f"serial read failed: {e}")
                self._running = False
                break

    def send(self, command: HarnessCommand) -> bool:
        """serializes and sends a command over the port"""
        if not self._serial or not self._serial.is_open:
            print("cannot send because serial connection is not established or is not open")
            return False
        try:
            raw_str = command.to_string().rstrip("\r\n") + "\n" # turn it into a string
            self._serial.write(raw_str.encode("utf-8")) # transmits the data through serial connection using the .write function of pySerial
            self._serial.flush()
            return True
        except serial.SerialException as e:
            print (f"Failed to send data: {e}") # show the error to the user
            return False

    def disconnect(self) -> None:
        """safely stops the thread loop and closes the serial connection"""
        self._running = False # set the state variable to reflect the fact that it is no longer running
        # wait for thread to finish current loop
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout = 2.0) # block the execution of _read_thread until it finishes executing, for a maximum of 2 seconds, if it doesn't finish executing then the main program resumes anyways
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None


