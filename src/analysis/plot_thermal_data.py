#!/usr/bin/env python3
"""
Plot all four channels of thermal logger data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path


def plot_thermal_data(csv_file, output_file=None):
    """
    Plot all four channels of thermal data.
    
    Args:
        csv_file: Path to CSV file
        output_file: Optional output image file (if None, displays interactively)
    """
    # Read CSV file
    df = pd.read_csv(csv_file)
    
    # Check if it's real-time data (has timestamp) or recorded data (has sample_num)
    if 'timestamp' in df.columns:
        x_column = 'timestamp'
        x_label = 'Time'
        # Convert timestamp to datetime for better plotting
        df[x_column] = pd.to_datetime(df[x_column])
        # Use sample index for cleaner x-axis
        x_data = range(len(df))
        x_label = 'Sample Number'
    else:
        x_column = 'sample_num'
        x_data = df[x_column]
        x_label = 'Sample Number'
    
    # Replace 'ERROR' with NaN for plotting
    channels = ['ch1_celsius', 'ch2_celsius', 'ch3_celsius', 'ch4_celsius']
    channel_names = ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4']
    colors = ['#0060ad', '#dd5522', '#44aa44', '#8844cc']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot each channel if it has valid data
    plotted_channels = []
    for i, (channel, name, color) in enumerate(zip(channels, channel_names, colors)):
        # Convert ERROR to NaN
        df[channel] = pd.to_numeric(df[channel], errors='coerce')
        
        # Check if channel has any valid data
        if df[channel].notna().any():
            ax.plot(x_data, df[channel], label=name, color=color, linewidth=1.5, marker='o', markersize=2)
            plotted_channels.append(name)
    
    # Only configure plot if we have data to show
    if plotted_channels:
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel('Temperature (°C)', fontsize=12)
        ax.set_title('Thermal Logger - All Channels', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10)
        
        # Format the layout
        plt.tight_layout()
        
        # Save or show
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"Plot saved to {output_file}")
            print(f"Plotted channels: {', '.join(plotted_channels)}")
        else:
            print(f"Plotted channels: {', '.join(plotted_channels)}")
            plt.show()
    else:
        print("No valid data found in any channel")


def main():
    parser = argparse.ArgumentParser(
        description='Plot thermal logger data for all channels'
    )
    parser.add_argument(
        'csv_file',
        help='Input CSV file with thermal data'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output image file (png, pdf, svg, etc.). If not specified, displays interactively.'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"Error: File not found: {args.csv_file}")
        return 1
    
    try:
        plot_thermal_data(args.csv_file, args.output)
        return 0
    except Exception as e:
        print(f"Error plotting data: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
