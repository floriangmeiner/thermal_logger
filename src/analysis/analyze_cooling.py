#!/usr/bin/env python3
"""
Fit Newton's Law of Cooling to thermal data to determine thermal time constant.
T(t) = T_env + (T_0 - T_env) * exp(-t/tau)
"""

import csv
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import os

def newtons_law_cooling(t, T_env, T_0, tau):
    """
    Newton's Law of Cooling model
    
    Parameters:
    t: time (seconds)
    T_env: environmental/ambient temperature
    T_0: initial temperature at t=0
    tau: thermal time constant (seconds)
    """
    return T_env + (T_0 - T_env) * np.exp(-t / tau)

def parse_timestamp(ts_str):
    """Parse ISO format timestamp to datetime"""
    return datetime.fromisoformat(ts_str)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Fit Newton\'s Law of Cooling to thermal data to determine thermal time constant.'
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
    
    # Extract cooling phase (from peak onwards)
    t_cooling = time_seconds[peak_idx:]
    T_cooling = temps[peak_idx:]
    
    # Reset time to 0 at the start of cooling
    t_cooling = t_cooling - peak_time
    
    print(f"\nCooling phase:")
    print(f"  Duration: {t_cooling[-1]:.1f} seconds ({t_cooling[-1]/60:.1f} minutes)")
    print(f"  Temperature range: {T_cooling[0]:.2f}°C → {T_cooling[-1]:.2f}°C")
    print(f"  Number of data points: {len(t_cooling)}")
    
    # Initial parameter estimates
    T_env_guess = T_cooling[-1]  # Final temperature as ambient
    T_0_guess = T_cooling[0]      # Initial temperature (peak)
    tau_guess = 300                # Initial guess: 5 minutes
    
    print(f"\nInitial parameter guesses:")
    print(f"  T_env: {T_env_guess:.2f}°C")
    print(f"  T_0: {T_0_guess:.2f}°C")
    print(f"  tau: {tau_guess:.1f}s")
    
    # Set bounds dynamically based on data
    T_env_lower = max(10, T_env_guess - 10)
    T_env_upper = T_env_guess + 10
    T_0_lower = T_0_guess - 10
    T_0_upper = max(T_0_guess + 10, T_0_guess * 1.2)  # Allow 20% above peak
    tau_lower = 10
    tau_upper = max(10000, t_cooling[-1] * 2)  # Allow up to 2x the total cooling duration
    
    bounds_lower = [T_env_lower, T_0_lower, tau_lower]
    bounds_upper = [T_env_upper, T_0_upper, tau_upper]
    
    print(f"\nFitting bounds:")
    print(f"  T_env: [{T_env_lower:.1f}, {T_env_upper:.1f}] °C")
    print(f"  T_0:   [{T_0_lower:.1f}, {T_0_upper:.1f}] °C")
    print(f"  tau:   [{tau_lower:.1f}, {tau_upper:.1f}] s")
    
    # Fit the model
    try:
        popt, pcov = curve_fit(
            newtons_law_cooling,
            t_cooling,
            T_cooling,
            p0=[T_env_guess, T_0_guess, tau_guess],
            bounds=(bounds_lower, bounds_upper),
            maxfev=10000
        )
        
        T_env_fit, T_0_fit, tau_fit = popt
        perr = np.sqrt(np.diag(pcov))  # Standard errors
        
        print(f"\n{'='*60}")
        print(f"FITTED PARAMETERS:")
        print(f"{'='*60}")
        print(f"  T_env (ambient):        {T_env_fit:.3f} ± {perr[0]:.3f} °C")
        print(f"  T_0 (initial):          {T_0_fit:.3f} ± {perr[1]:.3f} °C")
        print(f"  τ (time constant):      {tau_fit:.1f} ± {perr[2]:.1f} seconds")
        print(f"                          {tau_fit/60:.2f} ± {perr[2]/60:.2f} minutes")
        print(f"{'='*60}")
        
        # Calculate R-squared
        T_fit = newtons_law_cooling(t_cooling, *popt)
        ss_res = np.sum((T_cooling - T_fit)**2)
        ss_tot = np.sum((T_cooling - np.mean(T_cooling))**2)
        r_squared = 1 - (ss_res / ss_tot)
        
        print(f"\nGoodness of fit:")
        print(f"  R² = {r_squared:.6f}")
        print(f"  RMSE = {np.sqrt(ss_res/len(T_cooling)):.4f}°C")
        
        # Calculate characteristic times
        print(f"\nCharacteristic cooling times:")
        print(f"  Time to reach 63% of final temperature: τ = {tau_fit:.1f}s ({tau_fit/60:.2f} min)")
        print(f"  Time to reach 95% of final temperature: 3τ = {3*tau_fit:.1f}s ({3*tau_fit/60:.2f} min)")
        print(f"  Time to reach 99% of final temperature: 5τ = {5*tau_fit:.1f}s ({5*tau_fit/60:.2f} min)")
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Data and fit
        ax1.plot(t_cooling/60, T_cooling, 'b.', alpha=0.5, label='Measured data', markersize=3)
        
        # Generate smooth fit line
        t_smooth = np.linspace(0, t_cooling[-1], 1000)
        T_smooth = newtons_law_cooling(t_smooth, *popt)
        ax1.plot(t_smooth/60, T_smooth, 'r-', linewidth=2, 
                label=f'Fit: τ = {tau_fit:.1f}s ({tau_fit/60:.2f} min)')
        
        ax1.axhline(y=T_env_fit, color='g', linestyle='--', alpha=0.7, 
                   label=f'T_env = {T_env_fit:.2f}°C')
        ax1.axhline(y=T_0_fit, color='orange', linestyle='--', alpha=0.7,
                   label=f'T_0 = {T_0_fit:.2f}°C')
        
        # Mark tau on the plot
        T_at_tau = newtons_law_cooling(tau_fit, *popt)
        ax1.plot(tau_fit/60, T_at_tau, 'ro', markersize=10, 
                label=f'At τ: {T_at_tau:.2f}°C')
        
        ax1.set_xlabel('Time (minutes)', fontsize=12)
        ax1.set_ylabel('Temperature (°C)', fontsize=12)
        ax1.set_title('Newton\'s Law of Cooling - Channel 1 Data Fit', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Residuals
        residuals = T_cooling - T_fit
        ax2.plot(t_cooling/60, residuals, 'b.', alpha=0.5, markersize=3)
        ax2.axhline(y=0, color='r', linestyle='-', linewidth=1)
        ax2.fill_between(t_cooling/60, -perr[0], perr[0], alpha=0.2, color='red',
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
        output_filename = f"cooling_fit_analysis_{input_name}.png"
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
