import os, time
from functools import wraps
from flask import Flask, request, render_template, session, redirect, abort, g
from werkzeug.security import generate_password_hash, check_password_hash

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
        # ye naam pehli baar aaya -> naya account ban jata hai (signup)
        pwhash = generate_password_hash(password)
        user = db.create_user(username, pwhash, email or None)
        db.log_event(username, "account created")
    else:
        if not check_password_hash(user["password_hash"], password):
            return redirect("/")      # galat password
        if user["banned"]:
            return redirect("/?banned=1")

    session["user"] = user["username"]
    db.log_event(user["username"], "logged in")
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
    status = "★ VIP" if u["is_vip"] else ("VIP pending (admin approve karega)" if u["vip_requested"] else "Standard")
    return page("PROFILE", "Aapka account", [
        ("username", u["username"]),
        ("email", u["email"] or "—"),
        ("account", status),
        ("role", "Admin" if u["is_admin"] else "Member"),
        ("joined", str(u["created_at"])[:16]),
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
        rows = [("system", "abhi tak koi activity nahi")]
    return page("MESSAGES", "Website ki real activity log", rows)


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
                msg = ("err", "Current password galat hai")
            elif len(new_pw) < 4:
                msg = ("err", "Naya password thoda lamba rakho")
            else:
                db.set_password(u["username"], generate_password_hash(new_pw))
                db.log_event(u["username"], "password changed")
                msg = ("ok", "Password badal diya")

        elif action == "username":
            new_name = request.form.get("new_username", "").strip()
            if not new_name:
                msg = ("err", "Naya username likho")
            elif db.get_user(new_name):
                msg = ("err", "Ye username pehle se liya hua hai")
            else:
                db.rename_user(u["username"], new_name)
                db.log_event(new_name, f'username changed from {u["username"]}')
                session["user"] = new_name
                msg = ("ok", f'Username "{new_name}" ho gaya — agli baar isi naam se login karna')

        elif action == "vip_request":
            if not u["is_vip"]:
                db.request_vip(u["username"])
                db.log_event(u["username"], "requested VIP access")
                msg = ("ok", "VIP request bhej di, admin approve karega")

        elif action == "email":
            new_email = request.form.get("new_email", "").strip()
            db.update_email(u["username"], new_email or None)
            db.log_event(u["username"], "email updated")
            msg = ("ok", "Email update ho gaya")

        u = db.get_user(session["user"])
        g.user = u

    return render_template("settings.html", user=u, msg=msg)


# ============================================================
# ★ VIP PAGES
# ============================================================

@app.route("/vip/1")
@vip_required
def vip_metasploit():
    return page("METASPLOIT", "Apna Metasploit console/RPC yahan jodo (sirf apne authorized setup ke liye)",
                [("status", "placeholder — apna integration add karo")])


@app.route("/vip/4")
@vip_required
def vip_sherlock():
    return page("SHERLOCK (OSINT)", "Kisi bhi naam se accounts dhoondhne wala tool — ye maine jaan-bujh kar wire nahi kiya (wajah chat mein hai). Apna integration yahan add karo.",
                [("status", "placeholder — apna integration add karo")])


import re as _re
_IP_RE = _re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


@app.route("/vip/2")
@vip_required
def vip_osint():
    if not tool_on("osint"):
        return page("OSINT TOOL", "Ye tool admin ne abhi band kar rakha hai", [("status", "disabled by admin")])

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
                rows.append(("error", r.get("message", "lookup failed")))
        except ImportError:
            rows.append(("error", "requirements.txt me requests add karo"))
        except Exception:
            rows.append(("error", "network/lookup failed, dobara try karo"))
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
    return page("OSINT TOOL", "Domain WHOIS ya IP geolocation lookup", rows,
                qparam="domain", qlabel="domain ya IP daalo (example.com ya 8.8.8.8)", qvalue=q)


@app.route("/vip/3")
@vip_required
def vip_breach_check():
    if not tool_on("breach"):
        return page("DATA BREACH CHECK", "Ye tool admin ne abhi band kar rakha hai", [("status", "disabled by admin")])

    email = request.args.get("email", "").strip()
    rows = []
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
        except Exception:
            rows.append(("error", "network/lookup failed, dobara try karo"))
    return page("DATA BREACH CHECK", "XposedOrNot ka free API (koi key nahi chahiye)", rows,
                qparam="email", qlabel="email daalo (someone@example.com)", qvalue=email)


# ============================================================
# 📈 PAPER TRADING — virtual money, real live crypto prices
# ============================================================
COINS = [("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL"),
         ("dogecoin", "DOGE"), ("cardano", "ADA"), ("ripple", "XRP")]


def fetch_prices():
    ids = ",".join(c[0] for c in COINS)
    try:
        import requests
        r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd", timeout=8)
        data = r.json()
        return {sym: data.get(cid, {}).get("usd") for cid, sym in COINS}
    except Exception:
        return {sym: None for cid, sym in COINS}


@app.route("/trade", methods=["GET", "POST"])
@login_required
def trade():
    u = g.user
    msg = None
    prices = fetch_prices()

    if request.method == "POST":
        symbol = request.form.get("symbol", "").upper()
        side = request.form.get("side")
        price = prices.get(symbol)
        try:
            qty = float(request.form.get("qty", "0"))
        except ValueError:
            qty = 0

        if price is None:
            msg = ("err", "Price abhi load nahi ho payi, dobara try karo")
        elif qty <= 0:
            msg = ("err", "Sahi quantity daalo")
        elif side == "buy":
            ok, text = db.buy_asset(u["username"], symbol, qty, price)
            msg = ("ok" if ok else "err", text)
            if ok:
                db.log_event(u["username"], f"bought {qty} {symbol} @ {price}")
        elif side == "sell":
            ok, text = db.sell_asset(u["username"], symbol, qty, price)
            msg = ("ok" if ok else "err", text)
            if ok:
                db.log_event(u["username"], f"sold {qty} {symbol} @ {price}")

        u = db.get_user(u["username"])
        g.user = u

    holdings = db.get_holdings(u["username"])
    for h in holdings:
        h["price"] = prices.get(h["symbol"])
        h["value"] = (h["price"] or 0) * float(h["qty"])
        h["pnl"] = h["value"] - float(h["qty"]) * float(h["avg_price"])

    trades = db.get_trades(u["username"], 15)
    return render_template("trade.html", user=u, coins=COINS, prices=prices,
                           holdings=holdings, trades=trades, msg=msg)


# ============================================================
# ⚙ ADMIN PANEL — sirf is_admin=True ke liye
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
            db.log_event(target, "VIP approved by admin")
            msg = ("ok", f"{target} ko VIP mil gaya")
        elif action == "deny_vip":
            db.set_vip(target, False)
            db.log_event(target, "VIP request denied by admin")
            msg = ("ok", f"{target} ki VIP request hata di")
        elif action == "revoke_vip":
            db.set_vip(target, False)
            db.log_event(target, "VIP revoked by admin")
            msg = ("ok", f"{target} ki VIP hata di")
        elif action == "toggle_tool":
            tool = request.form.get("tool")
            newv = "off" if tool_on(tool) else "on"
            db.set_setting("tool_" + tool, newv)
            msg = ("ok", f"{tool} ab {newv}")

        elif action == "ban":
            db.set_banned(target, True)
            db.log_event(target, "banned by admin")
            msg = ("ok", f"{target} ban ho gaya")

        elif action == "unban":
            db.set_banned(target, False)
            db.log_event(target, "unbanned by admin")
            msg = ("ok", f"{target} ka ban hata diya")

        elif action == "set_balance":
            try:
                amount = float(request.form.get("amount", "0"))
                db.set_balance(target, amount)
                db.log_event(target, f"balance set to {amount} by admin")
                msg = ("ok", f"{target} ka balance {amount} ho gaya")
            except ValueError:
                msg = ("err", "Sahi number daalo")

    users = db.list_users()
    tools = {"osint": tool_on("osint"), "breach": tool_on("breach")}
    return render_template("admin.html", users=users, tools=tools, msg=msg)
