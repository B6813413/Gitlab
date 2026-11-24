# Captures — หลักฐานภาพจริง Lab 04

ภาพทั้งหมดถูกเก็บใหม่หลัง UI รอบสุดท้าย (SPICE ปิดช่อง Lab 03 / กราฟเลื่อนได้บนจอแคบ)

| ไฟล์ | ขนาด | กรณี | วิธีเก็บ |
|---|---|---|---|
| `b5-transient-10mV-1kHz.png` | 785×3638 | B5 · Transient Vin=10 mV peak, f=1 kHz | Chrome headless โพสต์ฟอร์มจริงผ่าน iframe กว้าง 785px |
| `b6-transient-20mV-1kHz.png` | 785×3638 | B6 · เปลี่ยน amplitude เป็น 20 mV | Chrome headless โพสต์ฟอร์มจริงผ่าน iframe กว้าง 785px |
| `b8-desktop-bode-result.png` | 1280×900 | B8 · Desktop result + Bode chart | Chrome headless `--window-size=1280,900` |
| `b8-mobile-bode-result.png` | 390×1200 | B8 · Phone-width result + Bode chart | Chrome headless โพสต์ฟอร์มจริงผ่าน iframe กว้าง 390px |
| `b8-desktop-bode.png` | 1280×900 | B8 · Desktop GET/selector view | Chrome headless `--window-size=1280,900` |
| `b8-mobile-bode.png` | 390×844 | B8 · Phone-width GET/selector view | Chrome headless `--window-size=390,844` |

ค่าตัวเลข/กราฟที่ใช้ตัดสิน B1–B8 อ่านจาก DOM และ ngspice log ใน
[`../validation.md`](../validation.md) ไม่ได้ใช้ screenshot เป็นหลักฐานตัวเลขเพียงอย่างเดียว
