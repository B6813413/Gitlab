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
import shutil
import subprocess
import tempfile
from pathlib import Path

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
            # Gain is Vout/Vin, so ngspice must print the input reference too.
            # Phase is likewise relative: vp(vout) - vp(vin).
            ".print ac vdb(vout) vp(vout) vdb(vin) vp(vin)",
        ]
    else:
        lines += [
            ".tran 10u 5m",
            ".print tran v(vin) v(vout)",
        ]

    lines.append(".end")
    return "\n".join(lines) + "\n"


# ---- ASCII log parsing ----------------------------------------------------

#: Column spellings ngspice may use for the OP node voltages.  Single letters
#: cover the vertical ``name value`` shape, ``v(x)`` covers print tables.
_OP_VOLTAGE_COLUMNS = {
    "vb": "vb", "v(b)": "vb", "b": "vb",
    "ve": "ve", "v(e)": "ve", "e": "ve",
    "vc": "vc", "v(c)": "vc", "c": "vc",
}
#: Collector current column.  Task 1's netlist prints ``@q1[ic]``.
_OP_CURRENT_COLUMNS = {"ic": "ic", "@q1[ic]": "ic", "i(q1)": "ic"}
_OP_COLUMNS = {**_OP_VOLTAGE_COLUMNS, **_OP_CURRENT_COLUMNS}
_OP_REQUIRED = ("vb", "ve", "vc", "ic")

#: Column names handed to :func:`parse_print_table` for transient sweeps.
#: AC uses :func:`parse_ac_log` because gain needs both Vout and Vin tables.
_SERIES_COLUMNS = {"tran": ["time", "vin", "vout"]}

#: AC table headers emitted by ngspice for ``.print ac ...``.  Each function
#: family is printed as its own table, so rows are merged by frequency before
#: the gain and phase are derived.
_AC_COLUMNS = {
    "frequency": "freq",
    "freq": "freq",
    "vdb(vout)": "vdb_vout",
    "vp(vout)": "vp_vout",
    "vdb(vin)": "vdb_vin",
    "vp(vin)": "vp_vin",
}

_LOG_EXCERPT_LIMIT = 2000


def _is_number(token: str) -> bool:
    try:
        float(token)
    except (TypeError, ValueError):
        return False
    return True


def _op_values(log: str) -> dict[str, float]:
    """Collect raw OP columns from vertical rows or an ``Index`` table."""
    found: dict[str, float] = {}
    header: list[str] | None = None

    for line in str(log or "").splitlines():
        tokens = line.split()
        if not tokens:
            continue

        # Vertical shape: "b   1.942000e+00" / "@q1[ic]   1.230000e-03".
        key = tokens[0].lower()
        if len(tokens) >= 2 and key in _OP_COLUMNS and _is_number(tokens[1]):
            found.setdefault(_OP_COLUMNS[key], float(tokens[1]))
            continue

        if not any(_is_number(token) for token in tokens):
            # Header shape: "Index   v(b)   v(e)   v(c)   @q1[ic]".
            lowered = [token.lower() for token in tokens]
            if any(token in _OP_COLUMNS for token in lowered):
                header = lowered
            continue

        # Data row of a print table; an "Index" column shifts values by one.
        if header is None or not all(_is_number(token) for token in tokens):
            continue
        values = list(tokens)
        if len(values) == len(header) + 1:
            values = values[1:]
        if len(values) != len(header):
            continue
        for column, value in zip(header, values):
            if column in _OP_COLUMNS:
                found.setdefault(_OP_COLUMNS[column], float(value))

    return found


def parse_op_log(log: str) -> dict[str, float]:
    """Parse an ngspice operating-point log into SI values.

    Returns ``vb``, ``ve``, ``vc``, ``vce`` and ``ic``.  ``vce`` is derived as
    ``vc - ve`` and the printed ``@q1[ic]`` column is mapped to ``ic``; neither
    value is ever fabricated.  A log missing any of those columns raises
    ``ValueError`` so callers can report an error instead of partial results.
    """
    found = _op_values(log)
    missing = [name for name in _OP_REQUIRED if name not in found]
    if missing:
        raise ValueError(
            "log ของ ngspice ไม่มีค่า operating point ครบ (ขาด "
            + ", ".join(missing)
            + ")"
        )
    found["vce"] = found["vc"] - found["ve"]
    return {name: found[name] for name in ("vb", "ve", "vc", "vce", "ic")}


def parse_print_table(log: str, columns: list[str]) -> list[dict[str, float]]:
    """Parse a whitespace-separated ngspice ``.print`` table.

    Header and separator lines are skipped.  Each numeric row is mapped to
    ``columns`` in order; a leading integer ``Index`` column is discarded when
    present.  Returns ``[]`` when the log contains no data rows.
    """
    names = list(columns)
    if not names:
        return []

    rows: list[dict[str, float]] = []
    for line in str(log or "").splitlines():
        tokens = line.split()
        if len(tokens) == len(names) + 1 and _is_number(tokens[0]):
            tokens = tokens[1:]
        elif len(tokens) != len(names):
            continue
        if not all(_is_number(token) for token in tokens):
            continue
        rows.append(
            {name: float(token) for name, token in zip(names, tokens)}
        )
    return rows


def parse_ac_log(log: str) -> list[dict[str, float]]:
    """Derive Vin-referenced gain (dB) and phase (degrees) from an AC log.

    ngspice prints each ``.print ac`` function family as its own table (for
    example ``vdb(vout)/vp(vout)`` then ``vdb(vin)/vp(vin)``).  Rows are merged
    by frequency; a frequency without all four columns is skipped rather than
    producing a fabricated gain.  Phase is unwrapped only into (-180, 180]
    degrees so a CE inversion renders as about -180 degrees, not -3.14.
    """
    merged: dict[str, dict[str, float]] = {}
    header: list[str | None] | None = None

    for line in str(log or "").splitlines():
        tokens = line.split()
        if not tokens:
            continue
        lowered = [token.lower() for token in tokens]
        if "index" in lowered and any(token in _AC_COLUMNS for token in lowered):
            header = [_AC_COLUMNS.get(token) for token in lowered]
            continue
        if header is None or len(tokens) != len(header):
            continue
        if not all(_is_number(token) for token in tokens):
            continue

        row: dict[str, float] = {}
        for name, token in zip(header, tokens):
            if name is not None:
                row[name] = float(token)
        freq = row.get("freq")
        if freq is None:
            continue
        merged.setdefault(f"{freq:.12g}", {}).update(row)

    rows: list[dict[str, float]] = []
    required = ("vdb_vout", "vdb_vin", "vp_vout", "vp_vin")
    for key in sorted(merged, key=float):
        record = merged[key]
        if any(name not in record for name in required):
            continue
        phase_deg = math.degrees(record["vp_vout"] - record["vp_vin"])
        if phase_deg > 180.0:
            phase_deg -= 360.0
        elif phase_deg < -180.0:
            phase_deg += 360.0
        rows.append({
            "freq": record["freq"],
            "gain_db": record["vdb_vout"] - record["vdb_vin"],
            "phase_deg": phase_deg,
        })
    return rows


def _excerpt(*parts: str, limit: int = _LOG_EXCERPT_LIMIT) -> str:
    """Join log evidence and keep only the last ``limit`` characters."""
    text = "\n".join(
        str(part).strip() for part in parts if part and str(part).strip()
    )
    return text[-limit:]


def _text(value) -> str:
    """Normalise ``TimeoutExpired`` payloads (bytes or text) to ``str``."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def run_analysis(
    params: dict,
    analysis: str,
    engine_path: str | None = None,
    timeout: int = 20,
) -> dict:
    """Run one ngspice analysis and return a result dictionary.

    The netlist is built in a fresh temporary directory and ngspice is invoked
    with an argument list (never a shell) under ``timeout``.  Every failure —
    invalid input, missing binary, non-zero exit, empty log, unparseable log —
    returns ``status="error"`` with ``values=None`` and ``series=None``; stale
    or partially parsed results are never returned.
    """
    name = str(analysis or "").strip().lower()
    engine = (engine_path or "ngspice").strip() or "ngspice"
    result = {
        "status": "error",
        "engine": engine,
        "analysis": name,
        "model": _raw(params, "bjt_model"),
        "values": None,
        "series": None,
        "log_excerpt": "",
        "error": "",
    }

    try:
        netlist = build_netlist(params, name)
    except ValueError as exc:
        result["error"] = str(exc)
        return result

    executable = shutil.which(engine)
    if not executable:
        result["error"] = (
            "ไม่พบโปรแกรม ngspice สำหรับจำลองวงจร "
            "(กรุณาติดตั้ง ngspice หรือระบุ engine_path)"
        )
        return result

    log_text = ""
    excerpt = ""
    try:
        with tempfile.TemporaryDirectory(prefix="lab04-ngspice-") as tmp:
            (Path(tmp) / "case.cir").write_text(netlist, encoding="utf-8")
            try:
                proc = subprocess.run(
                    # Do NOT pass -r: ngspice 47 then ignores .print lines and
                    # the ASCII log has no table for our parsers.  The raw
                    # binary is unused here; -o keeps the real log evidence.
                    [
                        executable,
                        "-b",
                        "-o",
                        "run.log",
                        "case.cir",
                    ],
                    cwd=tmp,
                    timeout=timeout,
                    capture_output=True,
                    text=True,
                    shell=False,
                )
            except subprocess.TimeoutExpired as exc:
                result["error"] = f"ngspice ใช้เวลาเกิน {timeout} วินาที"
                result["log_excerpt"] = _excerpt(
                    _text(exc.stdout), _text(exc.stderr)
                )
                return result
            except OSError as exc:
                result["error"] = f"เรียก ngspice ไม่สำเร็จ: {exc}"
                return result

            # Read the ASCII log first; ngspice may ignore .print when -r is
            # used, so a missing table is detected by the parsers below.
            log_file = Path(tmp) / "run.log"
            if log_file.exists():
                log_text = log_file.read_text(
                    encoding="utf-8", errors="replace"
                )
            elif proc.stdout:
                log_text = proc.stdout
            excerpt = _excerpt(log_text, proc.stderr or "")
    except OSError as exc:
        result["error"] = f"เตรียมไฟล์ netlist สำหรับ ngspice ไม่สำเร็จ: {exc}"
        return result

    result["log_excerpt"] = excerpt

    if proc.returncode != 0:
        result["error"] = f"ngspice ทำงานล้มเหลว (exit code {proc.returncode})"
        return result
    if not log_text.strip():
        result["error"] = "ngspice ไม่ได้สร้าง log ผลลัพธ์ (log ว่าง)"
        return result

    if name == "dc":
        try:
            values = parse_op_log(log_text)
        except ValueError:
            result["error"] = (
                "อ่านผลลัพธ์ DC (operating point) จาก log ของ ngspice ไม่ได้"
            )
            return result
        result["status"] = "success"
        result["values"] = values
        return result

    if name == "ac":
        series = parse_ac_log(log_text)
    else:
        series = parse_print_table(log_text, _SERIES_COLUMNS[name])
    if not series:
        result["error"] = (
            f"ไม่พบข้อมูลผลลัพธ์ {name.upper()} ใน log ของ ngspice"
        )
        return result
    result["status"] = "success"
    result["series"] = series
    return result
