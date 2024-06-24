import os
import pathlib
from flask import Flask, request, abort, render_template, redirect, url_for, session
from flask_mqtt import Mqtt
from utils import db
from services import services_bp

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'silverease.ntub.edu.tw'  # 您的 MQTT 代理地址
app.config['MQTT_BROKER_PORT'] = 8883  # MQTT 代理端口
app.config['MQTT_USERNAME'] = ''  # 如果需要的話，填寫您的 MQTT 用戶名
app.config['MQTT_PASSWORD'] = ''  # 如果需要的話，填寫您的 MQTT 密碼
app.config['MQTT_KEEPALIVE'] = 60  # KeepAlive 週期，以秒為單位
app.config['MQTT_TLS_ENABLED'] = True  # 啟用 TLS 加密
app.config['MQTT_TLS_CA_CERTS'] = os.path.join(
    pathlib.Path(__file__).parent, 'ca/my-ca.crt')
app.config['MQTT_TLS_VERSION'] = 5
mqtt = Mqtt(app)

app.register_blueprint(services_bp, url_prefix="/")


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


if __name__ == "__main__":
    app.run(debug=1)
