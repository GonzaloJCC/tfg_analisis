import os
import numpy as np
import matplotlib.pyplot as plt
from neuron import h

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column



# Control del Zoom Inicial
HABILITAR_ZOOM = False
ZOOM_INICIO = 50
ZOOM_FIN = 150

# Carpetas de salida
PDF_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"
FILE_NAME = "Simulacion_NEURON_Linsker"

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

SLICE = 10 # ignore the first n values for image clarity
W_MAX = 2.0
TIME = 10000 # ms
# PA_FLAG = 1000 # For pA
PA_FLAG = 1 # For nA

h.load_file('stdrun.hoc')
h.dt = 0.005 # Equivalente a step del cpp ---- const double step = 0.005

n1 = h.Section(name='n1') # Neurona 1
n2 = h.Section(name='n2') # Neurona 2
n3 = h.Section(name='n3') # Neurona 3

n1.insert('hh') # Hodgkin-Huxley
n2.insert('hh')
n3.insert('hh')

for n in [n1, n2, n3]:
    n.L = 500     # Longitud en micrómetros -> sacado del cpp al definir las neuronas 1 * 7.854e-3; <- diametro
    n.diam = 500  # Diámetro en micrómetros

syn1 = h.Linsker(n2(0.5)) # Sinapsis 1, se llama Linsker porque en el .mod se llama así
h.setpointer(n1(0.5)._ref_v, 'vpre', syn1)

syn2 = h.Linsker(n2(0.5))
h.setpointer(n3(0.5)._ref_v, 'vpre', syn2)

syn1.w = 0.0015 # Inicializar unos pesos
syn2.w = 0.001

weights = [syn1.w, syn2.w]

stim1 = h.IClamp(n1(0.5)) # Estímulo en la neurona 1 --- h1.add_synaptic_input(0.5);
stim1.delay = 0 # Inicio del estímulo
stim1.dur = TIME # Duración del estímulo
stim1.amp = 500 / PA_FLAG  # 500 nA # Amplitud del estímulo

stim2 = h.IClamp(n2(0.5)) # Estímulo en la neurona 2 --- h2.add_synaptic_input(0.5);
stim2.delay = 0 # Inicio del estímulo
stim2.dur = TIME # Duración del estímulo
stim2.amp = 500 / PA_FLAG  # 500 nA # Amplitud del estímulo

stim3 = h.IClamp(n3(0.5)) # Estímulo en la neurona 3 --- h3.add_synaptic_input(0.5); <- mitad de la neurona
stim3.delay = 0 # Inicio del estímulo
stim3.dur = TIME # Duración del estímulo --- for time; ...
stim3.amp = 600 / PA_FLAG  # 600 nA # Amplitud del estímulo

t_vec = h.Vector().record(h._ref_t)
w1_vec = h.Vector().record(syn1._ref_w)
w2_vec = h.Vector().record(syn2._ref_w)
i1_vec = h.Vector().record(syn1._ref_i)
i2_vec = h.Vector().record(syn2._ref_i)

h.finitialize(-65)

# Definir los pesos de nuevo para que no se sobreescriban
syn1.w = 0.0015 
syn2.w = 0.001

t_stop = TIME
synapses = [syn1, syn2]
slower = 0 # 

print(f"Simulando {TIME} ms en NEURON (Modelo de Linsker)...")
while h.t < t_stop:
    if slower == 25:
        stim1.amp = 0
        slower = 0
    else:
        stim1.amp = 500 / PA_FLAG  # 500 nA
        slower += 1

    h.fadvance()
    
    # Nomalizar 
    w_sum = sum([s.w for s in synapses])
    n = len(synapses)
    w_mean = w_sum / n
    
    for s in synapses:
        s.w = s.w - w_mean
        
        if s.w > W_MAX: s.w = W_MAX
        if s.w < -W_MAX: s.w = -W_MAX

print("¡Simulación completada!")

t_np = np.array(t_vec)[SLICE:]
w1_np = np.array(w1_vec)[SLICE:]
w2_np = np.array(w2_vec)[SLICE:]
i1_np = np.array(i1_vec)[SLICE:]
i2_np = np.array(i2_vec)[SLICE:]

# GENERACIÓN DE GRÁFICAS (PDF y HTML)
script_dir = os.path.dirname(os.path.abspath(__file__))

# PDF
print("Generando PDF...")
fig, axs = plt.subplots(2, 1, figsize=(6, 5), sharex=True)  

axs[0].plot(t_np, i1_np, label=r'$i_1$', color='red')
axs[0].plot(t_np, i2_np, label=r'$i_2$', color='blue')
label_corriente = r'Corriente ($nA$)' if PA_FLAG == 1 else r'Corriente ($pA$)'
axs[0].set_ylabel(label_corriente) 
axs[0].legend(loc='upper right')
axs[0].grid(True, alpha=0.3)

axs[1].plot(t_np, w1_np, label=r'$w_1$', color='red')
axs[1].plot(t_np, w2_np, label=r'$w_2$', color='blue')
axs[1].set_ylabel(r'Pesos ($w$)')
axs[1].set_xlabel(r'Tiempo ($ms$)')
axs[1].legend(loc='upper right')
axs[1].grid(True, alpha=0.3)

if HABILITAR_ZOOM:
    axs[0].set_xlim(ZOOM_INICIO, ZOOM_FIN)

plt.tight_layout()

# Guardar PDF dinámicamente según la unidad de corriente
pdf_dir_abs = os.path.join(script_dir, PDF_FOLDER)
os.makedirs(pdf_dir_abs, exist_ok=True)
pdf_name = f"{FILE_NAME}_nA.pdf" if PA_FLAG == 1 else f"{FILE_NAME}_pA.pdf"
pdf_path = os.path.join(pdf_dir_abs, pdf_name)
plt.savefig(pdf_path)

# HTML
print("Generando HTML Interactivo...")
bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
os.makedirs(bokeh_dir_abs, exist_ok=True)
bokeh_path = os.path.join(bokeh_dir_abs, f"{FILE_NAME}.html")

output_file(bokeh_path, title=f"NEURON Linsker: {FILE_NAME}")

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

fig_kws = {"title": f"Resultados Linsker - {FILE_NAME}", "width": 900, "height": 250, "tools": TOOLS, "output_backend": "webgl"}
if HABILITAR_ZOOM:
    fig_kws["x_range"] = (ZOOM_INICIO, ZOOM_FIN)

p1 = figure(**fig_kws)
p1.line(t_np, i1_np, legend_label="i1", color="red", line_width=2)
p1.line(t_np, i2_np, legend_label="i2", color="blue", line_width=2)
p1.yaxis.axis_label = "Corriente (nA)" if PA_FLAG == 1 else "Corriente (pA)"
p1.legend.click_policy = "hide"

p2 = figure(width=900, height=250, tools=TOOLS, x_range=p1.x_range, output_backend="webgl")
p2.line(t_np, w1_np, legend_label="w1", color="red", line_width=1.5)
p2.line(t_np, w2_np, legend_label="w2", color="blue", line_width=1.5)
p2.xaxis.axis_label = "Tiempo (ms)"
p2.yaxis.axis_label = "Pesos (w)"
p2.legend.click_policy = "hide"

layout = column(p1, p2)
save(layout)

print(f" -> PDF guardado en: {pdf_path}")
print(f" -> HTML guardado en: {bokeh_path}")
