from flask import Flask, render_template, session, request, jsonify
from utils import db
from services import cam_bp, event_bp, hos_bp, linebot_bp, med_bp, set_bp,scheduler,mqtt
from config import Config

app = Flask(__name__)

app.config.from_object(Config())
app.register_blueprint(med_bp, url_prefix="/med")
app.register_blueprint(hos_bp, url_prefix="/hos")
app.register_blueprint(event_bp, url_prefix="/event")
app.register_blueprint(cam_bp, url_prefix="/cam")
app.register_blueprint(set_bp, url_prefix="/set")
app.register_blueprint(linebot_bp, url_prefix="/")
scheduler.init_app(app)
scheduler.start()
mqtt.init_app(app)


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


@app.route("/login", methods=["POST"])
def login():
    session["login"] = True
    session["userID"] = request.get_json()["userID"]
    return jsonify({"msg": "ok"})


if __name__ == "__main__":
    app.run(debug=1)
