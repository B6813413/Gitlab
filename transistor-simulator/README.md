# Transistor DC Bias Simulator — ENG29 2121 Lab 03

Flask web application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common Emitter ได้ **3 แบบ** ในหน้าเดียว:

| โหมด | ค่า `mode` | วงจร |
|---|---|---|
| Voltage Divider Bias | `voltage_divider` | เดิมจาก Lab 02 (ผลต้องคงเดิม) |
| Fixed Bias | `fixed` | RB จาก VCC ไปฐาน, อีมิตเตอร์ต่อกราวด์ (VE = 0) |
| Emitter Bias (แหล่งจ่ายเดียว) | `emitter` | RB จาก VCC ไปฐาน + RE จากอีมิตเตอร์ลงกราวด์ |

ผู้ใช้เลือกโหมด → กรอกค่าอุปกรณ์ที่โหมดนั้นใช้ → กด **Calculate DC Bias** →
Flask รับ HTTP request → validate แยกตามโหมด → Python คำนวณจากสมการ →
แสดงผลพร้อมหน่วยใน browser

**Repository / Remote:** https://github.com/B6813413/Gitlab.git

## โครงสร้าง

```
transistor-simulator/
├── app.py                  # Flask app + HTTP routes, mode dispatch, formatters
├── dc_bias.py              # pure engineering calculations (ไม่ import Flask)
├── templates/index.html    # GET mode form + POST input form + results (Jinja2)
├── static/style.css        # responsive layout
├── tests/test_dc_bias.py   # unit tests ของสมการ/validation/unit parsing
├── tests/test_web.py       # Flask HTTP route + form structure tests
├── opencode.json           # Playwright MCP config สำหรับ browser verification
├── requirements.txt
├── AGENTS.md
└── docs/
    ├── design-note.md      # Lab 03 design decisions
    ├── validation.md       # ตาราง A1–A5 + หลักฐานจาก browser
    └── reflection.md       # บันทึกสะท้อนคิด
```

## ติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate          # macOS / Linux
python -m pip install -r requirements.txt
```

รันเซิร์ฟเวอร์ (เปิด http://127.0.0.1:5000/):

```powershell
python -m flask --app app run --debug
# หรือ
python app.py
```

รันเทสต์ (จากในโฟลเดอร์ `transistor-simulator`):

```powershell
python -m unittest discover -s tests -v
```

ผลล่าสุด: **Ran 62 tests ... OK**

## Frontend / Backend / Template / Static / HTTP

| ส่วน | ไฟล์ | หน้าที่ |
|---|---|---|
| Frontend | `templates/index.html` | ฟอร์มเลือกโหมด (GET) + ฟอร์มกรอกค่า/ปุ่มคำนวณ (POST) + ตารางผล; ไม่มีโค้ดคำนวณ |
| Static | `static/style.css` | หน้าตาและการจัดวาง (responsive) โหลดผ่าน `url_for('static', filename='style.css')` |
| Backend | `app.py` | รับ `GET`/`POST`, อ่าน mode, validate, แปลงหน่วย, dispatch ไปยังฟังก์ชันคำนวณ, render template พร้อม status code |
| Engineering logic | `dc_bias.py` | `fixed_bias()`, `emitter_bias()`, `voltage_divider_bias()`, `compute_bias()`, `parse_resistance()`, `validate_inputs()` — ไม่รู้จัก HTTP/HTML |
| Template | `templates/index.html` | Jinja2; server ส่ง `result`, `errors`, `values`, `mode`, `diagram` มา render |

### โครงสร้างฟอร์ม (important)

- **ฟอร์มที่ 1** `method="get"` มีเฉพาะ `<select name="mode">` — เปลี่ยนโหมดแล้ว
  browser โหลดหน้าใหม่ แสดงเฉพาะช่องที่ใช้กับโหมดนั้น และล้างผลรอบก่อน
- **ฟอร์มที่ 2** `method="post"` มี `<input type="hidden" name="mode">` + ช่องค่า + ปุ่ม
  Calculate — เป็นฟอร์มคนละอันกับฟอร์มแรก (ห้ามซ้อนกัน เพราะ browser จะตัด DOM
  ทำให้ช่อง/ปุ่มหลุดออกจากฟอร์มแล้วกดคำนวณไม่ส่ง POST)

เมื่อกดปุ่ม Calculate browser ส่ง `POST /` (`application/x-www-form-urlencoded`)
พร้อม hidden `mode` → Flask เข้า `index()` → `validate_inputs(form, mode)` →
`parse_resistance()` แปลง kΩ → Ω → `compute_bias(mode, inputs)` → render ผล
(HTTP 200) หรือข้อความผิดพร้อมค่าเดิม (HTTP 400)

## ค่าอ้างอิง / เกณฑ์ตรวจ (Lab 03 §07)

ค่าร่วมทุกกรณี: **VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V**
หน่วยบนฟอร์ม: VCC/VBE เป็น V, RC/RB/RE/R1/R2 เป็น kΩ
เกณฑ์: ผลต่างไม่เกิน **0.01 mA (IC)** และ **0.02 V (VCE)** เทียบค่าอ้างอิงที่ยังไม่ปัด

| กรณี | อินพุต | IC (อ้างอิง) | VCE (อ้างอิง) |
|---|---|---|---|
| A1 | Voltage Divider · R1=100, R2=22, RE=1 kΩ | 1.2299 mA | 8.0522 V |
| A2 | Fixed · RB=1000 kΩ (=1 MΩ) | 1.1300 mA | 9.5140 V |
| A3 | Emitter · RB=1000 kΩ, RE=1 kΩ | 1.0263 mA | 8.7055 V |
| A4 | Emitter · RB=1000 kΩ, RE=2 kΩ | 0.9401 mA | 8.0328 V |
| A5 | Fixed · RB=0 | แจ้งให้แก้ RB, HTTP 400, ไม่มีตารางผลค้าง | — |

ผลจริงจาก browser และหลักฐานอยู่ใน [`docs/validation.md`](docs/validation.md)

## สมการที่ใช้

```
ทุกโหมด: IC = β·IB, IE = (β+1)·IB, VB = VE + VBE,
         VC = VCC − IC·RC, VCE = VC − VE

Voltage Divider: VTH = VCC·R2/(R1+R2), RTH = R1·R2/(R1+R2)
                 IB  = (VTH − VBE) / [RTH + (β+1)·RE], VE = IE·RE

Fixed Bias:      IB = (VCC − VBE) / RB, VE = 0

Emitter Bias:    IB = (VCC − VBE) / [RB + (β+1)·RE], VE = IE·RE
```

โซนการทำงาน (`VCE(sat) = 0.2 V`): `IB ≤ 0` → **cutoff**,
`VCE < 0.2` → **saturation** (แสดง IC(sat)), อื่น ๆ → **active**
เมื่ออยู่นอก active หน้าจอแสดงคำเตือนว่าแบบจำลอง Forward-Active ใช้ไม่ได้

## การแสดงผล

- **IC แสดงเป็น mA เสมอ** (`format_ic_ma()`) ตามที่โจทย์ Lab 03 กำหนด
- IB/IE ใช้ engineering notation (µA ถ้าต่ำกว่า 1 mA, มิฉะนั้น mA)
- แรงดันเป็น V, ความต้านทานเป็น Ω/kΩ — ตัวเลข 3 ตำแหน่งทศนิยม

## Browser verification

ใช้ **OpenCode Browser Tool** (`browser.tabs.*`, `snapshot`, `evaluate`, `press`)
เป็นวิธีตรวจจริง เพราะ Playwright MCP ยังไม่พร้อมในสภาพแวดล้อมนี้
(มี `opencode.json` กำหนด Playwright MCP ไว้แล้ว เปิดใช้ได้เมื่อพร้อม)
ใบงานให้คะแนนทุกวิธีเท่ากัน — รายละเอียดอยู่ใน `docs/validation.md`

## หมายเหตุ

- ตัวต้านทานรับค่าเป็น Ω (`100000`), มี `k` ต่อท้าย (`100k`, `2.2k`) หรือเลือก
  หน่วย kΩ/Ω ในฟอร์ม — แปลงเป็น Ω ที่จุดรับค่าเดียวใน `app.py` ก่อนส่งให้ `dc_bias.py`
- validation เป็น **per-mode**: Divider ต้องการ R1/R2/RE, Fixed ต้องการ RB,
  Emitter ต้องการ RB และ RE; โหมดที่ไม่รู้จักแจ้งข้อผิดพลาด (ไม่เดาว่าเป็น Divider)
- ผลนอก Forward-Active เป็นผลจากสมการเชิงเส้น ไม่ใช่ผลจำลองที่แม่นยำ
- Week 3 ไม่มี Bode Plot / Transient / SPICE / ฐานข้อมูล / login / JavaScript AJAX
