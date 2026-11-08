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

def vip_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect("/")
        if not session["user"]["vip"]:
            return redirect("/dashboard")
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


# ---------- ✏️ NORMAL PAGES ----------
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


# ============================================================
# ★ VIP PAGES — sirf coreintel@nia.com se login karne par khulte hain
# ============================================================

# ---- VIP 1: METASPLOIT ----
# Isko maine jaan-bujh kar wire nahi kiya — chat mein wajah likhi hai.
@app.route("/vip/1")
@vip_required
def vip_metasploit():
    return page("METASPLOIT", "Apna Metasploit console/RPC yahan jodo (sirf apne authorized setup ke liye)",
                [("status", "placeholder — apna integration add karo")])


# ---- VIP 2: OSINT TOOL (domain WHOIS lookup) ----
# requirements.txt mein 'python-whois' add karo
@app.route("/vip/2")
@vip_required
def vip_osint():
    domain = request.args.get("domain", "").strip()
    rows = [("usage", "URL ke end mein jodo: ?domain=example.com")]
    if domain:
        rows = [("checked domain", domain)]
        try:
            import whois
            w = whois.whois(domain)
            rows.append(("registrar", str(w.registrar)))
            rows.append(("created", str(w.creation_date)))
            rows.append(("expires", str(w.expiration_date)))
        except ImportError:
            rows.append(("error", "requirements.txt me python-whois add karo"))
        except Exception as e:
            rows.append(("error", str(e)))
    return page("OSINT TOOL", "Domain WHOIS lookup (apna OSINT source yahan badal sakte ho)", rows)


# ---- VIP 3: DATA BREACH CHECK (Have I Been Pwned API) ----
# 1. https://haveibeenpwned.com/API/Key se apni API key lo
# 2. Render → Environment me HIBP_KEY naam se wahi key daal do
@app.route("/vip/3")
@vip_required
def vip_breach_check():
    email = request.args.get("email", "").strip()
    key = os.environ.get("HIBP_KEY")
    rows = [("usage", "URL ke end mein jodo: ?email=someone@example.com")]
    if email and not key:
        rows = [("error", "HIBP_KEY set nahi hai (Render → Environment)")]
    elif email:
        rows = [("checked email", email)]
        try:
            import requests
            r = requests.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                headers={"hibp-api-key": key, "user-agent": "coreintel-dashboard"},
                timeout=8,
            )
            if r.status_code == 200:
                rows.append(("breaches found", ", ".join(b["Name"] for b in r.json())))
            elif r.status_code == 404:
                rows.append(("result", "no breach found"))
            else:
                rows.append(("result", f"error {r.status_code}"))
        except ImportError:
            rows.append(("error", "requirements.txt me requests add karo"))
        except Exception as e:
            rows.append(("error", str(e)))
    return page("DATA BREACH CHECK", "Have I Been Pwned se check karta hai", rows)
