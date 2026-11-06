from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    user_name = request.form.get('name')
    user_password = request.form.get('password')
    vip_email = request.form.get('email')

    if user_name and user_password:
        print(f"नया लॉगिन -> नाम: {user_name}, पासवर्ड: {user_password}")
        
        # अगर ईमेल भरा गया है, तो VIP चालू हो जाएगा
        is_vip = True if vip_email else False 
        
        # यहाँ हम डैशबोर्ड दिखा रहे हैं और नाम/VIP स्टेटस भेज रहे हैं
        return render_template('dashboard.html', name=user_name, vip=is_vip)
    
    else:
        return "<h1>लॉगिन फेल! कृपया नाम और पासवर्ड दोनों भरें।</h1>"

if __name__ == '__main__':
    app.run(debug=True)
