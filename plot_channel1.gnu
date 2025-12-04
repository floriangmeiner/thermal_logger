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
# Skip header row, use row number for x and column 2 (ch1_celsius) for y
# Filter out ERROR values by checking if it's a number
plot '/home/maron2/Documents/repos/internal/thermal_logger/logs/off_to_full_speed.csv' every ::1 using 0:(stringcolumn(2) eq "ERROR" ? NaN : column(2)) with linespoints ls 1 notitle
