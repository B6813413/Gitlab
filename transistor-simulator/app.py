from flask import Flask, render_template, request

from dc_bias import dc_operating_point, parse_resistance, validate_inputs

app = Flask(__name__)

DEFAULT_VALUES = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.7",
    "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
}


def format_current(amps) -> str:
    """Format current in engineering notation (µA / mA)."""
    if abs(amps) >= 1e-3:
        return f"{amps * 1000:.3f} mA"
    return f"{amps * 1e6:.3f} µA"


def format_voltage(volts) -> str:
    """Format voltage in volts with three decimals."""
    return f"{volts:.3f} V"


def format_resistance(ohms) -> str:
    """Format resistance in Ω / kΩ with three decimals."""
    if abs(ohms) >= 1000:
        return f"{ohms / 1000:.3f} kΩ"
    return f"{ohms:.3f} Ω"


def build_diagram(values: dict) -> dict:
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
        "beta": num("beta", "100"),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", values=dict(DEFAULT_VALUES),
                               errors=None, result=None,
                               diagram=build_diagram(DEFAULT_VALUES))

    form = request.form.to_dict()
    errors = validate_inputs(form)
    if errors:
        return render_template("index.html", values=form, errors=errors,
                               result=None,
                               diagram=build_diagram(form)), 400

    try:
        vcc = float(form["vcc"])
        beta = float(form["beta"])
        vbe = float(form["vbe"])
        r1 = parse_resistance(form["r1"], form.get("r1_unit", "ohm"))
        r2 = parse_resistance(form["r2"], form.get("r2_unit", "ohm"))
        rc = parse_resistance(form["rc"], form.get("rc_unit", "ohm"))
        re_ = parse_resistance(form["re"], form.get("re_unit", "ohm"))
    except (KeyError, ValueError):
        return render_template("index.html", values=form,
                               errors={"form": "ต้องเป็นตัวเลขที่จำกัด"},
                               result=None,
                               diagram=build_diagram(form)), 400

    op = dc_operating_point(vcc, r1, r2, rc, re_, beta, vbe)
    result = {
        "region": op["region"],
        "region_label": op["region"].capitalize(),
        "ic_sat": format_current(op["ic_sat"]),
        "vce": format_voltage(op["vce"]),
        "vth": format_voltage(op["vth"]),
        "rth": format_resistance(op["rth"]),
        "ib": format_current(op["ib"]),
        "ic": format_current(op["ic"]),
        "ie": format_current(op["ie"]),
        "ve": format_voltage(op["ve"]),
        "vb": format_voltage(op["vb"]),
        "vc": format_voltage(op["vc"]),
        "rows": [
            ("VTH (Thevenin)", format_voltage(op["vth"])),
            ("RTH (Thevenin)", format_resistance(op["rth"])),
            ("VB", format_voltage(op["vb"])),
            ("VE", format_voltage(op["ve"])),
            ("VC", format_voltage(op["vc"])),
            ("VCE", format_voltage(op["vce"])),
            ("IB", format_current(op["ib"])),
            ("IC", format_current(op["ic"])),
            ("IE", format_current(op["ie"])),
        ],
    }
    return render_template("index.html", values=form, errors=None,
                           result=result,
                           diagram=build_diagram(form))


if __name__ == "__main__":
    app.run(debug=True)
