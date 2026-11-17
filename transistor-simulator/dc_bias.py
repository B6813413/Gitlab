"""DC bias calculations for BJT common-emitter bias circuits.

Pure engineering logic: this module must not import Flask or know about HTTP.
All values are SI units (volts, ohms, amps); beta is dimensionless.

Supported modes (selected via `compute_bias`):
  - voltage_divider: VTH/RTH Thevenin input to base  (unchanged Lab 2 function)
  - fixed:           RB from VCC to Base, Emitter tied to ground (VE = 0)
  - emitter:         RB from VCC to Base, RE from Emitter to ground
"""

import math

VCE_SAT = 0.2  # V, boundary below which Forward-Active model is not valid


def parse_resistance(text: str, unit: str = "ohm") -> float:
    """Parse a resistance string in ohms.

    Accepted units: "ohm" (default) or "kohm" (multiply by 1000).
    A trailing "k"/"K" suffix in the value overrides the unit (100k == 100 * kΩ).
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("กรุณากรอกค่านี้")
    multiplier = 1.0
    if str(unit or "ohm").strip().lower() in ("kohm", "k"):
        multiplier = 1000.0
    if raw and raw[-1] in "kK":
        multiplier = 1000.0
        raw = raw[:-1].strip()
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("ต้องเป็นตัวเลขที่จำกัด") from exc
    if not math.isfinite(value):
        raise ValueError("ต้องเป็นตัวเลขที่จำกัด")
    return value * multiplier


def validate_inputs(values: dict, mode: str = "voltage_divider") -> dict:
    """Validate raw form values for the selected bias mode.

    Returns a mapping of field -> Thai error message (empty when valid).
    Only fields required by the chosen mode are validated, per Lab 03:
    "ตรวจเฉพาะช่องที่จำเป็นของโหมดนั้น".
    """
    errors: dict[str, str] = {}
    parsed: dict[str, float] = {}

    def raw(field: str) -> str:
        return str((values or {}).get(field, "")).strip()

    # ---- Plain-number common inputs (no unit suffix) ----
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

    if "beta" in parsed and parsed["beta"] <= 0:
        errors["beta"] = "ต้องมากกว่า 0"

    if "vbe" in parsed and "vcc" in parsed:
        if parsed["vbe"] <= 0 or parsed["vbe"] >= parsed["vcc"]:
            errors["vbe"] = "ต้องอยู่ระหว่าง 0 กับ VCC"

    # ---- Resistance inputs (accept kohm/ohm unit or k suffix) ----
    def _parse_res_field(field: str):
        unit = str((values or {}).get(f"{field}_unit", "ohm")).strip().lower()
        try:
            parsed[field] = parse_resistance(raw(field), unit)
        except ValueError as exc:
            errors[field] = str(exc)

    # RC required by every mode
    _parse_res_field("rc")
    if "rc" in parsed and parsed["rc"] <= 0:
        errors["rc"] = "ต้องมากกว่า 0"

    # ---- Mode-specific inputs ----
    if mode == "voltage_divider":
        _parse_res_field("r1")
        _parse_res_field("r2")
        _parse_res_field("re")
        for field in ("r1", "r2"):
            if field in parsed and parsed[field] <= 0:
                errors[field] = "ต้องมากกว่า 0"
        if "re" in parsed and parsed["re"] < 0:
            errors["re"] = "ต้องไม่ติดลบ"

    elif mode == "fixed":
        _parse_res_field("rb")
        if "rb" in parsed and parsed["rb"] <= 0:
            errors["rb"] = "ต้องมากกว่า 0"

    elif mode == "emitter":
        _parse_res_field("rb")
        _parse_res_field("re")
        if "rb" in parsed and parsed["rb"] <= 0:
            errors["rb"] = "ต้องมากกว่า 0"
        if "re" in parsed and parsed["re"] < 0:
            errors["re"] = "ต้องไม่ติดลบ"

    else:
        errors["mode"] = f"โหมดวงจร '{mode}' ไม่รู้จัก กรุณาเลือกโหมดที่ถูกต้อง"

    return errors


def _region_and_warning(ib_a: float, vce_v: float) -> tuple:
    """Return (region, warning) for the Forward-Active validity check."""
    if ib_a <= 0:
        return (
            "cutoff",
            "คำนวณได้ IB <= 0: แบบจำลอง Forward Active อาจใช้ไม่ได้ "
            "(ตรวจสอบขอบเขต Cutoff / Saturation)",
        )
    if vce_v <= VCE_SAT:
        return (
            "saturation",
            f"คำนวณได้ VCE = {vce_v:.4f} V (<= {VCE_SAT} V): "
            "แบบจำลอง Forward Active อาจใช้ไม่ได้ "
            "(ตรวจสอบขอบเขต Saturation)",
        )
    return ("active", None)


def dc_operating_point(vcc, r1, r2, rc, re, beta, vbe, vce_sat=0.2):
    """Return the DC operating point of a voltage-divider bias circuit.

    Unchanged from Lab 2. Direct callers must keep denominators non-zero.
    Callers should validate input via `validate_inputs` first.
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
    region, warning = _region_and_warning(ib, vce)
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
        "warning": warning,
    }


def fixed_bias(vcc, rc, beta, vbe, rb):
    """Fixed Bias (แหล่งจ่ายเดียว).

    RB ต่อจาก VCC ไป Base, Emitter ต่อลงกราวด์โดยตรง (VE = 0).
    IB = (VCC - VBE) / RB
    """
    ib = (vcc - vbe) / rb
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = 0.0  # Fixed bias: emitter tied directly to ground
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    region, warning = _region_and_warning(ib, vce)
    ic_sat = (vcc - VCE_SAT) / rc
    return {
        "mode": "fixed",
        "vth": None,
        "rth": None,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "ve": ve,
        "vb": vb,
        "vc": vc,
        "vce": vce,
        "region": region,
        "ic_sat": ic_sat,
        "warning": warning,
    }


def emitter_bias(vcc, rc, beta, vbe, rb, re_):
    """Emitter Bias (แหล่งจ่ายเดียว).

    RB ต่อจาก VCC ไป Base, RE ต่อจาก Emitter ลงกราวด์.
    IB = (VCC - VBE) / [RB + (beta + 1) * RE]
    """
    ib = (vcc - vbe) / (rb + (beta + 1.0) * re_)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re_
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    region, warning = _region_and_warning(ib, vce)
    ic_sat = (vcc - VCE_SAT) / (rc + re_)
    return {
        "mode": "emitter",
        "vth": None,
        "rth": None,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "ve": ve,
        "vb": vb,
        "vc": vc,
        "vce": vce,
        "region": region,
        "ic_sat": ic_sat,
        "warning": warning,
    }


def compute_bias(mode: str, inputs: dict) -> dict:
    """Dispatch to the selected bias function.

    mode: "voltage_divider" | "fixed" | "emitter"
    inputs: dict of already-converted SI values (volts, ohms, amps).

    Unknown mode returns an error dict (never silently falls back to Divider).
    """
    try:
        vcc = float(inputs["vcc"])
        rc = float(inputs["rc"])
        beta = float(inputs["beta"])
        vbe = float(inputs["vbe"])
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "mode": mode,
            "error": f"กรุณากรอกค่าร่วมให้ครบถ้วนและเป็นตัวเลข ({exc})",
            "warning": None,
            "vb": None, "ve": None, "vc": None, "vce": None,
            "ic": None, "ie": None, "ib": None,
        }

    if mode == "fixed":
        try:
            rb = float(inputs["rb"])
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "mode": mode,
                "error": f"กรุณากรอกค่า RB (Fixed Bias) ให้ครบถ้วนและเป็นตัวเลข ({exc})",
                "warning": None,
                "vb": None, "ve": None, "vc": None, "vce": None,
                "ic": None, "ie": None, "ib": None,
            }
        result = fixed_bias(vcc, rc, beta, vbe, rb)
        result["error"] = None
        return result

    if mode == "emitter":
        try:
            rb = float(inputs["rb"])
            re_ = float(inputs["re"])
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "mode": mode,
                "error": f"กรุณากรอกค่า RB และ RE (Emitter Bias) ให้ครบถ้วนและเป็นตัวเลข ({exc})",
                "warning": None,
                "vb": None, "ve": None, "vc": None, "vce": None,
                "ic": None, "ie": None, "ib": None,
            }
        result = emitter_bias(vcc, rc, beta, vbe, rb, re_)
        result["error"] = None
        return result

    if mode == "voltage_divider":
        try:
            r1 = float(inputs["r1"])
            r2 = float(inputs["r2"])
            re_ = float(inputs["re"])
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "mode": mode,
                "error": f"กรุณากรอกค่า R1, R2 และ RE ให้ครบถ้วนและเป็นตัวเลข ({exc})",
                "warning": None,
                "vb": None, "ve": None, "vc": None, "vce": None,
                "ic": None, "ie": None, "ib": None,
            }
        result = dc_operating_point(vcc, r1, r2, rc, re_, beta, vbe)
        result["mode"] = "voltage_divider"
        result["error"] = None
        return result

    return {
        "mode": mode,
        "error": f"โหมดวงจร '{mode}' ไม่รู้จัก กรุณาเลือกโหมดที่ถูกต้อง",
        "warning": None,
        "vb": None, "ve": None, "vc": None, "vce": None,
        "ic": None, "ie": None, "ib": None,
    }
