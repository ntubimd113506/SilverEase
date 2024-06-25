from flask import Flask, render_template
from flask_apscheduler import APScheduler
from utils import db
from services import cam_bp, event_bp, hos_bp, linebot_bp, med_bp, set_bp


class Config:
    SCHEDULER_API_ENABLED = True


app = Flask(__name__)
scheduler = APScheduler()
app.config.from_object(Config())
app.register_blueprint(med_bp, url_prefix="/med")
app.register_blueprint(hos_bp, url_prefix="/hos")
app.register_blueprint(event_bp, url_prefix="/event")
app.register_blueprint(cam_bp, url_prefix="/cam")
app.register_blueprint(set_bp, url_prefix="/set")
app.register_blueprint(linebot_bp, url_prefix="/linebot")
scheduler.init_app(app)
scheduler.start()


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


if __name__ == "__main__":
    app.run(debug=1)
