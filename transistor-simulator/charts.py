"""Dependency-free SVG charts for real ngspice series.

Every coordinate comes from the rows produced by :func:`spice_engine.run_analysis`.
No simulated value is hard-coded here; an empty series produces an explicit
"no data" message instead of a plausible-looking trace.
"""

import html
import math

_WIDTH = 720
_HEIGHT = 320
_LEFT = 66
_RIGHT = 638
_TOP = 28
_BOTTOM = 268
_GRID_STEPS = 5


def _finite(rows, key, scale=1.0):
    values = []
    for row in rows:
        try:
            value = float(row[key]) * scale
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    return values


def _bounds(values):
    low, high = min(values), max(values)
    if math.isclose(low, high):
        pad = abs(low) * 0.1 or 1.0
        return low - pad, high + pad
    pad = (high - low) * 0.08
    return low - pad, high + pad


def _x(value, low, high):
    return _LEFT + (value - low) / (high - low) * (_RIGHT - _LEFT)


def _y(value, low, high):
    return _BOTTOM - (value - low) / (high - low) * (_BOTTOM - _TOP)


def _number(value):
    if value == 0 or 1e-3 <= abs(value) < 1e5:
        return f"{value:.3g}"
    return f"{value:.2e}"


def _grid():
    """Axis grid drawn with explicit M/L path commands (no chart library)."""
    parts = []
    for step in range(_GRID_STEPS + 1):
        x = _LEFT + (_RIGHT - _LEFT) * step / _GRID_STEPS
        parts.append(f'<path d="M{x:.2f} {_TOP} L{x:.2f} {_BOTTOM}" '
                     'stroke="#dce7ee" fill="none"/>')
        y = _TOP + (_BOTTOM - _TOP) * step / _GRID_STEPS
        parts.append(f'<path d="M{_LEFT} {y:.2f} L{_RIGHT} {y:.2f}" '
                     'stroke="#dce7ee" fill="none"/>')
    parts.append(f'<path d="M{_LEFT} {_TOP} L{_LEFT} {_BOTTOM} '
                 f'L{_RIGHT} {_BOTTOM}" stroke="#486275" fill="none"/>')
    return "\n".join(parts)


def _ticks(values, low, high, axis):
    parts = []
    for step in range(_GRID_STEPS + 1):
        value = low + (high - low) * step / _GRID_STEPS
        if axis == "x":
            at = _x(value, low, high)
            parts.append(
                f'<text x="{at:.2f}" y="{_BOTTOM + 18}" text-anchor="middle" '
                f'font-size="11" fill="#486275">{_number(value)}</text>'
            )
        else:
            at = _y(value, low, high)
            parts.append(
                f'<text x="{_LEFT - 8}" y="{at + 4:.2f}" text-anchor="end" '
                f'font-size="11" fill="#486275">{_number(value)}</text>'
            )
    return "\n".join(parts)


def _legend(items):
    parts = []
    for index, (label, colour) in enumerate(items):
        x = _LEFT + 12 + index * 170
        parts.append(
            f'<rect x="{x}" y="{_TOP + 4}" width="18" height="4" fill="{colour}"/>'
            f'<text x="{x + 24}" y="{_TOP + 12}" font-size="12" fill="#17344b">'
            f'{html.escape(label)}</text>'
        )
    return "\n".join(parts)


def _empty(label):
    return (
        f'<svg viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" '
        f'aria-label="{html.escape(label)}" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="#f6fafc"/>'
        f'<text x="{_WIDTH / 2}" y="{_HEIGHT / 2}" text-anchor="middle" '
        'font-size="16" fill="#486275">ไม่มีข้อมูลจาก ngspice</text></svg>'
    )


def _polyline(rows, x_key, y_key, x_low, x_high, y_low, y_high,
              x_scale=1.0, colour="#07766e"):
    points = []
    for row in rows:
        try:
            x_value = float(row[x_key]) * x_scale
            y_value = float(row[y_key])
        except (KeyError, TypeError, ValueError):
            continue
        if not (math.isfinite(x_value) and math.isfinite(y_value)):
            continue
        points.append(f"{_x(x_value, x_low, x_high):.2f},"
                      f"{_y(y_value, y_low, y_high):.2f}")
    if not points:
        return ""
    return (f'<polyline points="{" ".join(points)}" fill="none" '
            f'stroke="{colour}" stroke-width="2.2"/>')


def render_bode_svg(series):
    """Render gain/phase against frequency from an ngspice ``.ac`` series."""
    label = "กราฟ Bode จาก ngspice: Gain (dB) และ Phase (°) เทียบ Frequency (Hz)"
    rows = [row for row in (series or []) if isinstance(row, dict)]
    freqs = _finite(rows, "freq")
    gains = _finite(rows, "gain_db")
    phases = _finite(rows, "phase_deg")
    if not (freqs and gains and phases):
        return _empty(label)

    x_low, x_high = _bounds(freqs)
    gain_low, gain_high = _bounds(gains)
    phase_low, phase_high = _bounds(phases)
    return "\n".join([
        f'<svg viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" '
        f'aria-label="{html.escape(label)}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="#f6fafc"/>',
        _grid(),
        _polyline(rows, "freq", "gain_db", x_low, x_high,
                  gain_low, gain_high, colour="#07766e"),
        _polyline(rows, "freq", "phase_deg", x_low, x_high,
                  phase_low, phase_high, colour="#a65a2c"),
        _ticks(freqs, x_low, x_high, "x"),
        _ticks(gains, gain_low, gain_high, "y"),
        f'<text x="{(_LEFT + _RIGHT) / 2:.1f}" y="{_HEIGHT - 8}" '
        'text-anchor="middle" font-size="13" fill="#17344b">Frequency (Hz)</text>',
        f'<text x="12" y="{(_TOP + _BOTTOM) / 2:.1f}" transform='
        f'"rotate(-90 12 {(_TOP + _BOTTOM) / 2:.1f})" text-anchor="middle" '
        'font-size="13" fill="#07766e">Gain (dB)</text>',
        f'<text x="{_WIDTH - 10}" y="{(_TOP + _BOTTOM) / 2:.1f}" transform='
        f'"rotate(90 {_WIDTH - 10} {(_TOP + _BOTTOM) / 2:.1f})" text-anchor="middle" '
        'font-size="13" fill="#a65a2c">Phase (°)</text>',
        _legend([("Gain (dB)", "#07766e"), ("Phase (°)", "#a65a2c")]),
        "</svg>",
    ])


def render_transient_svg(series):
    """Render Vin/Vout against time (ms) from an ngspice ``.tran`` series."""
    label = "กราฟสัญญาณตามเวลาจาก ngspice: Vin และ Vout เทียบเวลา (ms)"
    rows = [row for row in (series or []) if isinstance(row, dict)]
    times = _finite(rows, "time", scale=1000.0)
    volts = _finite(rows, "vin") + _finite(rows, "vout")
    if not (times and volts):
        return _empty(label)

    x_low, x_high = _bounds(times)
    y_low, y_high = _bounds(volts)
    return "\n".join([
        f'<svg viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" '
        f'aria-label="{html.escape(label)}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{_WIDTH}" height="{_HEIGHT}" fill="#f6fafc"/>',
        _grid(),
        _polyline(rows, "time", "vin", x_low, x_high, y_low, y_high,
                  x_scale=1000.0, colour="#07766e"),
        _polyline(rows, "time", "vout", x_low, x_high, y_low, y_high,
                  x_scale=1000.0, colour="#a65a2c"),
        _ticks(times, x_low, x_high, "x"),
        _ticks(volts, y_low, y_high, "y"),
        f'<text x="{(_LEFT + _RIGHT) / 2:.1f}" y="{_HEIGHT - 8}" '
        'text-anchor="middle" font-size="13" fill="#17344b">Time (ms)</text>',
        f'<text x="12" y="{(_TOP + _BOTTOM) / 2:.1f}" transform='
        f'"rotate(-90 12 {(_TOP + _BOTTOM) / 2:.1f})" text-anchor="middle" '
        'font-size="13" fill="#17344b">Voltage (V)</text>',
        _legend([("Vin (V)", "#07766e"), ("Vout (V)", "#a65a2c")]),
        "</svg>",
    ])
