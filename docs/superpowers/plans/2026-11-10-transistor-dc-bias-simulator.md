# Transistor DC Bias Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask web app ที่รับค่าอุปกรณ์ Voltage-Divider Bias แล้วคำนวณและแสดง VB, VE, VC, VCE, IC (พร้อม IB/IE/VTH/RTH) ตามโจทย์ ENG29 2121 Lab 02

**Architecture:** Flask server-rendered form POST ไม่มี JavaScript การคำนวณอยู่ใน `dc_bias.py` แบบ pure function (ไม่ import Flask) ส่วน `app.py` parse form → validate → เรียกคำนวณ → render ด้วย Jinja2

**Tech Stack:** Python 3.12, Flask, Jinja2, unittest, HTML/CSS

**Spec:** `transistor-simulator/docs/design-note.md` (อ้างอิงโจทย์ Lab02 §06, §09)

## Global Constraints

- dependency เดียวที่เพิ่มได้: `Flask` (ห้ามเพิ่ม JS framework / ORM / pytest)
- ใช้ `unittest` เท่านั้น
- UI เป็น server-rendered form POST ไม่มี JavaScript
- `VCE(sat) = 0.2 V` คงที่
- ผลลัพธ์บังคับ: **VB, VE, VC, VCE [V], IC [mA]**; เสริม IB, IE, VTH, RTH
- ความต้านทานรับ `100000` และ `100k` (ต้องแปลง kΩ → Ω ก่อนคำนวณ)
- หน่วย: V, Ω, β; กระแส µA/mA, แรงดัน V, ความต้านทาน Ω/kΩ ทศนิยม 3 ตำแหน่ง
- ข้อความ validation / region / warning ใช้ค่าคงที่ตาม task ห้ามเปลี่ยนถ้อยคำ
- ทุกคำสั่งรันจาก repo root `C:\Users\B6813413\Documents\Default Project`
- branch งาน: `week2/flask-dc-bias`
- เกณฑ์ตรวจรับ A1–A7 ของ Lab02 ต้องผ่านทั้งหมด

## Review Focus

- ช่องว่าง / ไม่กรอก → 400 + ข้อความ ไม่ใช่ 500 (Task 6)
- `abc`, `nan`, `inf`, `1e999` → ถูกปฏิเสธ (Task 3)
- `R1+R2` หรือ `RC+RE` เป็น 0 → ห้าม ZeroDivisionError (Task 3, Task 2)
- `VTH ≤ VBE` (cutoff) และ `VCE` ใกล้ 0 (saturation) → ต้องมี warning ชัดเจน (Task 2, Task 5)
- ค่า `100k`, `2.2k` → ต้องแปลงเป็น Ω ถูกต้อง (Task 3)
- β = 1 (ขอบล่าง) → สูตรยังถูก ไม่ crash (Task 2)
- VC ติดลบใน saturation → ต้องไม่รายงานเป็นค่าปกติเงียบ ๆ (Task 5)

---

### Task 1: Core DC calculation (active region)

**Files:**
- Create: `transistor-simulator/dc_bias.py`
- Create: `transistor-simulator/tests/test_dc_bias.py`
- Create: `transistor-simulator/tests/__init__.py` (ว่าง)
- Create: `transistor-simulator/requirements.txt`

**Interfaces:**
- Consumes: ไม่มี
- Produces: `dc_operating_point(vcc, r1, r2, rc, re, beta, vbe, vce_sat=0.2) -> dict` คืน key `vth, rth, ib, ic, ie, ve, vb, vc, vce, region, ic_sat` (SI: V, Ω, A; `region` ∈ `"active" | "saturation" | "cutoff"`)

- [ ] **Step 1: Write the failing test**

`transistor-simulator/tests/test_dc_bias.py`:

```python
import unittest

from dc_bias import dc_operating_point


class TestDCOperatingPoint(unittest.TestCase):
    def test_active_region_matches_reference(self):
        r = dc_operating_point(12, 100000, 22000, 2200, 1000, 100, 0.7)
        self.assertAlmostEqual(r["vth"], 2.1639344262295084, places=9)
        self.assertAlmostEqual(r["rth"], 18032.786885245903, places=6)
        self.assertAlmostEqual(r["ib"], 1.2298581462608458e-05, places=12)
        self.assertAlmostEqual(r["ic"], 0.0012298581462608458, places=12)
        self.assertAlmostEqual(r["ie"], 0.0012421567277234543, places=12)
        self.assertAlmostEqual(r["ve"], 1.2421567277234544, places=9)
        self.assertAlmostEqual(r["vb"], 1.9421567277234544, places=9)
        self.assertAlmostEqual(r["vc"], 9.29431207822614, places=9)
        self.assertAlmostEqual(r["vce"], 8.052155350502685, places=9)
        self.assertEqual(r["region"], "active")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: Implement `dc_operating_point` + requirements**

`transistor-simulator/dc_bias.py` — สูตรตาม design note §6 ครบทุกบรรทัด, คืน `region="active"` เมื่อ `ib > 0` และ `vce >= vce_sat` (สาขาอื่นเติม Task 2) และ `ic_sat = (vcc - vce_sat) / (rc + re)`

`transistor-simulator/requirements.txt`:

```
Flask>=3.0,<4.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (1 test)

- [ ] **Step 5: Commit**

```bash
git add transistor-simulator/dc_bias.py transistor-simulator/tests transistor-simulator/requirements.txt
git commit -m "feat(week2): add DC operating point calculation"
```

---

### Task 2: Region classification (cutoff / saturation) + β edge case

**Files:**
- Modify: `transistor-simulator/dc_bias.py`
- Test: `transistor-simulator/tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `dc_operating_point(...)` จาก Task 1
- Produces: `region` ครบสามค่า, `ic_sat` ถูกทุกกรณี

- [ ] **Step 1: Add failing tests**

```python
    def test_saturation_region_detected(self):
        r = dc_operating_point(12, 100000, 22000, 10000, 1000, 100, 0.7)
        self.assertEqual(r["region"], "saturation")
        self.assertAlmostEqual(r["ic_sat"], 1.0727272727272728e-03, places=12)
        self.assertLess(r["vce"], 0)

    def test_cutoff_region_detected(self):
        r = dc_operating_point(12, 100000, 2200, 2200, 1000, 100, 0.7)
        self.assertEqual(r["region"], "cutoff")
        self.assertLessEqual(r["vth"], 0.7)

    def test_beta_one_is_active(self):
        r = dc_operating_point(12, 100000, 22000, 2200, 1000, 1, 0.7)
        self.assertEqual(r["region"], "active")
        self.assertAlmostEqual(r["ib"], 7.307692307692309e-05, places=12)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: FAIL — saturation/cutoff ถูกจัดเป็น `"active"`

- [ ] **Step 3: Implement classification**

`cutoff` ถ้า `ib <= 0`, `saturation` ถ้า `vce < vce_sat`, มิฉะนั้น `active`

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add transistor-simulator/dc_bias.py transistor-simulator/tests/test_dc_bias.py
git commit -m "feat(week2): classify active, saturation and cutoff regions"
```

---

### Task 3: Resistance parsing + input validation

**Files:**
- Modify: `transistor-simulator/dc_bias.py`
- Modify: `transistor-simulator/tests/test_dc_bias.py`

**Interfaces:**
- Consumes: ไม่มี
- Produces:
  - `parse_resistance(text: str) -> float` — รับ `"100000"`, `"100k"`, `"2.2k"`, `" 10 K "`; raise `ValueError` เมื่อว่าง/ไม่ใช่ตัวเลข/ไม่ finite
  - `validate_inputs(values: dict[str, str]) -> dict[str, str]` — คืน `{field: ข้อความ}`; `{}` เมื่อถูกต้อง; ไม่ raise

- [ ] **Step 1: Add failing tests**

```python
from dc_bias import validate_inputs, parse_resistance


class TestParseResistance(unittest.TestCase):
    def test_plain_ohms(self):
        self.assertEqual(parse_resistance("100000"), 100000.0)

    def test_k_suffix(self):
        self.assertEqual(parse_resistance("100k"), 100000.0)
        self.assertEqual(parse_resistance("2.2k"), 2200.0)
        self.assertEqual(parse_resistance(" 10 K "), 10000.0)

    def test_invalid_raises(self):
        for bad in ("", "abc", "nan", "inf", "1e999"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_resistance(bad)


class TestValidateInputs(unittest.TestCase):
    def base(self, **over):
        data = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                "re": "1k", "beta": "100", "vbe": "0.7"}
        data.update(over)
        return data

    def test_valid_input_has_no_errors(self):
        self.assertEqual(validate_inputs(self.base()), {})

    def test_blank_field_is_rejected(self):
        self.assertIn("vcc", validate_inputs(self.base(vcc="")))

    def test_non_numeric_is_rejected(self):
        self.assertIn("r1", validate_inputs(self.base(r1="abc")))

    def test_non_finite_is_rejected(self):
        self.assertIn("rc", validate_inputs(self.base(rc="1e999")))

    def test_non_positive_resistors_rejected(self):
        for field in ("r1", "r2", "rc"):
            with self.subTest(field=field):
                self.assertIn(field, validate_inputs(self.base(**{field: "0"})))

    def test_negative_re_is_rejected(self):
        self.assertIn("re", validate_inputs(self.base(re="-1")))

    def test_beta_must_be_positive(self):
        for bad in ("0", "-5", "abc"):
            with self.subTest(bad=bad):
                self.assertIn("beta", validate_inputs(self.base(beta=bad)))

    def test_vbe_must_be_between_zero_and_vcc(self):
        self.assertIn("vbe", validate_inputs(self.base(vbe="0")))
        self.assertIn("vbe", validate_inputs(self.base(vbe="12")))

    def test_zero_vcc_is_rejected(self):
        self.assertIn("vcc", validate_inputs(self.base(vcc="0")))

    def test_zero_r1_plus_r2_does_not_divide_by_zero(self):
        errors = validate_inputs(self.base(r1="0", r2="0"))
        self.assertIn("r1", errors)
        self.assertIn("r2", errors)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: FAIL — `ImportError: cannot import name 'parse_resistance'`

- [ ] **Step 3: Implement parsing + validation**

ข้อความคงที่: `"กรุณากรอกค่านี้"`, `"ต้องเป็นตัวเลขที่จำกัด"`, `"ต้องมากกว่า 0"`, `"ต้องไม่ติดลบ"`, `"ต้องอยู่ระหว่าง 0 กับ VCC"` เก็บ error ทุกช่อง (ไม่หยุดที่ช่องแรก); ช่องความต้านทานใช้ `parse_resistance`, ช่องอื่นใช้ `float` + ตรวจ `math.isfinite`

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (17 tests)

- [ ] **Step 5: Commit**

```bash
git add transistor-simulator/dc_bias.py transistor-simulator/tests/test_dc_bias.py
git commit -m "feat(week2): parse k-ohm values and validate inputs"
```

---

### Task 4: Flask app, GET route, template and static CSS

**Files:**
- Create: `transistor-simulator/app.py`
- Create: `transistor-simulator/templates/index.html`
- Create: `transistor-simulator/static/style.css`
- Create: `transistor-simulator/tests/test_web.py`

**Interfaces:**
- Consumes: `dc_bias` (ยังไม่เรียก)
- Produces: Flask instance `app`; เทมเพลตมี input `name` = `vcc, r1, r2, rc, re, beta, vbe`, ปุ่ม "คำนวณ DC Bias", `vbe` มี `value="0.7"`

- [ ] **Step 1: Write failing test**

`transistor-simulator/tests/test_web.py`:

```python
import unittest

from app import app


class TestIndexPage(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        for field in (b'name="vcc"', b'name="r1"', b'name="r2"', b'name="rc"',
                      b'name="re"', b'name="beta"', b'name="vbe"'):
            self.assertIn(field, resp.data)
        self.assertIn(b'value="0.7"', resp.data)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Implement app + template + css**

- `app.py`: `app = Flask(__name__)`, route `GET /` → `render_template("index.html")`, `if __name__ == "__main__": app.run(debug=True)`
- `templates/index.html`: `<form method="post">` จัดกลุ่ม supply (VCC) → divider (R1, R2) → load (RC, RE) → transistor (β, VBE) ทุกช่องมี `<label>` ระบุหน่วย, `placeholder` ตัวอย่าง `100k`, ปุ่ม submit, `<link>` ไป `url_for('static', filename='style.css')`
- `static/style.css`: 2 คอลัมน์บนจอใหญ่ / 1 คอลัมน์บนมือถือ, ตารางผลอ่านง่าย

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (18 tests)

- [ ] **Step 5: Commit**

```bash
git add transistor-simulator/app.py transistor-simulator/templates transistor-simulator/static transistor-simulator/tests/test_web.py
git commit -m "feat(week2): add Flask form page and static styles"
```

---

### Task 5: POST route — success path, formatting, region warning

**Files:**
- Modify: `transistor-simulator/app.py`
- Modify: `transistor-simulator/templates/index.html`
- Modify: `transistor-simulator/tests/test_web.py`

**Interfaces:**
- Consumes: `dc_bias.dc_operating_point`, `dc_bias.validate_inputs`, `dc_bias.parse_resistance`
- Produces: `format_current(amps) -> str`, `format_voltage(volts) -> str`, `format_resistance(ohms) -> str`; เทมเพลตแสดงตารางเมื่อมี `result`

- [ ] **Step 1: Add failing tests**

```python
from app import app, format_current, format_voltage, format_resistance


class TestCalculateRoute(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        self.valid = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                      "re": "1k", "beta": "100", "vbe": "0.7"}

    def test_post_valid_shows_operating_point(self):
        resp = self.client.post("/", data=self.valid)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"2.164 V", resp.data)      # VTH
        self.assertIn(b"18.033 k\xce\xa9", resp.data)  # RTH
        self.assertIn(b"12.299 \xc2\xb5A", resp.data)  # IB
        self.assertIn(b"1.230 mA", resp.data)     # IC
        self.assertIn(b"1.242 mA", resp.data)     # IE
        self.assertIn(b"1.242 V", resp.data)      # VE
        self.assertIn(b"1.942 V", resp.data)      # VB
        self.assertIn(b"9.294 V", resp.data)      # VC
        self.assertIn(b"8.052 V", resp.data)      # VCE
        self.assertIn(b"Active", resp.data)

    def test_post_saturation_shows_warning(self):
        resp = self.client.post("/", data=dict(self.valid, rc="10k"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Saturation", resp.data)
        self.assertIn(b"1.073 mA", resp.data)
        self.assertIn("Forward-Active".encode("utf-8"), resp.data)

    def test_formatters_use_engineering_units(self):
        self.assertEqual(format_current(12.299e-06), "12.299 \u00b5A")
        self.assertEqual(format_current(1.229858e-03), "1.230 mA")
        self.assertEqual(format_voltage(8.0521553), "8.052 V")
        self.assertEqual(format_resistance(18032.7869), "18.033 k\u03a9")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: FAIL — ยังไม่มี formatter/ยังไม่คำนวณ

- [ ] **Step 3: Implement POST + formatters + result table**

- `POST /`: parse ด้วย `parse_resistance` สำหรับ r1, r2, rc, re และ `float` สำหรับ vcc, beta, vbe; ถ้า validate ผ่านเรียก `dc_operating_point` → ส่ง `result` ที่ format แล้วเข้าเทมเพลต
- formatter: `abs(x) >= 1e-3` → `f"{x*1000:.3f} mA"` มิฉะนั้น `f"{x*1e6:.3f} µA"`; แรงดัน `f"{v:.3f} V"`; ความต้านทาน `abs(r) >= 1000` → `f"{r/1000:.3f} kΩ"` มิฉะนั้น `f"{r:.3f} Ω"`
- เทมเพลต: ตาราง VTH, RTH, IB, IC, IE, VE, VB, VC, VCE, region (`Active` / `Saturation` / `Cutoff`); เมื่อ region ไม่ใช่ active แสดงกล่องเตือนที่มีคำว่า `Forward-Active` และ (ถ้า saturation) `IC(sat)`

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (21 tests)

- [ ] **Step 5: Commit**

```bash
git add transistor-simulator/app.py transistor-simulator/templates/index.html transistor-simulator/tests/test_web.py
git commit -m "feat(week2): render DC operating point with region warning"
```

---

### Task 6: POST route — error path with sticky form

**Files:**
- Modify: `transistor-simulator/app.py`
- Modify: `transistor-simulator/templates/index.html`
- Modify: `transistor-simulator/tests/test_web.py`

**Interfaces:**
- Consumes: `validate_inputs`
- Produces: response 400 พร้อม `errors` (dict) และ `values` (dict) เข้าเทมเพลต

- [ ] **Step 1: Add failing tests**

```python
    def test_post_invalid_returns_400_with_message(self):
        resp = self.client.post("/", data=dict(self.valid, vcc="0"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ต้องมากกว่า 0".encode("utf-8"), resp.data)

    def test_invalid_post_keeps_user_values(self):
        resp = self.client.post("/", data=dict(self.valid, r1="abc"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b'value="abc"', resp.data)
        self.assertIn(b'value="22k"', resp.data)

    def test_all_blank_returns_400(self):
        resp = self.client.post("/", data={})
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn(b"Active", resp.data)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: FAIL — ได้ 200 หรือไม่มีข้อความ error

- [ ] **Step 3: Implement error rendering**

`POST /`: ถ้า `errors` ไม่ว่าง → `render_template(..., errors=errors, values=request.form)`, status 400; เทมเพลตแสดงข้อความใต้ช่องนั้นด้วย `errors.get('vcc')` และเติม `value="{{ values.get('vcc', '') }}"` ทุกช่อง (VBE: `values.get('vbe', '0.7')`)

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (24 tests)

- [ ] **Step 5: Commit**

```bash
git add transistor-simulator/app.py transistor-simulator/templates/index.html transistor-simulator/tests/test_web.py
git commit -m "feat(week2): show validation errors and keep user input"
```

---

### Task 7: Project docs (README, AGENTS) and repo README conflict

**Files:**
- Modify: `README.md` (repo root — merge conflict ค้าง)
- Create: `transistor-simulator/README.md`
- Create: `transistor-simulator/AGENTS.md`

**Interfaces:**
- Consumes: โครงสร้างจริงจาก Task 1–6
- Produces: เอกสารที่ทำให้ A7 (clone → install → run → test) ผ่าน

- [ ] **Step 1: Fix root README conflict**

แทนบล็อก `<<<<<<< HEAD ... >>>>>>> feature/input-validation` ทั้งบล็อกด้วย README เดียว: ชื่อ repo, วัตถุประสงค์รายวิชา, Week 1 = DC Circuit Calculator (`electrical.py`), Week 2 = Transistor DC Bias Simulator (`transistor-simulator/`) ห้ามเหลือ marker

- [ ] **Step 2: Verify no conflict markers remain**

Run: `git grep -n -E "^(<<<<<<<|=======|>>>>>>>)" -- README.md`
Expected: ไม่มีผลลัพธ์ (exit 1)

- [ ] **Step 3: Write `transistor-simulator/README.md`**

ต้องมี: install (`python -m venv .venv`, activate, `pip install -r requirements.txt`), run (`python -m flask --app app run --debug` → http://127.0.0.1:5000/), test (`python -m unittest discover -s tests -v` จากในโฟลเดอร์), ตัวอย่างค่าอ้างอิง Lab02 + ผลที่ควรได้, ตาราง Frontend / Backend / Template / Static / HTTP request-response ชี้ไฟล์จริง, สมการ, ข้อจำกัด (DC + Forward-Active เท่านั้น), หมายเหตุการกรอก `k` suffix

- [ ] **Step 4: Write `transistor-simulator/AGENTS.md`**

Conventions: Python 3.12, Flask เท่านั้น, ห้ามเพิ่ม JS, สมการต้องอยู่ใน `dc_bias.py` และห้าม import Flask, ใช้ `unittest`, UI ภาษาไทย, รันเทสต์ก่อน commit, ห้าม commit ผลคำนวณที่ไม่มี test รองรับ, ห้ามลบ warning นอก active region

- [ ] **Step 5: Commit**

```bash
git add README.md transistor-simulator/README.md transistor-simulator/AGENTS.md
git commit -m "docs(week2): document app architecture and fix README conflict"
```

---

### Task 8: Verification evidence, reflection scaffold, push

**Files:**
- Create: `transistor-simulator/docs/validation.md`
- Create: `transistor-simulator/docs/reflection.md`

**Interfaces:**
- Consumes: ผลรันจริงทั้งหมด
- Produces: หลักฐานตามเกณฑ์ Lab02 §09–10 (test log + ตารางตรวจมือ)

- [ ] **Step 1: Run the full suite and capture output**

Run: `python -m unittest discover -s transistor-simulator/tests -t transistor-simulator -v`
Expected: `OK` (24 tests) — บันทึกจำนวน/ชื่อเทสต์ลง `docs/validation.md`

- [ ] **Step 2: Manual hand-check against the lab reference**

คำนวณมือด้วย VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, β=100, VBE=0.7 ตามสมการ §6 แล้วจด VTH, RTH, IB, IC, IE, VE, VB, VC, VCE ลงตารางเทียบค่ากับแอป (ต้องตรงที่ทศนิยม 3 ตำแหน่ง)

- [ ] **Step 3: Write `docs/validation.md`**

ตาราง: รายการตรวจ (A1–A7) | วิธี | ผลจริง | ผ่าน/ไม่ผ่าน + ค่าตรวจมือ + บรรทัดสรุปผลรันเทสต์ (คัดลอกของจริง)

- [ ] **Step 4: Scaffold `docs/reflection.md`**

หัวข้อให้ **นักศึกษาเขียนเอง**: Frontend/Backend/Template/Static คืออะไรในโปรเจกต์นี้, กด Calculate แล้ว HTTP request เดินทางอย่างไร, จุดที่ AI ช่วยและจุดที่ตรวจแก้เอง, ทำไมผลนอก Active Region ต้องมี warning, เหตุใดเปิด `templates/index.html` ตรง ๆ จึงไม่เท่ากับรัน Flask — ห้ามเติมคำตอบแทน

- [ ] **Step 5: Manual smoke test**

Run: `python transistor-simulator/app.py` แล้วเปิด http://127.0.0.1:5000/ กรอกค่าอ้างอิง → ต้องเห็นผลตรงตาราง; ทดลองกรอก `vcc=0` → เห็น error; ปิดเซิร์ฟเวอร์

- [ ] **Step 6: Commit**

```bash
git add transistor-simulator/docs/validation.md transistor-simulator/docs/reflection.md
git commit -m "docs(week2): add validation evidence and reflection scaffold"
```

- [ ] **Step 7: Push branch**

```bash
git push -u origin week2/flask-dc-bias
```

Expected: push สำเร็จ; merge เข้า `main` เป็นการตัดสินใจของผู้ใช้ (ไม่ทำในแผนนี้)
