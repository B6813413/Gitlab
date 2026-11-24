"""Flask web app for BJT DC Bias — ENG29 2121 Lab 03 (extends Lab 2).

หน้าเดียว เลือกวงจรไบอัสได้สามแบบ:
  - Voltage Divider Bias (เดิมจาก Lab 2, ผลต้องคงเดิมเมื่อกรอกค่าเดิม)
  - Fixed Bias (ใหม่)
  - Emitter Bias แหล่งจ่ายเดียว (ใหม่)

สมการคำนวณอยู่ใน dc_bias.py (pure Python, ไม่ import Flask) ตามที่ใบงานกำหนด.
app.py รับผิดชอบ HTTP: parse form -> validate -> เรียกคำนวณ -> render template.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from charts import render_bode_svg, render_transient_svg
from dc_bias import compute_bias, parse_resistance, validate_inputs
from spice_engine import SPICE_DEFAULTS, run_analysis, validate_spice_inputs

app = Flask(__name__)

ANALYSIS_LABELS = {
    "bias": "Analytical DC Bias (Lab 03)",
    "spice_dc": "SPICE DC (.op)",
    "spice_ac": "SPICE AC (Bode)",
    "spice_tran": "SPICE Transient",
}
SPICE_ANALYSIS = {
    "spice_dc": "dc",
    "spice_ac": "ac",
    "spice_tran": "tran",
}

DEFAULT_VALUES = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "rb": "1000", "beta": "100", "vbe": "0.7",
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm",
    "re_unit": "kohm", "rb_unit": "kohm",
    "mode": "voltage_divider",
    "rl": "10", "cin": "10", "cout": "10",
    "amp": "0.01", "freq": "1k", "bjt_model": "QNPN",
}

MODE_LABELS = {
    "voltage_divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias (แหล่งจ่ายเดียว)",
}

# ฟิลด์ที่จำเป็นนอกจากค่าร่วม (vcc/rc/beta/vbe) ของแต่ละโหมด
MODE_EXTRA_FIELDS = {
    "voltage_divider": ["r1", "r2", "re"],
    "fixed": ["rb"],
    "emitter": ["rb", "re"],
}

# ฟิลด์ร่วมทั้งหมดที่ฟอร์มอาจแสดง
FORM_FIELDS = ["vcc", "r1", "r2", "rc", "re", "rb", "beta", "vbe"]


def format_current(amps) -> str:
    """Format current in engineering notation (µA / mA)."""
    if amps is None:
        return ""
    if abs(amps) >= 1e-3:
        return f"{amps * 1000:.3f} mA"
    return f"{amps * 1e6:.3f} µA"


def format_ic_ma(amps) -> str:
    """Format collector current in mA (Lab 03 กำหนดให้แสดง IC เป็น mA เสมอ)."""
    if amps is None:
        return ""
    return f"{amps * 1000:.3f} mA"


def format_voltage(volts) -> str:
    """Format voltage in volts with three decimals."""
    if volts is None:
        return ""
    return f"{volts:.3f} V"


def format_resistance(ohms) -> str:
    """Format resistance in Ω / kΩ with three decimals."""
    if ohms is None:
        return ""
    if abs(ohms) >= 1000:
        return f"{ohms / 1000:.3f} kΩ"
    return f"{ohms:.3f} Ω"


def build_diagram(values: dict, mode: str) -> dict:
    """Display-ready strings for the SVG schematic (raw user values)."""
    v = dict(values or {})

    def num(key: str, fallback: str) -> str:
        raw = str(v.get(key, fallback)).strip()
        return raw if raw else fallback

    def res(key: str, fallback: str) -> str:
        unit = str(v.get(f"{key}_unit", "kohm")).strip().lower()
        label = "kΩ" if unit == "kohm" else "Ω"
        return f"{num(key, fallback)} {label}"

    return {
        "vcc": f"{num('vcc', '12')} V",
        "r1": res("r1", "100"),
        "r2": res("r2", "22"),
        "rc": res("rc", "2.2"),
        "re": res("re", "1"),
        "rb": res("rb", "1000"),
        "beta": num("beta", "100"),
        "mode": mode,
    }


def _render(values, errors, result, diagram, mode, *, analysis="bias",
            spice_result=None, status=200):
    """Render the one page with a stable context on every branch."""
    return render_template(
        "index.html", values=values, errors=errors, result=result,
        diagram=diagram, mode=mode, mode_labels=MODE_LABELS,
        analysis=analysis, analysis_labels=ANALYSIS_LABELS,
        spice_result=spice_result,
    ), status


def _spice_params(form):
    """Merge SPICE defaults with submitted fields before validation.

    A partial POST (e.g. only ``amp``/``freq`` changed) is still a complete,
    valid netlist; missing values come from the Lab 04 reference circuit.
    """
    params = dict(SPICE_DEFAULTS)
    for key, value in form.items():
        if value in (None, "") or not (key in SPICE_DEFAULTS or key.endswith("_unit")):
            continue
        params[key] = value
    return params


def _spice_view(raw):
    """Display-ready copy of an engine result (formatter-reused, no fabrication)."""
    view = dict(raw or {})
    values = view.get("values") or {}
    view["rows"] = (
        [
            ("VB", format_voltage(values.get("vb"))),
            ("VE", format_voltage(values.get("ve"))),
            ("VC", format_voltage(values.get("vc"))),
            ("VCE", format_voltage(values.get("vce"))),
            ("IC", format_ic_ma(values.get("ic"))),
        ] if values else []
    )
    chart = ""
    svg = ""
    if view.get("status") == "success":
        if view.get("analysis") == "ac":
            chart, svg = "Bode", render_bode_svg(view.get("series"))
        elif view.get("analysis") == "tran":
            chart, svg = "Transient", render_transient_svg(view.get("series"))
    view["chart"] = chart
    view["svg"] = svg
    return view


@app.route("/", methods=["GET", "POST"])
def index():
    submitted_mode = (request.form.get("mode") or request.args.get("mode")
                      or DEFAULT_VALUES["mode"])
    mode = submitted_mode if submitted_mode in MODE_LABELS else DEFAULT_VALUES["mode"]
    submitted_analysis = (request.form.get("analysis")
                          or request.args.get("analysis") or "bias")
    analysis = submitted_analysis if submitted_analysis in ANALYSIS_LABELS else "bias"

    errors = None
    result = None
    spice_result = None
    values = dict(DEFAULT_VALUES)
    values["mode"] = mode

    # โหมดที่ไม่รู้จักต้องแจ้งข้อผิดพลาด (ไม่เดาว่าเป็น Voltage Divider)
    if submitted_mode not in MODE_LABELS:
        errors = {"mode": f"โหมดวงจร '{submitted_mode}' ไม่รู้จัก กรุณาเลือกโหมดที่ถูกต้อง"}
    if submitted_analysis not in ANALYSIS_LABELS:
        errors = dict(errors or {})
        errors["analysis"] = (
            f"ไม่รู้จักการวิเคราะห์ '{submitted_analysis}' กรุณาเลือก analysis ที่ถูกต้อง"
        )
        if request.method == "POST":
            return _render(
                values, errors, None, build_diagram(values, mode), mode,
                analysis=analysis, status=400,
            )

    if request.method == "POST":
        form = request.form.to_dict()

        # SPICE dispatch: ใช้ engine จริง แต่ไม่แตะเส้นทาง dc_bias เดิม
        if analysis != "bias":
            params = _spice_params(form)
            spice_errors = validate_spice_inputs(params)
            if spice_errors:
                errors = dict(errors or {})
                errors.update(spice_errors)
                return _render(
                    values, errors, None, build_diagram(values, mode), mode,
                    analysis=analysis, status=400,
                )
            raw = run_analysis(params, SPICE_ANALYSIS[analysis])
            spice_result = _spice_view(raw)
            status = 200 if raw.get("status") == "success" else 502
            return _render(
                values, errors, None, build_diagram(values, mode), mode,
                analysis=analysis, spice_result=spice_result, status=status,
            )

        values = {k: form.get(k, DEFAULT_VALUES.get(k, "")) for k in FORM_FIELDS}
        values["mode"] = mode
        values.update({f"{f}_unit": form.get(f"{f}_unit", DEFAULT_VALUES.get(f"{f}_unit", "kohm"))
                       for f in ("r1", "r2", "rc", "re", "rb")})

        form_errors = validate_inputs(form, submitted_mode)
        if form_errors:
            if errors:
                errors.update(form_errors)
            else:
                errors = form_errors
        if errors:
            return _render(
                values, errors, None, build_diagram(values, mode), mode,
                analysis=analysis, status=400,
            )

        # แปลงหน่วยจากฟอร์ม (kΩ -> Ω ฯลฯ) ที่จุดรับค่าเดียวก่อนส่งให้ dc_bias.py
        try:
            inputs = {
                "mode": submitted_mode,
                "vcc": float(form["vcc"]),
                "rc": parse_resistance(form["rc"], form.get("rc_unit", "ohm")),
                "beta": float(form["beta"]),
                "vbe": float(form["vbe"]),
            }
            if mode == "voltage_divider":
                inputs.update({
                    "r1": parse_resistance(form["r1"], form.get("r1_unit", "ohm")),
                    "r2": parse_resistance(form["r2"], form.get("r2_unit", "ohm")),
                    "re": parse_resistance(form["re"], form.get("re_unit", "ohm")),
                })
            elif mode == "fixed":
                inputs["rb"] = parse_resistance(form["rb"], form.get("rb_unit", "ohm"))
            elif mode == "emitter":
                inputs["rb"] = parse_resistance(form["rb"], form.get("rb_unit", "ohm"))
                inputs["re"] = parse_resistance(form["re"], form.get("re_unit", "ohm"))
        except (KeyError, ValueError) as exc:
            errors = {"form": f"ต้องเป็นตัวเลขที่จำกัด ({exc})"}
            return _render(
                values, errors, None, build_diagram(values, mode), mode,
                analysis=analysis, status=400,
            )

        op = compute_bias(submitted_mode, inputs)
        if op.get("error"):
            errors = {"form": op["error"]}
            return _render(
                values, errors, None, build_diagram(values, mode), mode,
                analysis=analysis, status=400,
            )

        result = {
            "mode": op.get("mode", mode),
            "region": op.get("region"),
            "region_label": (op.get("region") or "").capitalize(),
            "ic_sat": format_current(op["ic_sat"]) if op.get("ic_sat") is not None else "",
            "vce": format_voltage(op["vce"]),
            "vth": (format_voltage(op["vth"]) if op.get("vth") is not None else ""),
            "rth": (format_resistance(op["rth"]) if op.get("rth") is not None else ""),
            "ib": format_current(op["ib"]),
            "ic": format_ic_ma(op["ic"]),
            "ie": format_current(op["ie"]),
            "ve": format_voltage(op["ve"]),
            "vb": format_voltage(op["vb"]),
            "vc": format_voltage(op["vc"]),
            "warning": op.get("warning"),
            "rows": [
                ("โหมด", op.get("mode", mode)),
                ("VTH (Thevenin)", format_voltage(op["vth"]) if op.get("vth") is not None else "—"),
                ("RTH (Thevenin)", format_resistance(op["rth"]) if op.get("rth") is not None else "—"),
                ("VB", format_voltage(op["vb"])),
                ("VE", format_voltage(op["ve"])),
                ("VC", format_voltage(op["vc"])),
                ("VCE", format_voltage(op["vce"])),
                ("IB", format_current(op["ib"])),
                ("IC", format_ic_ma(op["ic"])),
                ("IE", format_current(op["ie"])),
            ],
        }

    return _render(
        values, errors, result, build_diagram(values, mode), mode,
        analysis=analysis,
    )


if __name__ == "__main__":
    app.run(debug=True)
