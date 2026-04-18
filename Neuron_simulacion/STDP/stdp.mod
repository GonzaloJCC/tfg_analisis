NEURON {
    POINT_PROCESS STDP
    POINTER vpre
    RANGE g, i, s
    RANGE A_plus, A_minus, tau_plus, tau_minus, g_max, g_min, E_syn, tau_syn, v_thresh
    NONSPECIFIC_CURRENT i
}

UNITS {
    (nA) = (nanoamp)
    (mV) = (millivolt)
}

PARAMETER {
    A_plus = 0.005
    A_minus = 0.00525
    tau_plus = 20 (ms)
    tau_minus = 20 (ms)
    g_max = 1.0
    g_min = 0.0
    E_syn = 0 (mV)
    tau_syn = 5 (ms)
    v_thresh = -54 (mV)
}

ASSIGNED {
    v (mV)
    vpre (mV)
    i (nA)
    g
    s
    last_t (ms)
    last_spike_pre (ms)
    last_spike_post (ms)
    vpre_old (mV)
    vpost_old (mV)
}

INITIAL {
    s = 0
    g = 0.005
    last_t = -1
    last_spike_pre = -999  
    last_spike_post = -999
    vpre_old = -65
    vpost_old = -65
}

BREAKPOINT {
    LOCAL delta_t, f_delta_t
    
    if (t > last_t) {
        
        s = s * exp(-dt / tau_syn)

        if (vpre >= v_thresh && vpre_old < v_thresh) {
            last_spike_pre = t
            s = 1.0 
            
            delta_t = last_spike_pre - last_spike_post 

            if (delta_t > 0) {
                f_delta_t = -A_minus * exp(-delta_t / tau_minus)
                g = g + f_delta_t 
            }
        }

        if (v >= v_thresh && vpost_old < v_thresh) {
            last_spike_post = t
            
            delta_t = last_spike_pre - last_spike_post 

            if (delta_t < 0) {
                f_delta_t = A_plus * exp(delta_t / tau_plus)
                g = g + f_delta_t 
            }
        }

        if (g > g_max) { g = g_max }
        
        if (g < g_min) { g = g_min }

        vpre_old = vpre
        vpost_old = v
        last_t = t
    }

    i = g * s * (v - E_syn)
}
