import os
import sys
import re
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- LÍNEAS MODIFICADAS PARA CARGAR LOS MECANISMOS DE NEURON ---
script_dir = os.path.dirname(os.path.abspath(__file__))
import neuron
# Obligamos a NEURON a leer la carpeta donde compilaste el Linsker.mod
neuron.load_mechanisms(os.path.abspath(os.path.join(script_dir, '../Neuron_simulacion/Linsker')))
from neuron import h
# ---------------------------------------------------------------

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import gridplot

# =========================================================================
# CONFIGURACIÓN GENERAL
# =========================================================================
FILE_NAME = "Comparacion_Linsker"
PDF_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"
TXT_FOLDER = "Resultados_TXT"

HABILITAR_ZOOM = True # <--------------------------------------- ZOOM
ZOOM_INICIO = 100
ZOOM_FIN = 200

TIME = 10000 # ms de simulación
PA_FLAG = 1 # Para nA en NEURON (Ajusta si necesitas pA)
SLICE = 10
W_MAX = 2.0

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
# PARTE 1: EJECUTAR NEUN (C++) Y LEER DATOS
# =========================================================================
def extract_cpp_params():
    print("--- Analizando código C++ (Neun) ---")
    cpp_file = os.path.abspath(os.path.join(script_dir, '../../Neun/examples/linskerSynapse.cpp'))
    if not os.path.exists(cpp_file):
        print(f"Error: No se encontró {cpp_file}")
        sys.exit(1)
    params_found = {}
    with open(cpp_file, 'r') as f:
        content = f.read()
    pattern = r"syn_args\.params\[Synapsis::(\w+)\]\s*=\s*([^;]+);"
    matches = re.findall(pattern, content)
    for name, value in matches:
        params_found[name] = value.strip()
    return params_found

def run_neun_model(output_txt_path):
    print("--- Compilando y Ejecutando Neun ---")
    build_dir = os.path.abspath(os.path.join(script_dir, '../../Neun/build'))
    if os.path.exists(output_txt_path):
        os.remove(output_txt_path)
    cmd = (
        'rm -f examples/linskerSynapse && '
        'touch examples/linskerSynapse.cpp && '
        'make && '
        f'cd examples && ./linskerSynapse > "{output_txt_path}"'
    )
    subprocess.run(cmd, cwd=build_dir, shell=True, check=True)

txt_dir_abs = os.path.join(script_dir, TXT_FOLDER)
os.makedirs(txt_dir_abs, exist_ok=True)
full_txt_path = os.path.join(txt_dir_abs, "Neun_Linsker_Output.txt")

run_neun_model(full_txt_path)

# Cargar datos de Neun con Pandas
columns = ['Time', 'V1pre', 'V2pre', 'Vpost', 'i1', 'i2', 'w1', 'w2', 'SUM(W)']
df_neun = pd.read_csv(full_txt_path, sep=r'\s+', names=columns, header=0, engine='c')
df_plot = df_neun.iloc[::1, :].copy()

# =========================================================================
# PARTE 2: EJECUTAR NEURON (PYTHON)
# =========================================================================
print(f"--- Simulando {TIME} ms en NEURON ---")
h.load_file('stdrun.hoc')
h.dt = 0.005

n1 = h.Section(name='n1')
n2 = h.Section(name='n2')
n3 = h.Section(name='n3')

n1.insert('hh')
n2.insert('hh')
n3.insert('hh')

for n in [n1, n2, n3]:
    n.L = 500
    n.diam = 500

syn1 = h.Linsker(n2(0.5))
h.setpointer(n1(0.5)._ref_v, 'vpre', syn1)
syn2 = h.Linsker(n2(0.5))
h.setpointer(n3(0.5)._ref_v, 'vpre', syn2)

syn1.w = 0.0015
syn2.w = 0.001
weights = [syn1.w, syn2.w]

stim1 = h.IClamp(n1(0.5))
stim1.delay = 0
stim1.dur = TIME
stim1.amp = 500 / PA_FLAG

stim2 = h.IClamp(n2(0.5))
stim2.delay = 0
stim2.dur = TIME
stim2.amp = 500 / PA_FLAG

stim3 = h.IClamp(n3(0.5))
stim3.delay = 0
stim3.dur = TIME
stim3.amp = 600 / PA_FLAG

t_vec = h.Vector().record(h._ref_t)
w1_vec = h.Vector().record(syn1._ref_w)
w2_vec = h.Vector().record(syn2._ref_w)
i1_vec = h.Vector().record(syn1._ref_i)
i2_vec = h.Vector().record(syn2._ref_i)

h.finitialize(-65)
syn1.w = 0.0015
syn2.w = 0.001

t_stop = TIME
synapses = [syn1, syn2]
slower = 0

while h.t < t_stop:
    if slower == 25:
        stim1.amp = 0
        slower = 0
    else:
        stim1.amp = 500 / PA_FLAG
        slower += 1

    h.fadvance()
    
    # Normalizar pesos
    w_sum = sum([s.w for s in synapses])
    w_mean = w_sum / len(synapses)
    for s in synapses:
        s.w = s.w - w_mean
        if s.w > W_MAX: s.w = W_MAX
        if s.w < -W_MAX: s.w = -W_MAX

t_np = np.array(t_vec)[SLICE:]
w1_np = np.array(w1_vec)[SLICE:]
w2_np = np.array(w2_vec)[SLICE:]
i1_np = np.array(i1_vec)[SLICE:]
i2_np = np.array(i2_vec)[SLICE:]

# =========================================================================
# PARTE 3: GENERACIÓN DE GRÁFICAS COMPARATIVAS MATPLOTLIB (2x2)
# =========================================================================
print("--- Generando figura 2x2 (PDF) ---")
fig, axs = plt.subplots(2, 2, figsize=(10, 6), sharex='col')

# --- COLUMNA 1: NEUN ---
axs[0, 0].set_title(r'Plasticidad de Linsker en Neun (Implementada)', fontsize=12, fontweight='bold', fontfamily='serif')
axs[0, 0].plot(df_plot['Time'], df_plot['i1'], label=r'$i_1$', color='red')
axs[0, 0].plot(df_plot['Time'], df_plot['i2'], label=r'$i_2$', color='blue')
axs[0, 0].set_ylabel(r'Corriente ($pA$)')
axs[0, 0].legend(loc='upper right')
axs[0, 0].grid(True, alpha=0.3)

axs[1, 0].plot(df_plot['Time'], df_plot['w1'], label=r'$w_1$', color='red')
axs[1, 0].plot(df_plot['Time'], df_plot['w2'], label=r'$w_2$', color='blue')
axs[1, 0].set_ylabel(r'Pesos ($w$)')
axs[1, 0].set_xlabel(r'Tiempo ($ms$)')
axs[1, 0].legend(loc='upper right')
axs[1, 0].grid(True, alpha=0.3)

# --- COLUMNA 2: NEURON ---
axs[0, 1].set_title(r'Plasticidad de Linsker en NEURON (Validación)', fontsize=12, fontweight='bold', fontfamily='serif')
axs[0, 1].plot(t_np, i1_np, label=r'$i_1$', color='red')
axs[0, 1].plot(t_np, i2_np, label=r'$i_2$', color='blue')
label_corriente_neuron = r'Corriente ($nA$)' if PA_FLAG == 1 else r'Corriente ($pA$)'
axs[0, 1].set_ylabel(label_corriente_neuron)
axs[0, 1].legend(loc='upper right')
axs[0, 1].grid(True, alpha=0.3)

axs[1, 1].plot(t_np, w1_np, label=r'$w_1$', color='red')
axs[1, 1].plot(t_np, w2_np, label=r'$w_2$', color='blue')
axs[1, 1].set_ylabel(r'Pesos ($w$)')
axs[1, 1].set_xlabel(r'Tiempo ($ms$)')
axs[1, 1].legend(loc='upper right')
axs[1, 1].grid(True, alpha=0.3)

# Aplicar Zoom
if HABILITAR_ZOOM:
    axs[0, 0].set_xlim(ZOOM_INICIO, ZOOM_FIN)
    axs[0, 1].set_xlim(ZOOM_INICIO, ZOOM_FIN)

plt.tight_layout()

pdf_dir_abs = os.path.join(script_dir, PDF_FOLDER)
os.makedirs(pdf_dir_abs, exist_ok=True)
pdf_path = os.path.join(pdf_dir_abs, f"{FILE_NAME}.pdf")
plt.savefig(pdf_path)

# =========================================================================
# PARTE 4: GENERACIÓN DE HTML INTERACTIVO (BOKEH 2x2)
# =========================================================================
print("--- Generando HTML Interactivo 2x2 ---")
bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
os.makedirs(bokeh_dir_abs, exist_ok=True)
bokeh_path = os.path.join(bokeh_dir_abs, f"{FILE_NAME}.html")
output_file(bokeh_path, title=f"Comparativa Linsker")

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"
W, H = 500, 300

# Lógica del zoom para Bokeh
kwargs_neun = {"title": "Plasticidad de Linsker en Neun (Implementada)", "width": W, "height": H, "tools": TOOLS, "output_backend": "webgl"}
kwargs_neuron = {"title": "Plasticidad de Linsker en NEURON (Validación)", "width": W, "height": H, "tools": TOOLS, "output_backend": "webgl"}

if HABILITAR_ZOOM:
    kwargs_neun["x_range"] = (ZOOM_INICIO, ZOOM_FIN)
    kwargs_neuron["x_range"] = (ZOOM_INICIO, ZOOM_FIN)

# 1. Neun Arriba (Corriente)
p_neun_i = figure(**kwargs_neun)
p_neun_i.line(df_plot['Time'], df_plot['i1'], legend_label="i1", color="red", line_width=1.5)
p_neun_i.line(df_plot['Time'], df_plot['i2'], legend_label="i2", color="blue", line_width=1.5)
p_neun_i.yaxis.axis_label = "Corriente (pA)"

# 2. Neun Abajo (Pesos)
p_neun_w = figure(width=W, height=H, tools=TOOLS, x_range=p_neun_i.x_range, output_backend="webgl")
p_neun_w.line(df_plot['Time'], df_plot['w1'], legend_label="w1", color="red", line_width=2)
p_neun_w.line(df_plot['Time'], df_plot['w2'], legend_label="w2", color="blue", line_width=2)
p_neun_w.xaxis.axis_label = "Tiempo (ms)"
p_neun_w.yaxis.axis_label = "Pesos (w)"

# 3. NEURON Arriba (Corriente)
p_neuron_i = figure(**kwargs_neuron)
p_neuron_i.line(t_np, i1_np, legend_label="i1", color="red", line_width=1.5)
p_neuron_i.line(t_np, i2_np, legend_label="i2", color="blue", line_width=1.5)
p_neuron_i.yaxis.axis_label = "Corriente (nA)" if PA_FLAG == 1 else "Corriente (pA)"

# 4. NEURON Abajo (Pesos)
p_neuron_w = figure(width=W, height=H, tools=TOOLS, x_range=p_neuron_i.x_range, output_backend="webgl")
p_neuron_w.line(t_np, w1_np, legend_label="w1", color="red", line_width=1.5)
p_neuron_w.line(t_np, w2_np, legend_label="w2", color="blue", line_width=1.5)
p_neuron_w.xaxis.axis_label = "Tiempo (ms)"
p_neuron_w.yaxis.axis_label = "Pesos (w)"

# Ocultar leyendas al clickar y forzar fuente tipo LaTeX
for p in [p_neun_i, p_neun_w, p_neuron_i, p_neuron_w]: 
    p.legend.click_policy = "hide"
    if p.title:
        p.title.text_font = "serif"
        p.title.text_font_size = "13pt"
        p.title.text_font_style = "bold"

# Crear grid (Matriz de 2x2)
layout = gridplot([[p_neun_i, p_neuron_i], [p_neun_w, p_neuron_w]])
save(layout)

print(f" -> PDF guardado en: {pdf_path}")
print(f" -> HTML guardado en: {bokeh_path}")