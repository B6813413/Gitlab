# BJT Amplifier Simulator — ENG29 2121 Lab 04

Flask web app หน้าเดียวที่ต่อยอดจาก Lab 03 โดยเปรียบเทียบ **ผลคำนวณ DC แบบสมการ**
กับ **ผลจำลองจริงจาก ngspice** ของวงจร Common-Emitter Amplifier:

- **Analytical DC Bias (Lab 03)** — Voltage Divider / Fixed / Emitter (สมการเดิมไม่เปลี่ยน)
- **SPICE DC (.op)** — VB/VE/VC/VCE/IC จาก operating point ของ ngspice
- **SPICE AC (Bode)** — gain (dB) = `vdb(vout) − vdb(vin)` และ phase (°)
  = `vp(vout) − vp(vin)` จาก small-signal (อ้างอิงที่ Vin ไม่ใช่ค่า absolute ของ Vout)
- **SPICE Transient** — Vin/Vout ตามเวลา (ms) ที่ความถี่/แอมพลิจูดที่ผู้ใช้กรอก

ทุกผลลัพธ์มีป้ายแหล่งที่มา (`engine`, `status`, `model`) และ log จริงจาก ngspice
กราฟทั้งสองแบบเป็น SVG ที่สร้างจาก series ใน log เท่านั้น (ไม่มีค่าฮาร์ดโค้ดและไม่เพิ่ม JS library)

**Repository / Remote:** https://github.com/B6813413/Gitlab.git
**Branch ที่ใช้ทำ Lab 04:** `lab04/spice-simulator`

## โครงสร้าง

```text
transistor-simulator/
├── app.py                    # Flask HTTP: parse/validate/dispatch/render + formatters
├── dc_bias.py                # pure Python: สมการ Lab 03 (ไม่ import Flask)
├── spice_engine.py           # pure Python: netlist builder, validation, ngspice runner, parser
├── charts.py                 # pure Python: SVG Bode/transient จาก series จริง
├── templates/index.html      # GET selector + POST form + analytical/SPICE result panels
├── static/style.css          # responsive layout (desktop/mobile)
├── tests/
│   ├── test_dc_bias.py       # สมการ/validation Lab 03
│   ├── test_web.py           # HTTP/form Lab 03 (regression)
│   ├── test_spice_engine.py  # netlist/parser/runner (mock ngspice)
│   ├── test_spice_web.py     # dispatch + UI structure
│   └── test_charts.py        # SVG axes/units/accessibility/data fidelity
├── opencode.json             # Playwright MCP config
├── requirements.txt          # มี Flask เท่านั้น
├── AGENTS.md
└── docs/
    ├── validation.md         # A1–A5 (Lab 03) + B1–B8 (Lab 04) พร้อมหลักฐาน
    ├── design-note.md        # Lab 03 → Lab 04 architecture delta
    ├── reflection.md         # สะท้อนคิด
    └── captures/             # screenshot จริง B5/B6/B8
```

## ติดตั้ง

ต้องการ Python 3.12 และ Flask (dependency เดียวของโปรเจกต์):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
python -m pip install -r requirements.txt
```

### ngspice (external binary — ไม่ใช่ pip dependency)

รัน analysis แบบ SPICE ต้องมี `ngspice` ใน `PATH`:

```powershell
ngspice --version
# ต้องเห็น ** ngspice-47 : Circuit level simulation program
```

บน Windows เครื่องนี้ `winget install --id ngspice` ไม่พบแพ็กเกจ จึงติดตั้งแบบพกพาแทน:

1. โหลด `ngspice-47_64.7z` จาก https://ngspice.sourceforge.io/download.html
2. แยกไฟล์ด้วย `tar -xf ngspice-47_64.7z -C <folder>` (bsdtar ของ Windows รองรับ 7z)
3. เพิ่ม `<folder>\Spice64\bin` ลง `PATH`

ตัวอย่างสำหรับ session นี้ (ใช้ console build เพื่อให้ `-o run.log` เขียน log ข้อความ):

```powershell
$env:PATH = 'C:\Users\B6813413\AppData\Local\Temp\opencode\ngspice-bin;' + $env:PATH
ngspice --version
```

เทสต์ทั้งหมดใช้ mock บน `subprocess.run` จึง **รันได้โดยไม่ต้องติดตั้ง ngspice**;
เฉพาะ browser acceptance B2–B6 ที่ใช้ solver จริงต้องมี binary

## รันแอป

```powershell
# workdir: transistor-simulator/
$env:PATH = '<ngspice bin folder>;' + $env:PATH
python -m flask --app app run --debug
# เปิด http://127.0.0.1:5000/
```

เลือก **Analysis** ในฟอร์มด้านบน → กรอกค่า (SPICE จะโชว์ RL/CIN/COUT/Vin/freq/model เพิ่ม)
→ กดปุ่ม Run/Calculate → อ่านผลด้านขวา

## รันเทสต์

```powershell
python -m unittest discover -s tests -v
```

ผลล่าสุด: **Ran 135 tests ... OK** (รันจากโฟลเดอร์ `transistor-simulator/`)

## โมเดลและหน่วยที่ใช้

Circuit อ้างอิง Lab 04 (ไม่มี emitter bypass capacitor) ถูกเขียนใน `spice_engine.py`:

```spice
.model QNPN NPN(IS=1e-14 BF=100 VAF=100)
```

ค่าเริ่มต้น: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ,
RL = 10 kΩ, CIN = COUT = 10 µF, Vin = 10 mV peak, f = 1 kHz

- ตัวต้านทานรับ `kΩ/Ω` หรือ suffix `k`; C รับเป็น µF; `freq` รับ `Hz` หรือ suffix `k`
- AC: decade sweep 10 Hz → 1 MHz (101 จุด) จาก `.ac dec 20 10 1meg`
- Transient: 0 → 5 ms, step 10 µs (508 จุด) จาก `.tran 10u 5m`
- `.print` ถูกใช้เป็นแหล่งข้อมูล (ไม่ได้อ่าน rawfile) เพราะ ngspice 47 จะข้าม `.print`
  ทันทีที่ส่ง `-r run.raw`; runner จึงส่งเฉพาะ `-b -o run.log case.cir`

## ความแตกต่างที่ต้องระวัง

- ผล SPICE DC **ไม่เท่ากับผล analytical** ของ Lab 03 โดยตรง: Lab 03 สมมติ VBE คงที่ 0.7 V
  และ β คงที่ ส่วนโมเดล `QNPN` คำนวณ VBE จาก `IS`, `BF`, `VAF` จริง ตัวอย่างค่าเริ่มต้น:
  - Analytical Divider: IC ≈ 1.230 mA, VCE ≈ 8.052 V
  - SPICE `.op`: VB 1.949 V, VE 1.289 V, VC 9.189 V, VCE 7.900 V, IC 1.278 mA
  นี่เป็นความคลาดเคลื่อนของโมเดล ไม่ใช่ regression ของสมการ Lab 03
- POST แบบ SPICE เป็น partial update: ช่องที่ไม่ได้ส่งจะได้ค่าจาก `SPICE_DEFAULTS`;
  ค่าที่ส่งมาจะถูกแสดงกลับในฟอร์ม (sticky) ทุก branch รวม branch error
- เมื่อเลือก analysis แบบ SPICE ช่อง `mode`, `β`, `VBE` ของ Lab 03 จะถูกปิดใช้งานและ
  ทำเครื่องหมาย “ไม่ใช้ใน SPICE” — netlist ใช้ CE Reference และ `.model QNPN` (BF=100)
  เสมอ จึงไม่รับค่าจากสามช่องนั้น
- บนจอแคบ (≤ 880px) กราฟยังใช้ความกว้างเดิม 760px แล้วเลื่อนแนวนอนใน `.chart`
  แทนการบีบข้อความ; หน้าเว็บยังไม่มี horizontal overflow
- ผล AC เป็น small-signal linearisation รอบ operating point; transient ใช้โมเดลเดียวกัน
- หน้าเว็บเป็น server-rendered form POST ล้วน ๆ ไม่มี AJAX/framework ฝั่งหน้าเว็บ
- Flask dev server ใช้สำหรับพัฒนาในเครื่องเท่านั้น

## ตาราง B1–B8 (ผลที่เห็นจริงจาก browser)

| Case | Action ใน Browser / Expected | Observed จริง | หน่วย | วิธีตรวจ | Status | หลักฐาน |
|---|---|---|---|---|---|---|
| **B1 · Regression** | เปิด Divider / Fixed / Emitter แล้วกรอกชุดค่า Lab 03; ผลต้องตรงค่าอ้างอิงและสลับโหมดได้ | Divider: IC **1.230 mA**, VCE **8.052 V** (VB 1.942, VE 1.242, VC 9.294, VTH 2.164 V, RTH 18.033 kΩ, IB 12.299 µA) · Fixed: IC **1.130 mA**, VCE **9.514 V** (VB 0.700, VE 0.000, IB 11.300 µA) · Emitter: IC **1.026 mA**, VCE **8.705 V** (VB 1.737, VE 1.037, VC 9.742, IB 10.263 µA) | mA, V | OpenCode Browser Tool + `evaluate` fill + `requestSubmit()` + `wait('text')` + `evaluate` อ่าน `<table>` | **PASS** | h2 เปลี่ยนเป็น `[voltage_divider]`, `[fixed]`, `[emitter]`; ไม่มี `.field-error`; ตารางผลตรง A1/A2/A3 เดิมทุกตัว |
| **B2 · DC SPICE** | เลือก CE Reference + Analysis `spice_dc` แล้ว run; ต้องเห็น VB/VE/VC/VCE/IC จาก ngspice + model/status | `Engine: ngspice · Status: success · Model: QNPN`; VB **1.949 V**, VE **1.289 V**, VC **9.189 V**, VCE **7.900 V**, IC **1.278 mA** | V, mA | OpenCode Browser Tool POST จริง + ngspice 47 | **PASS** | log: `0  1.949112e+00  1.289454e+00  9.189410e+00  1.278193e-03`; `<details>` แสดง log excerpt จริง |
| **B3 · Change RE** | เปลี่ยน RE เพียงค่าเดียว (1 → 2 kΩ) แล้ว run DC ซ้ำ; OP ต้องเปลี่ยน ไม่ใช่ค่าค้าง | ก่อน: IC **1.278 mA**, VCE **7.900 V** → หลัง: IC **0.696 mA**, VCE **9.065 V** (VB 2.048 V, VE 1.405 V, VC 10.469 V) | mA, V, kΩ | OpenCode Browser Tool + `wait('textGone')` กันอ่านผลเก่า | **PASS** | log รอบหลัง: `0  2.048198e+00  1.404550e+00  1.046912e+01  6.958787e-04`; status ยัง `success` |
| **B4 · AC** | Run AC แล้วดู Bode; frequency/gain/phase ต้องมีหน่วย มาจาก run จริง และอ้าง Vin (ไม่ใช่ค่า absolute ของ Vout) | `Status: success`, **101 จุดข้อมูล**; label = `กราฟโบเดแสดงอัตราขยายและเฟสเทียบความถี่ จากผลจำลอง 101 จุดข้อมูล`; polyline 2 เส้น × 101 points; axis `Frequency (Hz)`, `Gain (dB)`, `Phase (°)` | Hz, dB, ° | OpenCode Browser Tool + อ่าน `aria-label`, `<text>`, `<polyline>`, `<details><pre>` | **PASS** | netlist พิมพ์ `vdb(vout) vp(vout) vdb(vin) vp(vin)` → log มี 2 ตาราง; gain = `vdb(vout)−vdb(vin)`, phase = `vp(vout)−vp(vin)` (ที่ 1 kHz ≈ **+4.86 dB**, ≈ **−179.9°**); ตาราง Vin ท้าย: `100 1.000000e+06 -4.00000e+01 0.000000e+00`; caption ระบุสเกลลอการิทึม; `browser.console` คืน `[]` |
| **B5 · Transient** | Run `.tran` ที่ **10 mV peak, 1 kHz**; เห็น Vin/Vout ตามเวลา มีป้ายเวลา/แรงดัน และสัญญาณกลับเฟส | `Status: success`, **508 จุดข้อมูล**; axis `Time (ms)` / `Voltage (V)`; legend `Vin (V)`, `Vout (V)`; correlation ของ y-coordinate Vincent/Vout = **−0.999997** → กลับเฟสตามข้อสมมติ CE | V, ms | OpenCode Browser Tool + SVG points + log + screenshot | **PASS** | log ท้าย: `507  5.000000e-03  -1.22465e-17  -2.42388e-05`; captures/`b5-transient-10mV-1kHz.png` |
| **B6 · Change Source** | เปลี่ยน amplitude 0.01 → 0.02 V แล้ว run ซ้ำ; waveform ต้องเปลี่ยนไม่ใช่กราฟ hard-code | peak \|Vin\| **0.00999845 → 0.0199969 V**, peak \|Vout\| **0.0175098 → 0.03503924 V** (เพิ่ม ~2× ตาม amplitude ใหม่) | V | OpenCode Browser Tool + parse log table ก่อน/หลัง + screenshot | **PASS** | captures/`b6-transient-20mV-1kHz.png`; หลัง POST ฟอร์มโชว์ `amp = 0.02` (sticky) และ log รอบหลังยืนยันว่า ngspice ได้ 20 mV |
| **B7 · Invalid / Fail** | ใส่ RE = 0 แล้ว run | แจ้ง **`ต้องมากกว่า 0`** ใต้ช่อง RE; ไม่มี `.panel-spice`, ไม่มี chart, ไม่มี badge `Status: success` | — | OpenCode Browser Tool + `field-error` DOM | **PASS** | error เกิดจาก `validate_spice_inputs()` ฝั่ง Flask (HTTP 400) ก่อนเรียก ngspice; ไม่โชว์ผลสำเร็จปลอม |
| **B8 · UI** | เปิด desktop/phone viewport แล้วเปลี่ยนโหมด; กราฟ/หน่วย/ปุ่มอ่านง่าย ไม่มีเนื้อหาถูกตัด | Desktop (800px DOM): layout `756.219px`, chart viewport **714px**, overflow **0** · Phone (iframe 390px): layout `346.219px` (single column), chart viewport **304px**, SVG **760px** (เลื่อนใน `.chart`), page overflow **0**, ปุ่มกว้าง ~306px; axis/legend ครบทั้งสองขนาด | px | OpenCode Browser Tool DOM + Chrome headless screenshots | **PASS** | captures/`b8-desktop-bode-result.png` (1280×900), `b8-mobile-bode-result.png` (390×1200); ตรวจ computed style ใน iframe 800/390px ด้วย browser tool หลัง CSS polish |

ดูรายละเอียดและหลักฐานเพิ่มเติม (snapshot, ngspice log, screenshot) ใน
[`docs/validation.md`](docs/validation.md) วิธีที่ใช้จริงคือ OpenCode Browser Tool
(Playwright MCP ยังไม่พร้อมในสภาพแวดล้อมนี้) และ Chrome headless สำหรับ screenshot
สองขนาดจอตามที่ใบงานอนุญาตให้ใช้วิธีอื่นและระบุวิธีจริง

## หมายเหตุ Lab 03 ที่ยังใช้เหมือนเดิม

- UI และข้อความ error เป็นภาษาไทย ทุกค่ามีหน่วย
- ฟอร์มแยกเป็น 2 อัน (GET selector + POST input) ห้ามซ้อนกัน
- warning เมื่ออยู่นอก Forward-Active ยังคงอยู่ตามข้อกำหนด Lab 02
- ผลนอก Forward-Active ของ analytical เป็นผลจากสมการเชิงเส้น ไม่ใช่ผลจำลองจริง
