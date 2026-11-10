"""DC bias calculations for a BJT common-emitter voltage-divider bias circuit.

Pure engineering logic: this module must not import Flask or know about HTTP.
All values are SI units (volts, ohms, amps); beta is dimensionless.
"""

import math


def parse_resistance(text: str) -> float:
    """Parse a resistance string in ohms. Accepts an optional k/K suffix."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("กรุณากรอกค่านี้")
    value_text = raw
    multiplier = 1.0
    if value_text[-1] in "kK":
        multiplier = 1000.0
        value_text = value_text[:-1].strip()
    try:
        value = float(value_text)
    except (TypeError, ValueError) as exc:
        raise ValueError("ต้องเป็นตัวเลขที่จำกัด") from exc
    if not math.isfinite(value):
        raise ValueError("ต้องเป็นตัวเลขที่จำกัด")
    return value * multiplier


def validate_inputs(values: dict[str, str]) -> dict[str, str]:
    """Validate raw form values; return a mapping of field to Thai error message."""
    errors: dict[str, str] = {}
    parsed: dict[str, float] = {}

    def raw(field: str) -> str:
        return str((values or {}).get(field, "")).strip()

    for field in ("r1", "r2", "rc", "re"):
        try:
            parsed[field] = parse_resistance(raw(field))
        except ValueError as exc:
            errors[field] = str(exc)

    for field in ("vcc", "beta", "vbe"):
        value_text = raw(field)
        if not value_text:
            errors[field] = "กรุณากรอกค่านี้"
            continue
        try:
            value = float(value_text)
        except (TypeError, ValueError):
            errors[field] = "ต้องเป็นตัวเลขที่จำกัด"
            continue
        if not math.isfinite(value):
            errors[field] = "ต้องเป็นตัวเลขที่จำกัด"
            continue
        parsed[field] = value

    if "vcc" in parsed and parsed["vcc"] <= 0:
        errors["vcc"] = "ต้องมากกว่า 0"

    for field in ("r1", "r2", "rc"):
        if field in parsed and parsed[field] <= 0:
            errors[field] = "ต้องมากกว่า 0"

    if "re" in parsed and parsed["re"] < 0:
        errors["re"] = "ต้องไม่ติดลบ"

    if "beta" in parsed and parsed["beta"] <= 0:
        errors["beta"] = "ต้องมากกว่า 0"

    if "vbe" in parsed and "vcc" in parsed:
        if parsed["vbe"] <= 0 or parsed["vbe"] >= parsed["vcc"]:
            errors["vbe"] = "ต้องอยู่ระหว่าง 0 กับ VCC"

    return errors

def dc_operating_point(vcc, r1, r2, rc, re, beta, vbe, vce_sat=0.2):
    """Return the DC operating point of a voltage-divider bias circuit.

    Direct callers must keep denominators non-zero. Callers should validate
    input via `validate_inputs` first; this guard only converts a cryptic
    ZeroDivisionError into a clear ValueError.
    """
    if r1 + r2 == 0:
        raise ValueError("R1 + R2 ต้องมากกว่า 0")
    if rc + re == 0:
        raise ValueError("RC + RE ต้องมากกว่า 0")

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
