import eventlet
eventlet.monkey_patch()

import os, base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from flask_pymongo import PyMongo
from bson.objectid import ObjectId

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret123'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')

# Render Variable ကို ဖတ်တဲ့အပိုင်း (Indentation မှန်အောင် သေချာကြည့်ပါ)
mongo_uri = os.environ.get('MONGO_URI')

if not mongo_uri:
    # Local မှာ စမ်းနေတာဆိုရင် ဒီအတိုင်း ပေးထားမယ်
    app.config["MONGO_URI"] = "mongodb://localhost:27017/chat_app_db"
else:
    # Render ပေါ်ရောက်ရင် MONGO_URI ကို သုံးမယ်
    app.config["MONGO_URI"] = mongo_uri

mongo = PyMongo(app)

# Upload folder ရှိမရှိ စစ်မယ်
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.phone = user_data['phone']

@login_manager.user_loader
def load_user(user_id):
    if not user_id: return None
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None
    except:
        return None

# Routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        user_data = mongo.db.users.find_one({"phone": phone})
        if user_data:
            login_user(User(user_data))
            return redirect(url_for('index'))
        flash('ဖုန်းနံပါတ် မှားနေပါသည် သို့မဟုတ် Register အရင်လုပ်ပါ။')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form.get('phone')
        username = request.form.get('username')
        if not mongo.db.users.find_one({"phone": phone}):
            mongo.db.users.insert_one({"phone": phone, "username": username})
            flash('Register အောင်မြင်ပါသည်။ Login ဝင်နိုင်ပါပြီ။')
            return redirect(url_for('login'))
        flash('ဒီဖုန်းနံပါတ် ရှိနှင့်ပြီးသားပါ။')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10 * 1024 * 1024)

@socketio.on('message')
def handle_message(data):
    time_str = datetime.now().strftime("%I:%M %p")
    emit('message', {
        'user': current_user.username, 
        'message': data['message'], 
        'time': time_str,
        'type': 'text'
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
