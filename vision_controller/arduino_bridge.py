import serial
import time

# --- 1. Configuration ---
# CHANGE THIS to match your Arduino's port (e.g., 'COM3' for Windows or '/dev/tty.usbmodem...' for Mac)
ARDUINO_PORT = 'COM7' 
BAUD_RATE = 9600

# --- 2. Connect to Arduino ---
try:
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    # Open the serial port
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    
    # Crucial: The Arduino resets every time a Python script connects to it. 
    # We must wait 2 seconds for it to wake up before sending commands!
    time.sleep(2) 
    print("Connection established!\n")
except Exception as e:
    print(f"Critical Error: Could not connect to {ARDUINO_PORT}. Details: {e}")
    exit()

# Dictionary to map numbers to the exact array in your Arduino code
screw_dict = {
    '0': 'Rusted',
    '1': 'Robertson',
    '2': 'Phillips',
    '3': 'Slot',
    '4': 'Hex'
}

print("--- Conveyor Belt Control Bridge ---")
print("Enter a number to simulate detecting a screw:")
for key, value in screw_dict.items():
    print(f"  {key} : {value}")
print("Type 'q' to quit.\n")

# --- 3. The Communication Loop ---
while True:
    user_input = input("Enter screw type (0-4): ").strip()

    if user_input.lower() == 'q':
        print("Closing bridge...")
        break

    if user_input in screw_dict:
        print(f"--> Sending '{screw_dict[user_input]}' command to Arduino...")
        
        # We must encode the string into bytes before sending it over the USB cable
        ser.write(user_input.encode('utf-8'))
        
        # Wait a moment to let the Arduino process and reply
        time.sleep(0.5)
        
        # Read any text the Arduino sends back to us (for debugging)
        while ser.in_waiting > 0:
            arduino_reply = ser.readline().decode('utf-8').strip()
            print(f"    Arduino Reply: {arduino_reply}")
    else:
        print("Invalid input. Please enter 0, 1, 2, 3, or 4.")

ser.close()