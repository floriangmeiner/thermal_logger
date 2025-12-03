#!/usr/bin/env python3
"""
Debug recorded data transfer to see all frames.
"""

import serial
import time
import sys


def hex_dump(data, label=""):
    """Print data in hex format."""
    if label:
        print(f"{label}:")
    hex_str = " ".join(f"{b:02X}" for b in data)
    print(f"  {hex_str}")
    print(f"  Length: {len(data)} bytes")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_recorded.py <port>")
        sys.exit(1)
        
    port = sys.argv[1]
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )
        
        print(f"Connected to {port}")
        print("=" * 70)
        
        # Send recorded data command
        print("\nSending RECORDED DATA command (0x02)")
        cmd = bytearray([0xAA, 0x55, 0x02, 0x03, 0x04])
        hex_dump(cmd, "Sending")
        ser.write(cmd)
        
        print("\nWaiting for responses...")
        print("=" * 70)
        
        frame_num = 0
        sample_count = 0
        total_bytes = 0
        
        while True:
            # Try to read frame header
            header = ser.read(2)
            if len(header) < 2:
                print(f"\nNo more data (timeout after {frame_num} frames)")
                break
                
            if header[0] != 0x55 or header[1] != 0xAA:
                print(f"\nInvalid header: {header[0]:02X} {header[1]:02X}")
                break
                
            # Read instruction and frame length
            instruction = ser.read(1)
            if len(instruction) < 1:
                break
            instruction = instruction[0]
            
            frame_length = ser.read(1)
            if len(frame_length) < 1:
                break
            frame_length = frame_length[0]
            
            # Read remaining data
            remaining = frame_length - 2
            data = ser.read(remaining)
            
            if len(data) < remaining:
                print(f"\nIncomplete frame (expected {remaining}, got {len(data)})")
                break
            
            # Reconstruct full frame
            full_frame = bytearray([0x55, 0xAA, instruction, frame_length]) + data
            total_bytes += len(full_frame)
            
            print(f"\n--- Frame {frame_num + 1} ---")
            hex_dump(full_frame, "Full frame")
            
            # Check instruction
            if instruction != 0x02:
                print(f"  Unexpected instruction: {instruction:02X} (expected 0x02)")
                break
                
            # Parse payload (excluding checksum)
            payload = data[:-1]
            checksum = data[-1]
            
            print(f"  Instruction: {instruction:02X}")
            print(f"  Frame length: {frame_length} bytes")
            print(f"  Payload size: {len(payload)} bytes")
            print(f"  Checksum: {checksum:02X}")
            
            # Verify checksum
            checksum_calc = sum(full_frame[:-1]) & 0xFF
            if checksum_calc == checksum:
                print(f"  Checksum: ✓")
            else:
                print(f"  Checksum: ✗ (expected {checksum_calc:02X})")
            
            # Parse temperature samples
            samples_in_frame = len(payload) // 8
            print(f"  Samples in frame: {samples_in_frame}")
            
            for i in range(samples_in_frame):
                idx = i * 8
                if idx + 7 < len(payload):
                    temps = []
                    for ch in range(4):
                        ch_idx = idx + (ch * 2)
                        temp_raw = payload[ch_idx] | (payload[ch_idx + 1] << 8)
                        if temp_raw == 0x6D60:
                            temps.append("ERROR")
                        else:
                            temps.append(f"{temp_raw/10.0:.1f}°C")
                    
                    print(f"    Sample {sample_count}: CH1={temps[0]} CH2={temps[1]} CH3={temps[2]} CH4={temps[3]}")
                    sample_count += 1
            
            frame_num += 1
            
            # Check if this looks like the last frame
            if len(payload) < 60:
                print(f"\n  Note: Short frame ({len(payload)} bytes) - likely the last one")
            
            # Small delay between reads
            time.sleep(0.05)
            
        print("\n" + "=" * 70)
        print(f"\nSummary:")
        print(f"  Total frames: {frame_num}")
        print(f"  Total samples: {sample_count}")
        print(f"  Total bytes: {total_bytes}")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"Error: {e}")
        return 1
        
    return 0


if __name__ == '__main__':
    exit(main())
