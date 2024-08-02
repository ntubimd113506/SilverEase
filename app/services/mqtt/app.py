import json
import base64
import os
from datetime import datetime
from linebot.models import *
from flask_mqtt import Mqtt
from utils import db
from ..line import app as line


mqtt = Mqtt()


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe("myTopic")
    mqtt.subscribe("ESP32/#")


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    topic = str(message.topic).split("/")
    DevID = topic[1]
    action = topic[2]
    msg = message.payload.decode()
    try:
        data = json.loads(msg)
    except:
        pass

    print(f"Received message on topic {message.topic}: {message.payload.decode()}")

    if action == "help":
        try:
            data = json.loads(msg)
            img = data["image"]
            # gps=data["gps"]
            sent_mess(DevID, img)

        except json.JSONDecodeError:
            print("Invalid JSON")

    if action == "checkLink":
        if check_device(DevID):
            mqtt.publish(f"ESP32/{DevID}/isLink")

    if action == "link":
        FamilyID = decode_FamilyCode(msg)
        if FamilyID:
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE Family SET DevID=%s WHERE FamilyID=%s
                """,
                (DevID, FamilyID),
            )
            conn.commit()
            conn.close()

            reMsg = FlexSendMessage(
                alt_text="綁定成功",
                contents={
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": "https://silverease.ntub.edu.tw/static/imgs/S_create.png",
                        "size": "full",
                        "aspectRatio": "20:15",
                        "aspectMode": "cover",
                        "action": {
                            "type": "uri",
                            "label": "action",
                            "uri": "https://silverease.ntub.edu.tw",
                        },
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "綁定成功",
                                "weight": "bold",
                                "size": "xl",
                                "align": "center",
                            }
                        ],
                    },
                },
            )
            user = get_FamilyUser(FamilyID)["MainUser"]
            print(user)
            line.line_bot_api.push_message(user, reMsg)

def get_FamilyUser(FamilyID):
    data = {}

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MainUserID FROM Family WHERE FamilyID=%s", FamilyID)
    res = cur.fetchone()
    data["MainUser"] = res[0]

    cur.execute("SELECT SubUserID FROM FamilyLink WHERE FamilyID=%s", FamilyID)
    data["SubUser"] = [k[0] for k in cur.fetchall()]
    return data


def decode_FamilyCode(FamilyCode):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT FamilyID FROM FamilyCode WHERE CodeID=%s", FamilyCode)
    return (
        cur.fetchone()[0]
        if cur.execute("SELECT FamilyID FROM FamilyCode WHERE CodeID=%s", FamilyCode)
        else 0
    )


def check_device(DevID):
    conn = db.get_connection()
    cur = conn.cursor()
    res = cur.execute("SELECT FamilyID FROM Family WHERE DevID=%s", DevID)
    return cur.fetchone()[0] if res else 0


def sent_mess(DevID, img):
    filename = f"{DevID}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
    if not img == "":
        imgdata = base64.b64decode(img)
        filepath = os.path.join("app", "static", "imgs", "upload", filename)
        with open(filepath, "wb") as f:
            f.write(imgdata)

    FamilyID=check_device(DevID)
    users = get_FamilyUser(FamilyID)

    # 從資料庫檢索到的使用者資訊是一個列表，需要提取出每個使用者的 ID
    UserIDs = [row for row in users["SubUser"]]
    print(UserIDs)
    
    conn=db.get_connection()
    cur=conn.cursor()
    cur.execute('INSERT INTO `113-ntub113506`.Location (FamilyID) VALUES (%s)', (FamilyID))
    cur.execute("SELECT LocatNo FROM Location WHERE FamilyID=%s order by LocatNo desc limit 1",(FamilyID))
    LocatNo=cur.fetchone()[0]
    cur.execute("INSERT INTO SOS (LocatNo) Values(%s)",(LocatNo))
    cur.execute("SELECT SOSNo FROM SOS WHERE LocatNo=%s",LocatNo)
    SOSNo=cur.fetchone()[0]

    thumbnail_image_url = f"https://silverease.ntub.edu.tw/img/{filename}"
    resMsg = FlexSendMessage(
        alt_text="緊急通知",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": thumbnail_image_url,
                "size": "full",
                "aspectRatio": "20:15",
                "aspectMode": "cover",
                "action": {"type": "uri", "uri": thumbnail_image_url},
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "緊急通知",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                    }
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
                            "type": "postback",
                            "label": "收到",
                            "data": json.dumps({"action": "help", "DevID": DevID, "SOSNo": SOSNo}),
                            "text":"你按ㄌ"
                        },
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "定位資訊",
                            "uri": "https://silverease.ntub.edu.tw",
                        },
                    },
                ],
                "flex": 0,
            },
        },
    )

    line.line_bot_api.push_message(users["MainUser"], resMsg)
    # for userID in UserIDs:
    #     line.line_bot_api.push_message(userID, resMsg)

    return True
