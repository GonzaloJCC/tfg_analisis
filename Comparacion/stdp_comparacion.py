import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import os
import sys
import re
import numpy as np

# Cargar librerías de NEURON
import neuron
from neuron import h

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column

# CONFIGURACIÓN
FILE_NAME = "Comparacion_STDP_Neun_vs_Neuron"

# Control del Zoom Inicial
HABILITAR_ZOOM = True
ZOOM_INICIO = 50
ZOOM_FIN = 150

# Carpetas de salida
TXT_FOLDER = "Resultados_TXT"
PDF_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"

# LaTeX config
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

TIME = 10000 # Irrelevante si no se cambia Neun
SLICE = 1 
THRESHOLD_VAL = -54.0

script_dir = os.path.dirname(os.path.abspath(__file__))

# NEUN
def run_neun():
    print("\n--- Ejecutando Simulador NEUN ---")
    neun_cpp_file = os.path.abspath(os.path.join(script_dir, "../../Neun/examples/STDPSynapse.cpp"))
    neun_build_dir = os.path.abspath(os.path.join(script_dir, "../../Neun/build"))
    
    if not os.path.exists(neun_cpp_file):
        print(f"Error: No se encuentra {neun_cpp_file}")
        sys.exit(1)

    txt_dir_abs = os.path.join(script_dir, TXT_FOLDER)
    os.makedirs(txt_dir_abs, exist_ok=True)
    full_txt_path = os.path.join(txt_dir_abs, f"{FILE_NAME}_Neun.txt")

    if os.path.exists(full_txt_path):
        os.remove(full_txt_path)

    cmd = (
        'rm -f examples/STDPSynapse && '
        'touch examples/STDPSynapse.cpp && '
        'make && '
        f'cd examples && ./STDPSynapse > "{full_txt_path}"'
    )
    
    try:
        subprocess.run(cmd, cwd=neun_build_dir, shell=True, check=True)
        print(f"Datos de Neun guardados en: {full_txt_path}")
        return full_txt_path
    except subprocess.CalledProcessError as e:
        print(f"Error compilando/ejecutando Neun: {e}")
        sys.exit(1)

txt_path = run_neun()

# Leer datos de Neun
columns = ['Time', 'vpre1', 'vpre2', 'vpost', 'i1', 'i2', 'g1', 'g2']
df_neun = pd.read_csv(txt_path, sep=r'\s+', names=columns, header=0, engine='c')
df_neun = df_neun.iloc[::SLICE, :].copy()

# NEURON
print("\n--- Ejecutando Simulador NEURON ---")
neuron_mech_dir = os.path.abspath(os.path.join(script_dir, '../Neuron_simulacion/STDP'))
if os.path.exists(os.path.join(neuron_mech_dir, 'x86_64')):
    neuron.load_mechanisms(neuron_mech_dir)
else:
    print(f"No se encontró la carpeta compilada 'x86_64' en {neuron_mech_dir}")

h.load_file('stdrun.hoc')
h.dt = 0.005 

# Red: 3 neuronas, 2 sinapsis
n1 = h.Section(name='n1') 
n2 = h.Section(name='n2') 
n3 = h.Section(name='n3') 

for n in [n1, n2, n3]:
    n.insert('hh')
    n.L = 500     
    n.diam = 500  

syn1 = h.STDP(n2(0.5))
h.setpointer(n1(0.5)._ref_v, 'vpre', syn1)

syn2 = h.STDP(n2(0.5))
h.setpointer(n3(0.5)._ref_v, 'vpre', syn2)

stim1 = h.IClamp(n1(0.5))
stim1.delay = 0 
stim1.dur = TIME
stim1.amp = 600 

stim3 = h.IClamp(n3(0.5)) 
stim3.delay = 0 
stim3.dur = TIME
stim3.amp = 500

stim2 = h.IClamp(n2(0.5))
stim2.delay = 0 
stim2.dur = TIME
stim2.amp = 500

# Grabar datos de la Sinapsis 1
t_vec = h.Vector().record(h._ref_t)
vpre1_vec = h.Vector().record(n1(0.5)._ref_v)
vpost_vec = h.Vector().record(n2(0.5)._ref_v)
g1_vec = h.Vector().record(syn1._ref_g)

h.finitialize(-65)
n1(0.5).v = -75
n3(0.5).v = -85
n2(0.5).v = -70
h.finitialize() 

syn1.g = 0.0052
syn2.g = 0.005

h.continuerun(TIME)
print("Simulación NEURON completada")

# Extraer datos
t_neuron = np.array(t_vec)[SLICE:]
vpre1_neuron = np.array(vpre1_vec)[SLICE:]
vpost_neuron = np.array(vpost_vec)[SLICE:]
g1_neuron = np.array(g1_vec)[SLICE:]

# Gráficas
print("\n--- Generando Gráficas ---")

# --- PDF ---
fig, axs = plt.subplots(4, 1, figsize=(8, 11), sharex=True)
# fig.suptitle(f"Comparación Sinapsis 1: NEUN vs NEURON", fontsize=12)

# Panel 1: Voltajes NEUN
axs[0].plot(df_neun['Time'], df_neun['vpre1'], label='V_pre1', color='red', alpha=0.8)
axs[0].plot(df_neun['Time'], df_neun['vpost'], label='V_post', color='green', alpha=0.8)
axs[0].axhline(THRESHOLD_VAL, color='gray', linestyle='--', alpha=0.5)
axs[0].set_ylabel(r'Voltaje ($mV$)')
axs[0].set_title("NEUN - Voltajes Sinapsis 1", fontsize=10, loc='left', fontweight='bold')
axs[0].legend(loc='upper right')
axs[0].grid(True, alpha=0.3)

# Panel 2: Conductancia NEUN
axs[1].plot(df_neun['Time'], df_neun['g1'], label='g1', color='red')
axs[1].set_ylabel(r'Cond. ($pS$)')
axs[1].set_title("NEUN - Conductancia Sinapsis 1", fontsize=10, loc='left', fontweight='bold')
axs[1].legend(loc='upper right')
axs[1].grid(True, alpha=0.3)

# Panel 3: Voltajes NEURON
axs[2].plot(t_neuron, vpre1_neuron, label='V_pre1', color='darkred', alpha=0.8)
axs[2].plot(t_neuron, vpost_neuron, label='V_post', color='darkgreen', alpha=0.8)
axs[2].axhline(THRESHOLD_VAL, color='gray', linestyle='--', alpha=0.5)
axs[2].set_ylabel(r'Voltaje ($mV$)')
axs[2].set_title("NEURON - Voltajes Sinapsis 1", fontsize=10, loc='left', fontweight='bold')
axs[2].legend(loc='upper right')
axs[2].grid(True, alpha=0.3)

# Panel 4: Conductancia NEURON
axs[3].plot(t_neuron, g1_neuron, label='g1', color='darkred')
axs[3].set_ylabel(r'Cond. ($pS$)')
axs[3].set_xlabel(r'Tiempo (ms)')
axs[3].set_title("NEURON - Conductancia Sinapsis 1", fontsize=10, loc='left', fontweight='bold')
axs[3].legend(loc='upper right')
axs[3].grid(True, alpha=0.3)

if HABILITAR_ZOOM:
    axs[0].set_xlim(ZOOM_INICIO, ZOOM_FIN)

plt.tight_layout()

pdf_dir_abs = os.path.join(script_dir, PDF_FOLDER)
os.makedirs(pdf_dir_abs, exist_ok=True)
pdf_path = os.path.join(pdf_dir_abs, f"{FILE_NAME}.pdf")
plt.savefig(pdf_path)


# --- HTML BOKEH ---
bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
os.makedirs(bokeh_dir_abs, exist_ok=True)
bokeh_path = os.path.join(bokeh_dir_abs, f"{FILE_NAME}.html")
output_file(bokeh_path, title=f"Comparativa: {FILE_NAME}")

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

fig_kws = {"width": 900, "height": 200, "tools": TOOLS, "output_backend": "webgl"}
if HABILITAR_ZOOM:
    fig_kws["x_range"] = (ZOOM_INICIO, ZOOM_FIN)

# P1: NEUN Voltajes
p1 = figure(title="NEUN - Voltajes Sinapsis 1", **fig_kws)
p1.line(df_neun['Time'], df_neun['vpre1'], legend_label="V_pre1", color="red", line_width=1.5)
p1.line(df_neun['Time'], df_neun['vpost'], legend_label="V_post", color="green", line_width=1.5)
p1.line(df_neun['Time'], [THRESHOLD_VAL]*len(df_neun), color="gray", line_dash="dashed", alpha=0.5)
p1.yaxis.axis_label = "Voltaje (mV)"
p1.legend.click_policy = "hide"

# P2: NEUN Conductancia
p2 = figure(title="NEUN - Conductancia", width=900, height=180, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p2.line(df_neun['Time'], df_neun['g1'], legend_label="g1", color="red", line_width=2)
p2.yaxis.axis_label = "Cond. (pS)"

# P3: NEURON Voltajes
p3 = figure(title="NEURON - Voltajes Sinapsis 1", width=900, height=200, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p3.line(t_neuron, vpre1_neuron, legend_label="V_pre1", color="darkred", line_width=1.5)
p3.line(t_neuron, vpost_neuron, legend_label="V_post", color="darkgreen", line_width=1.5)
p3.line(t_neuron, [THRESHOLD_VAL]*len(t_neuron), color="gray", line_dash="dashed", alpha=0.5)
p3.yaxis.axis_label = "Voltaje (mV)"
p3.legend.click_policy = "hide"

# P4: NEURON Conductancia
p4 = figure(title="NEURON - Conductancia", width=900, height=180, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p4.line(t_neuron, g1_neuron, legend_label="g1", color="darkred", line_width=2)
p4.xaxis.axis_label = "Tiempo (ms)"
p4.yaxis.axis_label = "Cond. (pS)"

layout = column(p1, p2, p3, p4)
save(layout)

print(f"\n¡Éxito!")
print(f" -> PDF: {pdf_path}")
print(f" -> HTML: {bokeh_path}")
