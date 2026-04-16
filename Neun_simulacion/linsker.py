import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import os
import sys
import re

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column

FILE_NAME = "Linsker_Experiment"

# Zoom Control
HABILITAR_ZOOM = False
ZOOM_INICIO = 50
ZOOM_FIN = 150

# Folders
TXT_FOLDER = "Resultados_TXT"
PNG_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"

# Set LaTeX parameters (Dejamos el usetex a True como tenías en este repo)
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

# Extract parameters from C++
def extract_cpp_params():
    print("--- Analyzing C++ code to find parameters ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cpp_file = os.path.abspath(os.path.join(script_dir, '../../Neun/examples/linskerSynapse.cpp'))
    
    if not os.path.exists(cpp_file):
        print(f"Error: Not found {cpp_file}")
        sys.exit(1)

    params_found = {}

    with open(cpp_file, 'r') as f:
        content = f.read()

    # Search for patterns like: syn_args.params[Synapsis::xo] = -65;
    pattern = r"syn_args\.params\[Synapsis::(\w+)\]\s*=\s*([^;]+);"
    matches = re.findall(pattern, content)
    
    for name, value in matches:
        params_found[name] = value.strip()

    return params_found

# Build dynamic name
params = extract_cpp_params()

# Choose which parameters form the name
keys_to_use = ['xo', 'yo', 'eta', 'k1', 'w_max']
filename_parts = []
title_parts = []

for k in keys_to_use:
    if k in params:
        val = params[k]
        filename_parts.append(f"{k}{val}")     # Example: xo-65
        title_parts.append(f"{k}={val}")       # Example: xo=-65

# If no params found, use "default"
suffix = "_".join(filename_parts) if filename_parts else "default"
base_filename = f"{FILE_NAME}_{suffix}" 


# Run code
def run_model(output_txt_path):
    print("--- Compiling and Running ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.abspath(os.path.join(script_dir, '../../../Neun/build'))
    
    # Eliminar el archivo TXT viejo para evitar errores
    if os.path.exists(output_txt_path):
        os.remove(output_txt_path)
        print("Borrando datos de la simulación anterior...")

    # Forzar recompilación eliminando el binario
    cmd = (
        'rm -f examples/linskerSynapse && '
        'touch examples/linskerSynapse.cpp && '
        'make && '
        f'cd examples && ./linskerSynapse > "{output_txt_path}"'
    )
    
    try:
        subprocess.run(cmd, cwd=build_dir, shell=True, check=True)
        print(f"Data saved in: {output_txt_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling/running: {e}")
        sys.exit(1)

# Path to save the txt
script_dir = os.path.dirname(os.path.abspath(__file__))
txt_dir_abs = os.path.join(script_dir, TXT_FOLDER)
os.makedirs(txt_dir_abs, exist_ok=True)

full_txt_path = os.path.join(txt_dir_abs, f"{base_filename}.txt")

# Run model
run_model(full_txt_path)

# Plot
if os.path.exists(full_txt_path):
    print("Generating PDF...")
    
    # For 2 synapses
    columns = ['Time', 'V1pre', 'V2pre', 'Vpost', 'i1', 'i2', 'w1', 'w2', 'SUM(W)']
    
    # For 4 synapses
    # columns = ['Time', 'V1pre', 'V2pre', 'V3pre', 'V4pre', 'Vpost', 'i1', 'i2', 'i3', 'i4', 'w1', 'w2', 'w3', 'w4', 'SUM(W)']

    df = pd.read_csv(full_txt_path, sep=r'\s+', names=columns, header=0, engine='c')
    
    df_plot = df.iloc[::1, :].copy()  # Change the number to take less data but simulate faster

    fig, (ax_i, ax_w) = plt.subplots(2, 1, figsize=(6, 5), sharex=True)

    # Title of the plot
    plot_title_str = ", ".join(title_parts)
    fig.suptitle(f"Linsker Model: {plot_title_str}")

    # Plots - Panel 1
    ax_i.plot(df_plot['Time'], df_plot['i1'], label='i1', color='red')
    ax_i.plot(df_plot['Time'], df_plot['i2'], label='i2', color='purple')

    # ax_i.plot(df_plot['Time'], df_plot['i3'], label='i3', color='green')
    # ax_i.plot(df_plot['Time'], df_plot['i4'], label='i4', color='blue')

    ax_i.set_ylabel(r'Corriente ($pA$)')
    ax_i.legend(loc='upper right')
    ax_i.grid(True, alpha=0.3)

    # Plots - Panel 2
    ax_w.plot(df_plot['Time'], df_plot['w1'], label='w1', color='brown')
    ax_w.plot(df_plot['Time'], df_plot['w2'], label='w2', color='darkgreen')

    # ax_w.plot(df_plot['Time'], df_plot['w3'], label='w3', color='green')
    # ax_w.plot(df_plot['Time'], df_plot['w4'], label='w4', color='blue')
    
    ax_w.set_ylabel(r'Pesos ($w$)')
    ax_w.set_xlabel(r'Tiempo ($ms$)')
    ax_w.legend(loc='upper right')
    ax_w.grid(True, alpha=0.3)

    # Conditional Zoom
    if HABILITAR_ZOOM:
        ax_i.set_xlim(ZOOM_INICIO, ZOOM_FIN)

    plt.tight_layout()

    # Save plot
    png_dir_abs = os.path.join(script_dir, PNG_FOLDER)
    os.makedirs(png_dir_abs, exist_ok=True)
    
    png_path = os.path.join(png_dir_abs, f"{base_filename}.pdf")
    plt.savefig(png_path)
    
    # Generate HTML
    print("Generating HTML...")
    bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
    os.makedirs(bokeh_dir_abs, exist_ok=True)
    bokeh_path = os.path.join(bokeh_dir_abs, f"{base_filename}.html")

    output_file(bokeh_path, title=f"Interactive Linsker: {base_filename}")

    TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

    # Set x_range dynamically based on HABILITAR_ZOOM
    fig_kws = {
        "title": f"Linsker Currents - {plot_title_str}", 
        "width": 900, 
        "height": 250, 
        "tools": TOOLS, 
        "output_backend": "webgl"
    }
    
    if HABILITAR_ZOOM:
        fig_kws["x_range"] = (ZOOM_INICIO, ZOOM_FIN)

    # P1: Currents
    p1 = figure(**fig_kws)
    p1.line(df_plot['Time'], df_plot['i1'], legend_label="i1", color="red", line_width=1.5)
    p1.line(df_plot['Time'], df_plot['i2'], legend_label="i2", color="purple", line_width=1.5)
    p1.yaxis.axis_label = "Corriente (pA)"
    p1.legend.click_policy = "hide"

    # P2: Weights (Synchronized with P1 x_range)
    p2 = figure(title="Linsker Weights", width=900, height=250, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
    p2.line(df_plot['Time'], df_plot['w1'], legend_label="w1", color="brown", line_width=2)
    p2.line(df_plot['Time'], df_plot['w2'], legend_label="w2", color="darkgreen", line_width=2)
    p2.xaxis.axis_label = "Tiempo (ms)"
    p2.yaxis.axis_label = "Pesos (w)"
    p2.legend.click_policy = "hide"

    # Group and save
    layout = column(p1, p2)
    save(layout)

    print(f"\n -> Data: {full_txt_path}")
    print(f" -> PDF: {png_path}")
    print(f" -> HTML: {bokeh_path}")
