# AGENTS.md — AI coding conventions

ใช้กับ AI agent และผู้ร่วมพัฒนาทุกคนในโฟลเดอร์นี้

## Environment

- Python 3.12
- Dependency เดียวที่เพิ่มได้: `Flask` (ดู `requirements.txt`)
- **ห้าม** เพิ่ม JavaScript framework, ORM, หรือเพิ่ม dependency อื่นโดยไม่ได้ตกลงก่อน

## Architecture

- สมการทางวิศวกรรมต้องอยู่ใน `dc_bias.py` และ **ห้าม** import Flask หรือพึ่งพา HTTP/HTML ในไฟล์นั้น
- `app.py` รับผิดชอบเฉพาะ HTTP: parse form → validate → เรียกคำนวณ → render template
- `templates/index.html` เป็น Jinja2 template — ห้ามฝังสมการฟิสิกส์ใน template
- `static/style.css` ดูแลเฉพาะ presentation

## Style & UI

- UI และข้อความข้อผิดพลาดเป็นภาษาไทย
- ทุกค่าที่แสดงต้องมีหน่วยกำกับ
- ข้อความ validation ต้องเป็นไปตามที่กำหนดใน `dc_bias.py` (`กรุณากรอกค่านี้`, `ต้องเป็นตัวเลขที่จำกัด`, `ต้องมากกว่า 0`, `ต้องไม่ติดลบ`, `ต้องอยู่ระหว่าง 0 กับ VCC`)

## Verification

- รันเทสต์ก่อน commit ทุกครั้ง: `python -m unittest discover -s tests -v` (จากโฟลเดอร์ `transistor-simulator/`)
- ห้าม commit ผลคำนวณหรือพฤติกรรมใหม่ที่ไม่มี test รองรับ
- ห้ามลบหรือเปลี่ยนคำเตือน (warning) เมื่ออยู่นอก Forward-Active — เป็นข้อกำหนดของ Lab 02 (A5)
- ถ้าแก้สมการ ต้องอัปเดตทั้ง `dc_bias.py`, test และ `docs/validation.md` ให้สอดคล้องกัน

## Git

- Commit เป็นหน่วยเล็ก ๆ ครั้งละหนึ่งงาน
- ห้าม commit `.venv/`, `.env`, API keys หรือ credentials
