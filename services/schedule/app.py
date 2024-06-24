from flask_apscheduler import APScheduler
from flask import Flask

app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()