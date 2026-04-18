NEURON {
    POINT_PROCESS Linsker
    POINTER vpre
    RANGE w, i
    RANGE eta, xo, yo, k1
    NONSPECIFIC_CURRENT i
}

UNITS {
    (nA) = (nanoamp)
    (mV) = (millivolt)
    (uS) = (microsiemens)
}

CONSTANT {
    W_MAX = 2.0
}

PARAMETER {
    eta = 0.00001
    xo = -65.0 (mV)
    yo = -65.0 (mV)
    k1 = -500.0
}

ASSIGNED {
    v (mV)
    vpost (mV)
    vpre (mV)
    i (nA)
}

STATE {
    w
}

INITIAL {
    w = 0.5
}

BREAKPOINT {
    SOLVE state METHOD cnexp
    vpost = v

    i = w * vpost

}

DERIVATIVE state {
    vpost = v
    w' = eta * ((vpre - xo) * (vpost - yo) + k1) : derivada respecto al tiempo de w (dW/dt)

    if (w > W_MAX) { w = W_MAX }
    if (w < -W_MAX) { w = -W_MAX }
}
