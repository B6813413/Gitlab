"""DC bias calculations for a BJT common-emitter voltage-divider bias circuit.

Pure engineering logic: this module must not import Flask or know about HTTP.
All values are SI units (volts, ohms, amps); beta is dimensionless.
"""


def dc_operating_point(vcc, r1, r2, rc, re, beta, vbe, vce_sat=0.2):
    """Return the DC operating point of a voltage-divider bias circuit."""
    vth = vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)
    ib = (vth - vbe) / (rth + (beta + 1) * re)
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    if ib <= 0:
        region = "cutoff"
    elif vce < vce_sat:
        region = "saturation"
    else:
        region = "active"
    ic_sat = (vcc - vce_sat) / (rc + re)
    return {
        "vth": vth,
        "rth": rth,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "ve": ve,
        "vb": vb,
        "vc": vc,
        "vce": vce,
        "region": region,
        "ic_sat": ic_sat,
    }
