# Validation — Lab 04 BJT Amplifier Simulator (B1–B8) + Lab 03 regression

วันที่ตรวจ: **2026-11-24** | repo: `transistor-simulator` | remote: https://github.com/B6813413/Gitlab.git
branch: `lab04/spice-simulator` | Python 3.12, Flask 3.1, Windows 11

## สภาพแวดล้อมจริง

| รายการ | ค่าที่ตรวจจริง |
|---|---|
| Browser | **OpenCode Browser Tool** (`tabs.open`, `navigate`, `evaluate`, `wait`, `snapshot`, `console`, `frames`) — Playwright MCP ไม่พร้อมใน harness นี้ จึงใช้ tool ที่ใบงานอนุญาตและระบุวิธีจริงในตาราง |
| Viewport screenshot | Chrome headless (`--headless=new --window-size=... --screenshot=...`) สำหรับภาพทุกไฟล์ใน `docs/captures/` (โพสต์ฟอร์มจริงผ่าน iframe กว้าง 785/390px สำหรับ B5/B6/B8); ตรวจ computed layout เพิ่มด้วย iframe จริงใน OpenCode Browser Tool |
| Server | `python -m flask --app app run --debug --port 5000` จาก `transistor-simulator/`; เปิด `http://127.0.0.1:5000/` สำเร็จ title = `Lab 04: BJT Amplifier Simulator — ENG29 2121` |
| ngspice | **`ngspice-47`** — `** ngspice-47 : Circuit level simulation program`, `** Compiled with KLU Direct Linear Solver`, `** Copyright 2001-2026, The ngspice team.` |
| วิธีได้ binary | `winget install --id ngspice` → `No package found matching input criteria.` จึงโหลด `ngspice-47_64.7z` จาก SourceForge แยกด้วย `tar -xf` และใช้ `ngspice_con.exe` เป็น `ngspice.exe` ใน `C:\Users\B6813413\AppData\Local\Temp\opencode\ngspice-bin` แล้วเติมลง `PATH` |
| BJT model ใน netlist | **`.model QNPN NPN(IS=1e-14 BF=100 VAF=100)`** (ไม่มี emitter bypass capacitor) |
| Console | ตรวจ `browser.console({level:'error'})` หลังโหลด/หลังรัน → `[]` ทั้งสองแท็บ (ไม่มี JS error) |

เกณฑ์การอ่านผล: ค่าที่คัดมาเป็นข้อความ/DOM จากหน้าเว็บจริงหลังส่งฟอร์ม ไม่ใช่การอ่านโค้ดหรือ curl
และกราฟต้องมี series มาจาก log ของ ngspice จริงเท่านั้น

## ตาราง B1–B8 (ผลที่เห็นจริงจาก browser)

| Case | Action ใน Browser / Expected | Observed จริง | หน่วย | วิธีตรวจ | Status | หลักฐาน |
|---|---|---|---|---|---|---|
| **B1 · Regression** | เปิด Divider / Fixed / Emitter แล้วกรอกชุดค่า Lab 03; ผลต้องตรงค่าอ้างอิงและสลับโหมดได้ | Divider: IC **1.230 mA**, VCE **8.052 V** (VB 1.942, VE 1.242, VC 9.294, VTH 2.164 V, RTH 18.033 kΩ, IB 12.299 µA) · Fixed: IC **1.130 mA**, VCE **9.514 V** (VB 0.700, VE 0.000, IB 11.300 µA) · Emitter: IC **1.026 mA**, VCE **8.705 V** (VB 1.737, VE 1.037, VC 9.742, IB 10.263 µA) | mA, V | OpenCode Browser Tool + `evaluate` fill + `requestSubmit()` + `wait('text')` + `evaluate` อ่าน `<table>` | **PASS** | h2 เปลี่ยนเป็น `[voltage_divider]`, `[fixed]`, `[emitter]`; ไม่มี `.field-error`; ตารางผลตรง A1/A2/A3 เดิมทุกตัว |
| **B2 · DC SPICE** | เลือก CE Reference + Analysis `spice_dc` แล้ว run; ต้องเห็น VB/VE/VC/VCE/IC จาก ngspice + model/status | `Engine: ngspice · Status: success · Model: QNPN`; VB **1.949 V**, VE **1.289 V**, VC **9.189 V**, VCE **7.900 V**, IC **1.278 mA** | V, mA | OpenCode Browser Tool POST จริง + ngspice 47 | **PASS** | log: `0  1.949112e+00  1.289454e+00  9.189410e+00  1.278193e-03`; `<details>` แสดง log excerpt จริง |
| **B3 · Change RE** | เปลี่ยน RE เพียงค่าเดียว (1 → 2 kΩ) แล้ว run DC ซ้ำ; OP ต้องเปลี่ยน ไม่ใช่ค่าค้าง | ก่อน: IC **1.278 mA**, VCE **7.900 V** → หลัง: IC **0.696 mA**, VCE **9.065 V** (VB 2.048 V, VE 1.405 V, VC 10.469 V) | mA, V, kΩ | OpenCode Browser Tool + `wait('textGone')` กันอ่านผลเก่า | **PASS** | log รอบหลัง: `0  2.048198e+00  1.404550e+00  1.046912e+01  6.958787e-04`; status ยัง `success` |
| **B4 · AC** | Run AC แล้วดู Bode; frequency/gain/phase ต้องมีหน่วยและมาจาก run จริง | `Status: success`, **101 จุดข้อมูล**; label = `กราฟโบเดแสดงอัตราขยายและเฟสเทียบความถี่ จากผลจำลอง 101 จุดข้อมูล`; polyline 2 เส้น × 101 points; axis `Frequency (Hz)`, `Gain (dB)`, `Phase (°)` | Hz, dB, ° | OpenCode Browser Tool + อ่าน `aria-label`, `<text>`, `<polyline>` | **PASS** | log ท้าย: `100  1.000000e+06  -3.51402e+01  -3.14159e+00`; caption ระบุสเกลลอการิทึม |
| **B5 · Transient** | Run `.tran` ที่ **10 mV peak, 1 kHz**; เห็น Vin/Vout ตามเวลา มีป้ายเวลา/แรงดัน และสัญญาณกลับเฟส | `Status: success`, **508 จุดข้อมูล**; axis `Time (ms)` / `Voltage (V)`; legend `Vin (V)`, `Vout (V)`; correlation ของ y-coordinate Vincent/Vout = **−0.999997** → กลับเฟสตามข้อสมมติ CE | V, ms | OpenCode Browser Tool + SVG points + log + screenshot | **PASS** | log ท้าย: `507  5.000000e-03  -1.22465e-17  -2.42388e-05`; captures/`b5-transient-10mV-1kHz.png` |
| **B6 · Change Source** | เปลี่ยน amplitude 0.01 → 0.02 V แล้ว run ซ้ำ; waveform ต้องเปลี่ยนไม่ใช่กราฟ hard-code | peak |Vin| **0.00999845 → 0.0199969 V**, peak |Vout| **0.0175098 → 0.03503924 V** (เพิ่ม ~2× ตาม amplitude ใหม่) | V | OpenCode Browser Tool + parse log table ก่อน/หลัง + screenshot | **PASS** | captures/`b6-transient-20mV-1kHz.png`; หลัง POST ฟอร์มโชว์ `amp = 0.02` (sticky) และ log รอบหลังยืนยันว่า ngspice ได้ 20 mV |
| **B7 · Invalid / Fail** | ใส่ RE = 0 แล้ว run | แจ้ง **`ต้องมากกว่า 0`** ใต้ช่อง RE; ไม่มี `.panel-spice`, ไม่มี chart, ไม่มี badge `Status: success` | — | OpenCode Browser Tool + `field-error` DOM | **PASS** | error เกิดจาก `validate_spice_inputs()` ฝั่ง Flask (HTTP 400) ก่อนเรียก ngspice; ไม่โชว์ผลสำเร็จปลอม |
| **B8 · UI** | เปิด desktop/phone viewport แล้วเปลี่ยนโหมด; กราฟ/หน่วย/ปุ่มอ่านง่าย ไม่มีเนื้อหาถูกตัด | Desktop (800px DOM): layout `756.219px`, chart **717px**, overflow **0** · Phone (iframe 390px): layout `346.219px` (single column), chart viewport **307px**, SVG **760px** (เลื่อนใน `.chart`), page overflow **0**, ปุ่มกว้าง 309px; axis/legend ครบทั้งสองขนาด | px | OpenCode Browser Tool DOM + Chrome headless screenshots | **PASS** | captures/`b8-desktop-bode-result.png` (1280×900), `b8-mobile-bode-result.png` (390×1200); ตรวจ computed style ใน iframe 390px ด้วย browser tool |

### UI provenance ที่ตรวจเพิ่มหลัง code review

สำหรับ `analysis != "bias"` ตรวจจากหน้าเว็บจริงแล้ว: `select[name=mode]`, `#beta`, `#vbe`
มี `disabled` และมีข้อความ “ไม่ใช้ใน SPICE”; หัวข้อวงจรเป็น `[CE Reference]` พร้อม
`aria-label="Common-emitter amplifier reference circuit"`; ภาพแสดง R1/R2/RE (ไม่ใช่ RB/GND)
และมีหมายเหตุ “β = 100 จาก .model · CIN 10 µF · COUT 10 µF · RL 10 kΩ”
(ค่าที่กรอกจะแสดงกลับหลัง POST) — ป้องกันความสับสนว่าช่อง β หรือโหมด Lab 03 มีผลต่อ ngspice

## รายละเอียดหลักฐานที่สำคัญ

### ngspice log — B2/B3 (DC operating point)

```text
Circuit: ce amplifier reference (lab 04, no emitter bypass)
Operating Point  Tue Nov 24 18:08:34  2026
Index   v(b)            v(e)            v(c)            @q1[ic]
0       1.949112e+00    1.289454e+00    9.189410e+00    1.278193e-03

# หลังเปลี่ยน RE = 2 kΩ (B3)
Operating Point  Tue Nov 24 18:08:51  2026
0       2.048198e+00    1.404550e+00    1.046912e+01    6.958787e-04
```

### ngspice log — B4/B5/B6 (series จริง)

```text
# AC ท้ายตาราง (101 rows)
100     1.000000e+06    -3.51402e+01    -3.14159e+00

# Transient 10 mV/1 kHz — สองแถวต่อเนื่อง + แถวสุดท้าย (508 rows)
503     4.962800e-03    -2.316120e-03    4.029522e-03
504     4.972800e-03    -1.700720e-03    2.952216e-03
507     5.000000e-03    -1.22465e-17    -2.42388e-05

```

สองแถวตัวอย่างด้านบนมาจากรัน 10 mV; สำหรับรัน 20 mV อ่าน peak ได้โดยตรงจาก
`.print` ของรอบนั้นว่า **peak |vin| = 1.999690e-02 V** และ **peak |vout| = 3.503924e-02 V**
(ไม่ได้นำแถวจากสองรันมาปนกัน)

### ความคลาดเคลื่อนของ SPICE DC เทียบ Lab 03 (ต้องอ่านก่อนเทียบค่า)

Lab 03 ใช้แบบจำลองเชิงเส้นที่สมมติ **VBE = 0.70 V คงที่** และ β = 100 คงที่
ส่วน SPICE ใช้ `.model QNPN NPN(IS=1e-14 BF=100 VAF=100)` ซึ่งคำนวณ VBE จากกระแสจริง
จึงได้ VBE ≈ 1.949 − 1.289 = **0.660 V** ที่จุดทำงานนี้ และ IC ≈ 1.278 mA แทน 1.230 mA

| แหล่งผล | VB | VE | VC | VCE | IC |
|---|---|---|---|---|---|
| Analytical Divider (A1) | 1.942 V | 1.242 V | 9.294 V | 8.052 V | 1.230 mA |
| ngspice `.op` (B2) | 1.949 V | 1.289 V | 9.189 V | 7.900 V | 1.278 mA |

นี่เป็น **ความแตกต่างของโมเดล ไม่ใช่ regression**: สมการ Lab 03 ยังผ่าน A1–A5 ทุกกรณี
(section ด้านล่าง) และหน้าเว็บแสดงที่มาของผลแต่ละแบบแยกกันแล้ว

## Automated tests

```powershell
python -m unittest discover -s tests -v
```

```text
Ran 123 tests in 0.071s
OK
```

ครอบคลุม: สมการ/validation Lab 03, HTTP 200/400 เดิม, netlist builder + input guards,
parser สำหรับ DC/AC/transient, runner (mock, มี regression ที่กัน `-r run.raw`
เพราะ ngspice 47 ข้าม `.print`), Flask dispatch, accessibility/units ของ SVG,
โครงสร้าง UI 2 forms + analysis selector, sticky SPICE POST, SPICE UI provenance
(ช่อง Lab 03 ถูกปิด / ภาพ CE Reference) และ mobile chart/caption tests

## Lab 03 A1–A5 (historical — ยังผ่านอยู่ใน B1)

ค่าร่วม: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V; เกณฑ์ |ΔIC| ≤ 0.01 mA, |ΔVCE| ≤ 0.02 V

| Case | อินพุต | IC อ้างอิง | IC จริง | VCE อ้างอิง | VCE จริง | Status |
|---|---|---|---|---|---|---|
| A1 | Divider · R1=100, R2=22, RE=1 kΩ | 1.2299 mA | **1.230 mA** | 8.0522 V | **8.052 V** | PASS |
| A2 | Fixed · RB=1000 kΩ | 1.1300 mA | **1.130 mA** | 9.5140 V | **9.514 V** | PASS |
| A3 | Emitter · RB=1000 kΩ, RE=1 kΩ | 1.0263 mA | **1.026 mA** | 8.7055 V | **8.705 V** | PASS |
| A4 | Emitter · RB=1000 kΩ, RE=2 kΩ | 0.9401 mA | **0.940 mA** | 8.0328 V | **8.033 V** | PASS |
| A5 | Fixed · RB=0 | error | `ค่า RB (Fixed Bias) ต้องมากกว่า 0`, HTTP 400, ไม่มีตารางผล | — | — | PASS |

## ส่วนที่ AI ช่วย / นักศึกษาตรวจ

- **AI ช่วย:** เขียน `spice_engine.py`, `charts.py`, dispatch ใน `app.py`, template/CSS,
  tests และรัน browser acceptance ตามลำดับ B1–B8
- **นักศึกษาควรตรวจเอง:** ทวน netlist กับ circuit ในใบงาน, เปลี่ยนค่า R1/R2/RC/RE แล้วเทียบ
  ทิศทางของ OP/gain, อ่าน log ว่า series มาจาก `.print` จริง, และปรับคำใน reflection ให้เป็นภาษาตัวเอง
- **บั๊กที่พบและแก้ระหว่างตรวจ:** ngspice 47 ข้าม `.print` ทันทีที่ runner ส่ง `-r run.raw`
  → ลบ flag นั้นออก (มี regression test รองรับ) ทำให้ DC/AC/transient อ่านค่าได้จริง
- **hardening เพิ่มระหว่างตรวจ:** ตะแกร่งความถี่ของ Bode ถูกปรับให้ตรงสเกลลอการิทึม
  (commit `7570de8`), SPICE POST ส่งค่ากรอกกลับมาทุก branch (commit `b0fb534`)
  และ code review รอบสุดท้ายเพิ่ม test สำหรับ SPICE UI/mobile chart/caption → รวม 123 tests
- **บั๊ก UI ที่ review พบแล้วแก้:** ตอนใช้ SPICE หน้าเว็บยังโชว์ช่อง `mode/β/VBE` แบบ
  Required และภาพวงจรตามโหมด Lab 03 ทั้งที่ engine ไม่รับค่าเหล่านั้น → ปิดช่อง,
  ตรึงภาพเป็น CE Reference และระบุว่า β=100 มาจาก `.model` (ตรวจใน browser แล้ว)

## ข้อจำกัด

- ต้องมี ngspice 47 ใน `PATH` สำหรับ analysis แบบ SPICE; tests ใช้ mock ไม่ต้องพึ่ง binary
- AC เป็น small-signal เชิงเส้นรอบ operating point, transient ใช้โมเดลเดียวกัน (ไม่มี piecewise)
- ไม่มีการเก็บ config ข้าม session, ไม่มี AJAX/login/ฐานข้อมูล, ใช้ Flask dev server ในเครื่องเท่านั้น
- ภาพทั้งหมดใน `docs/captures/` เก็บด้วย Chrome headless (B5/B6 ผ่าน iframe กว้าง 785px
  ที่โพสต์ฟอร์มจริง) เพื่อให้ตรง UI รอบสุดท้าย; ค่าตัวเลข/seriesตัดสินจาก DOM + ngspice log
  ใน OpenCode Browser Tool ไม่ใช่จากพิกเซลในภาพ
- tool ไม่มีคำสั่ง resize viewport โดยตรง จึงตรวจ computed layout เพิ่มด้วย iframe จริง 390px
