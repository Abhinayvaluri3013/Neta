# 🗳️ NETA — National Electronic Transparent Authentication
### Biometric Voting System Prototype

---

## 📁 Project Structure

```
NETA/
├── app.py                  ← Flask backend (run this!)
├── requirements.txt        ← Python dependencies
├── neta.db                 ← SQLite database (auto-created on first run)
│
├── templates/              ← Flask HTML templates
│   ├── index.html          ← Home / Landing page
│   ├── vote.html           ← Voting interface (Step 1→4)
│   └── admin.html          ← Live results & audit dashboard
│
├── static/
│   ├── css/
│   │   └── style.css       ← All styles
│   └── js/
│       └── main.js         ← Clock, animations, scroll
```

---

## 🚀 How to Run in VS Code

### Step 1 — Install Python dependencies
Open the VS Code terminal and run:
```bash
pip install -r requirements.txt
```

### Step 2 — Start the Flask server
```bash
python app.py
```

### Step 3 — Open in browser
```
http://localhost:5000         ← Home page
http://localhost:5000/vote    ← Voting portal
http://localhost:5000/admin   ← Admin / results dashboard
```

---

## 🧪 Demo Voters (for Expo testing)

| Aadhaar         | Name           | Constituency       |
|-----------------|----------------|--------------------|
| 123456789012    | Arjun Sharma   | New Delhi - 01     |
| 234567890123    | Priya Mehta    | Mumbai North       |
| 345678901234    | Ravi Kumar     | Hyderabad - 03     |
| 456789012345    | Anita Reddy    | Bengaluru South    |
| 567890123456    | Suresh Pillai  | Chennai Central    |

> Fingerprint scan is simulated — just tap the fingerprint button on the vote page.

---

## 🔐 Security Features (Expo Talking Points)

- **Biometric hash** — fingerprints are stored as SHA-256 hashes, never raw
- **Ballot anonymisation** — vote and identity stored in separate tables with no link
- **One-vote enforcement** — voter is flagged after voting; repeat attempts are blocked
- **Cryptographic receipt** — each vote gets a unique SHA-256 receipt
- **Audit log** — every action logged with masked Aadhaar (only last 4 digits shown)
- **Session invalidation** — session cleared immediately after vote is cast

---

## 🔄 Reset for Next Demo

To clear all votes and reset the database:
```bash
del neta.db        # Windows
rm neta.db         # Mac / Linux
python app.py      # Re-run to recreate
```

---

## 📌 API Endpoints

| Method | Endpoint                | Description                  |
|--------|-------------------------|------------------------------|
| POST   | /api/verify-aadhaar     | Step 1 — validate Aadhaar    |
| POST   | /api/verify-fingerprint | Step 2 — confirm biometric   |
| POST   | /api/cast-vote          | Step 3 — record vote         |
| GET    | /api/results            | Public vote tally            |
| GET    | /api/admin/stats        | Admin stats + audit log      |

---

*Built as a prototype for expo demonstration. Inspired by the Rajya Sabha discussion by MP Raghav Chadha on biometric voting in India.*