from flask import Flask, render_template, request

from dc_bias import dc_operating_point, parse_resistance, validate_inputs

app = Flask(__name__)


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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", values={"vbe": "0.7"}, errors=None,
                               result=None)

    form = request.form.to_dict()
    errors = validate_inputs(form)
    if errors:
        return render_template("index.html", values=form, errors=errors,
                               result=None), 400

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
                               result=None), 400

    op = dc_operating_point(vcc, r1, r2, rc, re_, beta, vbe)
    result = {
        "region": op["region"],
        "region_label": op["region"].capitalize(),
        "ic_sat": format_current(op["ic_sat"]),
        "rows": [
            ("VTH — แรงดันเทียบเท่า", format_voltage(op["vth"])),
            ("RTH — ความต้านทานเทียบเท่า", format_resistance(op["rth"])),
            ("IB — กระแสเบส", format_current(op["ib"])),
            ("IC — กระแสคอลเลกเตอร์", format_current(op["ic"])),
            ("IE — กระแสอีมิตเตอร์", format_current(op["ie"])),
            ("VE — แรงดันอีมิตเตอร์", format_voltage(op["ve"])),
            ("VB — แรงดันเบส", format_voltage(op["vb"])),
            ("VC — แรงดันคอลเลกเตอร์", format_voltage(op["vc"])),
            ("VCE — แรงดันคอลเลกเตอร์-อีมิตเตอร์", format_voltage(op["vce"])),
        ],
    }
    return render_template("index.html", values=form, errors=None,
                           result=result)


if __name__ == "__main__":
    app.run(debug=True)
