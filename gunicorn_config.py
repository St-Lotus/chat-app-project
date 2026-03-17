import os
workers = 1
worker_class = 'eventlet' # SocketIO အတွက် ဒါလိုအပ်ပါတယ်
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
