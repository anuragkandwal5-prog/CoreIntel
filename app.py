from flask import Flask, render_template

app = Flask(__name__)

# यह रूट आपकी वेबसाइट का मुख्य पेज (एंट्री गेट) है
@app.route('/')
def home():
    # render_template फंक्शन खुद-ब-खुद templates फोल्डर से login.html को ढूंढ कर स्क्रीन पर दिखा देगा
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
