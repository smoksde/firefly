import serial
import serial.tools.list_ports
import csv
import time
from datetime import datetime

def find_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    target_keywords = ["USB", "UART", "Silicon Labs", "CH340", "CP210", "Arduino", "ESP32"]
    for port in ports:
        if any(keyword.lower() in (port.description or "").lower() for keyword in target_keywords):
            return port.device
        if any(keyword.lower() in (port.manufacturer or "").lower() for keyword in target_keywords):
            return port.device
    if ports:
        return ports[0].device
    return None

def main():
    port = find_esp32_port()
    if not port:
        print("Error: No microcontroller detected. Is it plugged in?")
        return
    
    baud_rate = 115200 
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gimbal_test_{timestamp_str}.csv"
    
    print(f"Auto-detected device on port: {port}")
    print(f"Connecting at {baud_rate} baud...")
    
    try:
        ser = serial.Serial(port, baud_rate, timeout=2)
        ser.reset_input_buffer() 
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print(f"Saving data to: {filename}")
    print("Recording started. Press [Ctrl + C] to stop.")
    print("-" * 60)

    record_count = 0
    start_time = time.time()
    headers_written = False

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        try:
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Split line by commas
                data = line.split(',')
                
                # Check for the header line sent in setup()
                if "time_ms" in line and not headers_written:
                    writer.writerow(data)
                    headers_written = True
                    print(f"Headers configured: {data}")
                    continue
                
                # Record numerical data rows
                if len(data) == 7:
                    writer.writerow(data)
                    record_count += 1
                    
                    if record_count % 100 == 0:
                        elapsed = time.time() - start_time
                        print(f"Recorded {record_count} points | Time: {elapsed:.1f}s | Latest: {line}")
                        
        except KeyboardInterrupt:
            print("\n" + "-" * 60)
            print("Recording stopped by user.")
            
        finally:
            ser.close()
            elapsed_total = time.time() - start_time
            print(f"Success! Saved {record_count} rows to '{filename}' (Duration: {elapsed_total:.1f}s).")

if __name__ == "__main__":
    main()