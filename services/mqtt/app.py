import os, pathlib
from flask import Flask, Blueprint, request, jsonify, abort
from flask_mqtt import Mqtt

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'silverease.ntub.edu.tw'  # 您的 MQTT 代理地址
app.config['MQTT_BROKER_PORT'] = 8883  # MQTT 代理端口
app.config['MQTT_USERNAME'] = ''  # 如果需要的話，填寫您的 MQTT 用戶名
app.config['MQTT_PASSWORD'] = ''  # 如果需要的話，填寫您的 MQTT 密碼
app.config['MQTT_KEEPALIVE'] = 60  # KeepAlive 週期，以秒為單位
app.config['MQTT_TLS_ENABLED'] = True  # 啟用 TLS 加密
app.config['MQTT_TLS_CA_CERTS'] = os.path.join(pathlib.Path(__file__).parent,'ca/my-ca.crt')
app.config['MQTT_TLS_VERSION']=5
mqtt = Mqtt(app)

mqtt_bp = Blueprint('mqtt_bp', __name__)

@mqtt_bp.route('/publish/<msg>')
def pub_my_msg(msg):
    if len(msg) == 0:
        abort(404)
    mqtt.publish('mytopic',msg )
    return msg

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    print('Connected with result code ' + str(rc))
    mqtt.subscribe('mytopic')

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')
    # 你可以在這裡處理接收到的消息，例如保存到數據庫或其他處理邏輯

# @mqtt.on_disconnect()
# def handle_disconnect(client, userdata, rc):
#     print('Disconnected with result code ' + str(rc))
