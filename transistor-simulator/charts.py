"""Dependency-free SVG charts for Lab 04 simulation results.

The module is pure Python: it builds SVG markup as strings so Flask/Jinja can
embed it without adding a charting library.  Every plotted coordinate is
derived from the ``series`` rows returned by
:func:`spice_engine.run_analysis`; no simulated value is hard-coded here.

Design decisions
----------------
* Bode frequency uses a logarithmic x-axis when every ``freq`` is positive
  (the usual Bode convention).  A series containing zero/negative frequencies
  falls back to a linear axis instead of dropping points.
* Gain and phase use independent y-scales, so both traces stay visible.  Gain
  ticks are labelled on the left, phase ticks on the right.
* Transient ``time`` values are SI seconds and are converted to milliseconds
  for the axis.
* Rows missing a key or containing a non-finite value are skipped.  An empty
  (or wholly unusable) series returns an accessible placeholder with axes and
  a Thai "no data" message, never a fabricated trace.
"""

import html
import math

_WIDTH = 760
_HEIGHT = 440
_PLOT_LEFT = 78
_PLOT_RIGHT = 682
_PLOT_TOP = 52
_PLOT_BOTTOM = 376

_GRID_COLOR = "#e2e8f0"
_AXIS_COLOR = "#94a3b8"
_TEXT_COLOR = "#334155"
_GAIN_COLOR = "#2563eb"
_PHASE_COLOR = "#d97706"
_VIN_COLOR = "#16a34a"
_VOUT_COLOR = "#dc2626"

_AC_KEYS = ("freq", "gain_db", "phase_deg")
_TRAN_KEYS = ("time", "vin", "vout")


# ---- small numeric helpers -------------------------------------------------

def _finite(value):
    """Return ``value`` as a finite float, or ``None`` when unusable."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _rows(series, keys):
    """Copy valid rows from ``series``, keeping only the requested keys."""
    rows = []
    if not isinstance(series, (list, tuple)):
        return rows
    for row in series:
        if not isinstance(row, dict):
            continue
        values = {}
        for key in keys:
            number = _finite(row.get(key))
            if number is None:
                break
            values[key] = number
        else:
            rows.append(values)
    return rows


def _domain(values, padding=0.08):
    """Return a padded (low, high) range; constant data gets a real span."""
    low = min(values)
    high = max(values)
    scale = max(1.0, abs(low), abs(high))
    if high - low <= 1e-12 * scale:
        delta = abs(low) * 0.1 or 1.0
        return low - delta, high + delta
    span = high - low
    return low - span * padding, high + span * padding


def _map(value, low, high, start, end):
    """Map ``value`` from a data range onto a pixel range."""
    if high == low:
        return (start + end) / 2.0
    ratio = (value - low) / (high - low)
    return start + ratio * (end - start)


def _ticks(low, high, count=5):
    """Return rounded tick values covering ``low`` .. ``high``."""
    if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
        return [low] if math.isfinite(low) else []
    raw_step = (high - low) / max(1, count)
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    residual = raw_step / magnitude
    if residual <= 1:
        step = magnitude
    elif residual <= 2:
        step = 2 * magnitude
    elif residual <= 2.5:
        step = 2.5 * magnitude
    elif residual <= 5:
        step = 5 * magnitude
    else:
        step = 10 * magnitude

    value = math.ceil((low - step * 1e-9) / step) * step
    ticks = []
    while value <= high + step * 1e-9 and len(ticks) <= 20:
        snapped = round(value / step) * step
        if not ticks or abs(snapped - ticks[-1]) > step * 1e-6:
            ticks.append(snapped)
        value += step
    return ticks if len(ticks) >= 2 else [low, high]


def _log_ticks(low, high):
    """Return 1/2/5-per-decade ticks for a logarithmic frequency axis."""
    if low <= 0 or high <= 0 or high <= low:
        return _ticks(low, high)
    first = math.floor(math.log10(low))
    last = math.ceil(math.log10(high))
    ticks = []
    for exponent in range(first, last + 1):
        base = 10.0 ** exponent
        for multiplier in (1, 2, 5):
            value = multiplier * base
            if low * (1 - 1e-9) <= value <= high * (1 + 1e-9):
                ticks.append(value)
    if len(ticks) > 12:
        ticks = [
            10.0 ** exponent
            for exponent in range(first, last + 1)
            if low * (1 - 1e-9) <= 10.0 ** exponent <= high * (1 + 1e-9)
        ]
    return ticks if len(ticks) >= 2 else [low, high]


def _format_tick(value):
    if abs(value) < 1e-12:
        return "0"
    if abs(value) >= 1e6 or abs(value) < 1e-3:
        return f"{value:.3g}"
    return f"{value:.6g}"


# ---- SVG primitives --------------------------------------------------------

def _start(aria_label):
    label = html.escape(aria_label, quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {_WIDTH} {_HEIGHT}" width="{_WIDTH}" '
        f'height="{_HEIGHT}" role="img" aria-label="{label}">'
        f"<title>{label}</title>"
        f'<rect x="0" y="0" width="{_WIDTH}" height="{_HEIGHT}" '
        f'fill="#ffffff"/>'
    )


def _text(x, y, value, *, anchor="middle", size=12, color=_TEXT_COLOR,
          weight="normal", transform=""):
    extra = f' transform="{transform}"' if transform else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="sans-serif" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}"{extra}>{html.escape(str(value))}</text>'
    )


def _frame():
    return (
        f'<path class="plot-frame" d="M {_PLOT_LEFT} {_PLOT_TOP} '
        f'L {_PLOT_RIGHT} {_PLOT_TOP} L {_PLOT_RIGHT} {_PLOT_BOTTOM} '
        f'L {_PLOT_LEFT} {_PLOT_BOTTOM} Z" fill="none" '
        f'stroke="{_AXIS_COLOR}" stroke-width="1"/>'
    )


def _grid(x_positions, y_positions):
    parts = []
    for x in x_positions:
        parts.append(
            f'<line x1="{x:.2f}" y1="{_PLOT_TOP}" x2="{x:.2f}" '
            f'y2="{_PLOT_BOTTOM}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
        )
    for y in y_positions:
        parts.append(
            f'<line x1="{_PLOT_LEFT}" y1="{y:.2f}" x2="{_PLOT_RIGHT}" '
            f'y2="{y:.2f}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
        )
    return "".join(parts)


def _axis_titles(x_label, left_label, right_label=None):
    center_y = (_PLOT_TOP + _PLOT_BOTTOM) / 2.0
    parts = [
        _text((_PLOT_LEFT + _PLOT_RIGHT) / 2.0, _HEIGHT - 18, x_label,
              size=13, weight="bold"),
        _text(20, center_y, left_label, size=13, weight="bold",
              transform=f"rotate(-90 20 {center_y:.1f})"),
    ]
    if right_label:
        parts.append(
            _text(_WIDTH - 20, center_y, right_label, size=13, weight="bold",
                  transform=f"rotate(90 {_WIDTH - 20} {center_y:.1f})")
        )
    return "".join(parts)


def _legend(entries, y=30):
    parts = ['<g class="legend">']
    x = _PLOT_LEFT + 8
    for color, label in entries:
        parts.append(
            f'<path d="M {x} {y} L {x + 22} {y}" stroke="{color}" '
            f'stroke-width="3" fill="none"/>'
        )
        parts.append(_text(x + 28, y + 4, label, anchor="start", size=12))
        x += 40 + 7 * len(label)
    parts.append("</g>")
    return "".join(parts)


def _polyline(points, color, css_class):
    if not points:
        return ""
    coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f'<polyline class="{css_class}" points="{coords}" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linejoin="round" '
        f'stroke-linecap="round"/>'
    )


def _markers(points, color):
    if not 1 < len(points) <= 60:
        return ""
    return "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}"/>'
        for x, y in points
    )


def _empty(aria_label, x_label, left_label, right_label=None):
    return "".join([
        _start(aria_label),
        _frame(),
        _axis_titles(x_label, left_label, right_label),
        _text((_PLOT_LEFT + _PLOT_RIGHT) / 2.0,
              (_PLOT_TOP + _PLOT_BOTTOM) / 2.0,
              "ไม่มีข้อมูลสำหรับวาดกราฟ", size=16, weight="bold"),
        "</svg>",
    ])


# ---- public renderers ------------------------------------------------------

def render_bode_svg(series):
    """Render a Bode plot (gain and phase vs frequency) as an SVG string."""
    rows = _rows(series, _AC_KEYS)
    if not rows:
        return _empty(
            "กราฟโบเด (Bode) — ไม่มีข้อมูลสำหรับวาดกราฟ",
            "Frequency (Hz)", "Gain (dB)", "Phase (°)",
        )
    rows.sort(key=lambda row: row["freq"])

    frequencies = [row["freq"] for row in rows]
    use_log = all(value > 0 for value in frequencies)
    x_values = (
        [math.log10(value) for value in frequencies]
        if use_log else frequencies
    )
    x_low, x_high = _domain(x_values, padding=0.02 if use_log else 0.04)

    gain_low, gain_high = _domain([row["gain_db"] for row in rows])
    phase_low, phase_high = _domain([row["phase_deg"] for row in rows])
    gain_ticks = _ticks(gain_low, gain_high)
    phase_ticks = _ticks(phase_low, phase_high)
    freq_ticks = (
        _log_ticks(min(frequencies), max(frequencies))
        if use_log else _ticks(x_low, x_high)
    )

    x_positions = [
        _map(value, x_low, x_high, _PLOT_LEFT, _PLOT_RIGHT)
        for value in x_values
    ]
    gain_y = [
        _map(tick, gain_low, gain_high, _PLOT_BOTTOM, _PLOT_TOP)
        for tick in gain_ticks
    ]
    phase_y = [
        _map(tick, phase_low, phase_high, _PLOT_BOTTOM, _PLOT_TOP)
        for tick in phase_ticks
    ]
    gain_points = [
        (x, _map(row["gain_db"], gain_low, gain_high,
                 _PLOT_BOTTOM, _PLOT_TOP))
        for x, row in zip(x_positions, rows)
    ]
    phase_points = [
        (x, _map(row["phase_deg"], phase_low, phase_high,
                 _PLOT_BOTTOM, _PLOT_TOP))
        for x, row in zip(x_positions, rows)
    ]

    parts = [
        _start(
            "กราฟโบเดแสดงอัตราขยายและเฟสเทียบความถี่ "
            f"จากผลจำลอง {len(rows)} จุดข้อมูล"
        ),
        _legend([
            (_GAIN_COLOR, "อัตราขยาย (Gain, dB)"),
            (_PHASE_COLOR, "เฟส (Phase, °)"),
        ]),
        _grid(
            [_map(tick, x_low, x_high, _PLOT_LEFT, _PLOT_RIGHT)
             for tick in freq_ticks],
            gain_y,
        ),
        _frame(),
        _axis_titles("Frequency (Hz)", "Gain (dB)", "Phase (°)"),
    ]

    for tick in freq_ticks:
        position = _map(
            math.log10(tick) if use_log else tick,
            x_low, x_high, _PLOT_LEFT, _PLOT_RIGHT,
        )
        if _PLOT_LEFT - 1 <= position <= _PLOT_RIGHT + 1:
            parts.append(_text(position, _PLOT_BOTTOM + 18,
                               _format_tick(tick), size=11))
    for tick, position in zip(gain_ticks, gain_y):
        parts.append(_text(_PLOT_LEFT - 10, position + 4,
                           _format_tick(tick), anchor="end", size=11))
    for tick, position in zip(phase_ticks, phase_y):
        parts.append(_text(_PLOT_RIGHT + 10, position + 4,
                           _format_tick(tick), anchor="start", size=11))

    parts.append(_polyline(gain_points, _GAIN_COLOR, "series-gain"))
    parts.append(_markers(gain_points, _GAIN_COLOR))
    parts.append(_polyline(phase_points, _PHASE_COLOR, "series-phase"))
    parts.append(_markers(phase_points, _PHASE_COLOR))
    parts.append("</svg>")
    return "".join(parts)


def render_transient_svg(series):
    """Render Vin/Vout vs time (ms) as an SVG string."""
    rows = _rows(series, _TRAN_KEYS)
    if not rows:
        return _empty(
            "กราฟรูปคลื่นเวลาของแรงดันอินพุตและเอาต์พุต — "
            "ไม่มีข้อมูลสำหรับวาดกราฟ",
            "Time (ms)", "Voltage (V)",
        )
    rows.sort(key=lambda row: row["time"])

    times_ms = [row["time"] * 1000.0 for row in rows]
    volts = [row["vin"] for row in rows] + [row["vout"] for row in rows]
    x_low, x_high = _domain(times_ms, padding=0.04)
    y_low, y_high = _domain(volts)
    x_ticks = _ticks(x_low, x_high)
    y_ticks = _ticks(y_low, y_high)

    x_positions = [
        _map(value, x_low, x_high, _PLOT_LEFT, _PLOT_RIGHT)
        for value in times_ms
    ]
    y_positions = [
        _map(tick, y_low, y_high, _PLOT_BOTTOM, _PLOT_TOP)
        for tick in y_ticks
    ]
    vin_points = [
        (x, _map(row["vin"], y_low, y_high, _PLOT_BOTTOM, _PLOT_TOP))
        for x, row in zip(x_positions, rows)
    ]
    vout_points = [
        (x, _map(row["vout"], y_low, y_high, _PLOT_BOTTOM, _PLOT_TOP))
        for x, row in zip(x_positions, rows)
    ]

    parts = [
        _start(
            "กราฟรูปคลื่นเวลาของแรงดันอินพุตและเอาต์พุต "
            f"จากผลจำลอง {len(rows)} จุดข้อมูล"
        ),
        _legend([
            (_VIN_COLOR, "Vin (V)"),
            (_VOUT_COLOR, "Vout (V)"),
        ]),
        _grid(
            [_map(tick, x_low, x_high, _PLOT_LEFT, _PLOT_RIGHT)
             for tick in x_ticks],
            y_positions,
        ),
        _frame(),
        _axis_titles("Time (ms)", "Voltage (V)"),
    ]

    for tick in x_ticks:
        parts.append(_text(
            _map(tick, x_low, x_high, _PLOT_LEFT, _PLOT_RIGHT),
            _PLOT_BOTTOM + 18, _format_tick(tick), size=11,
        ))
    for tick, position in zip(y_ticks, y_positions):
        parts.append(_text(_PLOT_LEFT - 10, position + 4,
                           _format_tick(tick), anchor="end", size=11))

    parts.append(_polyline(vin_points, _VIN_COLOR, "series-vin"))
    parts.append(_markers(vin_points, _VIN_COLOR))
    parts.append(_polyline(vout_points, _VOUT_COLOR, "series-vout"))
    parts.append(_markers(vout_points, _VOUT_COLOR))
    parts.append("</svg>")
    return "".join(parts)
