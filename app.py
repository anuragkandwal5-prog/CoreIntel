from flask import Flask, request, render_template, session, redirect

app.secret_key = "koi-lamba-random-text-badal-do"

@app.route('/login', methods=['POST'])
def login():
    name = request.form.get('name', '').strip()
    password = request.form.get('password', '')
    email = request.form.get('email', '').strip()
    # TODO: yahan asli password check lagao
    session['user'] = {'name': name, 'vip': bool(email)}
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    u = session.get('user')
    if not u:
        return redirect('/')          # login ke bina andar nahi aa sakte
    return render_template('dashboard.html', name=u['name'], vip=u['vip'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
