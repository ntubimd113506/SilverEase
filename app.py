import os
import pathlib
from flask import Flask, render_template
from flask_apscheduler import APScheduler
from flask_mqtt import Mqtt
from utils import db
from services import services_bp

class Config:
    MQTT_BROKER_URL = 'silverease.ntub.edu.tw'  # 您的 MQTT 代理地址
    MQTT_BROKER_PORT = 8883  # MQTT 代理端口
    MQTT_KEEPALIVE = 60  # KeepAlive 週期，以秒為單位
    MQTT_TLS_ENABLED = True  # 啟用 TLS 加密
    MQTT_TLS_CA_CERTS = os.path.join(
        pathlib.Path(__file__).parent, 'ca/my-ca.crt')
    MQTT_TLS_VERSION = 5
    MQTT_CLIENT_ID = 'flask_mqtt'
    SCHEDULER_API_ENABLED = True


app = Flask(__name__)
app.config.from_object(Config())

mqtt = Mqtt(app)
scheduler = APScheduler()

scheduler.init_app(app)
scheduler.start()

app.register_blueprint(services_bp, url_prefix="/")


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


if __name__ == "__main__":
    app.run(debug=1)
