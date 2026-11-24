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

## Browser verification

ดูตาราง **B1–B8** และหลักฐาน (snapshot, ngspice log, screenshot) ใน
[`docs/validation.md`](docs/validation.md) วิธีที่ใช้จริงคือ OpenCode Browser Tool
(Playwright MCP ยังไม่พร้อมในสภาพแวดล้อมนี้) และ Chrome headless สำหรับ screenshot
สองขนาดจอตามที่ใบงานอนุญาตให้ใช้วิธีอื่นและระบุวิธีจริง

## หมายเหตุ Lab 03 ที่ยังใช้เหมือนเดิม

- UI และข้อความ error เป็นภาษาไทย ทุกค่ามีหน่วย
- ฟอร์มแยกเป็น 2 อัน (GET selector + POST input) ห้ามซ้อนกัน
- warning เมื่ออยู่นอก Forward-Active ยังคงอยู่ตามข้อกำหนด Lab 02
- ผลนอก Forward-Active ของ analytical เป็นผลจากสมการเชิงเส้น ไม่ใช่ผลจำลองจริง
