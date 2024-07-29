import requests
import json
from datetime import datetime, timedelta
from flask_mqtt import Mqtt
from utils import db


mqtt = Mqtt()


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('myTopic')
    mqtt.subscribe('ESP32/#')


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')
    if message.topic == 'ESP32/help':
        print("ESP32 need help")
        print(f'Received message on topic {message.topic}: {message.payload.decode()}')
        try:
            data = json.loads(message.payload.decode())
            DevID = data['DevID']
            sent_mess(DevID)

        except json.JSONDecodeError:
            print("Invalid JSON")
    if message.topic == 'ESP32/conn':
        print("ESP32 connected")
        print(f'Received message on topic {message.topic}: {message.payload.decode()}')

#-----------------------------------------------------------
    if message.topic == 'ESP32/gps':
            try:
                data = message.payload.decode()
                Map1 = str(data)
                Map = Map1.replace(" ","")
                print(f"Received GPS data - GoogleMap:{Map}")
                save_gps(Map)

            except :
                print("OK！")

    if message.topic == '/upGPS':
            try:
                data = message.payload.decode()
                Map1 = str(data)
                Map = Map1.replace(" ","")
                print(f"Received GPS data - GoogleMap:{Map}")
                upgrade_gps(Map)

            except :
                print("OK！")

def save_gps(Map):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        now = datetime.now()
        cursor.execute('INSERT INTO `113-ntub113506`.Location (FamilyID,Location,LocationTime) VALUES (%s,%s,%s)', (54,Map,now,))
        conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def upgrade_gps(Map):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor1 = conn.cursor()

    try:
        now = datetime.now()
        cursor1.execute('SELECT SubUserID FROM FamilyLink WHERE FamilyID = %s', (54))
        sub1 = cursor1.fetchone()
        sub = sub1[0]
        cursor.execute('INSERT INTO `113-ntub113506`.Location (FamilyID,Location,LocationTime) VALUES (%s,%s,%s)', (54,Map,now,))
        conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


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
