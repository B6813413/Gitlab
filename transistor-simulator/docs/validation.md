# Validation — Transistor DC Bias Simulator (Week 2)

วันที่: 2026-11-10 | Branch: `week2/flask-dc-bias`
Machines/tools: Git 2.56.0.windows.4, Python 3.12.7, Flask 3.1.3, Windows 11

## 1. Automated tests (A6)

Command (จากโฟลเดอร์ `transistor-simulator/`):

```powershell
python -m unittest discover -s tests -v
```

Latest run from repo root (`python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`):

```
Ran 24 tests in 0.016s
OK
```

Breakdown:

- `tests/test_dc_bias.py` — 17 tests
  - `TestDCOperatingPoint`: active reference case (Lab 02), saturation, cutoff, β=1
  - `TestParseResistance`: `kΩ` suffix parsing, `100k` → 100000, `2.2k` → 2200, invalid input
  - `TestValidateInputs`: blank / non-numeric / non-finite / non-positive / β≤0 / VBE range / zero divider
- `tests/test_web.py` — 7 tests
  - `TestIndexPage`: GET / = 200 + form fields
  - `TestCalculateRoute`: POST valid = 200 + formatted results, saturation warning, formatters, 400 on invalid input, sticky form, all-blank

Git Bash capture (task-done logs to `.superpowers/sdd/.../progress.md`):

```
Task 1: f958116..23c373f, Task 2: 23c373f..13afe2f, Task 3: 13afe2f..85b6312,
Task 4: 85b6312..df3705c, Task 5: df3705c..a6ee257, Task 6: a6ee257..7577086,
Task 7: 7577086..625ca9b
```

## 2. Independent hand calculation vs app (A3)

Duty case (ค่าเริ่มต้น Lab 02): `VCC=12 V, R1=100kΩ, R2=22kΩ, RC=2.2kΩ, RE=1kΩ, β=100, VBE=0.70 V`

Hand calculation follows Lab 02 §06:

```
VTH = 12 × 22 / (100 + 22)  = 2.164 V
RTH = (100k × 22k) / 122k    = 18.033 kΩ
IB  = (2.164 − 0.70) / (18.033k + 101 × 1k) = 12.299 µA
IC  = 100 × IB                = 1.230 mA
IE  = 101 × IB                = 1.242 mA
VE  = 1.242 mA × 1 kΩ         = 1.242 V
VB  = 1.242 V + 0.70 V        = 1.942 V
VC  = 12 − 1.230 mA × 2.2 kΩ  = 9.294 V
VCE = 9.294 − 1.242 = 8.052 V   → Active (VCE > 0.2 V)
```

| Quantity | Hand check | App output | Match (3 dp) |
|---|---|---|---|
| VTH | 2.164 V | 2.164 V | ✓ |
| RTH | 18.033 kΩ | 18.033 kΩ | ✓ |
| IB | 12.299 µA | 12.299 µA | ✓ |
| IC | 1.230 mA | 1.230 mA | ✓ |
| IE | 1.242 mA | 1.242 mA | ✓ |
| VE | 1.242 V | 1.242 V | ✓ |
| VB | 1.942 V | 1.942 V | ✓ |
| VC | 9.294 V | 9.294 V | ✓ |
| VCE | 8.052 V | 8.052 V | ✓ |
| Region | Active | Active | ✓ |

Saturation sanity check (RC = 10 kΩ): app reports region = `Saturation`,
`IC(sat) ≈ 1.073 mA`, and shows the `Forward-Active` warning — values come
from the linear model and are not silently presented as precise.

## 3. Acceptance checks (Lab 02 §09)

| # | Check | Method | Result |
|---|---|---|---|
| A1 | GET / = 200 + form | `unittest` + live HTTP smoke test (`Invoke-WebRequest`) | PASS (HTTP 200) |
| A2 | POST / computes in Python | `unittest` + live HTTP POST of `vcc=12 …` | PASS (HTTP 200, values rendered) |
| A3 | Engineering reference values | Hand calc table above | PASS |
| A4 | Invalid input shows error, no crash | Unit tests + HTTP POST `vcc=0` | PASS (HTTP 400, `ต้องมากกว่า 0`) |
| A5 | Outside Active Region warning | Unit test `test_post_saturation_shows_warning` | PASS |
| A6 | ≥3 math tests + ≥1 Flask client test | 24 tests total (17 math + 7 web) | PASS |
| A7 | Clone → install → run → test | Fresh clone of branch in clean temp dir | PASS (24 tests, OK) |

Live server smoke test (Flask dev server, port 5000):

```
127.0.0.1 - - GET  / HTTP/1.1" 200 -
127.0.0.1 - - POST / HTTP/1.1" 200 -
127.0.0.1 - - POST / HTTP/1.1" 400 -
```

## 4. Limitations

- Results only valid for **Forward-Active** with fixed β and fixed VBE (Lab 02 §06)
- Saturation / cutoff: the app shows the linear-model numbers with a warning and
  the clamped `IC(sat)`; it does **not** solve the piecewise model or ngspice
- Debug server is for local development only
