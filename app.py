from flask import Flask, request, render_template, session, redirect

app = Flask(__name__)
app.secret_key = "koi-lamba-random-text-badal-do" # इसे बाद में किसी मुश्किल पासवर्ड से बदल दीजिएगा

@app.route('/')
def home():
    # अगर आप पहले से लॉगिन हैं, तो सीधा डैशबोर्ड पर चले जाएंगे
    if 'user' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip()
    
    # यहाँ लॉगिन चेक हो रहा है (अगर नाम और पासवर्ड खाली नहीं हैं)
    if name and password:
        print(f"लॉगिन सफल: {name}")
        # ईमेल भरा गया है तो vip True हो जाएगा, नहीं तो False
        session['user'] = {'name': name, 'vip': bool(email)}
        return redirect('/dashboard')
    else:
        return "<h1>लॉगिन फेल! कृपया नाम और पासवर्ड दोनों भरें।</h1>"

@app.route('/dashboard')
def dashboard():
    u = session.get('user')
    # अगर कोई बिना लॉगिन किए डैशबोर्ड खोलना चाहे, तो उसे वापस लॉगिन पेज पर भेज देंगे
    if not u:
        return redirect('/') 
    
    # डैशबोर्ड पेज को आपका नाम और VIP का स्टेटस भेजा जा रहा है
    return render_template('dashboard.html', name=u['name'], vip=u['vip'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
