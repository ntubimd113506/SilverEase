from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = APScheduler(BackgroundScheduler())

def scheduer_listener(event):
    if not scheduler.running:
        scheduler.start()

scheduler.add_listener(scheduer_listener)
