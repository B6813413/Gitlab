# Lab 04 BJT Amplifier Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ต่อยอด Flask DC Bias app จาก Lab 3 (`transistor-simulator/`) ให้เป็น CE Amplifier Simulator v1 ที่รัน ngspice จริงสำหรับ `.op`, `.ac`, `.tran` โดยยังคง DC Bias 3 แบบเดิมครบทุกเทสต์

**Architecture:** คง `dc_bias.py` และเส้นทาง analytical เดิมไว้ทั้งหมด เพิ่ม `spice_engine.py` เป็น adapter ที่สร้าง netlist → เรียก `ngspice` ผ่าน `subprocess.run` → อ่าน log ที่ `.print` ออกมา, เพิ่ม `charts.py` สร้าง SVG จากข้อมูลจริงฝั่งเซิร์ฟเวอร์ (ไม่เพิ่ม dependency) และขยาย `app.py`/template ให้เลือก analysis ได้โดยยังมีฟอร์ม 2 อันเหมือนเดิม

**Tech Stack:** Python 3.12, Flask 3.1, Jinja2, unittest, `ngspice` external binary, server-rendered SVG

**Spec:** `C:\Users\B6813413\Downloads\Lab04_BJT_Amplifier_Simulator_2-2569.html` (Lab 04 handout §01–§11), `transistor-simulator/AGENTS.md`, `transistor-simulator/docs/design-note.md`

## Global Constraints

- Python 3.12; dependency เดียวที่เพิ่มได้คือ `Flask` (ห้ามเพิ่ม JS framework/ORM/pytest/dependency อื่นโดยไม่ตกลงก่อน) — `transistor-simulator/AGENTS.md`
- ใช้ `unittest` เท่านั้น; รัน `python -m unittest discover -s tests -v` จาก `transistor-simulator/` ก่อน commit ทุกครั้ง
- สมการ/โมเดลไฟฟ้าอยู่ใน `dc_bias.py` หรือ `spice_engine.py`; **ห้าม** import Flask ในสองไฟล์นี้; `app.py` ทำเฉพาะ HTTP; template ห้ามฝังสมการฟิสิกส์; `static/style.css` ดูแล presentation
- UI และข้อความ error เป็นภาษาไทย; ทุกค่าที่แสดงต้องมีหน่วย; ข้อความ validation เดิม (`กรุณากรอกค่านี้`, `ต้องเป็นตัวเลขที่จำกัด`, `ต้องมากกว่า 0`, `ต้องไม่ติดลบ`, `ต้องอยู่ระหว่าง 0 กับ VCC`) ห้ามเปลี่ยน
- ห้ามลบ/เปลี่ยนคำเตือน Forward-Active เดิม; `VCE_SAT = 0.2` คงที่; ผล A1–A5 ของ Lab 3 ต้องตรงเดิมทุกประการ
- ฟอร์มต้องเป็น 2 อันไม่ซ้อนกัน: GET form มี `<select name="mode">` (และ `<select name="analysis">` ตัวใหม่) + POST form มี hidden `mode` และ hidden `analysis`
- วงจรอ้างอิง Baseline (ไม่มี emitter bypass): VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, RL 10 kΩ, CIN = COUT = 10 µF, source 10 mV peak / 1 kHz
- ngspice เป็น external binary: เรียกด้วย argument เป็น **list**, **ห้าม** `shell=True`, มี `timeout`, แยก working directory ต่อรอบด้วย `tempfile.TemporaryDirectory`, ตรวจ `shutil.which("ngspice")`, exit code, log ว่าง และข้อผิดพลาดเสมอ
- ห้าม fabricate trace/hard-code ค่า success/โชว์กราฟเก่าตอน engine fail; ต้องมีป้าย `ngspice`, run status, ชื่อ BJT model และหน่วยบนแกนกราฟ
- ผล analytical (Lab 3) กับผล SPICE ต้องมีป้ายแยกที่มา ห้ามรวมเป็นค่าประเภทเดียวกัน
- เกณฑ์ B1–B8 ต้องบันทึกเป็น PASS/FAIL/NOT RUN พร้อมหลักฐานจริงใน `docs/validation.md`; ถ้า tool ไม่ได้รันให้เขียน NOT RUN ตามความจริง
- งานอยู่บน branch ใหม่ `lab04/spice-simulator` แยกจาก `main`; commit เล็ก ๆ ครั้งละหนึ่งงาน; ห้าม commit `.venv/`, `.env`, credentials หรือ run file ชั่วคราว

## Review Focus

- ngspice ไม่มีใน PATH / ติดตั้งไม่สำเร็จ → ต้องขึ้น error status ชัดเจนและ **ไม่มี** กราฟหรือตัวเลข success ค้าง (Task 2, Task 6)
- input ผิด เช่น `RE=0`, `abc`, `nan`, `1e999` หรือข้อความมี `;` → ถูกปฏิเสธก่อนสร้าง netlist, HTTP 400, ไม่ให้ข้อความฟอร์มเข้า solver (Task 1, Task 5)
- solver exit ไม่เป็นศูนย์ / timeout / log ว่าง / `.print` ไม่มีแถว → error status ไม่ใช่ “Success” (Task 2, Task 5)
- เปลี่ยน RE หรือ amplitude/frequency แล้วต้องเปลี่ยน netlist และกราฟจริง → ทดสอบว่าข้อมูลชุดที่ 2 ต่างจากชุดที่ 1 (Task 1, Task 3, Task 4)
- สับสน `.ac` กับ `.tran` หรือไม่มีหน่วย/ที่มา → แต่ละ analysis มีแกน+หน่วย+ป้าย engine แยกกันชัดเจน (Task 3, Task 4, Task 6)

---

### Task 1: Reference CE netlist builder + SPICE input validation

**Files:**
- Create: `transistor-simulator/spice_engine.py` (ไม่ import Flask)
- Create: `transistor-simulator/tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `parse_resistance()` จาก `dc_bias.py`
- Produces:
  - `SPICE_DEFAULTS: dict` — ค่า baseline ตาม Global Constraints (`vcc`, `r1`, `r2`, `rc`, `re`, `rl`, `cin`, `cout`, `amp`, `freq`, `bjt_model`)
  - `validate_spice_inputs(values: dict) -> dict[str, str]` — error ภาษาไทยตามข้อความเดิมของ `dc_bias.py`
  - `build_netlist(params: dict, analysis: str) -> str` — `analysis` ∈ `"dc" | "ac" | "tran"`; คืน netlist ที่มี directive และ `.print` ของ analysis นั้นเท่านั้น

- [ ] **Step 1: เขียนเทสต์ที่ยัง fail**

`transistor-simulator/tests/test_spice_engine.py`:

```python
import unittest
from spice_engine import SPICE_DEFAULTS, build_netlist, validate_spice_inputs

class TestNetlist(unittest.TestCase):
    def test_dc_netlist_has_op_and_expected_nodes(self):
        net = build_netlist(SPICE_DEFAULTS, "dc")
        self.assertIn(".op", net)
        self.assertNotIn(".ac", net)
        self.assertNotIn(".tran", net)
        for token in ("R1 vcc b 100k", "R2 b 0 22k", "RC vcc c 2.2k",
                      "RE e 0 1k", "Q1 c b e", "CIN vin b 10u",
                      "COUT c vout 10u", "RL vout 0 10k", ".end"):
            self.assertIn(token, net)

    def test_ac_and_tran_are_distinct_directives(self):
        ac = build_netlist(SPICE_DEFAULTS, "ac")
        tran = build_netlist(SPICE_DEFAULTS, "tran")
        self.assertIn(".ac dec", ac)
        self.assertIn("vdb(vout)", ac)
        self.assertNotIn(".tran", ac)
        self.assertIn(".tran", tran)
        self.assertIn("v(vin)", tran)
        self.assertNotIn(".ac", tran)

    def test_changed_params_change_netlist(self):
        base = build_netlist(SPICE_DEFAULTS, "tran")
        changed = build_netlist(dict(SPICE_DEFAULTS, re="2k", freq="2k"), "tran")
        self.assertNotEqual(base, changed)
        self.assertIn("RE e 0 2k", changed)
        self.assertIn("2k 0 0", changed)

    def test_unknown_analysis_raises(self):
        with self.assertRaises(ValueError):
            build_netlist(SPICE_DEFAULTS, "bogus")

class TestSpiceValidation(unittest.TestCase):
    def test_re_zero_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, re="0"))
        self.assertIn("re", errs)
        self.assertEqual(errs["re"], "ต้องมากกว่า 0")

    def test_injection_string_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, amp="0.01;rm -rf /"))
        self.assertIn("amp", errs)

    def test_non_finite_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, freq="nan"))
        self.assertIn("freq", errs)
```

- [ ] **Step 2: รันเทสต์จน fail**

Run: `python -m unittest discover -s tests -v` (workdir `transistor-simulator`)
Expected: FAIL — `ModuleNotFoundError: No module named 'spice_engine'`

- [ ] **Step 3: implement**

เขียน `spice_engine.py`: ใช้ `math.isfinite(float(...))` ตรวจ `vcc/freq/amp/`, `parse_resistance` ตรวจ `r1/r2/rc/re/rl/cin/cout` ( capacitor เขียนเป็น `10u` ใน netlist ), `bjt_model` ต้องเป็น `[A-Za-z0-9_]+` เท่านั้น; netlist ใช้ node `vcc b c e vin vout`, `.model QNPN NPN(IS=1e-14 BF=100 VAF=100)` และแปลงค่า SI เป็น string หน่วย SPICE (`k`, `u`) ที่จุดเดียว

- [ ] **Step 4: รันเทสต์จนผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: OK รวมเทสต์เดิม 62 ตัว + ใหม่ 7 ตัว

- [ ] **Step 5: commit**

```bash
git add transistor-simulator/spice_engine.py transistor-simulator/tests/test_spice_engine.py
git commit -m "feat(lab04): add CE netlist builder and SPICE input validation"
```

---

### Task 2: ngspice runner + ASCII log parser

**Files:**
- Modify: `transistor-simulator/spice_engine.py`
- Modify: `transistor-simulator/tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `build_netlist()` จาก Task 1
- Produces:
  - `run_analysis(params: dict, analysis: str, engine_path: str | None = None, timeout: int = 20) -> dict` คืน key `status` (`"success" | "error"`), `engine`, `analysis`, `model`, `values`, `series`, `log_excerpt`, `error`
  - `parse_op_log(log: str) -> dict[str, float]` คืน `vb, ve, vc, vce, ic` (SI)
  - `parse_print_table(log: str, columns: list[str]) -> list[dict[str, float]]`

- [ ] **Step 1: เพิ่มเทสต์ parser และ error path**

```python
class TestParsers(unittest.TestCase):
    def test_parse_op_log(self):
        log = "node        volt       volt\nvcc         1.200000e+01\nb           1.942000e+00\ne           1.242000e+00\nc           9.294000e+00\nvce         8.052000e+00\nic          1.230000e-03\n"
        op = parse_op_log(log)
        self.assertAlmostEqual(op["vb"], 1.942)
        self.assertAlmostEqual(op["ic"], 0.00123)

    def test_parse_print_table_skips_header_and_maps_columns(self):
        log = "Index freq vdb(vout) vp(vout)\n0 1.000000e+03 -4.200000e+00 -1.750000e+02\n1 2.000000e+03 -4.500000e+00 -1.760000e+02\n"
        rows = parse_print_table(log, ["freq", "gain_db", "phase_deg"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["phase_deg"], -175.0)

class TestRunnerErrors(unittest.TestCase):
    @patch("spice_engine.shutil.which", return_value=None)
    def test_missing_engine_returns_error_not_success(self, _):
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "error")
        self.assertIn("ngspice", r["error"])
        self.assertIsNone(r["values"])

    @patch("spice_engine.subprocess.run")
    def test_nonzero_exit_returns_error(self, mock_run):
        mock_run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="fatal")
        r = run_analysis(SPICE_DEFAULTS, "dc", engine_path="ngspice")
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["values"])
```

- [ ] **Step 2: รันเทสต์ให้ fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `ImportError: cannot import name 'run_analysis'`

- [ ] **Step 3: implement runner**

`run_analysis` เขียน netlist ลง `case.cir` ใน `TemporaryDirectory`, เรียก `ngspice -b -o run.log -r run.raw case.cir` ด้วย list argument + `cwd=tmp` + `timeout` + `capture_output`; ถ้า `shutil.which` ไม่เจอ/returncode ≠ 0/log ว่าง/parser คืน [] → คืน `status="error"` พร้อมข้อความไทยและ `values/series=None` เสมอ; เก็บ `log_excerpt` 2000 ตัวอักษรสุดท้ายเพื่อแสดงหลักฐาน

- [ ] **Step 4: รันเทสต์จนผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 5: commit**

```bash
git add transistor-simulator/spice_engine.py transistor-simulator/tests/test_spice_engine.py
git commit -m "feat(lab04): add ngspice subprocess runner and log parser"
```

---

### Task 3: Server-rendered SVG charts (no new dependency)

**Files:**
- Create: `transistor-simulator/charts.py`
- Create: `transistor-simulator/tests/test_charts.py`

**Interfaces:**
- Consumes: `series` จาก `run_analysis()` (`list[dict]`)
- Produces:
  - `render_bode_svg(series: list[dict]) -> str`
  - `render_transient_svg(series: list[dict]) -> str`

- [ ] **Step 1: เขียนเทสต์**

```python
class TestCharts(unittest.TestCase):
    def test_bode_has_units_and_data_points(self):
        rows = [{"freq": 100, "gain_db": -3, "phase_deg": -170},
                {"freq": 1000, "gain_db": -5, "phase_deg": -180}]
        svg = render_bode_svg(rows)
        self.assertIn("Frequency (Hz)", svg)
        self.assertIn("Gain (dB)", svg)
        self.assertIn("Phase (°)", svg)
        self.assertGreaterEqual(svg.count("L"), 4)

    def test_transient_reflects_input_amplitude(self):
        small = render_transient_svg([{"time": 0, "vin": 0.01, "vout": -0.1},
                                      {"time": 1, "vin": 0.02, "vout": -0.2}])
        large = render_transient_svg([{"time": 0, "vin": 0.1, "vout": -1.0},
                                      {"time": 1, "vin": 0.2, "vout": -2.0}])
        self.assertIn("Time (ms)", small)
        self.assertIn("Voltage (V)", small)
        self.assertNotEqual(small, large)
```

- [ ] **Step 2: รันให้ fail, Step 3 implement, Step 4 รันให้ผ่าน**

implement: คำนวณ min/max จากข้อมูลจริง, สร้าง `<polyline points="...">` สำหรับ gain/phase หรือ vin/vout, มีแกน/grid/legend และ `role="img" aria-label` ภาษาไทย; ห้ามใส่ตัวเลขผลจำลองคงที่ในโค้ด

- [ ] **Step 5: commit**

```bash
git add transistor-simulator/charts.py transistor-simulator/tests/test_charts.py
git commit -m "feat(lab04): add dependency-free SVG charts from real series"
```

---

### Task 4: Flask analysis dispatch + result provenance

**Files:**
- Modify: `transistor-simulator/app.py`
- Create: `transistor-simulator/tests/test_spice_web.py`

**Interfaces:**
- Consumes: `validate_spice_inputs`, `run_analysis`, `render_bode_svg`, `render_transient_svg`
- Produces: `ANALYSIS_LABELS`, `analysis` context variable, `spice_result` context variable; `result` เส้นทางเดิมไม่เปลี่ยน

- [ ] **Step 1: เขียนเทสต์**

```python
class TestSpiceDispatch(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_get_has_analysis_selector_and_still_two_forms(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertEqual(html.count("<form"), 2)
        self.assertIn('name="analysis"', html)
        self.assertIn("SPICE DC (.op)", html)

    @patch("app.run_analysis")
    def test_post_spice_dc_shows_engine_status(self, mock_run):
        mock_run.return_value = {"status": "success", "engine": "ngspice",
            "analysis": "dc", "model": "QNPN", "values": {"vb": 1.942, "ve": 1.242,
            "vc": 9.294, "vce": 8.052, "ic": 0.00123}, "series": None,
            "log_excerpt": "ok", "error": None}
        resp = self.client.post("/", data={"analysis": "spice_dc", "mode": "voltage_divider",
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
            "rl": "10", "cin": "10", "cout": "10", "amp": "0.01", "freq": "1k",
            "bjt_model": "QNPN"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Engine: ngspice", resp.data)
        self.assertIn(b"SPICE (.op)", resp.data)
        self.assertIn(b"1.230 mA", resp.data)

    @patch("app.run_analysis")
    def test_engine_error_never_shows_success_values(self, mock_run):
        mock_run.return_value = {"status": "error", "engine": "ngspice",
            "analysis": "dc", "model": "QNPN", "values": None, "series": None,
            "log_excerpt": "", "error": "ไม่พบ ngspice"}
        resp = self.client.post("/", data={"analysis": "spice_dc", "mode": "voltage_divider",
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
            "rl": "10", "cin": "10", "cout": "10", "amp": "0.01", "freq": "1k",
            "bjt_model": "QNPN"})
        self.assertEqual(resp.status_code, 502)
        self.assertNotIn(b"Success", resp.data)
        self.assertIn("ไม่พบ ngspice".encode("utf-8"), resp.data)

    @patch("app.run_analysis")
    def test_changed_source_changes_netlist_sent_to_engine(self, mock_run):
        mock_run.side_effect = lambda params, analysis, **kw: {"status": "error",
            "error": "stop", "values": None, "series": None, "engine": "ngspice",
            "analysis": analysis, "model": params["bjt_model"], "log_excerpt": ""}
        base = {"analysis": "spice_tran", "re": "1", "amp": "0.01", "freq": "1k"}
        self.client.post("/", data=base)
        self.client.post("/", data=dict(base, amp="0.02", freq="2k"))
        self.assertNotEqual(mock_run.call_args_list[0].args[0]["amp"],
                            mock_run.call_args_list[1].args[0]["amp"])
```

- [ ] **Step 2: รันให้ fail; Step 3 implement**

`analysis = request.form.get("analysis") or request.args.get("analysis") or "bias"`; ค่าไม่รู้จัก → error 400 เหมือน unknown mode; ถ้า `analysis=="bias"` ให้เดินโค้ดเดิมทุกบรรทัด; นอกนั้น parse ผ่าน `validate_spice_inputs` → `run_analysis` → สร้าง `spice_result` พร้อม formatter เดิม (`format_voltage`, `format_ic_ma`) และ SVG; invalid input → 400, engine error → 502; ส่ง `analysis`, `analysis_labels`, `spice_result` เข้า template ทุกครั้ง

- [ ] **Step 4: รันเทสต์จนผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: OK รวม 62 เดิม + เทสต์ใหม่ทุกตัว

- [ ] **Step 5: commit**

```bash
git add transistor-simulator/app.py transistor-simulator/tests/test_spice_web.py
git commit -m "feat(lab04): dispatch DC/AC/transient analysis in Flask app"
```

---

### Task 5: Template + CSS UI refinement

**Files:**
- Modify: `transistor-simulator/templates/index.html`
- Modify: `transistor-simulator/static/style.css`
- Modify: `transistor-simulator/tests/test_spice_web.py`

**Interfaces:**
- Consumes: `analysis`, `analysis_labels`, `spice_result` จาก Task 4
- Produces: หน้าเว็บที่มี analysis tabs, engine status badge, ผล DC พร้อมป้ายที่มา, Bode/transient SVG

- [ ] **Step 1: เพิ่มเทสต์โครงสร้าง**

```python
    def test_spice_result_block_has_provenance_and_units(self):
        html = self.client.get("/").get_data(as_text=True)
        for marker in ("analysis", "Engine status", "SPICE (.op)", "Bode", "Transient"):
            self.assertIn(marker, html)
```

- [ ] **Step 2: implement template**

GET form เดิมเพิ่ม `<select name="analysis">` อยู่ใน `<form method="get">` เดิม (ห้ามเพิ่ม `<form>`); POST form มี hidden `analysis`; แสดงช่อง CE เฉพาะ analysis แบบ SPICE; results แบ่งเป็น “Analytical (Lab 03)” กับ “SPICE simulation” พร้อม badge `ngspice`, model, status, log excerpt (collapsed) และ SVG ที่ได้จาก Task 3; อ่านง่ายบน desktop ~1280 px และ mobile ~390 px

- [ ] **Step 3: implement CSS**

เพิ่ม class สำหรับ analysis tabs, status badge (success/error), chart container, legend; ใช้ grid เดิมเป็นฐาน; ห้ามเปลี่ยนการคำนวณหรือผลลัพธ์

- [ ] **Step 4: รันเทสต์/ตรวจ diff**

Run: `python -m unittest discover -s tests -v`
Expected: OK; ตรวจว่า `html.count("<form") == 2` ยังผ่านและไม่มี inline physics ใน template

- [ ] **Step 5: commit**

```bash
git add transistor-simulator/templates/index.html transistor-simulator/static/style.css transistor-simulator/tests/test_spice_web.py
git commit -m "ui(lab04): add analysis selector, engine status and real plot panels"
```

---

### Task 6: ngspice install, browser acceptance B1–B8, docs, push

**Files:**
- Modify: `transistor-simulator/README.md`
- Modify: `transistor-simulator/docs/validation.md`
- Modify: `transistor-simulator/docs/design-note.md`
- Modify: `transistor-simulator/docs/reflection.md`
- Create: `transistor-simulator/docs/captures/` (ถ้ามี screenshot จริง)

**Interfaces:**
- Consumes: ทุก task ข้างต้น + `ngspice` binary

- [ ] **Step 1: ติดตั้ง/ตรวจ ngspice**

Run: `winget install --id ngspice -e --accept-source-agreements --accept-package-agreements` (ถ้าไม่มีใน PATH) แล้ว `ngspice --version`; บันทึกเวอร์ชันจริงใน validation

- [ ] **Step 2: รันแอปจริง**

Run (workdir `transistor-simulator`): `python -m flask --app app run --debug` แล้วเปิด `http://127.0.0.1:5000/`

- [ ] **Step 3: ตรวจ B1–B8 ด้วย browser จริง**

Load `browser` skill ก่อนเรียก tool; ทำ Navigate → Snapshot → Fill → Click → Snapshot → Read values → Compare ตามใบงาน §09; บันทึก PASS/FAIL/NOT RUN และหลักฐาน (snapshot/screenshot/ngspice log) ลง `docs/validation.md` โดยไม่เคลม PASS ถ้า tool ไม่ได้รัน

- [ ] **Step 4: อัปเดตเอกสาร**

README: วิธีติดตั้ง ngspice, รัน server, รันเทสต์, model ที่ใช้, ข้อจำกัด; design-note: architecture delta Lab 3 → Lab 4; reflection: 3–5 บรรทัด AI ทำอะไร/นักศึกษาตรวจอะไร; validation: ตาราง B1–B8 + เวอร์ชัน ngspice + BJT model + ความคลาดเคลื่อน

- [ ] **Step 5: verification สุดท้าย**

Run: `python -m unittest discover -s tests -v`
Expected: OK ทุกเทสต์; ตรวจ `git diff --check`; ตรวจไม่มี `.venv/`, `.env`, run file ชั่วคราว

- [ ] **Step 6: code review + commit + push**

Invoke `requesting-code-review` ก่อน commit สุดท้าย; แก้ตาม review; commit แล้ว `git push origin lab04/spice-simulator`; รายงาน repo URL + commit SHA

---

## Self-Review

- ครอบ §01–§11 ของใบงาน: outcomes/architecture/simulation flow/setup/plan/engineering/build/UI/browser/submission ถูก_map ไป Task 1–6 แล้ว
- §08 Impeccable ไม่มี skill -installed ใน harness นี้ → ถูกบันทึกเป็นข้อจำกัด/NOT RUN ใน Task 6 แทนการอ้างว่าทำแล้ว; ถ้าผู้ใช้อนุญาตให้ `npx impeccable install` จะเพิ่มเป็น step ใน Task 5 ก่อน commit
- ทุก interface ใช้ชื่อ/type สอดคล้องกันระหว่าง Task 1→2→3→4→5; formatter เดิมถูก reuse ไม่เขียนใหม่
- Global Constraints ถูกคัดจาก `AGENTS.md` และใบงาน verbatim; ไม่มี dependency ใหม่นอกเหนือจาก external `ngspice` ที่ใบงานบังคับ
