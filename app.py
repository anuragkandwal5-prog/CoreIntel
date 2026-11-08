import os, time
from functools import wraps
from flask import Flask, request, render_template, session, redirect, abort

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "badal-do-koi-lamba-random-text")

VIP_EMAIL = "coreintel@nia.com"   # sirf isi email se VIP khulega


# ---------- helpers ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

def page(title, note, items):
    u = session["user"]
    return render_template("page.html", title=title, note=note, items=items,
                           name=u["name"], vip=u["vip"])


# ---------- login / logout ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    email = request.form.get("email", "").strip()
    # TODO: yahan asli password check lagao
    if not name or not password:
        return redirect("/")
    is_vip = email.lower() == VIP_EMAIL.lower()     # sirf exact email match par VIP
    session["user"] = {"name": name, "vip": is_vip,
                       "since": time.strftime("%d %b %Y, %H:%M UTC", time.gmtime())}
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------- dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    u = session["user"]
    return render_template("dashboard.html", name=u["name"], vip=u["vip"])


# ---------- ✏️ NORMAL PAGES: har page ka content yahan likho ----------
@app.route("/profile")
@login_required
def profile():
    u = session["user"]
    return page("PROFILE", "Aapki account details", [
        ("username", u["name"]),
        ("account", "★ VIP" if u["vip"] else "Standard"),
        ("logged in", u["since"]),
    ])

@app.route("/files")
@login_required
def files():
    return page("FILES", "Yahan apni files ki list dikhao", [
        ("report.pdf", "2.1 MB"),
        ("notes.txt", "4 KB"),
    ])

@app.route("/messages")
@login_required
def messages():
    return page("MESSAGES", "Yahan messages dikhao", [
        ("system", "welcome to the terminal"),
    ])

@app.route("/settings")
@login_required
def settings():
    return page("SETTINGS", "Yahan settings dikhao", [
        ("theme", "hacker-green"),
        ("notifications", "on"),
    ])


# ---------- ★ VIP PAGES: sirf coreintel@nia.com se login karne par khulta hai ----------
# Teeno pages abhi sirf placeholder hain — asli tool (Metasploit / OSINT / breach-check
# API) yahan apne authorized setup ke hisaab se khud jodo.
VIP_PAGES = {
    1: ("METASPLOIT", "Apna Metasploit console/RPC yahan jodo (sirf apne authorized setup ke liye)",
        [("status", "placeholder — apna integration add karo")]),
    2: ("OSINT TOOL", "Apna OSINT tool/API yahan jodo",
        [("status", "placeholder — apna integration add karo")]),
    3: ("DATA BREACH CHECK", "Apna breach-check tool/API yahan jodo",
        [("status", "placeholder — apna integration add karo")]),
}

@app.route("/vip/<int:n>")
@login_required
def vip_page(n):
    if not session["user"]["vip"]:
        return redirect("/dashboard")      # VIP email se login nahi kiya to andar nahi
    if n not in VIP_PAGES:
        abort(404)
    return page(*VIP_PAGES[n])
