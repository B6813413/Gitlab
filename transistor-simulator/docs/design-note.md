# Design Note — Lab 03 BJT DC Bias Web App → Lab 04 BJT Amplifier Simulator

## 1. Intent

ต่อยอดจาก Lab 02 (Voltage Divider Bias เท่านั้น) เป็นเว็บแอป Flask **หน้าเดียว**
ที่เลือกวงจรไบอัส BJT Common Emitter ได้ 3 แบบ (Lab 03) แล้วใน Lab 04 เพิ่มการ
เปรียบเทียบกับผลจำลอง ngspice จริง 3 แบบ (DC/Bode/Transient):

1. **Voltage Divider Bias** (`voltage_divider`) — ผลเดิมต้องไม่เปลี่ยนเมื่อกรอกค่าเดิม
2. **Fixed Bias** (`fixed`) — RB จาก VCC ไปฐาน, อีมิตเตอร์ต่อกราวด์ (VE = 0)
3. **Emitter Bias แหล่งจ่ายเดียว** (`emitter`) — RB จาก VCC ไปฐาน + RE ลงกราวด์

ผู้ใช้เห็น VB, VE, VC, VCE, IB, IC, IE พร้อมหน่วย และคำเตือนเมื่อแบบจำลอง
Forward-Active ใช้ไม่ได้

## 2. Goals (acceptance Lab 03 §07)

| # | เกณฑ์ | การออกแบบ |
|---|---|---|
| A1 | Voltage Divider ผลตรง Lab 02 | คงสมการ Thevenin เดิมใน `voltage_divider_bias()` |
| A2 | Fixed Bias ตรง hand calc | `fixed_bias()`: IB=(VCC−VBE)/RB, VE=0 |
| A3 | Emitter Bias ตรง hand calc | `emitter_bias()`: IB=(VCC−VBE)/[RB+(β+1)RE] |
| A4 | เปลี่ยน RE แล้ว IC เปลี่ยนตามทิศทาง | โชว์ผลใหม่จาก POST ทุกครั้ง (ไม่ cache) |
| A5 | อินพุตผิด → แจ้งแก้, ไม่ล่ม, ไม่โชว์ผลเก่า | `validate_inputs()` per-mode + HTTP 400 + `result=None` |
| A6 | ตรวจด้วย Browser/MCP + เอกสาร | OpenCode Browser Tool + ตาราง A1–A5 ใน `docs/validation.md` |

นอกจากนั้น: `IC` ต้องแสดงเป็น **mA เสมอ**, โหมด unknown ต้องแจ้ง error
(ไม่เดาว่าเป็น Divider), และต้องมี Playwright MCP config (`opencode.json`)

## 3. Non-goals

Lab 03 เดิม: Bode plot, transient, signal generator, SPICE/ngspice — สำหรับ Lab 04
**ทำแล้ว** (ดู §12) แต่ยังไม่ทำ DC load line, ฐานข้อมูล, login, JavaScript/AJAX, websocket
หน้าเว็บยังเป็น server-rendered form POST เหมือนเดิม

## 4. Constraints

- Flask + Jinja2, Python 3.12, dependency เพิ่มเติมไม่มี (Flask เท่านั้น)
- `dc_bias.py` เป็น pure Python (ไม่ import Flask) แยกจาก `app.py` ชัดเจน
- ใช้ `unittest` ตามสไตล์เดิมของ repo
- UI ภาษาไทย ตัวเลขมีหน่วยทุกค่า
- รันด้วย `python -m flask --app app run --debug`

## 5. Architecture / Data flow

```
GET /?mode=<mode>
  → app.index(): อ่าน request.args["mode"] (default voltage_divider)
  → render index.html: เฉพาะช่องของโหมดนั้น, result=None, mode-form selected

POST /  (hidden mode + ค่าฟอร์ม)
  → app.index(): submitted_mode = request.form["mode"] or args or default
  → validate_inputs(form, submitted_mode)        # per-mode
  → parse_resistance() แปลง kΩ/Ω/k-suffix → Ω   # จุดเดียวใน app.py
  → compute_bias(submitted_mode, inputs)         # dispatch ไปฟังก์ชันที่ถูกต้อง
  → render: success = 200 + ตารางผล / error = 400 + ข้อความ + ค่าเดิม (result=None)
```

**ทำไมแยก 2 ฟอร์ม:** ตอนทำ Lab 03 รอบแรก `<form>` ถูกเขียนซ้อนกัน
(GET mode-form อยู่ใน POST form) browser จะตัด DOM ทำให้ input และปุ่ม Calculate
หลุดออกจากฟอร์ม → กดปุ่มแล้วไม่ส่ง POST เลย แก้โดยแยกเป็น 2 ฟอร์มอิสระและเพิ่ม
hidden `mode` ใน POST form เพื่อไม่ต้องพึ่ง query string

## 6. สมการอ้างอิง

```
Voltage Divider: VTH = VCC·R2/(R1+R2), RTH = R1·R2/(R1+R2)
                 IB  = (VTH − VBE) / [RTH + (β+1)·RE]

Fixed Bias:      IB  = (VCC − VBE) / RB,           VE = 0

Emitter Bias:    IB  = (VCC − VBE) / [RB + (β+1)·RE]

ร่วมกัน:          IC  = β·IB,  IE = (β+1)·IB,
                 VE  = IE·RE (Fixed = 0),  VB = VE + VBE,
                 VC  = VCC − IC·RC,  VCE = VC − VE
```

`VCE(sat) = 0.2 V`: `IB ≤ 0` → cutoff, `VCE < 0.2` → saturation,
อื่น → active; นอก active แสดง warning ว่าแบบจำลอง Forward-Active ใช้ไม่ได้

## 7. Validation rules (per mode)

| เงื่อนไข | ข้อความ |
|---|---|
| ช่องว่าง | "กรุณากรอกค่านี้" |
| ไม่ใช่ตัวเลข / ไม่ finite | "ต้องเป็นตัวเลขที่จำกัด" |
| VCC ≤ 0, β ≤ 0 | "ต้องมากกว่า 0" |
| RC ≤ 0 | "ต้องมากกว่า 0" |
| R1, R2 ≤ 0 (Divider) | "ต้องมากกว่า 0" |
| RB ≤ 0 (Fixed) | "ค่า RB (Fixed Bias) ต้องมากกว่า 0" |
| RB ≤ 0 (Emitter) | "ค่า RB (Emitter Bias) ต้องมากกว่า 0" |
| RE < 0 | "ต้องไม่ติดลบ" |
| VBE ≤ 0 หรือ ≥ VCC | "ต้องอยู่ระหว่าง 0 กับ VCC" |
| mode ไม่รู้จัก | "โหมดวงจร '…' ไม่รู้จัก กรุณาเลือกโหมดที่ถูกต้อง" |

ฟิลด์ที่ต้องการตามโหมด: Divider = `r1,r2,re`; Fixed = `rb`; Emitter = `rb,re`
ค่าร่วม = `vcc,rc,beta,vbe` — ช่องที่ไม่ใช้จะ `disabled` และไม่ถูกตรวจ
ข้อผิดพลาดแสดงใต้ช่องนั้น + คงค่าผู้ใช้ไว้ (sticky form)

## 8. HTTP / UI contract

- `GET /` หรือ `GET /?mode=<mode>` → 200, ฟอร์มตามโหมด, ไม่มีผลคำนวณ
- `POST /` → validate → คำนวณ → render เดิม
  - สำเร็จ 200 + ตารางผล + `โหมดที่คำนวณ: <mode>`
  - ผิด 400 + error + ค่าเดิม + ไม่มีตารางผล
- ผล: VB/VE/VC/VCE (V), **IC (mA เสมอ)**, IB/IE (µA หรือ mA แบบ engineering),
  VTH (V), RTH (Ω/kΩ) เฉพาะ Divider
- ภาพ SVG schematic ปรับตามโหมด (แสดง RB/RE/R1/R2 ที่ใช้จริง)
- เปลี่ยนโหมด = GET ใหม่ → ผลรอบก่อนหายไป (กันสับสนว่าผลเป็นของโหมดไหน)

## 9. File map

```
transistor-simulator/
├── app.py                  # mode dispatch, validation call, unit conversion, formatters
├── dc_bias.py              # 3 bias functions + compute_bias + validate_inputs + parse_resistance
├── templates/index.html    # 2 forms + results + SVG diagram
├── static/style.css
├── tests/test_dc_bias.py   # สมการ/validation/unit tests
├── tests/test_web.py       # HTTP, mode, form structure, formatter tests
├── opencode.json           # Playwright MCP server config
├── requirements.txt
├── AGENTS.md
├── README.md
└── docs/{design-note,validation,reflection}.md
```

## 10. Test strategy + ค่าอ้างอิง

62 tests ในรอบ Lab 03 (historic; ปัจจุบันรวม Lab 04 คือ 135 tests): math
(3 โหมดเทียบ hand calc, saturation/cutoff/β=1), parsing, validation
per-mode, dispatch, formatter, HTTP 200/400, form structure, browser regression cases

| กรณี | IC อ้างอิง | VCE อ้างอิง |
|---|---|---|
| A1 Divider | 1.2299 mA | 8.0522 V |
| A2 Fixed RB=1 MΩ | 1.1300 mA | 9.5140 V |
| A3 Emitter RB=1 MΩ, RE=1 kΩ | 1.0263 mA | 8.7055 V |
| A4 Emitter RE=2 kΩ | 0.9401 mA | 8.0328 V |
| A5 Fixed RB=0 | error, 400, ไม่มีตารางผล | — |

## 11. การตัดสินที่สำคัญระหว่างทำ

| ประเด็น | ตัดสิน |
|---|---|
| โหมดส่งยังไง | GET form เลือกโหมด + hidden field ใน POST (ไม่พึ่ง URL อย่างเดียว) |
| โหมด unknown | แจ้ง error ไม่ fallback (กันผลผิดเงียบ ๆ) |
| หน่วย IC | mA เสมอ (`format_ic_ma`) เพราะใบงานกำหนด |
| หน่วย IB/IE | engineering notation (µA ถ้าต่ำกว่า 1 mA) |
| เปลี่ยนโหมดแล้วผลเก่า | ล้างทิ้ง (GET ใหม่) กันอ่านผลผิดโหมด |
| วิธีตรวจ browser | OpenCode Browser Tool แทน Playwright MCP ที่ยังไม่พร้อม; เก็บ config ไว้ใน repo |
| หลักฐาน | DOM/snapshot จากหน้าเว็บจริง + screenshot ใน `docs/captures/` (Chrome headless) |

---

## 12. Lab 04 architecture delta (Lab 03 → Lab 04)

### สิ่งที่เพิ่ม (ไม่แตะสมการเดิม)

| ชั้น | Lab 03 | Lab 04 เพิ่ม | เหตุผล |
|---|---|---|---|
| Engineering | `dc_bias.py` เท่านั้น | `spice_engine.py` (netlist builder, `validate_spice_inputs`, `run_analysis`, parser) — pure Python ไม่ import Flask | แยก “สมการ” ออกจาก “solver ภายนอก” เหมือนที่ `dc_bias.py` แยกจาก HTTP |
| Chart | ไม่มี | `charts.py` สร้าง SVG จาก series จริง (Bode log-x, gain/phase คนละ scale; transient ms timebase) | ห้ามเพิ่ม JS library; ทุกจุดต้องมาจาก `.print` ไม่ใช่ hard-code |
| HTTP | `analysis` ไม่มี | `ANALYSIS_LABELS`, `SPICE_ANALYSIS`, `_spice_params()`, `_spice_view()`, `_render()` | dispatch DC/AC/tran โดยไม่กระทบเส้นทาง `result` เดิม |
| Template | 2 forms + analytical results | `<select name="analysis">` ใน GET form + hidden `analysis` ใน POST form + panel `SPICE simulation` พร้อม engine/status/model/log | แสดง provenance ให้ชัดว่าตัวเลขมาจากสมการหรือ ngspice |
| CSS | responsive เดิม | `.analysis-tabs`, `.engine-badge`, `.chart`, `.log-details` + media query | อ่านง่ายทั้ง desktop/mobile โดยไม่เพิ่ม framework |

### Data flow ใหม่

```text
GET /?mode=<mode>&analysis=<bias|spice_dc|spice_ac|spice_tran>
  → render selector + ช่องตาม mode/analysis (ผลรอบก่อนถูกล้าง)

POST /  (hidden mode + analysis + ค่าฟอร์ม)
  ├─ analysis == bias
  │    → validate_inputs → parse_resistance → compute_bias → result เดิม (HTTP 200/400)
  └─ analysis != bias
       → _spice_params(): merge SPICE_DEFAULTS กับฟิลด์ที่ส่งมา (partial POST ยังใช้ได้)
       → validate_spice_inputs() → 400 ถ้าผิด (เช่น RE=0)
       → run_analysis(params, dc|ac|tran)
            → build_netlist() → ngspice -b -o run.log case.cir (ไม่ส่ง -r)
            → parse_op_log() / parse_print_table() → values / series
       → 200 success หรือ 502 error + engine/status/model/log_excerpt จริง
       → render_bode_svg() / render_transient_svg() เฉพาะเมื่อ status == success
```

### การตัดสินที่สำคัญ

| ประเด็น | ตัดสิน | ผล/_cost_ |
|---|---|---|
| rawfile | **ไม่ส่ง `-r run.raw`** เพราะ ngspice 47 log ว่า `.print line ignored since rawfile was produced.` | ต้องพึ่ง `.print` เป็นแหล่งเดียว; มี regression test กันการกลับไปใช้ flag นี้ |
| ผล DC ไม่ตรง Lab 03 | แสดงคนละ panel + อธิบายโมเดล `QNPN` | ผู้ใช้ไม่สับสนว่า regression เสีย (B2: IC 1.278 mA เทียบ analytical 1.230 mA) |
| กราฟ | SVG string ใน Python + `|safe` เฉพาะ SVG ที่ generate เอง | ไม่มี dependency ใหม่; input ผ่าน `html.escape` ก่อนใส่ label |
| error path | 400 สำหรับ input ผิด, 502 สำหรับ solver ล้มเหลว | ไม่โชว์ตาราง success ปลอม (B7 ตรวจแล้ว) |
| ngspice ติดตั้ง | external binary, ไม่ added ลง `requirements.txt` | tests ใช้ mock จึงยัง `unittest discover` ได้แม้ไม่มี solver |
| Form sticky | `_spice_values()` คืนค่าที่ผู้ใช้ส่งกลับมาหลัง POST ทุก branch (รวม error) | ผู้ใช้เห็นค่าที่ใช้รันจริง; ช่องที่ไม่ได้ส่งได้จาก `SPICE_DEFAULTS` |
| UI provenance | SPICE ปิด `mode/β/VBE` และตรึงภาพเป็น CE Reference | engine ไม่รับสามช่องนี้; ป้องกันความเข้าใจผิดว่า result มาจากช่อง Lab 03 |
| Mobile chart | ≤ 880px ใช้ `minmax(0, 1fr)` + `.chart{overflow-x:auto}` + SVG `min-width:760px` | อ่านตัวอักษรกราฟได้โดยเลื่อนในกราฟ โดยไม่ดันความกว้างทั้งหน้า |

### Test/acceptance mapping

Task 1 netlist+validation → `test_spice_engine.py` · Task 2 runner+parser → เดิม + regression
`-r` · Task 3 charts → `test_charts.py` (log axis, Thai legend, empty axes, ms ticks)
· Task 4 dispatch → `test_spice_web.py` · Task 5 UI → structure test เดิม
· Task 6 → B1–B8 ใน `docs/validation.md` + screenshot ใน `docs/captures/`
