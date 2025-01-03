import requests
import json
import base64
import os
from datetime import datetime
from linebot.models import *
from datetime import datetime, timedelta
from flask_mqtt import Mqtt
from utils import db
from ..line import app as line

mqtt = Mqtt()


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe("ESP32/#")


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    if message.topic=="ESP32/check":
        mqtt.publish("online","")
        return
    topic = str(message.topic).split("/")
    DevID = topic[1]
    action = topic[2]
    try:
        msg = message.payload.decode()
        try:
            data = json.loads(msg)
            # print(data)
        except:
            pass
        print(f"Received message on topic {message.topic}: {msg}")
    except:
        msg = message.payload

    if action == "help":
        # return
        sent_mess(DevID, msg)

    if action == "checkLink":
        if check_device(DevID):
            mqtt.publish(f"ESP32/{DevID}/isLink")
        else:
            mqtt.publish(f"ESP32/{DevID}/noLink")

    if action == "offline":
        sent_dev_offline(DevID)

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

# -----------------------------------------------------------
    if action == 'gps':
        Map = data["lat"]+","+data["lon"]
        timeData = data["sendTime"].split(",")
        getTime = datetime(int(timeData[0]), int(timeData[1]), int(
            timeData[2]), int(timeData[3]), int(timeData[4]), int(timeData[5]))
        getTime = getTime+timedelta(hours=8)
        print(f"Received GPS coordinates: {Map}")
        print(f"Received GPS time: {getTime}")
        upgrade_gps(DevID, Map, getTime)

    if action=="noSOSLocat":
        try:
            timeData=msg.split(",")
            getTime = datetime(int(timeData[0]), int(timeData[1]), int(
                timeData[2]), int(timeData[3]), int(timeData[4]), int(timeData[5]))
            getTime = getTime+timedelta(hours=8)
            # if timeData[0]=="2000":
            #     getTime=datetime.now()            
        except:
            getTime=datetime.now()

        upgrade_gps(DevID, "noData", getTime)


def sent_dev_offline(DevID):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT FamilyID FROM Family WHERE DevID=%s", DevID)
    FamilyID = cur.fetchone()[0]
    users = get_FamilyUser(FamilyID)

    msg = FlexSendMessage(
        alt_text="裝置離線通知",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://developers-resource.landpress.line.me/fx/img/01_1_cafe.png",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
                "action": {
                    "type": "uri",
                    "uri": "https://line.me/"
                }
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "裝置離線通知",
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "text",
                        "text": "偵測到您的裝置已離線\n請確認您的裝置網路或電力是否異常",
                        "wrap": True
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "點我了解更多",
                            "uri": "http://linecorp.com/"
                        }
                    }
                ]
            }
        }
    )

    UserIDs = [user for user in users["SubUser"]]
    UserIDs.append(users["MainUser"])

    for user in UserIDs:
        line.line_bot_api.push_message(user, msg)


def upgrade_gps(DevID, Map, getTime):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        FamilyID = check_device(DevID)
        cursor.execute(
            'INSERT INTO `113-ntub113506`.Location (FamilyID,Location,LocationTime) VALUES (%s,%s,%s)', (FamilyID, Map, getTime,))
        conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


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
    if not img == "noImage":
        filepath = os.path.abspath(__file__)
        for i in range(3):
            filepath = os.path.dirname(filepath)
        filepath = os.path.join(filepath, "static", "imgs", "upload", filename)
        with open(filepath, "wb") as f:
            f.write(img)

    FamilyID = check_device(DevID)
    users = get_FamilyUser(FamilyID)

    # 從資料庫檢索到的使用者資訊是一個列表，需要提取出每個使用者的 ID
    UserIDs = [row for row in users["SubUser"]]
    print(UserIDs)
    """
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT LocatNo,Location FROM Location WHERE FamilyID=%s AND LocationTime BETWEEN DATE_SUB(now(),Interval 5 minute) AND now() order by LocatNo desc limit 1", (FamilyID))
    res = cur.fetchone()
    LocatNo=res[0]
    gps = res[1]
    try:
        cur.execute("INSERT INTO SOS (LocatNo) Values(%s)", (LocatNo))
    except:
        pass
    cur.execute("SELECT SOSNo FROM SOS WHERE LocatNo=%s", LocatNo)
    SOSNo = cur.fetchone()[0]
    conn.commit()
    conn.close()
    """
    if "gps" == "noData":
        Map = f"https://liff.line.me/{db.LIFF_ID}/sos/gps/{FamilyID}"
    else:
        Map = f"https://www.google.com/maps/search/?api=1&query=22.997437839235964,120.21225550737789"

    thumbnail_image_url = f"https://silverease.ntub.edu.tw/img/SilverEase.png"
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
                            "data": json.dumps({"action": "help", "DevID": DevID, "SOSNo": "123"}),
                            "text": "已通知長者"
                        },
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "定位資訊",
                            "uri": Map,
                        },
                    },
                ],
                "flex": 0,
            },
        },
    )

    try:
        for userID in UserIDs:
            line.line_bot_api.push_message(userID, resMsg)
    except:
        mqtt.publish("linePushFaild","")