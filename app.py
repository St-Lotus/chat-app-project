import os, base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'database.db')
app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'static/uploads')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")

# Online Users ကို မှတ်ရန်
online_users = {}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        user = User.query.filter_by(phone=phone).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('ဖုန်းနံပါတ် ရှာမတွေ့ပါ။')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form.get('phone')
        username = request.form.get('username')
        if not User.query.filter_by(phone=phone).first():
            new_user = User(phone=phone, username=username)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Socket Events
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        online_users[request.sid] = current_user.username
        emit('user_list', list(set(online_users.values())), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in online_users:
        del online_users[request.sid]
        emit('user_list', list(set(online_users.values())), broadcast=True)

@socketio.on('message')
def handle_message(data):
    time_str = datetime.now().strftime("%I:%M %p")
    msg_id = base64.b64encode(os.urandom(6)).decode('utf-8') # Unique ID for delete
    emit('message', {
        'id': msg_id,
        'user': current_user.username, 
        'message': data['message'], 
        'time': time_str,
        'type': 'text'
    }, broadcast=True)

@socketio.on('delete_msg')
def handle_delete(data):
    emit('msg_deleted', data['id'], broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=5000)
