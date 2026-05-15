import os
import numpy as np
import matplotlib.pyplot as plt
import nest

from bokeh.plotting import figure, output_file, save
from bokeh.layouts import column
from bokeh.models import Range1d

# =========================================================================
# CONFIGURACIÓN GENERAL Y LATEX
# =========================================================================
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

# Control del Zoom Temporal (Intervalo de 50 a 150 ms)
HABILITAR_ZOOM = True
ZOOM_INICIO = 50
ZOOM_FIN = 150

# Carpetas de salida
PDF_FOLDER = "Resultados_PDF"
BOKEH_FOLDER = "Resultados_HTML"
FILE_NAME = "NEST_STDP_Zoom"

TIME = 1000.0  # ms 
RESOLUTION = 0.005 # ms
THRESHOLD_VAL = -54.0

script_dir = os.path.dirname(os.path.abspath(__file__))

# =========================================================================
# 1. CONFIGURACIÓN DE NEST
# =========================================================================
print("\n--- Iniciando simulación en NEST Simulator ---")
nest.ResetKernel()
nest.resolution = RESOLUTION

n_pre1 = nest.Create("hh_cond_exp_traub")
n_post = nest.Create("hh_cond_exp_traub")
n_pre2 = nest.Create("hh_cond_exp_traub")

nest.SetStatus(n_pre1, {"V_m": -75.0, "I_e": 600.0})
nest.SetStatus(n_post, {"V_m": -70.0, "I_e": 500.0})
nest.SetStatus(n_pre2, {"V_m": -85.0, "I_e": 500.0})

wr1 = nest.Create("weight_recorder")
wr2 = nest.Create("weight_recorder")

stdp_params = {
    "Wmax": 1.0,
    "lambda": 0.005,
    "alpha": 1.05,
    "tau_plus": 20.0
}

nest.CopyModel("stdp_synapse", "stdp_syn1", {"weight_recorder": wr1[0], **stdp_params})
nest.CopyModel("stdp_synapse", "stdp_syn2", {"weight_recorder": wr2[0], **stdp_params})

nest.Connect(n_pre1, n_post, syn_spec={"synapse_model": "stdp_syn1", "weight": 0.0052, "delay": RESOLUTION})
nest.Connect(n_pre2, n_post, syn_spec={"synapse_model": "stdp_syn2", "weight": 0.0050, "delay": RESOLUTION})

multimeter = nest.Create("multimeter", params={"record_from": ["V_m"], "interval": RESOLUTION})
nest.Connect(multimeter, n_pre1 + n_post + n_pre2)

# =========================================================================
# 2. EJECUCIÓN
# =========================================================================
print(f"Simulando {TIME} ms...")
nest.Simulate(TIME)

events = nest.GetStatus(multimeter)[0]["events"]
t_v = events["times"][events["senders"] == n_pre1[0]]
v_pre1 = events["V_m"][events["senders"] == n_pre1[0]]
v_pre2 = events["V_m"][events["senders"] == n_pre2[0]]
v_post = events["V_m"][events["senders"] == n_post[0]]

ev_w1 = nest.GetStatus(wr1)[0]["events"]
t_w1 = np.concatenate(([0.0], ev_w1["times"], [TIME]))
w1 = np.concatenate(([0.0052], ev_w1["weights"], [ev_w1["weights"][-1] if len(ev_w1["weights"]) > 0 else 0.0052]))

ev_w2 = nest.GetStatus(wr2)[0]["events"]
t_w2 = np.concatenate(([0.0], ev_w2["times"], [TIME]))
w2 = np.concatenate(([0.0050], ev_w2["weights"], [ev_w2["weights"][-1] if len(ev_w2["weights"]) > 0 else 0.0050]))

# =========================================================================
# 3. GENERACIÓN PDF (MATPLOTLIB)
# =========================================================================
print("Generando PDF...")
fig, axs = plt.subplots(4, 1, figsize=(8, 10), sharex=True)

# SUBPLOT 1: Voltajes Sinapsis 1
axs[0].plot(t_v, v_pre1, label='V_pre1', color='red')
axs[0].plot(t_v, v_post, label='V_post', color='green')
axs[0].axhline(THRESHOLD_VAL, color='gray', linestyle='--', alpha=0.5, label='Umbral')
axs[0].set_ylabel(r'Voltaje ($mV$)')
axs[0].set_title("Interacción Sinapsis 1 (Pre1 y Post)", fontsize=10, loc='left')
axs[0].legend(loc='upper right')
axs[0].grid(True, alpha=0.3)

# SUBPLOT 2: Conductancia Sinapsis 1 (step fino y con zoom en Y)
axs[1].step(t_w1, w1, label='g1', color='darkred', where='post', linewidth=1)
axs[1].set_ylabel(r'Cond. ($pS$)')
axs[1].set_ylim(0.0, 0.1)
axs[1].legend(loc='upper right')
axs[1].grid(True, alpha=0.3)

# SUBPLOT 3: Voltajes Sinapsis 2
axs[2].plot(t_v, v_pre2, label='V_pre2', color='blue')
axs[2].plot(t_v, v_post, label='V_post', color='green')
axs[2].axhline(THRESHOLD_VAL, color='gray', linestyle='--', alpha=0.5, label='Umbral')
axs[2].set_ylabel(r'Voltaje ($mV$)')
axs[2].set_title("Interacción Sinapsis 2 (Pre2 y Post)", fontsize=10, loc='left')
axs[2].legend(loc='upper right')
axs[2].grid(True, alpha=0.3)

# SUBPLOT 4: Conductancia Sinapsis 2 (step fino y con zoom en Y)
axs[3].step(t_w2, w2, label='g2', color='darkblue', where='post', linewidth=1)
axs[3].set_ylabel(r'Cond. ($pS$)')
axs[3].set_xlabel(r'Tiempo (ms)')
axs[3].set_ylim(0.0, 0.1)
axs[3].legend(loc='upper right')
axs[3].grid(True, alpha=0.3)

if HABILITAR_ZOOM:
    axs[0].set_xlim(ZOOM_INICIO, ZOOM_FIN)

plt.tight_layout()

pdf_dir_abs = os.path.join(script_dir, PDF_FOLDER)
os.makedirs(pdf_dir_abs, exist_ok=True)
pdf_path = os.path.join(pdf_dir_abs, f"{FILE_NAME}.pdf")
plt.savefig(pdf_path)

# =========================================================================
# 4. GENERACIÓN HTML (BOKEH)
# =========================================================================
print("Generando HTML...")
bokeh_dir_abs = os.path.join(script_dir, BOKEH_FOLDER)
os.makedirs(bokeh_dir_abs, exist_ok=True)
bokeh_path = os.path.join(bokeh_dir_abs, f"{FILE_NAME}.html")
output_file(bokeh_path, title=f"NEST STDP Zoom")

TOOLS = "pan,wheel_zoom,box_zoom,reset,save,crosshair"

# P1: Voltajes S1 
if HABILITAR_ZOOM:
    p1 = figure(title="Interacción Sinapsis 1 (Pre1 y Post)", width=900, height=250, tools=TOOLS, x_range=(ZOOM_INICIO, ZOOM_FIN))
else:
    p1 = figure(title="Interacción Sinapsis 1 (Pre1 y Post)", width=900, height=250, tools=TOOLS)

p1.line(t_v, v_pre1, legend_label="V_pre1", color="red", line_width=1.5)
p1.line(t_v, v_post, legend_label="V_post", color="green", line_width=1.5)
p1.line(t_v, [THRESHOLD_VAL]*len(t_v), legend_label="Umbral", color="gray", line_dash="dashed", alpha=0.5)
p1.yaxis.axis_label = "Voltaje (mV)"
p1.legend.click_policy = "hide"

# P2: Cond S1 (step fino y zoom en Y)
p2 = figure(width=900, height=200, tools=TOOLS, x_range=p1.x_range, y_range=Range1d(0.0, 0.1))
p2.step(t_w1, w1, legend_label="g1", color="darkred", line_width=1, mode="after")
p2.yaxis.axis_label = "Cond. (pS)"

# P3: Voltajes S2 
p3 = figure(title="Interacción Sinapsis 2 (Pre2 y Post)", width=900, height=250, tools=TOOLS, x_range=p1.x_range)
p3.line(t_v, v_pre2, legend_label="V_pre2", color="blue", line_width=1.5)
p3.line(t_v, v_post, legend_label="V_post", color="green", line_width=1.5)
p3.line(t_v, [THRESHOLD_VAL]*len(t_v), legend_label="Umbral", color="gray", line_dash="dashed", alpha=0.5)
p3.yaxis.axis_label = "Voltaje (mV)"
p3.legend.click_policy = "hide"

# P4: Cond S2 (step fino y zoom en Y)
p4 = figure(width=900, height=200, tools=TOOLS, x_range=p1.x_range, y_range=Range1d(0.0, 0.1))
p4.step(t_w2, w2, legend_label="g2", color="darkblue", line_width=1, mode="after")
p4.xaxis.axis_label = "Tiempo (ms)"
p4.yaxis.axis_label = "Cond. (pS)"

layout = column(p1, p2, p3, p4)
save(layout)

print(f" -> PDF: {pdf_path}\n -> HTML: {bokeh_path}")
