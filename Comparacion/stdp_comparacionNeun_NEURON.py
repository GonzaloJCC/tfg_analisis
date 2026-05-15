import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import os
import sys
import numpy as np

# Cargar librerías de NEURON
import neuron
script_dir = os.path.dirname(os.path.abspath(__file__))
# Cargar mecanismos de STDP compilados
neuron.load_mechanisms(os.path.abspath(os.path.join(script_dir, '../Neuron_simulacion/STDP')))
from neuron import h

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import gridplot

# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================
FILE_NAME = "Comparacion_STDP_Grid"
TXT_FOLDER = "Resultados_TXT"
PDF_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"

HABILITAR_ZOOM = True
ZOOM_INICIO = 50
ZOOM_FIN = 150

TIME = 10000 
SLICE = 1 
THRESHOLD_VAL = -54.0

# Configuración LaTeX estricta para todo el documento
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

# =========================================================================
# PARTE 1: EJECUTAR NEUN (C++)
# =========================================================================
def run_neun():
    print("\n--- Ejecutando Simulador NEUN ---")
    neun_build_dir = os.path.abspath(os.path.join(script_dir, "../../Neun/build"))
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
    subprocess.run(cmd, cwd=neun_build_dir, shell=True, check=True)
    return full_txt_path

txt_path = run_neun()
columns = ['Time', 'vpre1', 'vpre2', 'vpost', 'i1', 'i2', 'g1', 'g2']
df_neun = pd.read_csv(txt_path, sep=r'\s+', names=columns, header=0, engine='c')
df_neun = df_neun.iloc[::SLICE, :].copy()

# =========================================================================
# PARTE 2: EJECUTAR NEURON (Python)
# =========================================================================
print("\n--- Ejecutando Simulador NEURON ---")
h.load_file('stdrun.hoc')
h.dt = 0.005 

n1 = h.Section(name='n1') 
n2 = h.Section(name='n2') 
n3 = h.Section(name='n3') 

for n in [n1, n2, n3]:
    n.insert('hh')
    n.L = 500     
    n.diam = 500  

syn1 = h.STDP(n2(0.5))
h.setpointer(n1(0.5)._ref_v, 'vpre', syn1)
syn2 = h.STDP(n2(0.5)) # Mantenemos la red pero no la graficamos
h.setpointer(n3(0.5)._ref_v, 'vpre', syn2)

stim1 = h.IClamp(n1(0.5))
stim1.delay, stim1.dur, stim1.amp = 0, TIME, 600 
stim3 = h.IClamp(n3(0.5)) 
stim3.delay, stim3.dur, stim3.amp = 0, TIME, 500
stim2 = h.IClamp(n2(0.5))
stim2.delay, stim2.dur, stim2.amp = 0, TIME, 500

t_vec = h.Vector().record(h._ref_t)
vpre1_vec = h.Vector().record(n1(0.5)._ref_v)
vpost_vec = h.Vector().record(n2(0.5)._ref_v)
i1_vec = h.Vector().record(syn1._ref_i)
g1_vec = h.Vector().record(syn1._ref_g)

h.finitialize(-65)
n1(0.5).v, n3(0.5).v, n2(0.5).v = -75, -85, -70
h.finitialize() 

syn1.g, syn2.g = 0.0052, 0.005

h.continuerun(TIME)

t_neuron = np.array(t_vec)[SLICE:]
vpre1_neuron = np.array(vpre1_vec)[SLICE:]
vpost_neuron = np.array(vpost_vec)[SLICE:]
i1_neuron = -np.array(i1_vec)[SLICE:] # Inversión para visualización
g1_neuron = np.array(g1_vec)[SLICE:]

# =========================================================================
# PARTE 3: GRÁFICAS PDF MATPLOTLIB (Grid 3x2) - SOLO SINAPSIS 1
# =========================================================================
print("\n--- Generando figura 3x2 (PDF) ---")
fig, axs = plt.subplots(3, 2, figsize=(10, 8), sharex='col')

# --- COLUMNA 1: NEUN ---
axs[0, 0].set_title(r'Plasticidad STDP en Neun (Implementada)', fontsize=12, fontfamily='serif')
axs[0, 0].plot(df_neun['Time'], df_neun['vpre1'], label=r'$V_{\mathrm{pre1}}$', color='red', alpha=0.8)
axs[0, 0].plot(df_neun['Time'], df_neun['vpost'], label=r'$V_{\mathrm{post}}$', color='blue', alpha=0.8)
axs[0, 0].axhline(THRESHOLD_VAL, color='gray', linestyle='--', alpha=0.5)
axs[0, 0].set_ylabel(r'Voltaje ($mV$)')
axs[0, 0].legend(loc='upper right')
axs[0, 0].grid(True, alpha=0.3)

axs[1, 0].plot(df_neun['Time'], df_neun['i1'], label=r'$i_{1}$', color='purple')
axs[1, 0].set_ylabel(r'Corriente Sinapsis 1 ($pA$)')
axs[1, 0].legend(loc='upper right')
axs[1, 0].grid(True, alpha=0.3)

axs[2, 0].plot(df_neun['Time'], df_neun['g1'], label=r'$g_{1}$', color='green')
axs[2, 0].set_ylabel(r'Cond. Sinapsis 1 ($pS$)')
axs[2, 0].set_xlabel(r'Tiempo ($ms$)')
axs[2, 0].legend(loc='upper right')
axs[2, 0].grid(True, alpha=0.3)

# --- COLUMNA 2: NEURON ---
axs[0, 1].set_title(r'Plasticidad STDP en NEURON (Validación)', fontsize=12, fontfamily='serif')
axs[0, 1].plot(t_neuron, vpre1_neuron, label=r'$V_{\mathrm{pre1}}$', color='red', alpha=0.8)
axs[0, 1].plot(t_neuron, vpost_neuron, label=r'$V_{\mathrm{post}}$', color='blue', alpha=0.8)
axs[0, 1].axhline(THRESHOLD_VAL, color='gray', linestyle='--', alpha=0.5)
axs[0, 1].set_ylabel(r'Voltaje ($mV$)')
axs[0, 1].legend(loc='upper right')
axs[0, 1].grid(True, alpha=0.3)

axs[1, 1].plot(t_neuron, i1_neuron, label=r'$i_{1}$', color='purple')
axs[1, 1].set_ylabel(r'Corriente Sinapsis 1 ($nA$)') 
axs[1, 1].legend(loc='upper right')
axs[1, 1].grid(True, alpha=0.3)

axs[2, 1].plot(t_neuron, g1_neuron, label=r'$g_{1}$', color='green')
axs[2, 1].set_ylabel(r'Cond. Sinapsis 1 ($pS$)')
axs[2, 1].set_xlabel(r'Tiempo ($ms$)')
axs[2, 1].legend(loc='upper right')
axs[2, 1].grid(True, alpha=0.3)

if HABILITAR_ZOOM:
    for ax in axs.flat: ax.set_xlim(ZOOM_INICIO, ZOOM_FIN)

plt.tight_layout()
plt.subplots_adjust(top=0.92)

pdf_dir_abs = os.path.join(script_dir, PDF_FOLDER)
os.makedirs(pdf_dir_abs, exist_ok=True)
pdf_path = os.path.join(pdf_dir_abs, f"{FILE_NAME}.pdf")
plt.savefig(pdf_path)

# =========================================================================
# PARTE 4: GRÁFICAS HTML BOKEH (Grid 3x2) - SOLO SINAPSIS 1
# =========================================================================
print("--- Generando HTML Interactivo 3x2 ---")
bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
os.makedirs(bokeh_dir_abs, exist_ok=True)
bokeh_path = os.path.join(bokeh_dir_abs, f"{FILE_NAME}.html")
output_file(bokeh_path, title=f"Comparativa STDP")

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"
W, H = 450, 250

fig_kws_neun = {"title": "Plasticidad STDP en Neun (Implementada)", "width": W, "height": H, "tools": TOOLS}
fig_kws_neuron = {"title": "Plasticidad STDP en NEURON (Validación)", "width": W, "height": H, "tools": TOOLS}

if HABILITAR_ZOOM:
    fig_kws_neun["x_range"] = (ZOOM_INICIO, ZOOM_FIN)
    fig_kws_neuron["x_range"] = (ZOOM_INICIO, ZOOM_FIN)

# --- NEUN ---
p_neun_v = figure(**fig_kws_neun)
p_neun_v.line(df_neun['Time'], df_neun['vpre1'], legend_label="V_pre1", color="red", line_width=1.5)
p_neun_v.line(df_neun['Time'], df_neun['vpost'], legend_label="V_post", color="blue", line_width=1.5)
p_neun_v.yaxis.axis_label = "Voltaje (mV)"

p_neun_i = figure(width=W, height=H, tools=TOOLS, x_range=p_neun_v.x_range)
p_neun_i.line(df_neun['Time'], df_neun['i1'], legend_label="i1", color="purple", line_width=1.5)
p_neun_i.yaxis.axis_label = "Corriente Sinapsis 1 (pA)"

p_neun_g = figure(width=W, height=H, tools=TOOLS, x_range=p_neun_v.x_range)
p_neun_g.line(df_neun['Time'], df_neun['g1'], legend_label="g1", color="green", line_width=2)
p_neun_g.xaxis.axis_label = "Tiempo (ms)"
p_neun_g.yaxis.axis_label = "Cond. Sinapsis 1 (pS)"

# --- NEURON ---
p_neuron_v = figure(**fig_kws_neuron)
p_neuron_v.line(t_neuron, vpre1_neuron, legend_label="V_pre1", color="red", line_width=1.5)
p_neuron_v.line(t_neuron, vpost_neuron, legend_label="V_post", color="blue", line_width=1.5)
p_neuron_v.yaxis.axis_label = "Voltaje (mV)"

p_neuron_i = figure(width=W, height=H, tools=TOOLS, x_range=p_neuron_v.x_range)
p_neuron_i.line(t_neuron, i1_neuron, legend_label="i1", color="purple", line_width=1.5)
p_neuron_i.yaxis.axis_label = "Corriente Sinapsis 1 (nA)"

p_neuron_g = figure(width=W, height=H, tools=TOOLS, x_range=p_neuron_v.x_range)
p_neuron_g.line(t_neuron, g1_neuron, legend_label="g1", color="green", line_width=2)
p_neuron_g.xaxis.axis_label = "Tiempo (ms)"
p_neuron_g.yaxis.axis_label = "Cond. Sinapsis 1 (pS)"

for p in [p_neun_v, p_neun_i, p_neun_g, p_neuron_v, p_neuron_i, p_neuron_g]: 
    p.legend.click_policy = "hide"
    if p.title:
        p.title.text_font = "serif"
        p.title.text_font_size = "13pt"

layout = gridplot([[p_neun_v, p_neuron_v], [p_neun_i, p_neuron_i], [p_neun_g, p_neuron_g]])
save(layout)

print(f"\n -> PDF: {pdf_path}")
print(f" -> HTML: {bokeh_path}")
