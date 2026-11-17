# Reflection — Lab 03 BJT DC Bias Web App

> **หมายเหตุสำหรับนักศึกษา:** ไฟล์นี้เป็นร่างที่สรุปจากบันทึกการตรวจจริงใน session นี้
> ใบงานกำหนดให้เขียนสะท้อนคิดด้วยภาษาของตัวเอง ห้ามคัดลอกจาก AI — กรุณาอ่านแล้ว
> ปรับคำ/เพิ่มความคิดเห็นของคุณเองก่อนส่งอาจารย์ โดยเฉพาะหัวข้อ 3, 5 และ 6

## 1. ส่วนประกอบของ Web App

- **Frontend:** `templates/index.html` — มี 2 ฟอร์ม: ฟอร์ม `GET` สำหรับเลือกโหมด
  (select `name="mode"`) และฟอร์ม `POST` สำหรับกรอกค่า + ปุ่ม Calculate
  นอกจากนี้ยังมีตารางผลและภาพ SVG schematic ที่เปลี่ยนตามโหมด
- **Backend:** `app.py` — route `index()` รับ `GET`/`POST`, อ่าน mode, เรียก
  `validate_inputs()`, แปลงหน่วยด้วย `parse_resistance()`, เรียก `compute_bias()`
  แล้ว render template พร้อม HTTP 200 หรือ 400
- **Engineering logic:** `dc_bias.py` — `fixed_bias()`, `emitter_bias()`,
  `voltage_divider_bias()`, `compute_bias()`, `validate_inputs()`, `parse_resistance()`
  ไม่ import Flask เลย จึงเทสต์ได้อิสระ
- **Template vs static:** Template คือไฟล์ Jinja ที่ server เติมค่าก่อนส่ง HTML
  (`templates/index.html`); static คือไฟล์ที่ browser โหลดตรง ๆ ไม่เปลี่ยนตาม request
  (`static/style.css` โหลดผ่าน `url_for('static', ...)`)

## 2. HTTP request/response

ลำดับจากกดปุ่ม Calculate:

1. Browser อ่านฟอร์ม `POST` (มี hidden `mode` + ค่า vcc/rc/rb/re/beta/vbe + หน่วย)
2. Browser ส่ง `POST /` แบบ `application/x-www-form-urlencoded`
3. Flask เข้า `index()` อ่าน `request.form.get("mode")` (หรือ `request.args` สำหรับ GET)
4. ตรวจค่า per-mode ถ้าผิด → render ทันทีด้วย HTTP 400 + ข้อความ + ค่าเดิม
5. ถ้าถูก → แปลง kΩ→Ω → `compute_bias(mode, inputs)` → ประกอบ `result`
6. Flask ส่ง HTML ที่มีตารางผลกลับมา HTTP 200 → browser แสดงผล

**ทำไมเปิด `file://templates/index.html` ไม่เหมือนรัน Flask:** ในไฟล์มี `{{ ... }}`
และ `url_for(...)` ซึ่งเป็น Jinja ที่ต้องมี server render ก่อน นอกจากนี้ไม่มี route
`/` ที่รับ POST และไม่มี Python ที่จะคำนวณ — การดับเบิลคลิกจึงเห็นแต่ template ดิบ

**ค่าฟอร์มไปถึง Python ยังไง:** อินพุตทุกตัวมี `name` → browser รวมเป็นคู่
`name=value` ใน body ของ POST → Flask เก็บไว้ใน `request.form` → `app.py` อ่าน
แล้วส่งเข้า `validate_inputs()` / `parse_resistance()` / `compute_bias()`

## 3. จุดที่ AI ช่วย และจุดที่ตรวจแก้เอง

- **AI ช่วย:** เขียนโครง `fixed_bias`/`emitter_bias`, `compute_bias()` dispatch,
  การ์ดโหมดใน template, tests, และเอกสารตามโจทย์
- **ตรวจเอง:** คำนวณ IC/VCE ด้วยมือเทียบ A2/A3/A4, ตรวจหน่วย kΩ→Ω, ทวนว่าโหมด
  ที่เลือกถูกต้อง, กดฟอร์มจริงใน browser แล้วอ่าน snapshot ทีละกรณี
- **จุดที่ AI ผิด/ไม่สมบูรณ์แล้วแก้ (สำคัญ 5 จุด):**
  1. `<form>` ซ้อนกัน → ปุ่ม Calculate หลุดจากฟอร์ม กดแล้วไม่ POST → แยก 2 ฟอร์ม
  2. โหมดแปลก ๆ เงียบ ๆ กลายเป็น Voltage Divider → เปลี่ยนเป็นแจ้ง error
  3. A4 โชว์ IC เป็น `940.100 µA` ทั้งที่โจทย์อยากได้ mA → `format_ic_ma()`
  4. RB=0 โชว์แค่ “ต้องมากกว่า 0” → เปลี่ยนเป็น “ค่า RB (Fixed Bias) ต้องมากกว่า 0”
  5. POST อ่านโหมดจาก query string อย่างเดียว → เพิ่ม hidden `mode` ในฟอร์ม

## 4. การตรวจสอบผลการคำนวณ

ตรวจ 3 ชั้น:
1. **คำนวณมืออิสระ** ก่อนรัน — A2: IB=11.3/1M=11.30 µA → IC=1.130 mA;
   A3: 11.3/(1M+101×1k)=10.263 µA → IC=1.026 mA; A4 เปลี่ยน RE=2k → IC=0.940 mA
2. **unit tests** 62 tests รันผ่าน (`python -m unittest discover -s tests -v`)
3. **browser จริง** A1–A5 ผ่าน OpenCode Browser Tool อ่าน snapshot หลังส่งฟอร์ม

**ค่าที่ตรวจซ้ำเป็นพิเศษ:** A4 เพราะเป็นกรณี “เปลี่ยน RE แล้ว IC ต้องลดลง”
เป็นการพิสูจน์ว่าตัวส่วน `(β+1)·RE` ถูกใช้จริง ไม่ใช่แค่ hardcoded ค่าเดิม
และ A5 เพราะต้องยืนยันว่า Flask ตรวจเอง (ไม่ใช่แค่ browser blocks) และไม่โชว์
ผลค้างจากรอบก่อน

## 5. ทำไมต้องเตือนเมื่ออยู่นอก Forward-Active

เมื่อ `IB ≤ 0` (เช่น `VTH ≤ VBE` ใน Divider) ทรานซิสเตอร์ตัด (cutoff) สมการ
`IC=β·IB` ให้ค่าศูนย์หรือติดลบ ซึ่งไม่มีความหมายทางกายภาพ เมื่อ `VCE < 0.2 V`
ทรานซิสเตอร์เข้า saturation ความสัมพันธ์ `IC=β·IB` ใช้ไม่ได้แล้วเพราะ B-E และ B-C
ทั้งคู่ forward-biased การที่แอปยังคำนวณต่อด้วยสมการเชิงเส้นจะให้ตัวเลขที่ดูน่าเชื่อถือ
แต่ผิด → ต้องแสดงคำเตือนเพื่อไม่ให้คนอ่านเอาไปใช้เป็นผลจำลองจริง

## 6. ข้อสังเกตและสิ่งที่ยังไม่เข้าใจ

- สิ่งที่ยังอยากลอง: แสดง DC load line บนกราฟ VCE–IC เพื่อเห็นจุดตัดกับโหลด
  และลองเปลี่ยน β แล้วดูว่าจุดทำงานขยับอย่างไร
- ถ้าจะทำ Week 4 จะเริ่มที่ `dc_bias.py` ก่อน เพราะเป็นแหล่งความจริงของสมการ
  แล้วค่อยเพิ่ม route/UI ที่ `app.py` และ `templates/index.html` ตามลำดับ
- ข้อจำกัดที่ยังติดอยู่: รันบน Flask debug server เฉพาะเครื่อง, ยังไม่มี persistent
  config, และหลักฐาน screenshot เก็บไม่ได้ในรอบนี้จึงใช้ accessibility snapshot แทน
