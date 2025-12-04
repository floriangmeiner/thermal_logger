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

### Basic Data Logging Usage

```bash
# Auto-generated filename in current directory
python src/thermal_logger.py /dev/ttyUSB0

# Auto-generated filename in specific directory
python src/thermal_logger.py /dev/ttyUSB0 -p ~/Documents/repos/internal/thermal_logger/logs

# Custom filename in current directory
python src/thermal_logger.py /dev/ttyUSB0 -o mydata.csv

# Custom filename in specific directory
python src/thermal_logger.py /dev/ttyUSB0 -o mydata.csv -p ~/Documents/repos/internal/thermal_logger/logs

# Recorded data with auto-generated name
python src/thermal_logger.py /dev/ttyUSB0 -m recorded -p ~/Documents/repos/internal/thermal_logger/logs
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


## Data Review & Analysis

### Plotting Data

Plot all channels from a CSV file:

```bash
# Display plot interactively
python src/plot_thermal_data.py logs/off_to_full_speed.csv

# Save to image file
python src/plot_thermal_data.py logs/off_to_full_speed.csv -o plot.png

# Other formats
python src/plot_thermal_data.py logs/off_to_full_speed.csv -o plot.pdf
python src/plot_thermal_data.py logs/off_to_full_speed.csv -o plot.svg
```

The plotting script automatically:
- Detects real-time vs recorded data format
- Only plots channels with valid data (skips channels with only ERROR values)
- Displays interactive plot or saves to file

### Analyzing Cooling Curves

Fit Newton's Law of Cooling to thermal data to determine thermal time constant:

```bash
# Basic usage with default column (ch1_celsius)
python src/analyze_cooling.py -i logs/off_to_full_speed.csv -o logs/

# Analyze a different channel
python src/analyze_cooling.py -i logs/thermal_data.csv -c ch2_celsius -o output/

# Save to current directory
python src/analyze_cooling.py -i logs/off_to_full_speed.csv -c ch1_celsius -o .
```

The analysis script:
- Automatically identifies peak temperature and cooling phase
- Fits exponential cooling model: T(t) = T_env + (T_0 - T_env) * exp(-t/τ)
- Calculates thermal time constant (τ) with uncertainty estimates
- Generates plots with fit results and residuals
- Output file: `cooling_fit_analysis_{input_filename}.png`
