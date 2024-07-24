import os, pathlib, requests, json
from PIL import Image
from io import BytesIO
from flask import Flask, Blueprint, abort
from flask_mqtt import Mqtt
from utils import db

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'silverease.ntub.edu.tw'  # 您的 MQTT 代理地址
app.config['MQTT_BROKER_PORT'] = 8883  # MQTT 代理端口
app.config['MQTT_USERNAME'] = ''  # 如果需要的話，填寫您的 MQTT 用戶名
app.config['MQTT_PASSWORD'] = ''  # 如果需要的話，填寫您的 MQTT 密碼
app.config['MQTT_KEEPALIVE'] = 1  # KeepAlive 週期，以秒為單位
app.config['MQTT_TLS_ENABLED'] = True  # 啟用 TLS 加密
app.config['MQTT_TLS_CA_CERTS'] = os.path.join(pathlib.Path(__file__).parent,'ca/my-ca.crt')
app.config['MQTT_TLS_VERSION']=5
app.config['MQTT_CLIENT_ID'] = 'flaskMQTT'
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
    mqtt.subscribe('myTopic')
    mqtt.subscribe('ESP32/#')

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    pass
    if message.topic == 'ESP32/help':
        print("ESP32 need help")
        print(f'Received message on topic {message.topic}: {message.payload.decode()}')
        try:
            data = json.loads(message.payload.decode())
            DevID = data['DevID']
            sent_mess(DevID)
            save_gps(DevID)

        except json.JSONDecodeError:
            print("Invalid JSON")
    if message.topic == 'ESP32/conn':
        print("ESP32 connected")
        print(f'Received message on topic {message.topic}: {message.payload.decode()}')

#------------------------------------------------------    
    if message.topic == 'ESP32/gps':
        try:
            data = message.payload.decode()
            Map = data
            print(f"Received GPS data - GoogleMap:{Map}")
            save_gps(Map)

        except :
            print("OK！")

def save_gps(Map):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO `113-ntub113506`.Location (Location) VALUES (%s)', (Map,))
        conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def sent_mess(DevID,filename=None):
    #取得資料庫連線
    conn = db.get_connection()

    #取得執行sql命令的cursor
    cursor = conn.cursor()  

    #取得傳入參數, 執行sql命令並取回資料
    # DevID = request.values.get('DevID')

    cursor.execute('SELECT SubUserID FROM FamilyLink where FamilyID = (SELECT FamilyID FROM Family WHERE DevID=%s)', (DevID))
    #cursor.execute('SELECT SubUserID FROM FamilyLink where FamilyID = (SELECT FamilyID FROM Family WHERE DevID="1")')

    data = cursor.fetchall()

    conn.commit()
    conn.close()

    # 從資料庫檢索到的使用者資訊是一個列表，需要提取出每個使用者的 ID
    UserIDs = [row[0] for row in data]
    print(UserIDs)

    # thumbnail_image_url=str("https://silverease.ntub.edu.tw/cam/img/" + filename).replace(" ","%20")
    headers = {'Authorization':f'Bearer {db.LINE_TOKEN_2}','Content-Type':'application/json'}
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
        req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',headers=headers,data=json.dumps(body).encode('utf-8'))
    # 印出得到的結果
        print(req.text)

    return True