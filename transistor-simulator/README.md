# Transistor DC Bias Simulator

Flask web application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
Common Emitter แบบ **Voltage-Divider Bias** ตามโจทย์ ENG29 2121 Lab 02

ผู้ใช้กรอกค่าอุปกรณ์ในฟอร์ม → Flask route รับ HTTP request → Python คำนวณจากสมการ
→ app ส่งค่ากลับมาแสดงใน browser

## โครงสร้าง

```
transistor-simulator/
├── app.py                  # Flask application & HTTP routes
├── dc_bias.py              # pure engineering calculations (ไม่ import Flask)
├── templates/index.html    # input form + DC results (Jinja2)
├── static/style.css        # responsive layout
├── tests/test_dc_bias.py   # unit tests ของสมการและ validation
└── tests/test_web.py       # Flask HTTP route tests
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

## Frontend / Backend / Template / Static / HTTP ทำงานอย่างไร

| ส่วน | ไฟล์ | หน้าที่ |
|---|---|---|
| Frontend | `templates/index.html` | ฟอร์มรับค่า VCC, R1, R2, RC, RE, β, VBE; เป็น markup + Jinja — ไม่มีโค้ดคำนวณ |
| Static | `static/style.css` | หน้าตาและการจัดวาง (responsive) โหลดผ่าน `url_for('static', filename='style.css')` |
| Backend | `app.py` | รับ HTTP request (`GET`/`POST`), validate, เรียกฟังก์ชันคำนวณ, เลือก template/status code |
| Engineering logic | `dc_bias.py` | `dc_operating_point()`, `parse_resistance()`, `validate_inputs()` — ไม่รู้จัก HTTP/HTML |
| Template | `templates/index.html` | Jinja2; server ส่งค่า `result`, `errors`, `values` มา render ก่อนตอบ response |

เมื่อกดปุ่ม **คำนวณ DC Bias**, browser ส่ง `POST /` พร้อมฟอร์ม
(`application/x-www-form-urlencoded`) → Flask เข้า route `index()` → validate →
คำนวณ → render `index.html` ด้วย `result` → browser ได้ HTML ที่มีค่า DC Bias
พร้อมหน่วยแล้ว (ไม่มี JavaScript)

## ค่าอ้างอิงจากโจทย์ (ใช้ตรวจผล)

VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V

| Quantity | Expected |
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
| Region | Active |

## สมการที่ใช้

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

โซนการทำงาน (`VCE(sat) = 0.2 V`): `VTH ≤ VBE` → **cutoff**,
`VCE < 0.2` → **saturation** (แสดง IC(sat)), อื่น ๆ → **active**

## หมายเหตุ

- ตัวต้านทานรับค่าเป็น Ω (`100000`) หรือมี `k` ต่อท้าย (`100k`, `2.2k`) — backend แปลงเป็น Ω ก่อนคำนวณ
- ผลนอก Forward-Active เป็นเพียงผลจากสมการเชิงเส้น ไม่ใช่ผลจำลองที่แม่นยำ — หน้าจอจะแสดงคำเตือน
- Week 2 เอาเฉพาะการคำนวณ DC bias เท่านั้น ไม่มี Bode Plot / Transient / SPICE
