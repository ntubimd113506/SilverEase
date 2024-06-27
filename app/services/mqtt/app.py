import requests
import json
import os
from PIL import Image
from io import BytesIO
from flask import Flask, abort
from flask_mqtt import Mqtt
from utils import db
from utils.mqtt import mqtt


class Config:
    MQTT_BROKER_URL = 'silverease.ntub.edu.tw'  # 您的 MQTT 代理地址
    MQTT_BROKER_PORT = 8883  # MQTT 代理端口
    MQTT_USERNAME = ''  # MQTT 用戶名
    MQTT_PASSWORD = ''  # MQTT 密碼
    MQTT_KEEPALIVE = 60  # KeepAlive 週期，以秒為單位
    MQTT_TLS_ENABLED = True  # 啟用 TLS 加密
    MQTT_TLS_CA_CERTS = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'ca', 'my-ca.crt')
    MQTT_TLS_VERSION = 5
    MQTT_CLIENT_ID = 'flask_mqtt'


app = Flask(__name__)
app.config.from_object(Config())
mqtt = Mqtt(app)


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('myTopic')
    mqtt.subscribe('ESP32/#')


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print(
        f'Received message on topic {message.topic}: {message.payload.decode()}')
    if message.topic == 'ESP32/help':
        print("ESP32 need help")
        print(
            f'Received message on topic {message.topic}: {message.payload.decode()}')
        try:
            data = json.loads(message.payload.decode())
            DevID = data['DevID']
            sent_mess(DevID)

        except json.JSONDecodeError:
            print("Invalid JSON")
    if message.topic == 'ESP32/conn':
        print("ESP32 connected")
        print(
            f'Received message on topic {message.topic}: {message.payload.decode()}')


def sent_mess(DevID, filename=None):
    # 取得資料庫連線
    conn = db.get_connection()

    # 取得執行sql命令的cursor
    cursor = conn.cursor()

    # 取得傳入參數, 執行sql命令並取回資料
    # DevID = request.values.get('DevID')

    cursor.execute(
        'SELECT SubUserID FROM FamilyLink where FamilyID = (SELECT FamilyID FROM Family WHERE DevID=%s)', (DevID))
    # cursor.execute('SELECT SubUserID FROM FamilyLink where FamilyID = (SELECT FamilyID FROM Family WHERE DevID="1")')

    data = cursor.fetchall()

    conn.commit()
    conn.close()

    # 從資料庫檢索到的使用者資訊是一個列表，需要提取出每個使用者的 ID
    UserIDs = [row[0] for row in data]
    print(UserIDs)

    # thumbnail_image_url=str("https://silverease.ntub.edu.tw/cam/img/" + filename).replace(" ","%20")
    headers = {'Authorization': f'Bearer {db.LINE_TOKEN_2}',
               'Content-Type': 'application/json'}
    # res = requests.get(url=thumbnail_image_url, stream=True)
    # try:
    #     with Image.open(BytesIO(res.content)) as img:
    #         img.load()
    # except:
    thumbnail_image_url = "https://silverease.ntub.edu.tw/cam/img/Fail.jpg"

    for userID in UserIDs:

        body = {
            'to': userID,
            "messages": [
                {
                    "type": "template",
                    "altText": "緊急通知!!!",
                    "template": {
                        "type": "buttons",
                        "thumbnailImageUrl": thumbnail_image_url,
                        "imageAspectRatio": "rectangle",
                        "imageSize": "cover",
                        "imageBackgroundColor": "#FFFFFF",
                        "title": "緊急通知",
                        "text": "是否收到",
                        "defaultAction": {
                            "type": "uri",
                            "label": "View detail",
                            "uri": thumbnail_image_url
                        },
                        "actions": [
                            {
                                "type": "message",
                                "label": "收到",
                                "text": "收到"
                            }
                        ]
                    }
                }
            ]
        }

    # 向指定網址發送 request
        req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',
                               headers=headers, data=json.dumps(body).encode('utf-8'))
    # 印出得到的結果
        print(req.text)

    return True
