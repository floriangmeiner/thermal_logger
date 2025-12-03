#!/usr/bin/gnuplot

# Gnuplot script to plot Channel 1 temperature data
set datafile separator ","

# Set terminal to display in window
set terminal qt size 1200,600 persist

# Title and labels
set title "Thermal Logger - Channel 1 Temperature" font ",14"
set xlabel "Sample Number"
set ylabel "Temperature (°C)"

# Grid
set grid

# Style
set style line 1 lc rgb '#0060ad' lt 1 lw 2 pt 7 ps 0.5

# Plot the data
# Skip header row, use column 1 (sample_num) for x and column 2 (ch1_celsius) for y
# Filter out ERROR values by checking if it's a number
plot 'thermal_recorded_20251203_154717.csv' every ::1 using 1:(strcol(2) eq "ERROR" ? NaN : $2) with linespoints ls 1 notitle
