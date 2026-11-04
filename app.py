from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# आपका सीक्रेट लॉगिन डेटा (आप इसे अपने हिसाब से बदल सकते हैं)
ADMIN_NAME = "Anurag"
ADMIN_EMAIL = "admin@coreintel.com"

# 1. मुख्य पेज (यहाँ आपका एनिमेटेड लॉगिन फॉर्म खुलेगा)
@app.route('/')
def home():
    return render_template('login.html')

# 2. लॉगिन चेक करने का सिस्टम
@app.route('/login', methods=['POST'])
def login():
    # लॉगिन फॉर्म से डेटा निकालना
    user_name = request.form.get('name')
    user_email = request.form.get('email')
    
    # चेक करना कि नाम और ईमेल सही है या नहीं
    if user_name.lower() == ADMIN_NAME.lower() and user_email == ADMIN_EMAIL:
        # अगर सही है, तो मास्टर डैशबोर्ड पर भेज दो
        return redirect('/dashboard')
    else:
        # अगर गलत है, तो एरर मैसेज दिखाओ
        return "<h1>गलत नाम या ईमेल! यह सुरक्षित सिस्टम है।</h1> <a href='/'>वापस जाएँ</a>"

# 3. आपका सुरक्षित मास्टर डैशबोर्ड (लॉगिन के बाद यहाँ आएंगे)
@app.route('/dashboard')
def dashboard():
    return """
    <h1 style='color: #27ae60; text-align: center; margin-top: 50px;'>CoreIntel मास्टर डैशबोर्ड में आपका स्वागत है, अनुराग!</h1>
    <p style='text-align: center;'>यहाँ हम आपके OSINT, Scam Detector, और Payload Generator टूल्स सेट करेंगे।</p>
    """

if __name__ == '__main__':
    app.run(debug=True)
