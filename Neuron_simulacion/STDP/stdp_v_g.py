import os
import numpy as np
import matplotlib.pyplot as plt
from neuron import h

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column

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

# Control del Zoom Inicial
HABILITAR_ZOOM = True
# HABILITAR_ZOOM = False
ZOOM_INICIO = 50
ZOOM_FIN = 150

# Carpetas de salida
PDF_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"
FILE_NAME = "STDP_v_g"


TIME = 10000 
SLICE = 1 # Submuestreo para las gráficas (1 de cada 10 puntos)


h.load_file('stdrun.hoc')
h.dt = 0.005 # Equivalente a 'step' del C++

n1 = h.Section(name='n1') # Pre-sináptica 1
n2 = h.Section(name='n2') # Post-sináptica
n3 = h.Section(name='n3') # Pre-sináptica 2

n1.insert('hh')
n2.insert('hh')
n3.insert('hh')

for n in [n1, n2, n3]:
    n.L = 500     # Longitud en micrómetros -> sacado del cpp al definir las neuronas 1 * 7.854e-3; <- diametro
    n.diam = 500  # Diámetro en micrómetros

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


t_vec = h.Vector().record(h._ref_t)
vpre1_vec = h.Vector().record(n1(0.5)._ref_v)
vpost_vec = h.Vector().record(n2(0.5)._ref_v)
vpre2_vec = h.Vector().record(n3(0.5)._ref_v)
g1_vec = h.Vector().record(syn1._ref_g)
g2_vec = h.Vector().record(syn2._ref_g)
i1_vec = h.Vector().record(syn1._ref_i)
i2_vec = h.Vector().record(syn2._ref_i)

h.finitialize(-65)
n1(0.5).v = -75
n3(0.5).v = -85
n2(0.5).v = -70
h.finitialize() 

syn1.g = 0.0052
syn2.g = 0.005

print(f"Simulando {TIME} ms en NEURON...")
h.continuerun(TIME)
print("Fin de la simulación")

# Extraer datos a Numpy y aplicar submuestreo (SLICE)
t_np = np.array(t_vec)[SLICE:]
vpre1_np = np.array(vpre1_vec)[SLICE:]
vpost_np = np.array(vpost_vec)[SLICE:]
vpre2_np = np.array(vpre2_vec)[SLICE:]
g1_np = np.array(g1_vec)[SLICE:]
g2_np = np.array(g2_vec)[SLICE:]

# Invertir el signo de la corriente para que la excitatoria sea positiva (convención visual)
i1_np = -np.array(i1_vec)[SLICE:]
i2_np = -np.array(i2_vec)[SLICE:]


# Plot
script_dir = os.path.dirname(os.path.abspath(__file__))
threshold_val = -54.0 # Umbral para las gráficas

# PDF ------------------------------------------------------------------------
print("Generando PDF")
fig, axs = plt.subplots(4, 1, figsize=(8, 10), sharex=True)

# Plot 1: Voltajes Sinapsis 1
axs[0].plot(t_np, vpre1_np, label='V_pre1', color='red')
axs[0].plot(t_np, vpost_np, label='V_post', color='green')
axs[0].axhline(threshold_val, color='gray', linestyle='--', alpha=0.5, label='Umbral')
axs[0].set_ylabel(r'Voltaje ($mV$)')
axs[0].set_title("Interacción Sinapsis 1 (Pre1 y Post)", fontsize=10, loc='left')
axs[0].legend(loc='upper right')
axs[0].grid(True, alpha=0.3)

# Plot 2: Conductancia Sinapsis 1
axs[1].plot(t_np, g1_np, label='g1', color='red')
axs[1].set_ylabel(r'Cond. ($pS$)')
axs[1].legend(loc='upper right')
axs[1].grid(True, alpha=0.3)

# Plot 3: Voltajes Sinapsis 2
axs[2].plot(t_np, vpre2_np, label='V_pre2', color='blue')
axs[2].plot(t_np, vpost_np, label='V_post', color='green')
axs[2].axhline(threshold_val, color='gray', linestyle='--', alpha=0.5, label='Umbral')
axs[2].set_ylabel(r'Voltaje ($mV$)')
axs[2].set_title("Interacción Sinapsis 2 (Pre2 y Post)", fontsize=10, loc='left')
axs[2].legend(loc='upper right')
axs[2].grid(True, alpha=0.3)

# Plot 4: Conductancia Sinapsis 2
axs[3].plot(t_np, g2_np, label='g2', color='blue')
axs[3].set_ylabel(r'Cond. ($pS$)')
axs[3].set_xlabel(r'Tiempo (ms)')
axs[3].legend(loc='upper right')
axs[3].grid(True, alpha=0.3)

# Zoom condicional
if HABILITAR_ZOOM:
    axs[0].set_xlim(ZOOM_INICIO, ZOOM_FIN)

plt.tight_layout()

# Guardar PDF
pdf_dir_abs = os.path.join(script_dir, PDF_FOLDER)
os.makedirs(pdf_dir_abs, exist_ok=True)
pdf_path = os.path.join(pdf_dir_abs, f"{FILE_NAME}.pdf")
plt.savefig(pdf_path)

# HTML -----------------------------------------------------------------------
print("Generando HTML Interactivo...")
bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
os.makedirs(bokeh_dir_abs, exist_ok=True)
bokeh_path = os.path.join(bokeh_dir_abs, f"{FILE_NAME}.html")

output_file(bokeh_path, title=f"NEURON STDP: {FILE_NAME}")

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

# Configurar el rango X dependiendo de si el zoom está habilitado o no
fig_kws = {"title": f"Interacción Sinapsis 1 (Pre1 y Post) - {FILE_NAME}", "width": 900, "height": 250, "tools": TOOLS, "output_backend": "webgl"}
if HABILITAR_ZOOM:
    fig_kws["x_range"] = (ZOOM_INICIO, ZOOM_FIN)

# Plot 1: Voltajes Sinapsis 1
p1 = figure(**fig_kws)
p1.line(t_np, vpre1_np, legend_label="V_pre1", color="red", line_width=1.5)
p1.line(t_np, vpost_np, legend_label="V_post", color="green", line_width=1.5)
p1.line(t_np, [threshold_val]*len(t_np), legend_label="Umbral", color="gray", line_dash="dashed", alpha=0.5)
p1.yaxis.axis_label = "Voltaje (mV)"
p1.legend.click_policy = "hide"

# Plot 2: Conductancia Sinapsis 1
p2 = figure(width=900, height=200, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p2.line(t_np, g1_np, legend_label="g1", color="red", line_width=2)
p2.yaxis.axis_label = "Cond. (pS)"

# Plot 3: Voltajes Sinapsis 2
p3 = figure(title="Interacción Sinapsis 2 (Pre2 y Post)", width=900, height=250, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p3.line(t_np, vpre2_np, legend_label="V_pre2", color="blue", line_width=1.5)
p3.line(t_np, vpost_np, legend_label="V_post", color="green", line_width=1.5)
p3.line(t_np, [threshold_val]*len(t_np), legend_label="Umbral", color="gray", line_dash="dashed", alpha=0.5)
p3.yaxis.axis_label = "Voltaje (mV)"
p3.legend.click_policy = "hide"

# Plot 4: Conductancia Sinapsis 2
p4 = figure(width=900, height=200, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p4.line(t_np, g2_np, legend_label="g2", color="blue", line_width=2)
p4.xaxis.axis_label = "Tiempo (ms)"
p4.yaxis.axis_label = "Cond. (pS)"

# Agrupar y guardar
layout = column(p1, p2, p3, p4)
save(layout)

print(f" -> PDF guardado en: {pdf_path}")
print(f" -> HTML guardado en: {bokeh_path}")