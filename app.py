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

    if not name or not password:
        return redirect("/")      # bas dono khali nahi hone chahiye

    is_vip = email.lower() == VIP_EMAIL.lower()     # sirf isi email se VIP
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

# ---- VIP 1: METASPLOIT — khali, aap khud karoge ----
@app.route("/vip/1")
@vip_required
def vip_metasploit():
    return page("METASPLOIT", "Apna Metasploit console/RPC yahan jodo (sirf apne authorized setup ke liye)",
                [("status", "placeholder — apna integration add karo")])


# ---- VIP 2: OSINT TOOL (domain -> WHOIS, IP -> geolocation) ----
# requirements.txt mein 'python-whois' add karo
import re as _re
_IP_RE = _re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

@app.route("/vip/2")
@vip_required
def vip_osint():
    q = request.args.get("domain", "").strip()
    rows = [("usage", "URL ke end mein jodo: ?domain=example.com ya ?domain=8.8.8.8")]
    if q and _IP_RE.match(q):
        rows = [("checked ip", q)]
        try:
            import requests
            r = requests.get(f"http://ip-api.com/json/{q}", timeout=8).json()
            if r.get("status") == "success":
                rows += [("country", r.get("country")), ("city", r.get("city")), ("isp", r.get("isp"))]
            else:
                rows.append(("error", r.get("message", "lookup failed")))
        except ImportError:
            rows.append(("error", "requirements.txt me requests add karo"))
        except requests.exceptions.RequestException:
            rows.append(("error", "network/lookup failed, dobara try karo"))
        except Exception:
            rows.append(("error", "kuch galat hua"))
    elif q:
        rows = [("checked domain", q)]
        try:
            import whois
            w = whois.whois(q)
            rows.append(("registrar", str(w.registrar)))
            rows.append(("created", str(w.creation_date)))
            rows.append(("expires", str(w.expiration_date)))
        except ImportError:
            rows.append(("error", "requirements.txt me python-whois add karo"))
        except Exception:
            rows.append(("error", "lookup failed, domain check karo"))
    return page("OSINT TOOL", "Domain WHOIS ya IP geolocation lookup", rows)


# ---- VIP 3: DATA BREACH CHECK (XposedOrNot — free, no API key) ----
@app.route("/vip/3")
@vip_required
def vip_breach_check():
    email = request.args.get("email", "").strip()
    rows = [("usage", "URL ke end mein jodo: ?email=someone@example.com")]
    if email:
        rows = [("checked email", email)]
        try:
            import requests
            r = requests.get(f"https://api.xposedornot.com/v1/check-email/{email}", timeout=8)
            data = r.json()
            breaches = [b[0] for b in data.get("breaches", []) if b]
            rows.append(("breaches found", ", ".join(breaches) if breaches else "none"))
        except ImportError:
            rows.append(("error", "requirements.txt me requests add karo"))
        except requests.exceptions.RequestException:
            rows.append(("error", "network/lookup failed, dobara try karo"))
        except Exception:
            rows.append(("error", "kuch galat hua"))
    return page("DATA BREACH CHECK", "XposedOrNot ka free API (koi key nahi chahiye)", rows)
