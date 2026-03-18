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

# Render ရဲ့ Env Variables ထဲမှာ MONGO_URI ဆိုပြီး Link ကို ထည့်ပေးထားရပါမယ်
app.config["MONGO_URI"] = os.environ.get('MONGO_URI')
mongo = PyMongo(app)

# Upload folder မရှိရင် ဆောက်မယ်
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Class for MongoDB
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.phone = user_data['phone']

@login_manager.user_loader
def load_user(user_id):
    if not user_id: return None
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return User(user_data) if user_data else None

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
            flash('Register လုပ်တာ အောင်မြင်ပါသည်။ Login ဝင်နိုင်ပါပြီ။')
            return redirect(url_for('login'))
        flash('ဒီဖုန်းနံပါတ် ရှိနှင့်ပြီးသားပါ။')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# SocketIO Logic
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

@socketio.on('file_upload')
def handle_file(data):
    try:
        f_name = data['filename']
        f_content = data['content']
        time_str = datetime.now().strftime("%I:%M %p")
        header, encoded = f_content.split(",", 1)
        file_bytes = base64.b64decode(encoded)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f_name)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        file_url = url_for('static', filename='uploads/' + f_name)
        emit('message', {
            'user': current_user.username, 
            'message': file_url, 
            'filename': f_name,
            'time': time_str,
            'type': 'file'
        }, broadcast=True)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
