import os, time
from functools import wraps
from flask import Flask, request, render_template, session, redirect, abort, g
from werkzeug.security import generate_password_hash, check_password_hash
import re as _re

import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "badal-do-koi-lamba-random-text")

with app.app_context():
    db.init_db()


# ---------- helpers ----------
def current_user():
    uname = session.get("user")
    if not uname:
        return None
    return db.get_user(uname)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return redirect("/")
        g.user = u
        return f(*args, **kwargs)
    return wrapper


def vip_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return redirect("/")
        if not u["is_vip"]:
            return redirect("/dashboard")
        g.user = u
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return redirect("/")
        if not u["is_admin"]:
            return redirect("/dashboard")
        g.user = u
        return f(*args, **kwargs)
    return wrapper


def page(title, note, items, qparam=None, qlabel=None, qvalue=""):
    u = g.user
    return render_template("page.html", title=title, note=note, items=items,
                           name=u["username"], vip=u["is_vip"],
                           qparam=qparam, qlabel=qlabel, qvalue=qvalue)


def tool_on(name):
    return db.get_setting("tool_" + name, "on") != "off"


# ---------- login / signup / logout ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    email = request.form.get("email", "").strip()

    if not username or not password:
        return redirect("/")

    user = db.get_user(username)
    if user is None:
        pwhash = generate_password_hash(password)
        user = db.create_user(username, pwhash, email or None)
        db.log_event(username, "अकाउंट बनाया गया")
    else:
        if not check_password_hash(user["password_hash"], password):
            return redirect("/")

    session["user"] = user["username"]
    db.log_event(user["username"], "लॉगिन किया")
    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------- dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    u = g.user
    return render_template("dashboard.html", name=u["username"], vip=u["is_vip"], admin=u["is_admin"])


# ---------- NORMAL PAGES ----------
@app.route("/profile")
@login_required
def profile():
    u = g.user
    status = "★ VIP" if u["is_vip"] else ("VIP पेंडिंग (एडमिन अप्रूव करेगा)" if u["vip_requested"] else "Standard")
    return page("PROFILE", "आपका अकाउंट", [
        ("यूज़रनेम", u["username"]),
        ("ईमेल", u["email"] or "—"),
        ("अकाउंट", status),
        ("रोल", "Admin" if u["is_admin"] else "Member"),
        ("जुड़ने की तारीख", str(u["created_at"])[:16]),
    ])


@app.route("/files")
@login_required
def files():
    return render_template("files.html")


@app.route("/messages")
@login_required
def messages():
    logs = db.recent_logs(30)
    rows = [(l["username"] or "system", f'{l["text"]} · {str(l["created_at"])[:16]}') for l in logs]
    if not rows:
        rows = [("system", "अभी तक कोई गतिविधि नहीं")]
    return page("MESSAGES", "वेबसाइट की रियल एक्टिविटी लॉग", rows)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    u = g.user
    msg = None
    if request.method == "POST":
        action = request.form.get("action")

        if action == "password":
            cur_pw = request.form.get("current", "")
            new_pw = request.form.get("new", "")
            if not check_password_hash(u["password_hash"], cur_pw):
                msg = ("err", "करंट पासवर्ड गलत है")
            elif len(new_pw) < 4:
                msg = ("err", "नया पासवर्ड थोड़ा लंबा रखें")
            else:
                db.set_password(u["username"], generate_password_hash(new_pw))
                db.log_event(u["username"], "पासवर्ड बदल दिया")
                msg = ("ok", "पासवर्ड बदल दिया गया है")

        elif action == "username":
            new_name = request.form.get("new_username", "").strip()
            if not new_name:
                msg = ("err", "नया यूज़रनेम लिखें")
            elif db.get_user(new_name):
                msg = ("err", "यह यूज़रनेम पहले से लिया हुआ है")
            else:
                db.rename_user(u["username"], new_name)
                db.log_event(new_name, f'यूज़रनेम {u["username"]} से बदला गया')
                session["user"] = new_name
                msg = ("ok", f'यूज़रनेम "{new_name}" हो गया — अगली बार इसी नाम से लॉगिन करें')

        elif action == "vip_request":
            if not u["is_vip"]:
                db.request_vip(u["username"])
                db.log_event(u["username"], "VIP एक्सेस के लिए रिक्वेस्ट भेजी")
                msg = ("ok", "VIP रिक्वेस्ट भेज दी गई है, एडमिन अप्रूव करेगा")

        u = db.get_user(session["user"])
        g.user = u

    return render_template("settings.html", user=u, msg=msg)


# ============================================================
# ★ VIP PAGES
# ============================================================

@app.route("/vip/1")
@vip_required
def vip_metasploit():
    return page("METASPLOIT", "अपना Metasploit console यहाँ जोड़ें",
                [("status", "placeholder — अपना कोड डालें")])


_IP_RE = _re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

@app.route("/vip/2")
@vip_required
def vip_osint():
    if not tool_on("osint"):
        return page("OSINT TOOL", "यह टूल एडमिन ने अभी बंद कर रखा है", [("status", "disabled by admin")])

    q = request.args.get("domain", "").strip()
    rows = []
    
    if q and _IP_RE.match(q):
        rows = [("checked ip", q)]
        try:
            import requests
            r = requests.get(f"http://ip-api.com/json/{q}", timeout=8).json()
            if r.get("status") == "success":
                rows += [("country", r.get("country")), ("city", r.get("city")), ("isp", r.get("isp"))]
            else:
                rows.append(("error", "आईपी नहीं मिला"))
        except Exception:
            rows.append(("error", "नेटवर्क एरर"))

    elif q:
        rows = [("checked domain", q)]
        try:
            import whois
            w = whois.whois(q)
            rows.append(("registrar", str(w.registrar)))
            rows.append(("created", str(w.creation_date)))
            rows.append(("expires", str(w.expiration_date)))
        except Exception:
            rows.append(("error", "डोमेन स्कैन फेल हो गया"))

    return page("OSINT TOOL", "Domain WHOIS या IP लोकेशन चेक करें", rows,
                qparam="domain", qlabel="यहाँ डोमेन (example.com) या IP डालें", qvalue=q)


@app.route("/vip/3")
@vip_required
def vip_breach_check():
    if not tool_on("breach"):
        return page("DATA BREACH CHECK", "यह टूल एडमिन ने अभी बंद कर रखा है", [("status", "disabled by admin")])

    email = request.args.get("email", "").strip()
    rows = []
    if email:
        rows = [("checked email", email)]
        try:
            import requests
            r = requests.get(f"https://api.xposedornot.com/v1/check-email/{email}", timeout=8)
            data = r.json()
            breaches = [b[0] for b in data.get("breaches", []) if b]
            rows.append(("breaches found", ", ".join(breaches) if breaches else "कोई लीक नहीं मिला"))
        except Exception:
            rows.append(("error", "नेटवर्क एरर"))
    return page("DATA BREACH CHECK", "XposedOrNot का फ्री API", rows,
                qparam="email", qlabel="यहाँ ईमेल डालें", qvalue=email)


# ============================================================
# ⚙ ADMIN PANEL
# ============================================================
@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    msg = None
    if request.method == "POST":
        action = request.form.get("action")
        target = request.form.get("username", "")

        if action == "approve_vip":
            db.set_vip(target, True)
            db.log_event(target, "एडमिन द्वारा VIP अप्रूव किया गया")
            msg = ("ok", f"{target} को VIP मिल गया")
        elif action == "deny_vip":
            db.set_vip(target, False)
            db.log_event(target, "एडमिन द्वारा VIP रिक्वेस्ट रद्द की गई")
            msg = ("ok", f"{target} की VIP रिक्वेस्ट हटा दी गई")
        elif action == "revoke_vip":
            db.set_vip(target, False)
            db.log_event(target, "एडमिन द्वारा VIP छीना गया")
            msg = ("ok", f"{target} का VIP हटा दिया गया")
        elif action == "toggle_tool":
            tool = request.form.get("tool")
            newv = "off" if tool_on(tool) else "on"
            db.set_setting("tool_" + tool, newv)
            msg = ("ok", f"{tool} अब {newv} है")

    users = db.list_users()
    tools = {"osint": tool_on("osint"), "breach": tool_on("breach")}
    return render_template("admin.html", users=users, tools=tools, msg=msg)
