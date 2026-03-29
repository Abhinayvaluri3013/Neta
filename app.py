# =====================================================
#  NETA — Face Recognition using OpenCV (no dlib!)
#  HOW TO RUN:
#    1. py -3.11 -m pip install flask opencv-python numpy
#    2. py -3.11 app.py
#    3. Open: http://localhost:5000
# =====================================================

from flask import Flask, render_template, request, jsonify, session
import sqlite3, hashlib, uuid, os, base64, numpy as np
import cv2
from datetime import datetime

app = Flask(__name__)
app.secret_key = "neta_expo_secret_2024"

DB_PATH   = "neta.db"
FACES_DIR = os.path.join("static", "faces")
os.makedirs(FACES_DIR, exist_ok=True)

# Load OpenCV face detector
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
# Load OpenCV face recognizer
FACE_RECOGNIZER = cv2.face.LBPHFaceRecognizer_create()
RECOGNIZER_TRAINED = False

# ─────────────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _fp_hash(aadhaar):
    return hashlib.sha256(f"FINGER_{aadhaar}".encode()).hexdigest()

def log_event(event, aadhaar=None, ip=None):
    hint = f"****{aadhaar[-4:]}" if aadhaar and len(aadhaar) >= 4 else "—"
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (event, aadhaar_hint, ip, timestamp) VALUES (?,?,?,?)",
        (event, hint, ip or "127.0.0.1", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            aadhaar          TEXT PRIMARY KEY,
            name             TEXT NOT NULL,
            fingerprint_hash TEXT NOT NULL,
            constituency     TEXT NOT NULL,
            face_registered  INTEGER DEFAULT 0,
            has_voted        INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            vote_id   TEXT PRIMARY KEY,
            candidate TEXT NOT NULL,
            receipt   TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            event        TEXT NOT NULL,
            aadhaar_hint TEXT,
            ip           TEXT,
            timestamp    TEXT NOT NULL
        )
    """)

    try:
        cur.execute("ALTER TABLE voters ADD COLUMN face_registered INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass

    count = cur.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
    if count == 0:
        demo_voters = [
            ("123456789012", "Arjun Sharma",  _fp_hash("123456789012"), "New Delhi Central"),
            ("234567890123", "Priya Mehta",   _fp_hash("234567890123"), "New Delhi Central"),
            ("345678901234", "Abhinay valuri",    _fp_hash("345678901234"), "New Delhi Central"),
            ("456789012345", "Anita Reddy",   _fp_hash("456789012345"), "New Delhi Central"),
            ("953888081020", "Karthik Tejavath", _fp_hash("953888081020"), "Khammam central"),
        ]
        cur.executemany(
            "INSERT INTO voters (aadhaar, name, fingerprint_hash, constituency) VALUES (?,?,?,?)",
            demo_voters
        )
        print("✅  Demo voters inserted.")

    conn.commit()
    conn.close()
    print("✅  Database ready →", DB_PATH)

# ─────────────────────────────────────────────────────
#  FACE HELPERS (OpenCV — no dlib!)
# ─────────────────────────────────────────────────────

def face_path(aadhaar):
    return os.path.join(FACES_DIR, f"{aadhaar}.jpg")

def decode_base64_image(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

def detect_face(img):
    """Detect face and return grayscale face crop. Returns None if no face."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80,80))
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    face_crop = gray[y:y+h, x:x+w]
    face_crop = cv2.resize(face_crop, (200, 200))
    return face_crop

def compare_faces(known_path, live_img):
    """Compare registered face with live webcam image. Returns (match, confidence)."""
    known_img  = cv2.imread(known_path)
    known_face = detect_face(known_img)
    live_face  = detect_face(live_img)

    if known_face is None:
        return False, 0, "Registered face corrupted. Please re-register."
    if live_face is None:
        return False, 0, "No face detected. Look directly at the camera."

    # Train recognizer on known face
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train([known_face], np.array([0]))

    # Predict on live face
    label, distance = recognizer.predict(live_face)

    # Distance: lower = more similar. <60 = good match, >100 = no match
    confidence = max(0, round((1 - distance / 100) * 100, 1))
    match = distance < 60

    return match, confidence, None

# ─────────────────────────────────────────────────────
#  PAGE ROUTES
# ─────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/vote")
def vote_page():
    return render_template("vote.html")

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

# ─────────────────────────────────────────────────────
#  API — Register Face
# ─────────────────────────────────────────────────────

@app.route("/api/register-face", methods=["POST"])
def register_face():
    data    = request.get_json() or {}
    aadhaar = data.get("aadhaar", "").strip()
    image   = data.get("image", "")

    if len(aadhaar) != 12 or not aadhaar.isdigit():
        return jsonify({"success": False, "message": "Invalid Aadhaar number."}), 400

    conn  = get_db()
    voter = conn.execute("SELECT * FROM voters WHERE aadhaar=?", (aadhaar,)).fetchone()
    conn.close()

    if not voter:
        return jsonify({"success": False, "message": "Aadhaar not found in voter roll."}), 404

    try:
        img  = decode_base64_image(image)
        face = detect_face(img)

        if face is None:
            return jsonify({"success": False, "message": "No face detected. Look directly at camera."}), 400

        # Save original image
        cv2.imwrite(face_path(aadhaar), img)

        conn = get_db()
        conn.execute("UPDATE voters SET face_registered=1 WHERE aadhaar=?", (aadhaar,))
        conn.commit()
        conn.close()

        log_event("FACE_REGISTERED", aadhaar, request.remote_addr)
        return jsonify({
            "success": True,
            "name":    voter["name"],
            "message": f"Face registered for {voter['name']}!"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# ─────────────────────────────────────────────────────
#  API — Step 1: Verify Aadhaar
# ─────────────────────────────────────────────────────

@app.route("/api/verify-aadhaar", methods=["POST"])
def verify_aadhaar():
    data    = request.get_json() or {}
    aadhaar = data.get("aadhaar", "").replace(" ", "").strip()

    if len(aadhaar) != 12 or not aadhaar.isdigit():
        return jsonify({"success": False, "message": "Invalid Aadhaar — must be 12 digits."}), 400

    conn  = get_db()
    voter = conn.execute("SELECT * FROM voters WHERE aadhaar=?", (aadhaar,)).fetchone()
    conn.close()

    log_event("AADHAAR_LOOKUP", aadhaar, request.remote_addr)

    if not voter:
        return jsonify({"success": False, "message": "Aadhaar not found in voter roll."}), 404
    if voter["has_voted"]:
        return jsonify({"success": False, "message": "This voter has already voted."}), 403
    if not voter["face_registered"]:
        return jsonify({"success": False, "message": "Face not registered. Go to /register first."}), 403

    session["pending_aadhaar"] = aadhaar
    return jsonify({
        "success":      True,
        "name":         voter["name"],
        "constituency": voter["constituency"],
        "message":      "Aadhaar verified. Proceed to fingerprint."
    })

# ─────────────────────────────────────────────────────
#  API — Step 2: Verify Fingerprint
# ─────────────────────────────────────────────────────

@app.route("/api/verify-fingerprint", methods=["POST"])
def verify_fingerprint():
    aadhaar = session.get("pending_aadhaar")
    if not aadhaar:
        return jsonify({"success": False, "message": "Session expired."}), 401

    conn  = get_db()
    voter = conn.execute(
        "SELECT fingerprint_hash, has_voted FROM voters WHERE aadhaar=?", (aadhaar,)
    ).fetchone()
    conn.close()

    log_event("FINGERPRINT_SCAN", aadhaar, request.remote_addr)

    if not voter or voter["has_voted"]:
        return jsonify({"success": False, "message": "Voter not found or already voted."}), 403
    if voter["fingerprint_hash"] != _fp_hash(aadhaar):
        return jsonify({"success": False, "message": "Fingerprint mismatch."}), 403

    session["fp_verified_aadhaar"] = aadhaar
    session.pop("pending_aadhaar", None)
    return jsonify({"success": True, "message": "Fingerprint confirmed. Proceed to face scan."})

# ─────────────────────────────────────────────────────
#  API — Step 3: Verify Face (OpenCV)
# ─────────────────────────────────────────────────────

@app.route("/api/verify-face", methods=["POST"])
def verify_face():
    aadhaar = session.get("fp_verified_aadhaar")
    if not aadhaar:
        return jsonify({"success": False, "message": "Session expired."}), 401

    data  = request.get_json() or {}
    image = data.get("image", "")
    if not image:
        return jsonify({"success": False, "message": "No image received."}), 400

    saved = face_path(aadhaar)
    if not os.path.exists(saved):
        return jsonify({"success": False, "message": "No registered face found."}), 404

    try:
        live_img = decode_base64_image(image)
        match, confidence, error_msg = compare_faces(saved, live_img)

        if error_msg:
            return jsonify({"success": False, "message": error_msg}), 400

        if match:
            session["authenticated_aadhaar"] = aadhaar
            session.pop("fp_verified_aadhaar", None)
            log_event("FACE_MATCH_OK", aadhaar, request.remote_addr)
            return jsonify({
                "success":    True,
                "confidence": confidence,
                "message":    f"Face verified! ({confidence}% match)"
            })
        else:
            log_event("FACE_MISMATCH", aadhaar, request.remote_addr)
            return jsonify({
                "success":    False,
                "confidence": confidence,
                "message":    f"Face does not match ({confidence}%). Access denied."
            }), 403

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

# ─────────────────────────────────────────────────────
#  API — Step 4: Cast Vote
# ─────────────────────────────────────────────────────

@app.route("/api/cast-vote", methods=["POST"])
def cast_vote():
    aadhaar = session.get("authenticated_aadhaar")
    if not aadhaar:
        return jsonify({"success": False, "message": "Not authenticated."}), 401

    data      = request.get_json() or {}
    candidate = data.get("candidate", "").strip()
    if not candidate:
        return jsonify({"success": False, "message": "No candidate selected."}), 400

    conn  = get_db()
    voter = conn.execute("SELECT has_voted FROM voters WHERE aadhaar=?", (aadhaar,)).fetchone()
    if not voter or voter["has_voted"]:
        conn.close()
        return jsonify({"success": False, "message": "Already voted."}), 403

    vote_id   = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    receipt   = hashlib.sha256(f"{vote_id}{candidate}{timestamp}".encode()).hexdigest()

    conn.execute(
        "INSERT INTO votes (vote_id, candidate, receipt, timestamp) VALUES (?,?,?,?)",
        (vote_id, candidate, receipt, timestamp)
    )
    conn.execute("UPDATE voters SET has_voted=1 WHERE aadhaar=?", (aadhaar,))
    conn.commit()
    conn.close()

    log_event("VOTE_CAST", aadhaar, request.remote_addr)
    session.clear()

    return jsonify({
        "success": True,
        "receipt": receipt[:16].upper(),
        "message": "Vote recorded! Thank you!"
    })

# ─────────────────────────────────────────────────────
#  API — Results & Admin
# ─────────────────────────────────────────────────────

@app.route("/api/results")
def results():
    conn  = get_db()
    rows  = conn.execute(
        "SELECT candidate, COUNT(*) as count FROM votes GROUP BY candidate ORDER BY count DESC"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as total FROM votes").fetchone()["total"]
    conn.close()
    return jsonify({
        "total_votes": total,
        "results": [{"candidate": r["candidate"], "votes": r["count"]} for r in rows]
    })

@app.route("/api/admin/stats")
def admin_stats():
    conn          = get_db()
    total_voters  = conn.execute("SELECT COUNT(*) as c FROM voters").fetchone()["c"]
    voted         = conn.execute("SELECT COUNT(*) as c FROM voters WHERE has_voted=1").fetchone()["c"]
    total_votes   = conn.execute("SELECT COUNT(*) as c FROM votes").fetchone()["c"]
    audit_entries = conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]
    recent_log    = conn.execute(
        "SELECT event, aadhaar_hint, ip, timestamp FROM audit_log ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return jsonify({
        "total_voters":  total_voters,
        "voted":         voted,
        "remaining":     total_voters - voted,
        "turnout_pct":   round(voted / total_voters * 100, 1) if total_voters else 0,
        "total_votes":   total_votes,
        "audit_entries": audit_entries,
        "recent_log":    [dict(r) for r in recent_log]
    })

# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n🗳️  NETA Biometric Voting System")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("   Home     → http://localhost:5000/")
    print("   Register → http://localhost:5000/register  ← do this FIRST")
    print("   Vote     → http://localhost:5000/vote")
    print("   Admin    → http://localhost:5000/admin")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    port = int(os.environ.get("PORT", 5000))
app.run(debug=True, host="0.0.0.0", port=port)