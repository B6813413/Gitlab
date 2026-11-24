"""SPICE netlist builder and input validation for the CE amplifier (Lab 04).

Pure engineering/formatting logic: this module must not import Flask and must
not know about HTTP.  It reuses :func:`dc_bias.parse_resistance` so raw form
text is validated before anything can reach the external solver.

Units of the accepted form values:

===========  =========================================================
``vcc``      volts
``r1`` ...   ohms (optional ``k`` suffix, or a ``*_unit=kohm`` companion)
``cin``      microfarads; written as e.g. ``10u`` in the netlist
``cout``     microfarads; written as e.g. ``10u`` in the netlist
``amp``      volts (peak) of the sinusoidal source
``freq``     hertz (optional ``k`` suffix; ``1k`` means 1 kHz)
===========  =========================================================
"""

import math
import re

from dc_bias import parse_resistance

#: Reference circuit from the Lab 04 handout (no emitter bypass capacitor).
SPICE_DEFAULTS = {
    "vcc": "12",
    "r1": "100k",
    "r2": "22k",
    "rc": "2.2k",
    "re": "1k",
    "rl": "10k",
    "cin": "10",
    "cout": "10",
    "amp": "0.01",
    "freq": "1k",
    "bjt_model": "QNPN",
}

_ANALYSES = ("dc", "ac", "tran")
_RESISTOR_FIELDS = ("r1", "r2", "rc", "re", "rl")
_CAP_FIELDS = ("cin", "cout")
_MODEL_NAME = re.compile(r"[A-Za-z0-9_]+\Z")


def _raw(values: dict, field: str) -> str:
    """Return a form value as stripped text (missing/None becomes "")."""
    value = (values or {}).get(field, "")
    if value is None:
        return ""
    return str(value).strip()


def _finite_number(text: str) -> float:
    """Parse a plain decimal number, rejecting nan/inf/1e999 and junk."""
    try:
        value = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("ต้องเป็นตัวเลขที่จำกัด") from exc
    if not math.isfinite(value):
        raise ValueError("ต้องเป็นตัวเลขที่จำกัด")
    return value


# ---- SI -> SPICE string formatting (single place for every unit) ----------

def _format_number(value: float) -> str:
    return f"{value:.12g}"


def _format_ohms(ohms: float) -> str:
    if ohms >= 1000.0:
        return f"{_format_number(ohms / 1000.0)}k"
    return _format_number(ohms)


def _format_microfarads(microfarads: float) -> str:
    return f"{_format_number(microfarads)}u"


def _format_hz(hz: float) -> str:
    if hz >= 1000.0:
        return f"{_format_number(hz / 1000.0)}k"
    return _format_number(hz)


# ---- Validation -----------------------------------------------------------

def validate_spice_inputs(values: dict) -> dict[str, str]:
    """Validate raw SPICE form values.

    Returns ``{field: Thai message}`` (empty when every value is acceptable).
    Messages come from the set defined in ``dc_bias.py``; no raw form text is
    ever passed through without being parsed and range-checked here.
    """
    errors: dict[str, str] = {}
    parsed: dict[str, float] = {}

    for field in ("vcc", "amp"):
        text = _raw(values, field)
        if not text:
            errors[field] = "กรุณากรอกค่านี้"
            continue
        try:
            parsed[field] = _finite_number(text)
        except ValueError as exc:
            errors[field] = str(exc)

    if "vcc" in parsed and parsed["vcc"] <= 0:
        errors["vcc"] = "ต้องมากกว่า 0"
    if "amp" in parsed and parsed["amp"] <= 0:
        errors["amp"] = "ต้องมากกว่า 0"

    # Frequency reuses the resistance grammar only for its "k" (kHz) suffix.
    text = _raw(values, "freq")
    if not text:
        errors["freq"] = "กรุณากรอกค่านี้"
    else:
        try:
            freq = parse_resistance(text)
        except ValueError as exc:
            errors["freq"] = str(exc)
        else:
            if freq <= 0:
                errors["freq"] = "ต้องมากกว่า 0"

    for field in _RESISTOR_FIELDS:
        unit = _raw(values, f"{field}_unit").lower() or "ohm"
        try:
            ohms = parse_resistance(_raw(values, field), unit)
        except ValueError as exc:
            errors[field] = str(exc)
            continue
        if ohms <= 0:
            errors[field] = "ต้องมากกว่า 0"

    # Capacitances are expressed in microfarads (written with a "u" suffix).
    for field in _CAP_FIELDS:
        try:
            microfarads = parse_resistance(_raw(values, field))
        except ValueError as exc:
            errors[field] = str(exc)
            continue
        if microfarads <= 0:
            errors[field] = "ต้องมากกว่า 0"

    model = _raw(values, "bjt_model")
    if not model:
        errors["bjt_model"] = "กรุณากรอกค่านี้"
    elif not _MODEL_NAME.fullmatch(model):
        errors["bjt_model"] = "ต้องเป็นตัวเลขที่จำกัด"

    return errors


def _si_values(params: dict) -> dict:
    """Validate and convert raw params into SI values for netlist building."""
    errors = validate_spice_inputs(params)
    if errors:
        detail = ", ".join(
            f"{field}={message}" for field, message in sorted(errors.items())
        )
        raise ValueError(f"ค่าอินพุต SPICE ไม่ถูกต้อง: {detail}")

    values = {
        "vcc": _finite_number(_raw(params, "vcc")),
        "amp": _finite_number(_raw(params, "amp")),
        "freq": parse_resistance(_raw(params, "freq")),
        "bjt_model": _raw(params, "bjt_model"),
    }
    for field in _RESISTOR_FIELDS:
        unit = _raw(params, f"{field}_unit").lower() or "ohm"
        values[field] = parse_resistance(_raw(params, field), unit)
    for field in _CAP_FIELDS:
        values[field] = parse_resistance(_raw(params, field))
    return values


# ---- Netlist --------------------------------------------------------------

def build_netlist(params: dict, analysis: str) -> str:
    """Build a complete ngspice netlist for one analysis.

    ``analysis`` is ``"dc"`` (``.op``), ``"ac"`` (``.ac``) or ``"tran"``
    (``.tran``).  The returned text contains only that analysis' directives
    and its matching ``.print`` line.  Invalid params raise ``ValueError`` so
    unvalidated form text can never reach the solver.
    """
    name = str(analysis or "").strip().lower()
    if name not in _ANALYSES:
        raise ValueError(
            f"ไม่รู้จัก analysis '{analysis}' (ต้องเป็น dc, ac หรือ tran)"
        )

    v = _si_values(params)
    model = v["bjt_model"]

    lines = [
        "CE amplifier reference (Lab 04, no emitter bypass)",
        f"VCC vcc 0 {_format_number(v['vcc'])}",
        f"VIN vin 0 DC 0 AC {_format_number(v['amp'])} "
        f"SIN(0 {_format_number(v['amp'])} {_format_hz(v['freq'])} 0 0)",
        f"R1 vcc b {_format_ohms(v['r1'])}",
        f"R2 b 0 {_format_ohms(v['r2'])}",
        f"RC vcc c {_format_ohms(v['rc'])}",
        f"RE e 0 {_format_ohms(v['re'])}",
        f"Q1 c b e {model}",
        f"CIN vin b {_format_microfarads(v['cin'])}",
        f"COUT c vout {_format_microfarads(v['cout'])}",
        f"RL vout 0 {_format_ohms(v['rl'])}",
        f".model {model} NPN(IS=1e-14 BF=100 VAF=100)",
    ]

    if name == "dc":
        # ngspice names the operating-point plot "op"; .print matches plot
        # typename, so this prints the OP values as a table in the log.
        # Device current uses the documented @device[keyword] form (BJT IC).
        lines += [
            ".op",
            ".print op v(b) v(e) v(c) @q1[ic]",
        ]
    elif name == "ac":
        lines += [
            ".ac dec 20 10 1meg",
            ".print ac vdb(vout) vp(vout)",
        ]
    else:
        lines += [
            ".tran 10u 5m",
            ".print tran v(vin) v(vout)",
        ]

    lines.append(".end")
    return "\n".join(lines) + "\n"
