import pandas as pd
import matplotlib.pyplot as plt

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import HoverTool

import subprocess
import os
import sys
import re

# Set LaTeX parameters
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "font.size": 11,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9
})

# Folders
TXT_FOLDER = "Resultados_TXT"
PNG_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"

FILE_NAME = "STDP_10s"

# Get parameters from C++
def extract_cpp_params():
    print("Getting C++ parameters from code...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Adjust path to Neun folder
    cpp_file = os.path.abspath(os.path.join(script_dir, "../../Neun/examples/STDPSynapse.cpp"))

    if not os.path.exists(cpp_file):
        print(f"Error: Not found {cpp_file}")
        sys.exit(1)

    params_found = {}

    with open(cpp_file, 'r') as f:
        content = f.read()

    # Search for patterns like: syn_args.params[Synapse:spike_threshold] = -54;
    pattern = r"syn_args\.params\[Synapse::(\w+)\]\s*=\s*([^;]+);"
    matches = re.findall(pattern, content)
    
    for name, value in matches:
        params_found[name] = value.strip()

    return params_found

# Build dynamic name
params = extract_cpp_params()

# Choose which parameters form the name
keys_to_use = ['A_minus', 'A_plus', 'tau_minus', 'tau_plus', 'spike_threshold', 'g_max']
filename_parts = []
title_parts = []

for k in keys_to_use:
    if k in params:
        val = params[k]
        filename_parts.append(f"{k}{val}")
        title_parts.append(f"{k}={val}")

# If no params found, use "default"
suffix = "_".join(filename_parts) if filename_parts else "default"
# Combine the global FILE_NAME with the extracted parameters
base_filename = f"{FILE_NAME}_{suffix}" 

# Run code
def run_model(output_txt_path):
    print("--- Compiling and Running ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.abspath(os.path.join(script_dir, '../../Neun/build'))
    
    # Delete old TXT file to prevent errors
    if os.path.exists(output_txt_path):
        os.remove(output_txt_path)
        print("Deleting data from previous simulation...")

    # Force recompilation by removing the binary
    cmd = (
        'rm -f examples/STDPSynapse && '
        'touch examples/STDPSynapse.cpp && '
        'make && '
        f'cd examples && ./STDPSynapse > "{output_txt_path}"'
    )
    
    try:
        subprocess.run(cmd, cwd=build_dir, shell=True, check=True)
        print(f"Data saved in: {output_txt_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling/running: {e}")
        sys.exit(1)

# Path for txt file
script_dir = os.path.dirname(os.path.abspath(__file__))
txt_dir_abs = os.path.join(script_dir, TXT_FOLDER)
os.makedirs(txt_dir_abs, exist_ok=True)

full_txt_path = os.path.join(txt_dir_abs, f"{base_filename}.txt")

# Run model
run_model(full_txt_path)

# Plot
if os.path.exists(full_txt_path):
    print("Generating plot (PDF)...")

    columns = ['Time', 'vpre1', 'vpre2', 'vpost', 'i1', 'i2', 'g1', 'g2']
    df = pd.read_csv(full_txt_path, sep=r'\s+', names=columns, header=0, engine='c')

    # Downsample for continuous plots (Change ::1 to ::10 or ::50)
    df_plot = df.iloc[::1, :].copy()

    # Generate PDF ------------------------------------------------------------------------------------------------
    fig, (ax_i, ax_w) = plt.subplots(2, 1, figsize=(6, 5), sharex=True)

    # Title of the plot
    plot_title_str = ", ".join(title_parts)
    fig.suptitle(f"STDP Simulation: {plot_title_str}")

    # Plot 1: Current
    ax_i.plot(df_plot['Time'], df_plot['i1'], label='i1', color='red')
    ax_i.plot(df_plot['Time'], df_plot['i2'], label='i2', color='blue')
    ax_i.set_ylabel(r'Current ($pA$)')
    ax_i.legend(loc='upper right')
    ax_i.grid(True, alpha=0.3)

    # Plot 2: Conductance
    ax_w.plot(df_plot['Time'], df_plot['g1'], label='g1', color='red')
    ax_w.plot(df_plot['Time'], df_plot['g2'], label='g2', color='blue')
    ax_w.set_ylabel(r'Conductance ($pS$)')
    ax_w.set_xlabel(r'Time (ms)')
    ax_w.legend(loc='upper right')
    ax_w.grid(True, alpha=0.3)
    
    # # Zoom from 50 to 150 ms to see individual spikes
    # ax_i.set_xlim(50, 150)

    plt.tight_layout()

    # Save PDF plot
    png_dir_abs = os.path.join(script_dir, PNG_FOLDER)
    os.makedirs(png_dir_abs, exist_ok=True)
    
    png_path = os.path.join(png_dir_abs, f"{base_filename}.pdf")
    plt.savefig(png_path)
    
    # Generate interactive HTML -----------------------------------------------------------------------------------
    print("Generating interactive plot (HTML)...")
    
    # Create folder for Bokeh
    bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
    os.makedirs(bokeh_dir_abs, exist_ok=True)
    
    bokeh_path = os.path.join(bokeh_dir_abs, f"{base_filename}.html")
    output_file(bokeh_path, title=f"Interactive STDP: {base_filename}")

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

    # P1: Currents
    p1 = figure(title=f"Currents - {plot_title_str}", width=900, height=250, tools=TOOLS, output_backend="webgl")
    p1.line(df_plot['Time'], df_plot['i1'], legend_label="i1 (Pre1)", color="red", line_width=1.5)
    p1.line(df_plot['Time'], df_plot['i2'], legend_label="i2 (Pre2)", color="blue", line_width=1.5)
    p1.yaxis.axis_label = "Current (pA)"
    p1.legend.click_policy = "hide"

    # P2: Conductance (Synchronized with P1 via x_range)
    p2 = figure(title="Conductance", width=900, height=250, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
    p2.line(df_plot['Time'], df_plot['g1'], legend_label="g1 (Pre1)", color="red", line_width=2)
    p2.line(df_plot['Time'], df_plot['g2'], legend_label="g2 (Pre2)", color="blue", line_width=2)
    p2.xaxis.axis_label = "Time (ms)"
    p2.yaxis.axis_label = "Conductance (pS)"
    p2.legend.click_policy = "hide"

    # Group the plots in a vertical column
    layout = column(p1, p2)
    save(layout)

    print(f"\n -> Data: {full_txt_path}")
    print(f" -> PDF: {png_path}")
    print(f" -> HTML: {bokeh_path}")
