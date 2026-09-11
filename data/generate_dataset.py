#!/usr/bin/env python3
"""Generate TRINETRA's synthetic demo dataset.

ENTIRELY FICTIONAL. No real people, phone numbers, accounts or case data.

The story it encodes (this is what makes the demo land):
  - Ramesh Kumar appears as "Ramesh Kumar", "Ramesh Kr." and "Kalia" (urf)
    across two FIRs -> entity resolution has something real to find.
  - Ramesh sends 4 transfers of ~Rs 45,000 each within 36 hours, all under
    the Rs 50,000 reporting threshold -> financial structuring fires.
  - On the night of the incident he makes 7 calls in 40 minutes to 5 numbers
    -> communication burst fires.
  - Two devices share tower TWR-DEL-114 in the same 12-minute window
    -> co-location fires (cell-tower precision, so NO metre claim).
  - Suspect A and Mule B share 3 mutual contacts but never speak directly
    -> Adamic-Adar surfaces them as an unverified lead.

Usage:  python data/generate_dataset.py
"""
import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(26189)

OUT = Path(__file__).parent / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)

INCIDENT = datetime(2026, 8, 14, 21, 30)

PEOPLE = {
    "ramesh":  {"name": "Ramesh Kumar",  "alias": "Kalia",  "phone": "9812345670"},
    "suresh":  {"name": "Suresh Yadav",  "alias": "",       "phone": "9812345671"},
    "mohd":    {"name": "Mohd Irfan",    "alias": "Irfan",  "phone": "9812345672"},
    "vikas":   {"name": "Vikas Sharma",  "alias": "",       "phone": "9812345673"},
    "deepak":  {"name": "Deepak Mishra", "alias": "Mule B", "phone": "9812345674"},
    "anil":    {"name": "Anil Verma",    "alias": "",       "phone": "9812345675"},
    "sunil":   {"name": "Sunil Rathore", "alias": "",       "phone": "9812345676"},
}
ACCOUNTS = {
    "ramesh": "50100234567891", "suresh": "50100234567892",
    "mohd": "50100234567893", "deepak": "50100234567894",
    "vikas": "50100234567895",
}
VEHICLES = {"ramesh": "DL08CA4321", "mohd": "HR26BC7788", "vikas": "UP16DE9012"}
TOWERS = ["TWR-DEL-114", "TWR-DEL-207", "TWR-GGN-051", "TWR-NOI-083"]

# Approximate tower positions (synthetic, Delhi NCR) - used for the map view.
TOWER_POS = {
    "TWR-DEL-114": (28.5355, 77.2410), "TWR-DEL-207": (28.5672, 77.2100),
    "TWR-GGN-051": (28.4595, 77.0266), "TWR-NOI-083": (28.5355, 77.3910),
}


# --------------------------------------------------------------- FIR 1
FIR1 = f"""FIRST INFORMATION REPORT
(Under Section 173 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

FIR No.: 0142/2026
Police Station: Cyber Cell, South District, New Delhi
Date of Registration: {(INCIDENT - timedelta(days=1)):%d/%m/%Y}
Sections: BNS-318 (Cheating), BNS-317 (Stolen property), BNS-61 (Criminal conspiracy)

Complainant: Smt. Kavita Raghavan, R/o Lajpat Nagar, New Delhi
Complainant contact: 9811100022

BRIEF FACTS OF THE CASE:

Complainant states that on {(INCIDENT - timedelta(days=3)):%d/%m/%Y} she received a
telephone call from mobile number 9812345670 wherein the caller identified
himself as a bank officer. The caller, later identified as Ramesh Kumar urf
Kalia, S/o Late Shri Mohan Lal, R/o Sangam Vihar, New Delhi, induced the
complainant to disclose her banking credentials.

A sum of Rs 3,85,000/- was subsequently transferred from the complainant's
account in four tranches to account number 50100234567891 held in the name of
the said Ramesh Kumar.

During preliminary enquiry it was revealed that the accused was in regular
contact with one Suresh Yadav (mobile 9812345671) and one Mohd Irfan urf Irfan
(mobile 9812345672). A vehicle bearing registration number DL08CA4321 was seen
near the complainant's residence and is registered in the name of Ramesh Kumar.

The accused also operates UPI handle ramesh.kalia@okaxis. Aadhaar number
4521 8890 3312 was furnished at the time of account opening.

Accordingly, a case under the above-mentioned sections is registered and
investigation is taken up.

Investigating Officer: Inspector R. Malhotra
"""

# --------------------------------------------------------------- FIR 2
FIR2 = f"""प्रथम सूचना रिपोर्ट / FIRST INFORMATION REPORT

FIR No.: 0187/2026
Police Station: Cyber Cell, South District, New Delhi
Date of Registration: {INCIDENT:%d/%m/%Y}
Sections: BNS-318, BNS-61, BNS-111 (Organised crime)

शिकायतकर्ता / Complainant: Shri Mahesh Gupta, R/o Kalkaji, New Delhi
संपर्क / Contact: 9811100033

संक्षिप्त विवरण / BRIEF FACTS:

शिकायतकर्ता ने बताया कि दिनांक {(INCIDENT - timedelta(days=2)):%d/%m/%Y} को उसे
मोबाइल नंबर 9812345672 से कॉल आया। कॉल करने वाले ने स्वयं को Ramesh Kr. बताया
और बैंक खाता संख्या 50100234567893 में राशि स्थानांतरित करने को कहा।

Investigation has revealed that the person identifying himself as Ramesh Kr.
is the same individual as Ramesh Kumar urf Kalia named in FIR 0142/2026 of
this police station. The mobile number 9812345670 used in the earlier case is
linked to the same UPI handle ramesh.kalia@okaxis.

आरोपी के सहयोगी / Associates identified: Deepak Mishra (मोबाइल 9812345674),
Vikas Sharma (मोबाइल 9812345673). वाहन संख्या HR26BC7788 भी घटनास्थल के पास
देखा गया, जो Mohd Irfan के नाम पर पंजीकृत है।

बैंक शाखा IFSC कोड HDFC0001234 के माध्यम से लेनदेन किया गया।

जांच अधिकारी / Investigating Officer: Inspector R. Malhotra
"""

# ----------------------------------------------------- SURVEILLANCE REPORT
SURVEILLANCE = f"""SURVEILLANCE REPORT — RESTRICTED
Reference: SUR/SD/2026/0091
Prepared by: SI Arjun Nair, South District
Period of observation: {(INCIDENT - timedelta(days=2)):%d/%m/%Y} to {INCIDENT:%d/%m/%Y}

OBSERVATIONS:

1. Subject Ramesh Kumar urf Kalia (mobile 9812345670) was observed on
   {(INCIDENT - timedelta(days=2)):%d/%m/%Y} at approximately 19:40 hrs at a
   tea stall near Sangam Vihar, in the company of one individual later
   identified as Suresh Yadav.

2. Vehicle DL08CA4321 was observed departing the location at 20:15 hrs.

3. On {(INCIDENT - timedelta(days=1)):%d/%m/%Y}, subject was observed meeting
   an unidentified male near Kalkaji Metro Station. The second individual was
   subsequently identified through vehicle registration HR26BC7788 as
   Mohd Irfan.

4. Technical surveillance indicates the subject's device and the device of
   Deepak Mishra (9812345674) were associated with the same serving cell
   TWR-DEL-114 during an overlapping window on {INCIDENT:%d/%m/%Y}.

NOTE: Cell-site association does not establish physical proximity to a
specific distance. Corroboration required.
"""


def write_firs():
    (OUT / "FIR_0142_2026.txt").write_text(FIR1, encoding="utf-8")
    (OUT / "FIR_0187_2026.txt").write_text(FIR2, encoding="utf-8")
    (OUT / "SURVEILLANCE_REPORT.txt").write_text(SURVEILLANCE, encoding="utf-8")

    # Try to also emit real PDFs if reportlab is available
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as pdfcanvas

        for name, body in (("FIR_0142_2026.pdf", FIR1),
                           ("SURVEILLANCE_REPORT.pdf", SURVEILLANCE)):
            c = pdfcanvas.Canvas(str(OUT / name), pagesize=A4)
            width, height = A4
            y = height - 50
            for line in body.split("\n"):
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.setFont("Helvetica", 9)
                c.drawString(45, y, line[:105])
                y -= 12
            c.save()
        print("  PDFs written (reportlab)")
    except ImportError:
        print("  reportlab not installed — .txt versions written instead")
        print("  (pip install reportlab  to also get PDFs)")


def write_cdr():
    """Includes the communication burst AND the shared-tower window."""
    rows = []

    # --- normal background traffic over 5 days ---
    for day in range(5):
        base = INCIDENT - timedelta(days=5 - day, hours=random.randint(1, 8))
        for _ in range(random.randint(4, 8)):
            a, b = random.sample(list(PEOPLE), 2)
            ts = base + timedelta(minutes=random.randint(0, 600))
            rows.append({
                "caller": PEOPLE[a]["phone"], "callee": PEOPLE[b]["phone"],
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": random.randint(20, 300),
                "tower_id": random.choice(TOWERS),
                "call_type": "OUTGOING",
            })

    # --- the burst: 7 calls in 40 minutes on incident night ---
    burst_start = INCIDENT - timedelta(minutes=45)
    targets = ["suresh", "mohd", "vikas", "anil", "sunil", "mohd", "suresh"]
    for i, target in enumerate(targets):
        ts = burst_start + timedelta(minutes=i * 6)
        rows.append({
            "caller": PEOPLE["ramesh"]["phone"], "callee": PEOPLE[target]["phone"],
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(15, 90),
            "tower_id": "TWR-DEL-114",
            "call_type": "OUTGOING",
        })

    # --- shared tower window: Ramesh + Deepak on TWR-DEL-114 ---
    for i in range(3):
        ts = INCIDENT + timedelta(minutes=i * 4)
        rows.append({
            "caller": PEOPLE["deepak"]["phone"], "callee": PEOPLE["anil"]["phone"],
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(30, 120),
            "tower_id": "TWR-DEL-114", "call_type": "OUTGOING",
        })

    # --- GPS-precise handset fixes: a genuine rendezvous the map can show ---
    base_lat, base_lon = 28.5356, 77.2412
    for i, who in enumerate(["ramesh", "deepak", "ramesh", "deepak"]):
        ts = INCIDENT + timedelta(minutes=i * 3)
        rows.append({
            "caller": PEOPLE[who]["phone"],
            "callee": PEOPLE["sunil"]["phone"],
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": random.randint(20, 60),
            "tower_id": "TWR-DEL-114", "call_type": "OUTGOING",
            "lat": round(base_lat + random.uniform(-0.0002, 0.0002), 6),
            "lon": round(base_lon + random.uniform(-0.0002, 0.0002), 6),
        })

    # --- mutual contacts for the Adamic-Adar lead (never A<->B directly) ---
    for mutual in ("vikas", "anil", "sunil"):
        for who in ("ramesh", "deepak"):
            ts = INCIDENT - timedelta(days=random.randint(1, 4),
                                      hours=random.randint(0, 12))
            rows.append({
                "caller": PEOPLE[who]["phone"], "callee": PEOPLE[mutual]["phone"],
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "duration": random.randint(40, 200),
                "tower_id": random.choice(TOWERS), "call_type": "OUTGOING",
            })

    rows.sort(key=lambda r: r["timestamp"])
    fields = ["caller", "callee", "timestamp", "duration", "tower_id",
              "call_type", "lat", "lon"]
    with open(OUT / "CDR.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return len(rows)


def write_bank():
    """Includes the structuring pattern: 4 x ~Rs 45,000 in 36 hours."""
    rows = []

    for _ in range(14):
        a, b = random.sample(list(ACCOUNTS), 2)
        ts = INCIDENT - timedelta(days=random.randint(3, 20),
                                  hours=random.randint(0, 23))
        rows.append({
            "txn_id": f"TXN{random.randint(100000, 999999)}",
            "from_account": ACCOUNTS[a], "to_account": ACCOUNTS[b],
            "amount": random.choice([2500, 7800, 12000, 3400, 18500]),
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "ifsc": "HDFC0001234", "mode": "IMPS",
        })

    # --- THE STRUCTURING PATTERN ---
    struct_start = INCIDENT - timedelta(hours=40)
    for i, amount in enumerate([45000, 47500, 44000, 46500]):
        ts = struct_start + timedelta(hours=i * 9)
        rows.append({
            "txn_id": f"TXN{700000 + i}",
            "from_account": ACCOUNTS["ramesh"],
            "to_account": ACCOUNTS[["suresh", "mohd", "deepak", "vikas"][i]],
            "amount": amount,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "ifsc": "HDFC0001234", "mode": "IMPS",
        })

    rows.sort(key=lambda r: r["timestamp"])
    with open(OUT / "BANK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def write_vehicle():
    rows = [
        {"registration_no": VEHICLES["ramesh"], "owner": PEOPLE["ramesh"]["name"],
         "make_model": "Maruti Swift", "colour": "White",
         "registered_on": "2021-03-14", "rto": "DL-08"},
        {"registration_no": VEHICLES["mohd"], "owner": PEOPLE["mohd"]["name"],
         "make_model": "Hyundai i20", "colour": "Silver",
         "registered_on": "2022-07-02", "rto": "HR-26"},
        {"registration_no": VEHICLES["vikas"], "owner": PEOPLE["vikas"]["name"],
         "make_model": "Honda City", "colour": "Grey",
         "registered_on": "2020-11-19", "rto": "UP-16"},
    ]
    with open(OUT / "VEHICLE.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Vehicles"
        ws.append(list(rows[0].keys()))
        for r in rows:
            ws.append(list(r.values()))
        wb.save(OUT / "VEHICLE.xlsx")
    except ImportError:
        pass
    return len(rows)


def write_criminal_history():
    rows = [
        {"person": PEOPLE["ramesh"]["name"], "case_ref": "FIR 0091/2024",
         "offense_type": "Cheating (IPC 420, pre-BNS)", "date": "2024-05-11",
         "police_station": "Cyber Cell, East District"},
        {"person": PEOPLE["ramesh"]["name"], "case_ref": "FIR 0233/2025",
         "offense_type": "Criminal conspiracy", "date": "2025-09-03",
         "police_station": "Cyber Cell, South District"},
        {"person": PEOPLE["mohd"]["name"], "case_ref": "FIR 0455/2025",
         "offense_type": "Stolen property", "date": "2025-01-27",
         "police_station": "Sector 29, Gurugram"},
        {"person": PEOPLE["deepak"]["name"], "case_ref": "FIR 0112/2025",
         "offense_type": "Cheating", "date": "2025-06-18",
         "police_station": "Cyber Cell, South District"},
    ]
    with open(OUT / "CRIMINAL_HISTORY.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    print("Generating TRINETRA synthetic dataset...")
    print("  (entirely fictional — no real people, numbers or cases)\n")
    write_firs()
    print(f"  CDR.csv               {write_cdr():>4} rows")
    print(f"  BANK.csv              {write_bank():>4} rows")
    print(f"  VEHICLE.csv/.xlsx     {write_vehicle():>4} rows")
    print(f"  CRIMINAL_HISTORY.csv  {write_criminal_history():>4} rows")
    print(f"\nWritten to: {OUT}")
    print("\nWhat the demo will find:")
    print("  • 'Ramesh Kumar' / 'Ramesh Kr.' / 'Kalia'  -> entity resolution")
    print("  • 4 transfers of ~Rs 45k in 36h            -> financial structuring")
    print("  • 7 calls in 40 min on incident night      -> communication burst")
    print("  • Ramesh + Deepak on TWR-DEL-114           -> co-location (cell precision)")
    print("  • Ramesh <-> Deepak, 3 mutual contacts     -> Adamic-Adar lead")
