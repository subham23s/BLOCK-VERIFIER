from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from blockchain import Blockchain
from hash_utils import generate_bytes_hash, detect_file_type
from pinata_utils import (
    save_blockchain_to_pinata,
    load_blockchain_from_pinata,
    test_pinata_connection,
    get_latest_cid
)
import os, base64, mimetypes, json, hashlib, time, io

# Load Pinata keys into pinata_utils
import pinata_utils as pu
pu.PINATA_API_KEY    = os.environ.get("PINATA_API_KEY", "")
pu.PINATA_SECRET_KEY = os.environ.get("PINATA_SECRET_KEY", "")

app = Flask(__name__)
app.secret_key = os.urandom(24)

USERS_FILE     = "users.json"
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# ── User helpers ───────────────────────────────────────────────────────────
def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE): return {}
    with open(USERS_FILE) as f: return json.load(f)

def save_users(u):
    with open(USERS_FILE, "w") as f: json.dump(u, f, indent=2)

def create_user(username, password):
    users = load_users()
    if username in users: return False, "Username already exists."
    users[username] = {"password": hp(password), "created_at": time.time(),
                       "login_count": 0, "files": []}
    save_users(users)
    return True, "ok"

def verify_user(username, password):
    u = load_users().get(username)
    return u and u["password"] == hp(password)

def bump_login(username):
    users = load_users()
    if username in users:
        users[username]["login_count"] = users[username].get("login_count", 0) + 1
        users[username]["last_login"] = time.time()
        save_users(users)
    return users.get(username, {}).get("login_count", 1)

def _normalize_files(files):
    """Convert old format (list of strings) to new format (list of dicts)."""
    result = []
    for f in files:
        if isinstance(f, str):
            result.append({"hash": f, "name": "unknown", "type": "file", "added": 0})
        elif isinstance(f, dict):
            result.append(f)
    return result

def add_file_to_user(username, file_hash, file_name, file_type):
    users = load_users()
    if username not in users: return
    users[username]["files"] = _normalize_files(users[username].get("files", []))
    entry = {"hash": file_hash, "name": file_name, "type": file_type, "added": time.time()}
    if not any(f["hash"] == file_hash for f in users[username]["files"]):
        users[username]["files"].append(entry)
    save_users(users)

def remove_file_from_user(username, file_hash):
    users = load_users()
    if username not in users: return
    users[username]["files"] = _normalize_files(users[username].get("files", []))
    users[username]["files"] = [f for f in users[username]["files"] if f["hash"] != file_hash]
    save_users(users)

def get_user_file_hashes(username):
    u = load_users().get(username)
    if not u: return []
    return [f["hash"] if isinstance(f, dict) else f for f in u.get("files", [])]

# ── Blockchain helpers ─────────────────────────────────────────────────────
def get_blockchain():
    try:
        d = load_blockchain_from_pinata()
        if d: return Blockchain.from_list(d)
    except: pass
    return Blockchain(difficulty=4)

def save_bc(bc): return save_blockchain_to_pinata(bc.to_list())

# ── Persistent file store ─────────────────────────────────────────────────
import pathlib
file_previews = {}   # hash -> data_url (images only, in-memory is fine)
UPLOAD_DIR = pathlib.Path("uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)

def save_file_bytes(file_hash, filename, raw_bytes):
    """Save file to disk using hash as folder."""
    folder = UPLOAD_DIR / file_hash
    folder.mkdir(exist_ok=True)
    filepath = folder / filename
    filepath.write_bytes(raw_bytes)
    return filepath

def get_file_bytes(file_hash, filename=None):
    """Retrieve file from disk."""
    folder = UPLOAD_DIR / file_hash
    if not folder.exists():
        return None, None
    if filename:
        fp = folder / filename
        if fp.exists():
            return fp.read_bytes(), filename
    # Find any file in folder
    files = list(folder.iterdir())
    if files:
        return files[0].read_bytes(), files[0].name
    return None, None


# ══════════════════════════════════════════════════════════════════════════
# ROUTES — MAIN APP
# ══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    u = data.get("username","").strip()
    p = data.get("password","").strip()
    if not u or not p: return jsonify({"success":False,"message":"Fields required."})
    if len(u) < 3: return jsonify({"success":False,"message":"Username too short (min 3)."})
    ok, msg = create_user(u, p)
    if ok: session["user"] = u
    return jsonify({"success":ok,"message":msg})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    u = data.get("username","").strip()
    p = data.get("password","").strip()
    # Check if admin credentials
    if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success":True,"is_admin":True})
    if verify_user(u, p):
        session["user"] = u
        count = bump_login(u)
        return jsonify({"success":True,"is_admin":False,"login_count":count})
    return jsonify({"success":False})

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({"success":True})

@app.route("/auth_status")
def auth_status():
    u = session.get("user")
    if not u:
        return jsonify({"logged_in": False, "username": ""})
    users = load_users()
    display = users.get(u, {}).get("display_name", u) if u and u.startswith("wallet:") else u
    return jsonify({"logged_in": True, "username": display})


@app.route("/wallet/challenge", methods=["POST"])
def wallet_challenge():
    """Generate a random challenge for the wallet to sign."""
    import secrets
    data = request.get_json()
    address = data.get("address", "").strip().lower()
    if not address or not address.startswith("0x") or len(address) != 42:
        return jsonify({"success": False, "message": "Invalid wallet address."})
    challenge = f"BlockVerify Login Request\nAddress: {address}\nNonce: {secrets.token_hex(16)}\nTimestamp: {int(time.time())}"
    session["wallet_challenge"] = challenge
    session["wallet_address"] = address
    return jsonify({"success": True, "challenge": challenge})

@app.route("/wallet/verify", methods=["POST"])
def wallet_verify():
    """Verify the signed challenge and log the user in or prompt for username."""
    from eth_account import Account
    from eth_account.messages import encode_defunct
    data = request.get_json()
    signature = data.get("signature", "").strip()
    address = data.get("address", "").strip().lower()
    challenge = session.get("wallet_challenge")
    stored_address = session.get("wallet_address", "").lower()
    if not challenge or not signature:
        return jsonify({"success": False, "message": "No challenge found. Try again."})
    if address != stored_address:
        return jsonify({"success": False, "message": "Address mismatch."})
    try:
        msg = encode_defunct(text=challenge)
        recovered = Account.recover_message(msg, signature=signature).lower()
        if recovered != address:
            return jsonify({"success": False, "message": "Signature verification failed."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Verification error: {e}"})
    # Check if wallet already has an account
    users = load_users()
    wallet_key = f"wallet:{address}"
    if wallet_key in users:
        username = users[wallet_key].get("display_name", address[:10])
        session["user"] = wallet_key
        count = bump_login(wallet_key)
        session.pop("wallet_challenge", None)
        return jsonify({"success": True, "exists": True, "username": username, "login_count": count})
    # New wallet user — needs username
    session.pop("wallet_challenge", None)
    return jsonify({"success": True, "exists": False, "address": address})

@app.route("/wallet/register", methods=["POST"])
def wallet_register():
    """Register a new wallet user with a chosen display name."""
    data = request.get_json()
    address = data.get("address", "").strip().lower()
    display_name = data.get("display_name", "").strip()
    if not address or not display_name:
        return jsonify({"success": False, "message": "Address and display name required."})
    if len(display_name) < 2:
        return jsonify({"success": False, "message": "Display name too short."})
    users = load_users()
    # Check display name not taken
    for u in users.values():
        if u.get("display_name", "").lower() == display_name.lower():
            return jsonify({"success": False, "message": "Display name already taken."})
    wallet_key = f"wallet:{address}"
    users[wallet_key] = {
        "password": None,
        "wallet_address": address,
        "display_name": display_name,
        "auth_type": "wallet",
        "created_at": time.time(),
        "login_count": 1,
        "last_login": time.time(),
        "files": []
    }
    save_users(users)
    session["user"] = wallet_key
    return jsonify({"success": True, "username": display_name})

@app.route("/my_files")
def my_files():
    u = session.get("user")
    if not u: return jsonify({"error":"Unauthorized"}), 401
    try:
        bc = get_blockchain()
        hashes = set(get_user_file_hashes(u))

        # Build a lookup from blockchain blocks
        block_lookup = {}
        for block in bc.chain[1:]:
            block_lookup[block.file_hash] = block

        # Also get file metadata from users.json directly as fallback
        users = load_users()
        user_files = _normalize_files(users.get(u, {}).get("files", []))

        result = []
        seen = set()
        for fentry in user_files:
            fhash = fentry["hash"]
            if fhash in seen:
                continue
            seen.add(fhash)
            block = block_lookup.get(fhash)
            result.append({
                "index":   block.index     if block else "?",
                "file_name": block.file_name if block else fentry.get("name","unknown"),
                "file_hash": fhash,
                "file_type": block.file_type if block else fentry.get("type","file"),
                "timestamp": block.timestamp if block else fentry.get("added", 0),
                "nonce":   block.nonce     if block else 0,
                "preview": file_previews.get(fhash)
            })
        return jsonify({"files":result})
    except Exception as e:
        import traceback
        return jsonify({"error":str(e), "trace": traceback.format_exc()}), 500

@app.route("/download/<file_hash>")
def download(file_hash):
    u = session.get("user")
    if not u: return jsonify({"error":"Unauthorized"}), 401
    if file_hash not in get_user_file_hashes(u):
        return jsonify({"error":"Not your file"}), 403
    bc = get_blockchain()
    block = bc.find_block_by_hash(file_hash)
    fname = block.file_name if block else "download"
    data, actual_name = get_file_bytes(file_hash, fname)
    if not data:
        return jsonify({"error":"File not found on server"}), 404
    mime = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    return send_file(io.BytesIO(data), mimetype=mime,
                     as_attachment=True, download_name=fname)

@app.route("/delete_file", methods=["POST"])
def delete_file():
    u = session.get("user")
    if not u: return jsonify({"success":False,"message":"Not logged in."}), 401
    data = request.get_json()
    fh = data.get("file_hash","")
    if fh not in get_user_file_hashes(u):
        return jsonify({"success":False,"message":"File not in your account."})
    remove_file_from_user(u, fh)
    file_previews.pop(fh, None)
    # Remove from disk
    import shutil
    folder = UPLOAD_DIR / fh
    if folder.exists():
        shutil.rmtree(folder)
    return jsonify({"success":True})

@app.route("/register", methods=["POST"])
def register():
    u = session.get("user")
    if not u: return jsonify({"status":"error","message":"Not logged in."}), 401
    if "file" not in request.files:
        return jsonify({"status":"error","message":"No file uploaded"}), 400
    f = request.files["file"]
    raw = f.read()
    fhash = generate_bytes_hash(raw)
    ftype = detect_file_type(f.filename)
    save_file_bytes(fhash, f.filename, raw)
    if ftype == "image":
        mime = mimetypes.guess_type(f.filename)[0] or "image/jpeg"
        file_previews[fhash] = f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    try:
        bc = get_blockchain()
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500
    # Check if THIS user already registered this exact file
    user_hashes = get_user_file_hashes(u)
    if fhash in user_hashes:
        existing = bc.find_block_by_hash(fhash)
        return jsonify({"status":"exists","file_name":f.filename,"file_hash":fhash,
            "block_index":existing.index if existing else "?"})

    # Always create a new block — even if another user registered the same file
    block = bc.add_block(f.filename, fhash, ftype)
    try:
        cid = save_bc(bc)
    except Exception as e:
        return jsonify({"status":"error","message":f"Pinata save failed: {e}"}), 500
    add_file_to_user(u, fhash, f.filename, ftype)
    return jsonify({"status":"registered","file_name":f.filename,"file_hash":fhash,
        "file_type":ftype,"block_index":block.index,"nonce":block.nonce,"ipfs_cid":cid})

@app.route("/verify", methods=["POST"])
def verify():
    if "file" not in request.files:
        return jsonify({"verified":False,"reason":"no_file"}), 400
    f = request.files["file"]
    raw = f.read()
    fhash = generate_bytes_hash(raw)
    ftype = detect_file_type(f.filename)
    try:
        bc = get_blockchain()
    except Exception as e:
        return jsonify({"verified":False,"reason":"blockchain_error","message":str(e)}), 500
    block = bc.find_block_by_hash(fhash)
    valid = bc.is_chain_valid()
    if block:
        return jsonify({"verified":True,"file_name":f.filename,"file_hash":fhash,
            "file_type":ftype,"block_index":block.index,"chain_valid":valid})
    return jsonify({"verified":False,"reason":"not_found","file_name":f.filename,
        "file_hash":fhash,"file_type":ftype})

@app.route("/chain")
def chain():
    try:
        bc = get_blockchain()
        return jsonify({"chain":bc.to_list(),"valid":bc.is_chain_valid(),"cid":get_latest_cid()})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/pinata_status")
def pinata_status():
    return jsonify({"connected":test_pinata_connection()})

# ══════════════════════════════════════════════════════════════════════════
# ROUTES — ADMIN
# ══════════════════════════════════════════════════════════════════════════

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    u = data.get("username", "").strip()
    p = data.get("password", "").strip()
    # Accept either: admin credentials OR already has admin session
    if (u == ADMIN_USERNAME and p == ADMIN_PASSWORD) or session.get("admin"):
        session["admin"] = True
        return jsonify({"success":True})
    return jsonify({"success":False})

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"success":True})

@app.route("/admin/auth_status")
def admin_auth_status():
    return jsonify({"logged_in":bool(session.get("admin"))})

@app.route("/admin/users")
def admin_users():
    if not session.get("admin"):
        return jsonify({"error":"Unauthorized"}), 401
    users = load_users()
    result = []
    for uname, udata in users.items():
        result.append({
            "username": uname,
            "created_at": udata.get("created_at", 0),
            "last_login": udata.get("last_login"),
            "login_count": udata.get("login_count", 0),
            "file_count": len(udata.get("files", [])),
            "files": udata.get("files", [])
        })
    return jsonify({"users": result})

@app.route("/admin/delete_user", methods=["POST"])
def admin_delete_user():
    if not session.get("admin"):
        return jsonify({"success":False,"message":"Unauthorized"}), 401
    data = request.get_json()
    username = data.get("username","")
    users = load_users()
    if username not in users:
        return jsonify({"success":False,"message":"User not found."})
    del users[username]
    save_users(users)
    return jsonify({"success":True})

@app.route("/admin/config", methods=["POST"])
def admin_config():
    if not session.get("admin"):
        return jsonify({"success":False,"message":"Unauthorized"}), 401
    import pinata_utils as pu
    data = request.get_json()
    api_key = data.get("api_key","")
    secret_key = data.get("secret_key","")
    pu.PINATA_API_KEY = api_key
    pu.PINATA_SECRET_KEY = secret_key
    os.environ["PINATA_API_KEY"] = api_key
    os.environ["PINATA_SECRET_KEY"] = secret_key
    env = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k,v = line.split("=",1)
                    env[k.strip()] = v.strip()
    env["PINATA_API_KEY"] = api_key
    env["PINATA_SECRET_KEY"] = secret_key
    with open(".env","w") as f:
        for k,v in env.items(): f.write(f"{k}={v}\n")
    connected = pu.test_pinata_connection()
    return jsonify({"success":connected,
        "message":"✅ Connected! Keys saved." if connected else "❌ Connection failed."})

@app.route("/admin/change_password", methods=["POST"])
def admin_change_password():
    if not session.get("admin"):
        return jsonify({"success":False,"message":"Unauthorized"}), 401
    global ADMIN_PASSWORD
    data = request.get_json()
    old_p = data.get("old_password","")
    new_p = data.get("new_password","")
    if old_p != ADMIN_PASSWORD:
        return jsonify({"success":False,"message":"❌ Current password is wrong."})
    if len(new_p) < 6:
        return jsonify({"success":False,"message":"❌ New password too short (min 6)."})
    ADMIN_PASSWORD = new_p
    os.environ["ADMIN_PASSWORD"] = new_p
    env = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k,v = line.split("=",1)
                    env[k.strip()] = v.strip()
    env["ADMIN_PASSWORD"] = new_p
    with open(".env","w") as f:
        for k,v in env.items(): f.write(f"{k}={v}\n")
    return jsonify({"success":True,"message":"✅ Admin password updated!"})

if __name__ == "__main__":
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, port=5000)