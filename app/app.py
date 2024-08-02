import os
from PIL import Image
from flask import Flask, render_template, session, request, jsonify, redirect, url_for
from flask_login import login_required
from utils import db
from services import cam_bp, event_bp, hos_bp, linebot_bp, med_bp, set_bp, user_bp , scheduler, mqtt, login_manager,sos_bp
from config import Config

app = Flask(__name__)

app.config.from_object(Config())
app.register_blueprint(med_bp, url_prefix="/med")
app.register_blueprint(hos_bp, url_prefix="/hos")
app.register_blueprint(event_bp, url_prefix="/event")
app.register_blueprint(cam_bp, url_prefix="/cam")
app.register_blueprint(set_bp, url_prefix="/set")
app.register_blueprint(linebot_bp, url_prefix="/")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(sos_bp, url_prefix="/sos")

scheduler.init_app(app)
mqtt.init_app(app)
login_manager.init_app(app)


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)

@app.route("/lostAndFound")
def lostAndFound():
    return render_template("lostAndFound.html")

@app.route('/img/<img>')
def display_image(img):
    try:
        with Image.open(os.path.join("app", "static", "imgs", "upload", img)) as file:
            file.load()
        return redirect(url_for('static', filename=f'imgs/upload/{img}'))
    except:
        return redirect(url_for('static', filename='/imgs/help.png'))

if __name__ == "__main__":
    app.run(debug=1)
