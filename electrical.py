import math
import sys


def analyze_dc(voltage_v, resistance_ohm):
    """Return current and power for a simple DC circuit using Ohm's law."""
    try:
        voltage_v = float(voltage_v)
        resistance_ohm = float(resistance_ohm)
    except (TypeError, ValueError) as exc:
        raise ValueError("Voltage and resistance must be numeric values.") from exc

    if not math.isfinite(voltage_v) or not math.isfinite(resistance_ohm):
        raise ValueError("Voltage and resistance must be finite numeric values.")

    if resistance_ohm <= 0:
        raise ValueError("Resistance must be greater than zero.")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3:
            voltage_v = sys.argv[1]
            resistance_ohm = sys.argv[2]
        else:
            voltage_v = 12
            resistance_ohm = 6

        result = analyze_dc(voltage_v, resistance_ohm)
        print(f"Voltage: {voltage_v} V")
        print(f"Resistance: {resistance_ohm} ohm")
        print(f"Current: {result['current_a']:.3f} A")
        print(f"Power: {result['power_w']:.3f} W")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)