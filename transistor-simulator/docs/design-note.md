# Design Note — Transistor DC Bias Simulator (Week 2)

## 1. Intent

เว็บแอป Flask สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common Emitter แบบ **Voltage-Divider Bias** ตามโจทย์ ENG29 2121 Lab 02
ผู้ใช้กรอกค่าอุปกรณ์แล้วเห็น **VB, VE, VC, VCE, IC** พร้อมค่ากลางที่ใช้คำนวณ
เพื่อใช้ตรวจมือและเขียนรายงานแลป

เป้าหมายการเรียนรู้: อธิบายได้ว่า Frontend, Backend, Template, Static resource,
HTTP Request/Response และ Source Code แต่ละส่วนทำหน้าที่อะไร

## 2. Goals (acceptance A1–A7 ของ Lab 02)

| # | เกณฑ์ | การออกแบบ |
|---|---|---|
| A1 | `GET /` → 200 + ฟอร์ม | Flask route + Jinja template |
| A2 | `POST /` → คำนวณจริงใน Python | `dc_bias.py` pure function |
| A3 | VB, VE, VC, VCE, IC ตรงกับการคำนวณอิสระ | สูตร Thevenin ตาม Lab 02 |
| A4 | Validation: R≤0, β≤0, VCC≤0, missing/non-numeric | `validate_inputs()` |
| A5 | Warning เมื่ออยู่นอก Forward-Active | ตรวจ `VTH ≤ VBE` (cutoff) และ `VCE` ใกล้ saturation |
| A6 | ≥3 tests ตรวจสมการ + ≥1 Flask test client | `tests/test_dc_bias.py`, `tests/test_web.py` |
| A7 | Clone → install → run → test ตาม README | README ครบ + `requirements.txt` |

นอกนั้น: แสดง IB/IE/VTH/RTH เพิ่มเพื่อการตรวจมือ และแปลง `k` (kΩ) → Ω
ก่อนคำนวณ

## 3. Non-goals (Week 2)

Bode plot, transient, signal generator, overlay animation, bias type อื่น
(Fixed/Emitter Bias), SPICE/ngspice, DC load line, ฐานข้อมูล, login,
JavaScript/AJAX

Anti-goal: แอปที่ "ดูสวย" แต่ตรวจสอบย้อนกลับไม่ได้ว่าค่ามาจากสมการใด หรือ
รายงานผลนอก Forward-Active ราวกับเป็นค่าที่เชื่อถือได้

## 4. Constraints

- Flask + Jinja2, server-rendered form POST (ไม่มี JS)
- Python 3.12, dependency เดียวที่เพิ่ม: Flask
- ใช้ `unittest` ตามสไตล์ Week 1 ของ repo
- รันด้วย `python -m flask --app app run --debug` หรือ `python app.py`
- UI ภาษาไทย, ตัวเลขมีหน่วยกำกับทุกค่า

## 5. Approaches ที่พิจารณา

| ทางเลือก | ข้อดี | ข้อเสีย | สรุป |
|---|---|---|---|
| A. Server-rendered form POST (เลือก) | เห็น HTTP request/response ชัด, เทสง่าย, ไม่มี JS | หน้าจอกะพริบตอน submit | **เลือก** |
| B. AJAX/JSON API + fetch | ลื่นกว่า, แยก API ชัด | ซ่อน HTTP flow, เพิ่ม JS ที่ไม่เกี่ยวกับสาระไฟฟ้า | ไม่ใช้ |
| C. SPA (React) | UI ยืดหยุ่น | เกินขอบเขต, เบี่ยงจาก Python backend | ไม่ใช้ |

## 6. สมการอ้างอิง (ตาม Lab 02 §06)

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
IC  = β · IB
IE  = (β + 1) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

จำแนกช่วงการทำงาน (`VCE(sat) = 0.2 V`):

- `VTH <= VBE` (หรือ `IB <= 0`) → **cutoff**
- `VCE < 0.2` → **saturation**
- อื่น ๆ → **active**

`IC(sat) = (VCC − VCE(sat)) / (RC + RE)` แสดงเป็นข้อมูลอ้างอิงเมื่อเข้า saturation

**คำเตือน (A5):** เมื่อไม่อยู่ใน active ต้องแสดงข้อความว่า
"แบบจำลอง Forward-Active ใช้ไม่ได้กับค่านี้ ค่าที่แสดงมาจากสมการเชิงเส้น
จึงไม่ใช่ผลจำลองที่แม่นยำ" และห้ามแสดงผลโดยไม่มี warning

## 7. Validation rules

| เงื่อนไข | ข้อความ |
|---|---|
| ช่องว่าง / ไม่มีค่า | "กรุณากรอกค่านี้" |
| ไม่ใช่ตัวเลข / ไม่ finite (`abc`, `nan`, `inf`, `1e999`) | "ต้องเป็นตัวเลขที่จำกัด" |
| VCC ≤ 0 | "ต้องมากกว่า 0" |
| R1, R2, RC ≤ 0 | "ต้องมากกว่า 0" |
| RE < 0 | "ต้องไม่ติดลบ" |
| β ≤ 0 | "ต้องมากกว่า 0" |
| VBE ≤ 0 หรือ VBE ≥ VCC | "ต้องอยู่ระหว่าง 0 กับ VCC" |

ความต้านทานรับได้ทั้ง `100000` และ `100k` / `2.2k` (แปลงเป็น Ω ก่อนคำนวณ)
ทุกข้อผิดพลาดแสดงใต้ช่องที่ผิดและคงค่าที่ผู้ใช้กรอกไว้ (sticky form)

## 8. HTTP / UI contract

- `GET /` → ฟอร์มว่าง, VBE default `0.7`
- `POST /` → validate → คำนวณ → render หน้าเดิมพร้อมผล
  - สำเร็จ: HTTP 200 + ตารางผล
  - ผิดพลาด: HTTP 400 + ข้อความรายช่อง + ค่าเดิม + ไม่มีตารางผล
- ผลลัพธ์: VB, VE, VC, VCE (V), IC (mA), IB (µA/mA), IE (mA), VTH (V), RTH (kΩ)
- กระแส: `|I| ≥ 1 mA` → mA, ต่ำกว่านั้น → µA, ทศนิยม 3 ตำแหน่ง
- ความต้านทาน: `≥ 1000 Ω` → kΩ, ต่ำกว่านั้น → Ω

## 9. File map

```
transistor-simulator/
├── app.py                  # Flask app + routes (GET/POST)
├── dc_bias.py              # pure calculation + validation (ไม่ import Flask)
├── templates/index.html    # form + results (Jinja2)
├── static/style.css        # responsive layout
├── tests/test_dc_bias.py   # สมการ + validation + unit parsing
├── tests/test_web.py       # HTTP routes ด้วย Flask test client
├── requirements.txt
├── README.md               # install/run/test + อธิบาย Frontend/Backend/Template/Static/HTTP
├── AGENTS.md               # AI coding conventions
└── docs/
    ├── design-note.md      # ไฟล์นี้
    ├── validation.md       # หลักฐานการทดสอบ/ตรวจมือ
    └── reflection.md       # บันทึกสะท้อนคิดของนักศึกษา
```

## 10. Test strategy + ค่าอ้างอิงจากโจทย์

ข้อมูลทดลองเริ่มต้นของ Lab 02: **VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ,
RE=1 kΩ, β=100, VBE=0.70 V**

ค่าอ้างอิง (คำนวณด้วยสคริปต์อิสระ + ตรวจมือใน `docs/validation.md`):

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.033 kΩ |
| IB | 12.299 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VE | 1.242 V |
| VB | 1.942 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| region | active |

เคสเพิ่มเติม:

| เคส | ค่า | ผลที่คาด |
|---|---|---|
| saturation | RC = 10 kΩ | region=saturation, IC(sat)=1.073 mA, VCE ติดลบ |
| cutoff | R2 = 2.2 kΩ (VTH=0.258 V) | region=cutoff, VTH ≤ VBE |
| β ต่ำสุด | β = 1 | region=active, IB=73.077 µA |

HTTP tests: GET 200 + ฟิลด์ครบ, POST ค่าถูกต้อง 200 + ค่าที่ format แล้ว,
POST ค่าผิด 400 + ข้อความ + ค่าเดิม, POST ว่าง 400

## 11. สิ่งที่เหลือให้ผู้สร้างตัดสิน

- ลำดับ/การจัดกลุ่มฟิลด์ในฟอร์ม (ตัดสิน: supply → divider → load → transistor)
- แสดงค่ากลางทั้งหมดในตารางเดียว (ตัดสิน: แสดงทั้งหมด)
