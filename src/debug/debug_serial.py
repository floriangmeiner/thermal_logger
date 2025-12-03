#!/usr/bin/env python3
"""
Debug script to capture and analyze raw serial data from thermal logger.
"""

import serial
import time
import sys


def hex_dump(data, label=""):
    """Print data in hex format."""
    if label:
        print(f"\n{label}:")
    hex_str = " ".join(f"{b:02X}" for b in data)
    print(f"  {hex_str}")
    print(f"  Length: {len(data)} bytes")
    
    
def analyze_checksum(data):
    """Try multiple checksum calculation methods."""
    print("\nChecksum analysis (trying different methods):")
    
    if len(data) < 2:
        print("  Insufficient data")
        return
        
    received_checksum = data[-1]
    print(f"  Received checksum (last byte): {received_checksum:02X}")
    
    # Method 1: Sum of all bytes except last, keep last 8 bits
    calc1 = sum(data[:-1]) & 0xFF
    match1 = "✓" if calc1 == received_checksum else "✗"
    print(f"  Method 1 (sum all except last): {calc1:02X} {match1}")
    
    # Method 2: Sum of all bytes including last, keep last 8 bits
    calc2 = sum(data) & 0xFF
    match2 = "✓" if calc2 == received_checksum else "✗"
    print(f"  Method 2 (sum all including last): {calc2:02X} {match2}")
    
    # Method 3: XOR of all bytes except last
    calc3 = 0
    for b in data[:-1]:
        calc3 ^= b
    match3 = "✓" if calc3 == received_checksum else "✗"
    print(f"  Method 3 (XOR all except last): {calc3:02X} {match3}")
    
    # Method 4: Sum starting from instruction byte (skip header)
    if len(data) >= 3:
        calc4 = sum(data[2:-1]) & 0xFF
        match4 = "✓" if calc4 == received_checksum else "✗"
        print(f"  Method 4 (sum from byte 2 onwards, except last): {calc4:02X} {match4}")
    
    # Method 5: Sum starting after frame length
    if len(data) >= 5:
        calc5 = sum(data[4:-1]) & 0xFF
        match5 = "✓" if calc5 == received_checksum else "✗"
        print(f"  Method 5 (sum from byte 4 onwards, except last): {calc5:02X} {match5}")
        
    # Method 6: Inverse/complement
    calc6 = (~sum(data[:-1])) & 0xFF
    match6 = "✓" if calc6 == received_checksum else "✗"
    print(f"  Method 6 (NOT(sum all except last)): {calc6:02X} {match6}")
    
    return received_checksum


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_serial.py <port>")
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
        print("=" * 60)
        
        # Test 1: Get device info (stop command)
        print("\n[TEST 1] Sending STOP command (get device info)")
        cmd = bytearray([0xAA, 0x55, 0x00, 0x03, 0x02])
        hex_dump(cmd, "Sending")
        ser.write(cmd)
        time.sleep(0.2)
        
        response = ser.read(100)
        if response:
            hex_dump(response, "Received")
            
            # Try to parse it
            print("\nParsing:")
            if len(response) >= 2:
                print(f"  Byte 0-1: {response[0]:02X} {response[1]:02X}")
                if response[0] == 0x55 and response[1] == 0xAA:
                    print("    ✓ Frame header matches (0x55AA)")
                elif response[0] == 0xAA and response[1] == 0x55:
                    print("    ✗ Frame header is 0xAA55 (byte order issue?)")
                    
            if len(response) >= 3:
                print(f"  Byte 2 (instruction): {response[2]:02X}")
                
            if len(response) >= 4:
                print(f"  Byte 3 (frame length): {response[3]:02X} ({response[3]} bytes)")
                expected_total = response[3]
                print(f"    Expected total frame size: {expected_total} bytes")
                print(f"    Actual received: {len(response)} bytes")
                
            if len(response) >= 5:
                print(f"  Data bytes (4 to end-1): {' '.join(f'{b:02X}' for b in response[4:-1])}")
                print(f"  Checksum byte (last): {response[-1]:02X}")
                
            # Detailed checksum analysis
            analyze_checksum(response)
                
        else:
            print("No response received")
            
        # Test 2: Get real-time data
        print("\n" + "=" * 60)
        print("\n[TEST 2] Sending REAL-TIME command")
        cmd = bytearray([0xAA, 0x55, 0x01, 0x03, 0x03])
        hex_dump(cmd, "Sending")
        ser.write(cmd)
        time.sleep(0.2)
        
        response = ser.read(100)
        if response:
            hex_dump(response, "Received")
            
            print("\nParsing:")
            if len(response) >= 2:
                print(f"  Byte 0-1: {response[0]:02X} {response[1]:02X}")
                
            if len(response) >= 3:
                print(f"  Byte 2 (instruction): {response[2]:02X}")
                
            if len(response) >= 4:
                print(f"  Byte 3 (frame length): {response[3]:02X} ({response[3]} bytes)")
                expected_total = response[3]
                print(f"    Expected total frame size: {expected_total} bytes")
                print(f"    Actual received: {len(response)} bytes")
                
            # Try to parse temperature data
            if len(response) >= 12:
                print("\n  Temperature data (assuming 16-bit little-endian, divide by 10):")
                for i in range(4):
                    idx = 4 + (i * 2)
                    if idx + 1 < len(response) - 1:  # -1 for checksum
                        temp_raw = response[idx] | (response[idx + 1] << 8)
                        temp_c = temp_raw / 10.0
                        print(f"    Channel {i+1}: {response[idx]:02X} {response[idx+1]:02X} = {temp_raw} = {temp_c:.1f}°C")
                        
            # Detailed checksum analysis
            analyze_checksum(response)
            
        else:
            print("No response received")
            
        # Test 3: Multiple real-time readings
        print("\n" + "=" * 60)
        print("\n[TEST 3] Sending multiple REAL-TIME commands")
        for i in range(3):
            print(f"\n--- Reading {i+1} ---")
            cmd = bytearray([0xAA, 0x55, 0x01, 0x03, 0x03])
            ser.write(cmd)
            time.sleep(0.3)
            
            response = ser.read(100)
            if response:
                hex_dump(response, f"Response {i+1}")
                if len(response) >= 12:
                    print("  Temps:", end="")
                    for ch in range(4):
                        idx = 4 + (ch * 2)
                        if idx + 1 < len(response) - 1:
                            temp_raw = response[idx] | (response[idx + 1] << 8)
                            print(f" CH{ch+1}={temp_raw/10.0:.1f}°C", end="")
                    print()
                analyze_checksum(response)
        else:
            print("No response received")
            
        ser.close()
        
    except serial.SerialException as e:
        print(f"Error: {e}")
        return 1
        
    return 0


if __name__ == '__main__':
    exit(main())
