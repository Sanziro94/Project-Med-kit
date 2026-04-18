import os
import time
import json
import socket
import requests
from mfrc522 import SimpleMFRC522

reader   = SimpleMFRC522()
hostname = socket.gethostname()
IPaddr   = socket.gethostbyname(hostname)
BASE_URL = f"http://{IPaddr}:50000"

DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")


ADMIN_UID = os.environ.get("ADMIN_UID", "")


IDLE_POLL_INTERVAL = 0.3


def load_db() -> dict:
    if not os.path.exists(DB_PATH) or os.stat(DB_PATH).st_size == 0:
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def save_db(db: dict) -> None:
    tmp = DB_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f, indent=4)
    os.replace(tmp, DB_PATH)   # atomic


def _post(path: str, payload: dict, timeout: int = 3):
    """POST to the Flask server; returns response or None on error."""
    try:
        return requests.post(f"{BASE_URL}{path}", json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        print(f"[RFID] HTTP error ({path}): {e}")
        return None

def _get(path: str, timeout: int = 3):
    try:
        return requests.get(f"{BASE_URL}{path}", timeout=timeout)
    except requests.exceptions.RequestException as e:
        print(f"[RFID] HTTP error ({path}): {e}")
        return None

def check_pending() -> list:
    """Return list of usernames waiting for card assignment."""
    r = _get("/pending-rfid")
    if r and r.status_code == 200:
        return r.json().get("pending", [])
    return []

def mark_done(username: str) -> None:
    """Tell the server that card assignment for this user is complete."""
    _post("/pending-rfid/done", {"username": username})


def assign_pending(username: str) -> None:
    """Scan a new card and bind its UID to a freshly registered user."""
    print(f"\n[RFID] New patient: {username}")
    print(f"[RFID] Please scan the card for {username}...")

    card_id, _ = reader.read()
    uid = str(card_id)
    time.sleep(0.5)

    db = load_db()

    if username not in db:
        print(f"[RFID] Username '{username}' not found in local DB — skipping")
        return

    for key, data in db.items():
        if data.get("uid") == uid:
            print(f"[RFID] Card already assigned to: {key}")
            time.sleep(2)
            return

    db[username]["uid"] = uid
    save_db(db)
    mark_done(username)
    print(f"[RFID] Card (uid={uid}) assigned to '{username}'")
    time.sleep(1)


def authenticate(uid: str) -> None:
    """
    Send the already-scanned UID to the server for validation.
    BUG FIX: original called reader.read() again inside this function,
             blocking until the next swipe instead of using the card just read.
    """
    r = _post("/accespy", {"uid": uid})
    if r is None:
        print("[RFID] Cannot reach server — is Flask running?")
        return
    if r.status_code == 200:
        data = r.json()
        print(f"[RFID] Access GRANTED → {data.get('redirect')}")
    elif r.status_code == 403:
        print("[RFID] Access DENIED — card not recognised")
    else:
        print(f"[RFID] Unexpected response: {r.status_code}")


if __name__ == "__main__":
    print("=" * 42)
    print("  MedKit RFID system ready")
    print(f"  Server : {BASE_URL}")
    if not ADMIN_UID:
        print("  WARNING: ADMIN_UID not set")
        print("  Run identify-card.py to find your admin card UID")
    print("  Scan a card to begin...")
    print("=" * 42)

    while True:
        # Priority: assign card to any waiting new patient first
        pending = check_pending()
        if pending:
            print(f"[RFID] {len(pending)} patient(s) waiting for card assignment")
            assign_pending(pending[0])
            print("Scan a card to continue...")
            continue

        # Normal scan — read ONCE, then decide what to do
        card_id, _ = reader.read()
        uid = str(card_id)
        time.sleep(IDLE_POLL_INTERVAL)

        if ADMIN_UID and uid == ADMIN_UID:
            print("[RFID] Admin card detected")
            # Extend here for admin actions
        else:
            authenticate(uid)

        print("Scan a card to continue...")
