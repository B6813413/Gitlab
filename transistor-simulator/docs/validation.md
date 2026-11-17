# Validation — Lab 03 BJT DC Bias Web App (A1–A5)

วันที่ตรวจ: 2026-11-17 | รีโป: `transistor-simulator` | Remote: https://github.com/B6813413/Gitlab.git
เครื่องมือ: Python 3.12, Flask 3.1, Windows 11, OpenCode Desktop Browser Tool

ค่าร่วมทุกกรณี: **VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V**
หน่วยบนฟอร์ม: VCC/VBE เป็น V; RC/RB/RE/R1/R2 เป็น kΩ
เกณฑ์: |ผลต่าง| ≤ **0.01 mA (IC)** และ ≤ **0.02 V (VCE)** เทียบค่าอ้างอิงที่ยังไม่ปัดเศษ

## วิธีตรวจจริง

ใช้ **OpenCode Browser Tool** (`browser.tabs.open` → `evaluate`/`fill` สำหรับกรอกค่า
→ `click`/`press`/`requestSubmit` สำหรับส่งฟอร์ม → `snapshot` สำหรับอ่านผล)
แทน **Playwright MCP** เพราะ MCP server ยังไม่พร้อมในสภาพแวดล้อมนี้
(ไฟล์ `opencode.json` ใน repo กำหนด Playwright MCP ไว้แล้ว đểเปิดใช้ได้เมื่อพร้อม)
ใบงาน Lab 03 §07 ระบุให้คะแนน Playwright MCP / OpenCode Browser / Manual เท่ากัน
และให้ระบุวิธีจริง → records อยู่ในคอลัมน์ “วิธีตรวจ” ด้านล่าง

หลักฐานเป็น **accessibility snapshot จากหน้าเว็บจริงหลังส่งฟอร์ม** (ไม่ใช่การอ่านโค้ด
หรือ curl) screenshot ไม่สามารถบันทึกได้เพราะหน้าต่าง desktop ไม่ได้อยู่ในโหมด.visible
ระหว่างรอบตรวจ จึงใช้ snapshot เป็นหลักฐานแทนตามที่ใบงานอนุญาต (“ข้อความผลที่คัดมา”)

## ตาราง A1–A5 (ผลที่เห็นจริงจาก browser)

| กรณี | โหมดและอินพุต | ค่าคาดหมายก่อนรัน | ผลที่เห็นจริง | หน่วย | วิธีตรวจ | สถานะ | หลักฐานจากหน้าเว็บ |
|---|---|---|---|---|---|---|---|
| A1 | Voltage Divider · R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | IC ≈ 1.2299 mA · VCE ≈ 8.0522 V | IC = **1.230 mA** · VCE = **8.052 V** (VB 1.942 V, VE 1.242 V, VC 9.294 V, VTH 2.164 V, RTH 18.033 kΩ, IB 12.299 µA, IE 1.242 mA) | IC mA · VCE V | OpenCode Browser Tool | PASS | snapshot แสดง “DC Bias Results [voltage_divider]”, ตาราง IB 12.299 µA / IC 1.230 mA / IE 1.242 mA / VCE 8.052 V และ “✓ Active region approximation OK”; `โหมดที่คำนวณ: voltage_divider` |
| A2 | Fixed · RB = 1 MΩ (กรอก 1000 kΩ, ไม่กรอก RE) | IC = 1.1300 mA · VCE = 9.5140 V | IC = **1.130 mA** · VCE = **9.514 V** (VB 0.700 V, VE 0.000 V, VC 9.514 V, IB 11.300 µA) | IC mA · VCE V | OpenCode Browser Tool | PASS | เปลี่ยนโหมดผ่าน select → ได้ `?mode=fixed`; snapshot แสดง “Circuit: … [Fixed Bias]”, ช่อง RE ถูกปิดใช้งาน, ผล IC 1.130 mA / VCE 9.514 V / “โหมดที่คำนวณ: fixed” |
| A3 | Emitter · RB = 1 MΩ, RE = 1 kΩ | IC ≈ 1.0263 mA · VCE ≈ 8.7055 V; ต้องมีช่อง RE และใช้ค่า RE | IC = **1.026 mA** · VCE = **8.705 V** (VB 1.737 V, VE 1.037 V, VC 9.742 V, IB 10.263 µA, IE 1.037 mA) | IC mA · VCE V | OpenCode Browser Tool | PASS | snapshot แสดงช่อง “RE (Emitter Resistor)” เปิดใช้งานรับ 1 kΩ + “Circuit: … [Emitter Bias (แหล่งจ่ายเดียว)]”, ผล IC 1.026 mA / VCE 8.705 V, “Active region approximation OK”; `โหมดที่คำนวณ: emitter` |
| A4 | Emitter · RB = 1 MΩ, **RE เปลี่ยน 1 → 2 kΩ** (ค่าอื่นคงเดิม) | IC ลดลงตามทิศทางที่ทำนาย ≈ 0.9401 mA · VCE ≈ 8.0328 V | IC = **0.940 mA** (ลดจาก 1.026) · VCE = **8.033 V** (VB 2.599 V, VE 1.899 V, VC 9.932 V, IB 9.401 µA) | IC mA · VCE V | OpenCode Browser Tool | PASS | ยังอยู่โหมด emitter เปลี่ยน RE เป็น 2 แล้วกดคำนวณใหม่: snapshot แสดง IC 0.940 mA (ลดลงจริงเมื่อเทียบ A3), VCE 8.033 V, “โหมดที่คำนวณ: emitter” |
| A5 | Fixed · RB = 0 | มีข้อความให้แก้ RB, เว็บไม่ล่ม, **ไม่แสดงผลเดิมเป็นผลรอบนี้** | แจ้ง **“ค่า RB (Fixed Bias) ต้องมากกว่า 0”** (Flask server-side), HTTP 400, ไม่มีตารางผลค้าง, เว็บใช้งานต่อได้ | — | OpenCode Browser Tool | PASS | snapshot แสดงข้อความสีแดงใต้ช่อง RB, หัวข้อ “DC Bias Results [Fixed Bias]” เป็น placeholder “Fill in the component values …” (ไม่มี `<table>`), ตรวจด้วย DOM ว่า `.field-error` = ["ค่า RB (Fixed Bias) ต้องมากกว่า 0"] และ `!!document.querySelector('table')` = false |

## การเทียบผลกับเกณฑ์

| กรณี | IC แสดง (3 dp) | IC อ้างอิง | |ΔIC| | VCE แสดง | VCE อ้างอิง | |ΔVCE| | ผ่านเกณฑ์ |
|---|---|---|---|---|---|---|---|
| A1 | 1.230 mA | 1.2299 mA | 0.0001 | 8.052 V | 8.0522 V | 0.0002 | ✓ |
| A2 | 1.130 mA | 1.1300 mA | 0.0000 | 9.514 V | 9.5140 V | 0.0000 | ✓ |
| A3 | 1.026 mA | 1.0263 mA | 0.0003 | 8.705 V | 8.7055 V | 0.0005 | ✓ |
| A4 | 0.940 mA | 0.9401 mA | 0.0001 | 8.033 V | 8.0328 V | 0.0002 | ✓ |

*แอปแสดง 3 ตำแหน่งทศนิยม จึงเทียบผลที่ปัดแล้วกับค่าอ้างอิงที่ยังไม่ปัดตามเกณฑ์ที่ตกลงในใบงาน*

## ค่าอ้างอิงอิสระ (คำนวณด้วยมือ/เครื่องคิดเลข ไม่ได้ดึงจากโค้ดที่ทดสอบ)

- **A2 Fixed Bias:** IB = (12 − 0.70) / 1,000,000 = 1.13×10⁻⁵ A → IC = 100·IB = **1.1300 mA**;
  VE = 0 V; VB = 0.70 V; VC = 12 − (1.13 mA × 2.2 kΩ) = **9.5140 V**; VCE = VC − VE = **9.5140 V**
- **A3 Emitter Bias:** IB = (12 − 0.70) / [1,000,000 + (100+1)×1,000] = 1.02634×10⁻⁵ A →
  IC = **1.0263 mA**; VE = 101·IB·1k ≈ **1.0366 V**; VC = 12 − IC×2200 ≈ **9.7421 V**;
  VCE ≈ **8.7055 V**
- **A4 Emitter Bias (RE=2 kΩ):** IB = 11.3 / [1,000,000 + 101×2,000] = 9.401×10⁻⁶ A →
  IC ≈ **0.9401 mA**; VE ≈ **1.8990 V**; VC ≈ **9.9318 V**; VCE ≈ **8.0328 V**
- **A1 Voltage Divider (Lab 02 คงเดิม):** VTH = 12×22/122 = 2.164 V,
  RTH = (100k×22k)/122k = 18.033 kΩ, IB = (2.164−0.70)/(18.033k+101×1k) = 12.299 µA,
  IC = **1.230 mA**, VE = 1.242 V, VC = 9.294 V, VCE = **8.052 V**

## สมการที่ใช้ (ใบงาน Lab 03)

ทุกโหมดรับ VCC, RC, β, VBE ร่วมกัน คำนวณใน Ω และ A แล้วแสดงผลเป็น V/mA:

- Fixed: `IB = (VCC − VBE) / RB`, `VE = 0`
- Emitter: `IB = (VCC − VBE) / [RB + (β+1)·RE]`
- Voltage Divider: `VTH = VCC·R2/(R1+R2)`, `RTH = R1·R2/(R1+R2)`,
  `IB = (VTH − VBE)/[RTH + (β+1)·RE]`
- ร่วมกัน: `IC = β·IB`, `IE = (β+1)·IB`, `VE = IE·RE` (Fixed ใช้ 0),
  `VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`

## Automated tests (A6)

```powershell
python -m unittest discover -s tests -v
```

```
Ran 62 tests in 0.058s
OK
```

ครอบคลุม: สมการทั้ง 3 โหมดเทียบ hand calc, `compute_bias()` dispatch + unknown mode,
per-mode validation (RB/RE/R1/R2), unit parsing (kΩ/Ω/k-suffix), formatter (IC เป็น mA เสมอ),
HTTP 200/400, sticky form, warning เมื่ออยู่นอก active, โครงสร้างฟอร์ม 2 อันไม่ซ้อนกัน
และ hidden mode ติดไปกับ POST, unknown mode ไม่ fallback ไป Divider

## ส่วนที่ AI ช่วย / นักศึกษาตรวจ

- **AI ช่วยสร้าง:** โครง `fixed_bias`, `emitter_bias`, dispatch ใน `compute_bias()`,
  การเชื่อม `app.py` + `templates/index.html`, regression tests, เอกสาร
- **นักศึกษาตรวจ/แก้เอง:** ตรวจสมการเทียบใบงาน, ทวนหน่วย kΩ→Ω ที่จุดรับค่าเดียว,
  ทดสอบ A1–A5 ใน browser จริง, ตรวจ warnings และข้อผิดพลาด
- **บั๊กที่พบและแก้ระหว่างตรวจ (สำคัญ):**
  1. `<form>` ซ้อนกันอยู่เดิม → browser ตัด DOM ทำให้ปุ่ม Calculate หลุดจากฟอร์ม
     และกดแล้วไม่ส่ง POST → แยกเป็น GET mode-form + POST input-form
  2. โหมดที่ไม่รู้จักเดิมเงียบ ๆ กลายเป็น Voltage Divider → แจ้ง error แทน
  3. IC เดิมโชว์ `940.100 µA` ใน A4 → ใช้ `format_ic_ma()` โชว์ `0.940 mA` เสมอ
  4. ข้อความ RB=0 เดิมเป็น “ต้องมากกว่า 0” → เปลี่ยนเป็น “ค่า RB (Fixed Bias) ต้องมากกว่า 0”
     ให้ตรงกับเกณฑ์ A5
  5. POST เดิมพึ่งพา query string อย่างเดียว → เพิ่ม hidden `mode` ใน POST form

## ข้อจำกัด

- ผลใช้ได้เฉพาะ Forward-Active ที่ β และ VBE คงที่ (ตามใบงาน)
- เมื่อ saturation/cutoff แอปแสดงผลจากสมการเชิงเส้น + คำเตือน ไม่ได้แก้โมเดล piecewise หรือ SPICE
- Flask dev server ใช้สำหรับพัฒนาในเครื่องเท่านั้น
- หลักฐานเป็น snapshot (ไม่มีภาพหน้าจอ) เพราะหน้าต่าง browser ไม่ได้อยู่ในโหมด visible ตอนเก็บหลักฐาน
