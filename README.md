# Thermal Logger Data Reader

Python script to read temperature data from TA612 thermal logger device and save to CSV files.

## Installation

Install required dependencies:

```bash
pip install -r src/requirements.txt
```

## Usage

### Real-time Data Logging

Log real-time temperature data continuously:

```bash
python src/thermal_logger.py /dev/ttyUSB0 -o data.csv
```

Log for a specific duration (60 seconds):

```bash
python src/thermal_logger.py /dev/ttyUSB0 -o data.csv -d 60
```

Log with custom sampling interval (0.5 seconds):

```bash
python src/thermal_logger.py /dev/ttyUSB0 -o data.csv -i 0.5
```

### Download Recorded Data

Download data stored in device memory:

```bash
python src/thermal_logger.py /dev/ttyUSB0 -m recorded -o recorded_data.csv
```

## Command-line Options

- `port`: Serial port device (e.g., `/dev/ttyUSB0` on Linux or `COM3` on Windows)
- `-o, --output`: Output CSV filename (default: auto-generated with timestamp)
- `-p, --path`: Output directory path (default: current directory)
- `-m, --mode`: Data mode - `realtime` or `recorded` (default: `realtime`)
- `-d, --duration`: Duration in seconds for realtime logging (default: continuous until Ctrl+C)
- `-i, --interval`: Sampling interval in seconds for realtime mode (default: 1.0)

## Output Format

CSV files contain temperature readings in degrees Celsius:

**Real-time mode:**
- `timestamp`: ISO format timestamp
- `ch1_celsius`, `ch2_celsius`, `ch3_celsius`, `ch4_celsius`: Temperature readings

**Recorded mode:**
- `sample_num`: Sample number
- `ch1_celsius`, `ch2_celsius`, `ch3_celsius`, `ch4_celsius`: Temperature readings

## Device Communication

- **Interface**: USB Serial
- **Settings**: 9600 baud, 8N1 (8 data bits, no parity, 1 stop bit)
- **Device**: TA612 thermal logger

## Examples

### Basic Usage

```bash
# Auto-generated filename in current directory
python src/thermal_logger.py /dev/ttyUSB0

# Auto-generated filename in specific directory
python src/thermal_logger.py /dev/ttyUSB0 -p /home/maron2/data

# Custom filename in current directory
python src/thermal_logger.py /dev/ttyUSB0 -o mydata.csv

# Custom filename in specific directory
python src/thermal_logger.py /dev/ttyUSB0 -o mydata.csv -p /home/maron2/data

# Recorded data with auto-generated name
python src/thermal_logger.py /dev/ttyUSB0 -m recorded -p ./recordings
```

### Finding Your Serial Port

Find your serial port:

**Linux:**
```bash
ls /dev/ttyUSB*
```

**macOS:**
```bash
ls /dev/tty.usb*
```

**Windows:**
Check Device Manager for COM port number.
