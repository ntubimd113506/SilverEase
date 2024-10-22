import os
from PIL import Image
from flask import Flask, render_template, session, request, jsonify, redirect, url_for
from flask_login import login_required
from linebot.models import FlexSendMessage
from utils import db
from services import (
    event_bp,
    hos_bp,
    analyze_bp,
    health_bp,
    linebot_bp,
    med_bp,
    set_bp,
    user_bp,
    scheduler,
    mqtt,
    login_manager,
    gps_bp,
    line_bot_api,
    sos_bp,
    ollama_bp
)
from config import Config

app = Flask(__name__)

app.config.from_object(Config())
app.register_blueprint(med_bp, url_prefix="/med")
app.register_blueprint(hos_bp, url_prefix="/hos")
app.register_blueprint(event_bp, url_prefix="/event")
app.register_blueprint(analyze_bp, url_prefix="/analyze")
app.register_blueprint(health_bp, url_prefix="/health")
app.register_blueprint(set_bp, url_prefix="/set")
app.register_blueprint(linebot_bp, url_prefix="/")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(gps_bp, url_prefix="/gps")
app.register_blueprint(sos_bp, url_prefix="/sos")
app.register_blueprint(ollama_bp, url_prefix="/ollama")

scheduler.init_app(app)
mqtt.init_app(app)
login_manager.init_app(app)


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


@app.route("/lostAndFound")
def lostAndFound():
    DevID = session.get("DevID")
    mqtt.publish(f"ESP32/{DevID}/newGPS", "")
    return render_template("lostAndFound.html")


@app.route("/lost_report", methods=["POST"])
def lost_report():
    DevID = session.get("DevID")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("select FamilyID,MainUserID from Family where DevID=%s",(DevID))
    res=cur.fetchone()
    FamilyID=res[0]
    MainUserID=res[1]
    cur.execute(
        "select SubUserID from FamilyLink Where FamilyID = %s", FamilyID)
        
    SubUserID = cur.fetchall()
    message = request.json["message"]
    userPro=line_bot_api.get_profile(MainUserID).as_json_dict()
    userName=userPro["displayName"]
    msg = FlexSendMessage(
        alt_text="遺失/走失通報",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://developers-resource.landpress.line.me/fx/img/01_1_cafe.png",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
                "action": {"type": "uri", "uri": "https://line.me/"},
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"已有人通報{userName}\n裝置遺失/長者走失",
                        "weight": "bold",
                        "size": "xl",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [{"type": "text", "text": message}],
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "查看最後位置",
                            "uri": f"https://liff.line.me/{db.LIFF_ID}/sos/gps/{FamilyID}",
                        },
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "margin": "sm",
                    },
                ],
                "flex": 0,
            },
        },
    )

    for user in SubUserID:
        line_bot_api.push_message(user[0], msg)
    return jsonify({"status": "success"})


@app.route("/img/<img>")
def display_image(img):
    try:
        with Image.open(os.path.join("static", "imgs", "upload", img)) as file:
            file.load()
        return redirect(url_for("static", filename=f"imgs/upload/{img}"))
    except:
        return redirect(url_for("static", filename="imgs/notfound.png"))


if __name__ == "__main__":
    app.run(debug=1)
