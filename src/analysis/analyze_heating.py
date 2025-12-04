#!/usr/bin/env python3
"""
Fit exponential heating model to thermal data to determine thermal time constant during heating.
T(t) = T_final - (T_final - T_0) * exp(-t/tau)
"""

import csv
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import os

def exponential_heating(t, T_final, T_0, tau):
    """
    Exponential heating model
    
    Parameters:
    t: time (seconds)
    T_final: final/steady-state temperature
    T_0: initial temperature at t=0
    tau: thermal time constant (seconds)
    """
    return T_final - (T_final - T_0) * np.exp(-t / tau)

def parse_timestamp(ts_str):
    """Parse ISO format timestamp to datetime"""
    return datetime.fromisoformat(ts_str)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Fit exponential heating model to thermal data to determine thermal time constant.'
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input CSV file path'
    )
    parser.add_argument(
        '-c', '--column',
        default='ch1_celsius',
        help='CSV column name for temperature data (default: ch1_celsius)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='.',
        help='Output directory for the analysis plot (default: current directory)'
    )
    
    args = parser.parse_args()
    
    csv_file = args.input
    temp_column = args.column
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    timestamps = []
    temps = []
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if temp_column not in row:
                print(f"Error: Column '{temp_column}' not found in CSV file.")
                print(f"Available columns: {', '.join(row.keys())}")
                return
            if row[temp_column] != 'ERROR':
                timestamps.append(parse_timestamp(row['timestamp']))
                temps.append(float(row[temp_column]))
    
    # Convert to numpy arrays
    temps = np.array(temps)
    
    # Calculate time in seconds from start
    start_time = timestamps[0]
    time_seconds = np.array([(t - start_time).total_seconds() for t in timestamps])
    
    # Find the peak temperature (maximum)
    peak_idx = np.argmax(temps)
    peak_temp = temps[peak_idx]
    peak_time = time_seconds[peak_idx]
    
    print(f"Peak temperature: {peak_temp:.2f}°C at t={peak_time:.1f}s")
    
    # Extract data from start to peak
    t_to_peak = time_seconds[:peak_idx+1]
    T_to_peak = temps[:peak_idx+1]
    
    # Detect start of heating by finding where temperature rate of change increases significantly
    # Calculate moving average of temperature derivative to smooth out noise
    window_size = max(10, len(T_to_peak) // 50)  # Adaptive window size
    dT_dt = np.gradient(T_to_peak, t_to_peak)
    
    # Use a moving average to smooth the derivative
    dT_dt_smooth = np.convolve(dT_dt, np.ones(window_size)/window_size, mode='valid')
    
    # Find where the rate of change exceeds a threshold
    initial_samples = max(20, len(dT_dt_smooth) // 10)
    baseline_rate = np.median(np.abs(dT_dt_smooth[:initial_samples]))
    baseline_std = np.std(dT_dt_smooth[:initial_samples])
    
    # More aggressive threshold: mean + 5*std of absolute values to catch significant increases
    threshold = np.mean(np.abs(dT_dt_smooth[:initial_samples])) + 5 * baseline_std
    
    # Additionally, look for sustained increase: at least 3 consecutive points above threshold
    heating_start_idx = 0
    consecutive_count = 0
    required_consecutive = 3
    
    for i in range(len(dT_dt_smooth)):
        if dT_dt_smooth[i] > threshold:
            consecutive_count += 1
            if consecutive_count >= required_consecutive:
                # Found sustained heating - go back to first point above threshold
                heating_start_idx = i - required_consecutive + 1 + window_size // 2
                break
        else:
            consecutive_count = 0
    
    # Make sure we don't go past the data or start at 0 if detection failed
    heating_start_idx = max(0, min(heating_start_idx, len(T_to_peak) - 1))
    
    # Additional check: make sure we've actually captured significant temperature rise
    # The heating phase should show at least 50% of the total temperature change
    total_temp_change = T_to_peak[-1] - T_to_peak[0]
    detected_temp_change = T_to_peak[-1] - T_to_peak[heating_start_idx]
    
    if detected_temp_change < 0.5 * total_temp_change and heating_start_idx > 0:
        # Detection might have missed early heating, try alternative method
        # Find where temperature exceeds initial temp + 10% of total change
        temp_threshold = T_to_peak[0] + 0.1 * total_temp_change
        for i in range(len(T_to_peak)):
            if T_to_peak[i] > temp_threshold:
                heating_start_idx = max(0, i - 5)  # Start slightly before threshold crossing
                print(f"Using alternative detection method (temperature threshold)")
                break
    
    print(f"Detected heating start at t={t_to_peak[heating_start_idx]:.1f}s, T={T_to_peak[heating_start_idx]:.2f}°C")
    print(f"Skipped {heating_start_idx} initial steady-state data points")
    
    # Extract heating phase (from heating start to peak)
    t_heating = t_to_peak[heating_start_idx:]
    T_heating = T_to_peak[heating_start_idx:]
    
    # Reset time to 0 at the start of heating
    t_heating = t_heating - t_heating[0]
    
    print(f"\nHeating phase:")
    print(f"  Duration: {t_heating[-1]:.1f} seconds ({t_heating[-1]/60:.1f} minutes)")
    print(f"  Temperature range: {T_heating[0]:.2f}°C → {T_heating[-1]:.2f}°C")
    print(f"  Number of data points: {len(t_heating)}")
    
    # Initial parameter estimates
    T_0_guess = T_heating[0]      # Initial temperature
    T_final_guess = T_heating[-1]  # Final/peak temperature
    tau_guess = 300                # Initial guess: 5 minutes
    
    print(f"\nInitial parameter guesses:")
    print(f"  T_0: {T_0_guess:.2f}°C")
    print(f"  T_final: {T_final_guess:.2f}°C")
    print(f"  tau: {tau_guess:.1f}s")
    
    # Set bounds dynamically based on data
    T_0_lower = max(10, T_0_guess - 10)
    T_0_upper = T_0_guess + 10
    T_final_lower = T_final_guess - 10
    T_final_upper = max(T_final_guess + 10, T_final_guess * 1.2)  # Allow 20% above peak
    tau_lower = 10
    tau_upper = max(10000, t_heating[-1] * 2)  # Allow up to 2x the total heating duration
    
    bounds_lower = [T_final_lower, T_0_lower, tau_lower]
    bounds_upper = [T_final_upper, T_0_upper, tau_upper]
    
    print(f"\nFitting bounds:")
    print(f"  T_final: [{T_final_lower:.1f}, {T_final_upper:.1f}] °C")
    print(f"  T_0:     [{T_0_lower:.1f}, {T_0_upper:.1f}] °C")
    print(f"  tau:     [{tau_lower:.1f}, {tau_upper:.1f}] s")
    
    # Fit the model
    try:
        popt, pcov = curve_fit(
            exponential_heating,
            t_heating,
            T_heating,
            p0=[T_final_guess, T_0_guess, tau_guess],
            bounds=(bounds_lower, bounds_upper),
            maxfev=10000
        )
        
        T_final_fit, T_0_fit, tau_fit = popt
        perr = np.sqrt(np.diag(pcov))  # Standard errors
        
        print(f"\n{'='*60}")
        print(f"FITTED PARAMETERS:")
        print(f"{'='*60}")
        print(f"  T_0 (initial):          {T_0_fit:.3f} ± {perr[1]:.3f} °C")
        print(f"  T_final (steady-state): {T_final_fit:.3f} ± {perr[0]:.3f} °C")
        print(f"  τ (time constant):      {tau_fit:.1f} ± {perr[2]:.1f} seconds")
        print(f"                          {tau_fit/60:.2f} ± {perr[2]/60:.2f} minutes")
        print(f"{'='*60}")
        
        # Calculate R-squared
        T_fit = exponential_heating(t_heating, *popt)
        ss_res = np.sum((T_heating - T_fit)**2)
        ss_tot = np.sum((T_heating - np.mean(T_heating))**2)
        r_squared = 1 - (ss_res / ss_tot)
        
        print(f"\nGoodness of fit:")
        print(f"  R² = {r_squared:.6f}")
        print(f"  RMSE = {np.sqrt(ss_res/len(T_heating)):.4f}°C")
        
        # Calculate characteristic times
        print(f"\nCharacteristic heating times:")
        print(f"  Time to reach 63% of final temperature: τ = {tau_fit:.1f}s ({tau_fit/60:.2f} min)")
        print(f"  Time to reach 95% of final temperature: 3τ = {3*tau_fit:.1f}s ({3*tau_fit/60:.2f} min)")
        print(f"  Time to reach 99% of final temperature: 5τ = {5*tau_fit:.1f}s ({5*tau_fit/60:.2f} min)")
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Data and fit
        ax1.plot(t_heating/60, T_heating, 'b.', alpha=0.5, label='Measured data', markersize=3)
        
        # Generate smooth fit line
        t_smooth = np.linspace(0, t_heating[-1], 1000)
        T_smooth = exponential_heating(t_smooth, *popt)
        ax1.plot(t_smooth/60, T_smooth, 'r-', linewidth=2, 
                label=f'Fit: τ = {tau_fit:.1f}s ({tau_fit/60:.2f} min)')
        
        ax1.axhline(y=T_final_fit, color='g', linestyle='--', alpha=0.7, 
                   label=f'T_final = {T_final_fit:.2f}°C')
        ax1.axhline(y=T_0_fit, color='orange', linestyle='--', alpha=0.7,
                   label=f'T_0 = {T_0_fit:.2f}°C')
        
        # Mark tau on the plot
        T_at_tau = exponential_heating(tau_fit, *popt)
        ax1.plot(tau_fit/60, T_at_tau, 'ro', markersize=10, 
                label=f'At τ: {T_at_tau:.2f}°C')
        
        ax1.set_xlabel('Time (minutes)', fontsize=12)
        ax1.set_ylabel('Temperature (°C)', fontsize=12)
        ax1.set_title('Exponential Heating Model - Data Fit', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Residuals
        residuals = T_heating - T_fit
        ax2.plot(t_heating/60, residuals, 'b.', alpha=0.5, markersize=3)
        ax2.axhline(y=0, color='r', linestyle='-', linewidth=1)
        ax2.fill_between(t_heating/60, -perr[0], perr[0], alpha=0.2, color='red',
                        label=f'±{perr[0]:.3f}°C uncertainty')
        ax2.set_xlabel('Time (minutes)', fontsize=12)
        ax2.set_ylabel('Residuals (°C)', fontsize=12)
        ax2.set_title('Fit Residuals', fontsize=12, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot with prefixed filename
        input_basename = os.path.basename(csv_file)
        input_name, input_ext = os.path.splitext(input_basename)
        output_filename = f"heating_fit_analysis_{input_name}.png"
        output_file = os.path.join(output_dir, output_filename)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to: {output_file}")
        
        plt.show()
        
    except Exception as e:
        print(f"\nError during fitting: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
