#!/usr/bin/env python3
"""
Analyze the frame structure based on captured data.
"""

# Test data from your output
test_frames = [
    {
        'name': 'Device Info',
        'bytes': [0x55, 0xAA, 0x00, 0x07, 0x64, 0x02, 0x4A, 0x01, 0xB7],
        'expected_instruction': 0x00,
    },
    {
        'name': 'Real-time Data',
        'bytes': [0x55, 0xAA, 0x01, 0x0B, 0xE1, 0x00, 0x60, 0x6D, 0x60, 0x6D, 0x60, 0x6D, 0x53],
        'expected_instruction': 0x01,
    }
]

print("=" * 70)
print("FRAME STRUCTURE ANALYSIS")
print("=" * 70)

for frame in test_frames:
    data = frame['bytes']
    print(f"\n{frame['name']}:")
    print(f"Raw bytes: {' '.join(f'{b:02X}' for b in data)}")
    print(f"Total length: {len(data)} bytes")
    
    # Parse components
    header = data[0:2]
    instruction = data[2]
    frame_length = data[3]
    checksum = data[-1]
    
    print(f"\nBreakdown:")
    print(f"  Header:       {header[0]:02X} {header[1]:02X} (2 bytes)")
    print(f"  Instruction:  {instruction:02X} (1 byte)")
    print(f"  Frame length: {frame_length:02X} = {frame_length} bytes")
    print(f"  Checksum:     {checksum:02X} (1 byte)")
    
    # Test different interpretations of frame_length
    print(f"\nFrame length interpretation:")
    print(f"  If frame_length includes header (2 bytes): mismatch! ({frame_length} != {len(data)})")
    print(f"  If frame_length excludes header: {2 + frame_length} = {len(data)} bytes ✓")
    
    # Calculate what frame_length covers
    payload_start = 4  # After header, instruction, and length byte
    payload_end = len(data) - 1  # Before checksum
    payload = data[payload_start:payload_end]
    
    print(f"\nPayload (bytes 4 to {payload_end-1}):")
    print(f"  Bytes: {' '.join(f'{b:02X}' for b in payload)}")
    print(f"  Length: {len(payload)} bytes")
    
    # frame_length should equal: instruction(1) + length_byte(1) + payload(n) + checksum(1)
    expected_frame_length = 1 + 1 + len(payload) + 1
    print(f"\nVerify frame_length calculation:")
    print(f"  instruction(1) + length_byte(1) + payload({len(payload)}) + checksum(1) = {expected_frame_length}")
    print(f"  Matches frame_length field ({frame_length})? {expected_frame_length == frame_length}")
    
    # Checksum verification
    checksum_calc = sum(data[:-1]) & 0xFF
    print(f"\nChecksum verification:")
    print(f"  Calculated: {checksum_calc:02X}")
    print(f"  Received:   {checksum:02X}")
    print(f"  Match: {'✓' if checksum_calc == checksum else '✗'}")
    
    # Parse specific data
    if instruction == 0x00:  # Device info
        if len(payload) >= 4:
            model = payload[0] | (payload[1] << 8)
            version_raw = payload[2] | (payload[3] << 8)
            version = version_raw / 100.0
            print(f"\nDevice info:")
            print(f"  Model: TA{model}")
            print(f"  Version: V{version:.2f}")
            
    elif instruction == 0x01:  # Temperature data
        print(f"\nTemperature data:")
        for i in range(4):
            idx = i * 2
            if idx + 1 < len(payload):
                temp_raw = payload[idx] | (payload[idx + 1] << 8)
                temp_c = temp_raw / 10.0
                
                # Check for error codes
                if temp_raw == 0x6D60:
                    status = "(ERROR: 0x6D60 - possibly disconnected/invalid)"
                elif temp_raw > 1000:  # > 100°C seems unlikely
                    status = "(WARNING: Unusually high)"
                else:
                    status = ""
                    
                print(f"  CH{i+1}: {payload[idx]:02X} {payload[idx+1]:02X} = {temp_raw} = {temp_c:.1f}°C {status}")

print("\n" + "=" * 70)
print("\nCONCLUSION:")
print("  - Frame header: 0x55AA (2 bytes)")
print("  - frame_length field: Excludes the 2-byte header")
print("  - Total frame size: 2 + frame_length")
print("  - Checksum: sum(all_bytes_except_last) & 0xFF")
print("  - 0x6D60 appears to be an error/invalid sensor code")
print("=" * 70)
