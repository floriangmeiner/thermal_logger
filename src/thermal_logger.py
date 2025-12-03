#!/usr/bin/env python3
"""
Thermal Logger Data Reader
Reads temperature data from TA612 thermal logger and writes to CSV file.
"""

import serial
import time
import csv
import argparse
from datetime import datetime
from pathlib import Path


class ThermalLogger:
    """Interface for TA612 thermal logger device."""
    
    # Frame headers
    FRAME_HEAD_PC = 0x55AA
    FRAME_HEAD_DEVICE = 0xAA55
    
    # Instructions
    CMD_STOP = 0x00
    CMD_REAL_TIME = 0x01
    CMD_RECORDED = 0x02
    CMD_TIME_SYNC = 0x03
    CMD_SET_FUNCTION = 0x04
    
    def __init__(self, port, baudrate=9600):
        """
        Initialize thermal logger connection.
        
        Args:
            port: Serial port device (e.g., '/dev/ttyUSB0' or 'COM3')
            baudrate: Communication speed (default: 9600)
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )
        time.sleep(0.1)  # Allow connection to stabilize
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Close the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            
    def _calculate_checksum(self, data):
        """Calculate 8-bit checksum (last 8 bits of sum)."""
        return sum(data) & 0xFF
        
    def _send_command(self, instruction, data=None):
        """
        Send a command frame to the device.
        
        Args:
            instruction: Command byte (0x00-0x04)
            data: Optional additional data bytes
        """
        frame = []
        
        # Frame header (16 bits, low byte first)
        frame.append(0xAA)
        frame.append(0x55)
        
        # Instruction
        frame.append(instruction)
        
        # Frame length
        if data:
            frame_length = 3 + len(data)
            frame.append(frame_length)
            frame.extend(data)
        else:
            frame.append(0x03)
            
        # Checksum
        checksum = self._calculate_checksum(frame)
        frame.append(checksum)
        
        self.ser.write(bytearray(frame))
        
    def _read_response(self):
        """Read and parse a response frame from the device."""
        # Read frame header
        header = self.ser.read(2)
        if len(header) < 2:
            return None
            
        if header[0] != 0x55 or header[1] != 0xAA:
            return None
            
        # Read instruction
        instruction = self.ser.read(1)
        if len(instruction) < 1:
            return None
        instruction = instruction[0]
        
        # Read frame length (excludes the 2-byte header)
        frame_length = self.ser.read(1)
        if len(frame_length) < 1:
            return None
        frame_length = frame_length[0]
        
        # Read remaining data (frame_length - 2: already read instruction and length byte)
        # frame_length = instruction(1) + length_byte(1) + payload(n) + checksum(1)
        # We already read instruction(1) and length_byte(1), so remaining = frame_length - 2
        remaining = frame_length - 2
        data = self.ser.read(remaining)
        
        if len(data) < remaining:
            return None
            
        # Last byte is checksum
        checksum = data[-1]
        payload = data[:-1]
        
        # Verify checksum - calculate on all bytes except the checksum itself
        all_bytes = [0x55, 0xAA, instruction, frame_length] + list(payload)
        calculated_checksum = self._calculate_checksum(all_bytes)
        
        if checksum != calculated_checksum:
            print(f"Warning: Checksum mismatch (expected {calculated_checksum:02X}, got {checksum:02X})")
            
        return {
            'instruction': instruction,
            'data': payload
        }
        
    def get_device_info(self):
        """
        Get device model and version information.
        
        Returns:
            dict: {'model': str, 'version': str}
        """
        self._send_command(self.CMD_STOP)
        response = self._read_response()
        
        if response and response['instruction'] == self.CMD_STOP:
            data = response['data']
            if len(data) >= 4:
                # Model: 16 bits, low byte first
                model = data[0] | (data[1] << 8)
                # Version: 16 bits, divide by 100
                version_raw = data[2] | (data[3] << 8)
                version = version_raw / 100.0
                
                return {
                    'model': f'TA{model}',
                    'version': f'V{version:.2f}'
                }
        return None
        
    def get_real_time_data(self):
        """
        Get real-time temperature data from all 4 channels.
        
        Returns:
            dict: {'timestamp': datetime, 'ch1': float, 'ch2': float, 'ch3': float, 'ch4': float}
                  Temperature values may be None if sensor is disconnected/invalid
        """
        self._send_command(self.CMD_REAL_TIME)
        response = self._read_response()
        
        if response and response['instruction'] == self.CMD_REAL_TIME:
            data = response['data']
            if len(data) >= 8:
                timestamp = datetime.now()
                temperatures = []
                
                # Parse 4 channels (16 bits each, low byte first, divide by 10)
                for i in range(4):
                    idx = i * 2
                    temp_raw = data[idx] | (data[idx + 1] << 8)
                    
                    # Check for error code (0x6D60 = disconnected/invalid sensor)
                    if temp_raw == 0x6D60:
                        temperatures.append(None)
                    else:
                        temp_celsius = temp_raw / 10.0
                        temperatures.append(temp_celsius)
                    
                return {
                    'timestamp': timestamp,
                    'ch1': temperatures[0],
                    'ch2': temperatures[1],
                    'ch3': temperatures[2],
                    'ch4': temperatures[3]
                }
        return None
        
    def get_recorded_data(self):
        """
        Get recorded temperature data from device memory.
        
        Yields:
            dict: {'ch1': float, 'ch2': float, 'ch3': float, 'ch4': float}
                  Temperature values may be None if sensor is disconnected/invalid
        """
        self._send_command(self.CMD_RECORDED)
        
        # Continue reading until no more data (timeout)
        while True:
            response = self._read_response()
            
            # Stop when no response or wrong instruction
            if not response or response['instruction'] != self.CMD_RECORDED:
                break
                
            data = response['data']
            
            # Parse channel data (16 bits each, low byte first)
            # Each sample is 8 bytes (4 channels * 2 bytes each)
            i = 0
            while i + 7 < len(data):
                temperatures = []
                for ch in range(4):
                    idx = i + (ch * 2)
                    temp_raw = data[idx] | (data[idx + 1] << 8)
                    
                    # Check for error code
                    if temp_raw == 0x6D60:
                        temperatures.append(None)
                    else:
                        temp_celsius = temp_raw / 10.0
                        temperatures.append(temp_celsius)
                        
                if len(temperatures) == 4:
                    yield {
                        'ch1': temperatures[0],
                        'ch2': temperatures[1],
                        'ch3': temperatures[2],
                        'ch4': temperatures[3]
                    }
                    
                i += 8


def log_real_time_data(port, output_file, output_dir, duration=None, interval=1.0):
    """
    Log real-time temperature data to CSV file.
    
    Args:
        port: Serial port device
        output_file: Output CSV file path (None for auto-generated name)
        output_dir: Output directory path
        duration: Duration in seconds (None for continuous)
        interval: Sampling interval in seconds
    """
    # Generate filename if not specified
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'thermal_data_{timestamp}.csv'
    
    # Combine with output directory
    output_path = Path(output_dir) / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with ThermalLogger(port) as logger:
        # Get device info
        info = logger.get_device_info()
        if info:
            print(f"Connected to {info['model']} {info['version']}")
        else:
            print("Connected to thermal logger")
            
        # Prepare CSV file
        fieldnames = ['timestamp', 'ch1_celsius', 'ch2_celsius', 'ch3_celsius', 'ch4_celsius']
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            print(f"Logging data to {output_path}")
            print("Press Ctrl+C to stop")
            
            start_time = time.time()
            sample_count = 0
            
            try:
                while True:
                    data = logger.get_real_time_data()
                    
                    if data:
                        row = {
                            'timestamp': data['timestamp'].isoformat(),
                            'ch1_celsius': data['ch1'] if data['ch1'] is not None else 'ERROR',
                            'ch2_celsius': data['ch2'] if data['ch2'] is not None else 'ERROR',
                            'ch3_celsius': data['ch3'] if data['ch3'] is not None else 'ERROR',
                            'ch4_celsius': data['ch4'] if data['ch4'] is not None else 'ERROR'
                        }
                        writer.writerow(row)
                        csvfile.flush()
                        
                        sample_count += 1
                        
                        # Format output
                        ch1_str = f"{data['ch1']:.1f}°C" if data['ch1'] is not None else "ERROR"
                        ch2_str = f"{data['ch2']:.1f}°C" if data['ch2'] is not None else "ERROR"
                        ch3_str = f"{data['ch3']:.1f}°C" if data['ch3'] is not None else "ERROR"
                        ch4_str = f"{data['ch4']:.1f}°C" if data['ch4'] is not None else "ERROR"
                        
                        print(f"Sample {sample_count}: CH1={ch1_str}  "
                              f"CH2={ch2_str}  "
                              f"CH3={ch3_str}  "
                              f"CH4={ch4_str}")
                    
                    # Check duration
                    if duration and (time.time() - start_time) >= duration:
                        break
                        
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                print(f"\nStopped. Logged {sample_count} samples.")


def download_recorded_data(port, output_file, output_dir):
    """
    Download recorded data from device memory to CSV file.
    
    Args:
        port: Serial port device
        output_file: Output CSV file path (None for auto-generated name)
        output_dir: Output directory path
    """
    # Generate filename if not specified
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'thermal_recorded_{timestamp}.csv'
    
    # Combine with output directory
    output_path = Path(output_dir) / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with ThermalLogger(port) as logger:
        # Get device info
        info = logger.get_device_info()
        if info:
            print(f"Connected to {info['model']} {info['version']}")
        else:
            print("Connected to thermal logger")
            
        # Prepare CSV file
        fieldnames = ['sample_num', 'ch1_celsius', 'ch2_celsius', 'ch3_celsius', 'ch4_celsius']
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            print(f"Downloading recorded data to {output_path}")
            
            sample_num = 0
            for data in logger.get_recorded_data():
                row = {
                    'sample_num': sample_num,
                    'ch1_celsius': data['ch1'] if data['ch1'] is not None else 'ERROR',
                    'ch2_celsius': data['ch2'] if data['ch2'] is not None else 'ERROR',
                    'ch3_celsius': data['ch3'] if data['ch3'] is not None else 'ERROR',
                    'ch4_celsius': data['ch4'] if data['ch4'] is not None else 'ERROR'
                }
                writer.writerow(row)
                sample_num += 1
                
                if sample_num % 100 == 0:
                    print(f"Downloaded {sample_num} samples...")
                    
            print(f"Download complete. Total samples: {sample_num}")


def main():
    parser = argparse.ArgumentParser(
        description='Thermal Logger Data Reader - Read temperature data from TA612 device'
    )
    parser.add_argument(
        'port',
        help='Serial port (e.g., /dev/ttyUSB0 or COM3)'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output CSV filename (default: auto-generated with timestamp)'
    )
    parser.add_argument(
        '-p', '--path',
        default='.',
        help='Output directory path (default: current directory)'
    )
    parser.add_argument(
        '-m', '--mode',
        choices=['realtime', 'recorded'],
        default='realtime',
        help='Data mode: realtime or recorded (default: realtime)'
    )
    parser.add_argument(
        '-d', '--duration',
        type=float,
        help='Duration in seconds for realtime mode (default: continuous)'
    )
    parser.add_argument(
        '-i', '--interval',
        type=float,
        default=1.0,
        help='Sampling interval in seconds for realtime mode (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'realtime':
            log_real_time_data(args.port, args.output, args.path, args.duration, args.interval)
        else:
            download_recorded_data(args.port, args.output, args.path)
            
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {args.port}")
        print(f"Details: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == '__main__':
    exit(main())
