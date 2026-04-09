import serial
import serial.tools.list_ports
import time

class ArduinoBridge:
    def __init__(self, port=None, baud_rate=9600):
        self.baud_rate = baud_rate
        self.ser = None
        
        # Added S and P to allowed commands
        self.cmd_dict = {
            '0': 'Rusted',
            '1': 'Robertson',
            '2': 'Phillips',
            '3': 'Slot',
            '4': 'Hex',
            'S': 'Start Belt',
            'P': 'Pause Belt'
        }

        self.port = port if port else self.find_arduino_port()

        if not self.port:
            print("\n[!] Hardware Warning: Could not find an Arduino UNO connected to this PC.")
            print("[!] Continuing in 'AI-Only' simulation mode...\n")
            return

        try:
            print(f"Connecting to Arduino on {self.port}...")
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            print("Waiting 2 seconds for Arduino to wake up...")
            time.sleep(2) 
            print("Hardware Connection Established!\n")
        except Exception as e:
            print(f"\n[!] Hardware Warning: Could not connect to {self.port}.")
            print(f"[!] Details: {e}")
            print("[!] Continuing in 'AI-Only' simulation mode...\n")
            self.ser = None

    def find_arduino_port(self):
        print("Scanning USB ports for Arduino UNO...")
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "Arduino" in port.description or "CH340" in port.description or "UNO" in port.description:
                print(f"--> Found Arduino! Device: {port.device} | Desc: {port.description}")
                return port.device
        return None

    def send_command(self, command):
        if self.ser is None:
            return False

        cmd_str = str(command)
        if cmd_str in self.cmd_dict:
            self.ser.write(cmd_str.encode('utf-8'))
            time.sleep(0.1) 
            while self.ser.in_waiting > 0:
                reply = self.ser.readline().decode('utf-8').strip()
                if reply:
                    print(f"    [Arduino]: {reply}")
            return True
        else:
            print(f"[!] Invalid command sent to ArduinoBridge: {cmd_str}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Hardware disconnected safely.")