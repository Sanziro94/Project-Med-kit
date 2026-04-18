from flask import Flask, jsonify, request, send_file, session, redirect, url_for
from flask_cors import CORS
import json, os, socket, threading, time, hashlib, secrets, re , urllib.request , urllib
from datetime import datetime , timedelta

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_PATH, "database.json")


app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(32))

DRAWER_CAPACITY = {#drawer size for each in cm^2
    1: 500,
    2: 500,
    3: 500
}

MED_PATH = os.path.join(BASE_PATH, "medicaments.json")
try:
   url = urllib.request.urlopen("https://raw.githubusercontent.com/Sanziro94/Project-Med-kit/main/medicaments.json")
   Medbase = json.loads(url.read().decode("UTF-8"))
   with open (MED_PATH, "w") as f:
       json.dump(Medbase,  f , indent=4)
   print("Medicaments was update succesfully")
except Exception as e:
    print(f"Couldn't update the medicaments database:{e}")
    if os.path.exists(MED_PATH):
        with open(MED_PATH, "r") as f:
            Medbase = json.load(f)
    else:
        Medbase = {}




hostname = socket.gethostname()
IPaddr   = socket.gethostbyname(hostname)


COOLDOWN_THRESHOLD = 3
COOLDOWN_WINDOW    = 10
COOLDOWN_SECONDS   = 30


ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "1234")
PW_SALT      = os.environ.get("PW_SALT", "medkit-salt")


file_lock = threading.Lock()
db_lock   = threading.Lock()


pending_rfid_data    = []
recent_registrations = []
on_cooldown          = False
BANNED_IPS           = set()


db: dict = {}


def _load_db_from_disk() -> dict:
    if not os.path.exists(DB_PATH) or os.stat(DB_PATH).st_size == 0:
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def _write_db_to_disk(snapshot: dict) -> None:
    """Atomic write: write to .tmp then rename (prevents corruption)."""
    tmp = DB_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(snapshot, f, indent=4)
    os.replace(tmp, DB_PATH)

with file_lock:
    db = _load_db_from_disk()
    if not db:
        _write_db_to_disk({})

def save_db() -> None:
    """Snapshot current db under lock, then write asynchronously."""
    with db_lock:
        snapshot = dict(db)
    threading.Thread(target=_write_db_to_disk, args=(snapshot,), daemon=True).start()

def hash_password(password: str) -> str:
    return hashlib.sha256((PW_SALT + password).encode()).hexdigest()

def check_password(stored: str, provided: str) -> bool:
    if len(stored) == 64:
        return secrets.compare_digest(stored, hash_password(provided))
    return secrets.compare_digest(stored, provided)

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,64}$")

def valid_username(u: str) -> bool:
    return bool(u and _USERNAME_RE.match(u))


def get_client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr)

def _check_admin_secret(data: dict) -> bool:
    return secrets.compare_digest(str(data.get("secret", "")), ADMIN_SECRET)

def ddos_loop() -> None:
    global on_cooldown
    while True:
        now = time.time()
        with db_lock:
            recent_registrations[:] = [t for t in recent_registrations
                                        if now - t < COOLDOWN_WINDOW]
            count = len(recent_registrations)
        if count >= COOLDOWN_THRESHOLD:
            on_cooldown = True
            print(f"[DDoS] Cooldown active for {COOLDOWN_SECONDS}s")
            time.sleep(COOLDOWN_SECONDS)
            with db_lock:
                recent_registrations.clear()
            on_cooldown = False
        time.sleep(0.5)

@app.before_request
def block_banned_ips():
    if get_client_ip() in BANNED_IPS:
        return jsonify({"error": "Your IP is banned"}), 403

@app.route("/ban-ip", methods=["POST"])
def ban_ip():
    data = request.get_json() or {}
    if not _check_admin_secret(data):
        return jsonify({"error": "forbidden"}), 403
    ip = data.get("ip", "").strip()
    if not ip:
        return jsonify({"error": "missing ip"}), 400
    BANNED_IPS.add(ip)
    return jsonify({"status": "ip_banned", "ip": ip}), 200

@app.route("/unban-ip", methods=["POST"])
def unban_ip():
    # BUG FIX: was missing auth — anyone could unban IPs
    data = request.get_json() or {}
    if not _check_admin_secret(data):
        return jsonify({"error": "forbidden"}), 403
    ip = data.get("ip", "").strip()
    if not ip:
        return jsonify({"error": "missing ip"}), 400
    if ip in BANNED_IPS:
        BANNED_IPS.discard(ip)
        return jsonify({"status": "ip_unbanned", "ip": ip}), 200
    return jsonify({"error": "ip_not_banned"}), 404

@app.route("/banned-ips", methods=["GET"])
def list_banned_ips():
    # BUG FIX: was open to anyone; now requires admin secret via query param
    secret = request.args.get("secret", "")
    if not secrets.compare_digest(secret, ADMIN_SECRET):
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"banned_ips": list(BANNED_IPS)}), 200


@app.route("/pending-rfid", methods=["POST"])
def pending_rfid():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    with db_lock:
        if not username or username not in db:
            return jsonify({"status": "error", "message": "User introuvable"}), 404
        if username not in pending_rfid_data:
            pending_rfid_data.append(username)
    return jsonify({"status": "ok", "pending": list(pending_rfid_data)}), 200

@app.route("/pending-rfid", methods=["GET"])
def get_pending_rfid():
    return jsonify({"pending": list(pending_rfid_data)}), 200

@app.route("/pending-rfid/done", methods=["POST"])
def remove_pending_rfid():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    if username in pending_rfid_data:
        pending_rfid_data.remove(username)
    return jsonify({"status": "ok", "pending": list(pending_rfid_data)}), 200


@app.route("/accespy", methods=["POST"])
def accespy():
    data = request.get_json() or {}
    uid  = str(data.get("uid", "")).strip()
    if not uid:
        return jsonify({"status": "error", "message": "missing uid"}), 400

    with db_lock:
        for username, info in db.items():
            if str(info.get("uid", "")) == uid:
                session["logged_in"] = True
                session["username"]  = username
                print(f"[RFID] Access granted: {username}")
                return jsonify({"status": "granted",
                                "redirect": info.get("given_page", "/article")}), 200

    print(f"[RFID] Access denied uid={uid}")
    return jsonify({"status": "denied"}), 403


@app.route("/my-traitement", methods=["GET"])
def my_traitement():
    if not session.get("logged_in"):
        return jsonify({"error": "not logged in"}), 401
    username = session.get("username", "")

    with db_lock:
        if not username or username not in db:
            return jsonify({"error": "user not found"}), 404
        traitement = list(db[username].get("traitement", []))
        for t in traitement:
            t["perime"] = expirancy(t.get("add_time"), t.get("object"))
    return jsonify({"traitement": traitement}), 200
    
            
   

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/article")
def get_article():
    if session.get("logged_in"):
        return send_file("article.html")
    return redirect(url_for("home"))

@app.route("/manager")
def get_manager():
    if session.get("logged_in"):
        return send_file("manager.html")
    return redirect(url_for("home"))

@app.route("/register-page")
def get_register():
    return send_file("register.html")

@app.route("/reset-page")
def get_reset():
    return send_file("reset.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/login", methods=["POST"])
def verification():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "missing fields"}), 400

    with db_lock:
        if username not in db:
            return jsonify({"status": "user_not_found",
                            "message": "User doesn't exist, want to create an account?"}), 404
        stored = db[username]["password"]
        if not check_password(stored, password):
            return jsonify({"error": "wrong password"}), 401
        if len(stored) != 64:          # upgrade legacy plain-text password
            db[username]["password"] = hash_password(password)
            save_db()

    return _pers_area(username)


@app.route("/register", methods=["POST"])
def create_account():
    if on_cooldown:
        return jsonify({"status": "rate_limited",
                        "message": "Too many registrations — try again shortly"}), 429

    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    user     = data.get("user", "").strip()
    admin    = data.get("admin", "")
    passk    = data.get("passk", "").strip()

    if not username or not password or not user or not passk:
        return jsonify({"error": "missing fields"}), 400
    if not valid_username(username):
        return jsonify({"error": "invalid username (3-64 chars, letters/digits/._-)"}), 400

    try:
        redirect_page = "/manager" if secrets.compare_digest(str(int(admin)), ADMIN_SECRET) else "/article"
    except (TypeError, ValueError):
        redirect_page = "/article"

    with db_lock:
        if username in db:
            return jsonify({"error": "user already exists"}), 409
        db[username] = {
            "password":   hash_password(password),
            "user":       user,
            "passk":      hash_password(passk),   # BUG FIX: hash passkey at rest
            "given_page": redirect_page,
            "traitement": []
        }

    save_db()
    with db_lock:
        recent_registrations.append(time.time())
    return jsonify({"status": "account_created", "redirect": redirect_page}), 201


@app.route("/reset-password", methods=["POST"])
def reset_passw():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    passk    = data.get("passk", "").strip()
    new_pass = data.get("password", "")

    if not username or not passk or not new_pass:
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    with db_lock:
        if username not in db:
            return jsonify({"status": "error", "message": "User not found"}), 404

        stored_passk = db[username].get("passk", "")
        passk_ok = (
            secrets.compare_digest(stored_passk, hash_password(passk))
            or secrets.compare_digest(stored_passk, passk)   # legacy plain-text
        )
        if not passk_ok:
            return jsonify({"status": "error", "message": "Invalid passkey"}), 401

        db[username]["password"] = hash_password(new_pass)

    save_db()
    return jsonify({"status": "success", "message": "Password updated"}), 200


def remaining_space(tiroirs) -> int:
    used = 0
    with db_lock:
        for info in db.values():
            for med in info.get("traitement", []):
                if int(med.get("tiroirs", -1)) == int(tiroirs):
                    med_name = med.get("object")
                    used += Medbase.get(med_name, {}).get("size", 0)
    return DRAWER_CAPACITY.get(tiroirs, 0) - used
    print(f"[DEBUG] tiroirs={tiroirs} type={type(tiroirs)} used={used} capacity={DRAWER_CAPACITY.get(int(tiroirs), 0)}")

    

@app.route("/Application", methods=["POST"])
def saveinfo():
    data     = request.get_json() or {}
    user_val = data.get("user", "").strip()
    time_val = data.get("time", "").strip()
    med_name = data.get("Object", "").strip()
    tiroirs  = data.get("Tiroirs")
    
    print(f"[DEBUG] user={user_val} time={time_val} med={med_name} tiroirs={tiroirs}")
    if not user_val or not time_val or not med_name:
        return jsonify({"status": "error", "message": "Champs manquants"}), 400
        

    med_size = Medbase.get(med_name, {}).get("size", 0)
    space = remaining_space(tiroirs)
    print(f"[DEBUG] space={space} med_size={med_size}")


    if int(space) < int(med_size):
        return jsonify({"status": "error", "message": "There is no space left"}), 409
    else:
        pass

    with db_lock:
        target_key = next((k for k, v in db.items() if v.get("user") == user_val), None)
        if target_key is None:
            return jsonify({"status": "error",
                            "message": "Aucun patient trouvé: " + user_val}), 404
        
        current_date = datetime.now().strftime("%Y-%m-%d")

        db[target_key]["traitement"].append({
            "time":    time_val,
            "object":  med_name,
            "tiroirs": tiroirs,
            "add_time": current_date
        })

    save_db()
    return jsonify({"status": "success",
                    "message": "Traitement enregistré pour " + user_val}), 200

def expirancy(added_at_str, med_name):
    if med_name not in Medbase:
        return False
    
    max_days = Medbase[med_name].get("days", 0)
    
    added_date = datetime.strptime(added_at_str, "%Y-%m-%d")
    
    expiration_date = added_date + timedelta(days=max_days)
    
    return datetime.now() > expiration_date
 
 
@app.route("/delapp", methods=["POST"])
def delete_info():
    data = request.get_json() or {}
    user_val = data.get("user", "").strip()
    time_val = data.get("time", "").strip()
    med_name = data.get("Object", "").strip()

    if not user_val or not time_val or not med_name:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    with db_lock:
        target_key = next((k for k, v in db.items() if v.get("user") == user_val), None)
        
        if target_key is None:
            return jsonify({"status": "error", "message": "User not found"}), 404

        old_traitement = db[target_key].get("traitement", [])
    
        new_traitement = [
            item for item in old_traitement 
            if not (item.get("object") == med_name and item.get("time") == time_val)
        ]

        if len(old_traitement) == len(new_traitement):
            return jsonify({"status": "error", "message": "Item not found in list"}), 404

        db[target_key]["traitement"] = new_traitement
    
    save_db()
    return jsonify({"status": "success", "message": "Item deleted successfully"}), 200


@app.route("/Medication", methods=["GET"])
def get_med_list():
 try:
    return jsonify(Medbase), 200 
 except Exception as e:
    return jsonify({"status":"error", "message":"Problem with medbase existance or check parsing"}),404

def _pers_area(username: str):
    session["logged_in"] = True
    session["username"]  = username
    with db_lock:
        redirect_page = db[username]["given_page"]
    return jsonify({"status": "success", "redirect": redirect_page})

if __name__ == "__main__":
    threading.Thread(target=ddos_loop, daemon=True).start()
    app.run(debug=False, port=50000, host="0.0.0.0")
