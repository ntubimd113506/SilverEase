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
    mqtt.subscribe("myTopic")
    mqtt.subscribe("ESP32/#")
    mqtt.subscribe("/SOSgps")


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    topic = str(message.topic).split("/")
    DevID = topic[1]
    action = topic[2]
    try:
        msg = message.payload.decode()
        try:
            data = json.loads(msg)
        except:
            pass
        print(f"Received message on topic {message.topic}: {msg}")
    except:
        msg = message.payload    

    if action == "help":
        sent_mess(DevID,msg)

    if action == "checkLink":
        if check_device(DevID):
            mqtt.publish(f"ESP32/{DevID}/isLink")
        else:
            mqtt.publish(f"ESP32/{DevID}/noLink")

    if action=="offline":
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

#-----------------------------------------------------------
    if action == 'gps':
        try:
            data = message.payload.decode()
            Map1 = str(data)
        
            # 找到 'query=' 字串的位置並提取其後的座標部分
            Map = Map1.split("query=")[-1]

            print(f"Received GPS coordinates: {Map}")
            upgrade_gps(Map)

        except Exception as e:
            print("Error:", str(e))

    if message.topic == '/upGPS':
        try:
            data = message.payload.decode()
            Map1 = str(data)
            
            # 找到 'query=' 字串的位置並提取其後的座標部分
            Map = Map1.split("query=")[-1]

            print(f"Received GPS coordinates: {Map}")
            upgrade_gps(Map)

        except Exception as e:
            print("Error:", str(e))

    
    if message.topic == '/SOSgps':
        try:
            data = message.payload.decode()
            Map1 = str(data)
        
            # 找到 'query=' 字串的位置並提取其後的座標部分
            Map = Map1.split("query=")[-1]

            print(f"Received GPS coordinates: {Map}")
            upgrade_gps(Map)

        except Exception as e:
            print("Error:", str(e))

def sent_dev_offline(DevID):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT FamilyID FROM Family WHERE DevID=%s", DevID)
    FamilyID = cur.fetchone()[0]
    user = get_FamilyUser(FamilyID)

    msg=FlexSendMessage()
        
    UserIDs = [row for row in user["SubUser"]]


def save_gps(Map):
    conn = db.get_connection()
    cursor = conn.cursor()
    # cursor1 = conn.cursor()
    try:
        now = datetime.now()
        # cursor1.execute('SELECT FamilyID FROM Family WHERE DevID = %s',(DevID))
        # FamID=cursor1.fetchone()[0]
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
    # cursor1 = conn.cursor()
    try:
        now = datetime.now()
        # cursor1.execute('SELECT FamilyID FROM Family WHERE DevID = %s',(DevID))
        # FamID=cursor1.fetchone()[0]
        cursor.execute('INSERT INTO `113-ntub113506`.Location (FamilyID,Location,LocationTime) VALUES (%s,%s,%s)', (54,Map,now,))
        conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    
def sos_gps(Map):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        FamID = 54
        now = datetime.now()

        # 插入地理位置資料
        cursor.execute('INSERT INTO `113-ntub113506`.Location (FamilyID, Location, LocationTime) VALUES (%s, %s, %s)', (FamID, Map, now))
        conn.commit()

        # 獲取最新的 LocatNo
        cursor.execute("SELECT LocatNo FROM Location WHERE FamilyID=%s ORDER BY LocatNo DESC LIMIT 1", (FamID,))
        LocatNo = cursor.fetchone()[0]

        # 插入 SOS 記錄
        cursor.execute('INSERT INTO `113-ntub113506`.SOS (LocatNo) VALUES (%s)',(LocatNo,))
        conn.commit()

        # 獲取所有的 SubUserID
        cursor.execute('SELECT SubUserID FROM `113-ntub113506`.FamilyLink WHERE FamilyID = %s', (FamID,))
        Sub = cursor.fetchall()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

    # 緊急通知訊息
    thumbnail_image_url = "https://silverease.ntub.edu.tw/static//imgs/help.png"
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
                            "data": json.dumps({"action": "help"}),
                            "text": "你按ㄌ",
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

    # 推送訊息給所有 SubUserID
    for user in Sub:
        line.line_bot_api.push_message(user[0], resMsg)



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
        filepath = os.path.join("app", "static", "imgs", "upload", filename)
        with open(filepath, "wb") as f:
            f.write(img)

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
    conn.commit()
    SOSNo=cur.fetchone()[0]
    #Map
    cur.execute("SELECT Location FROM Location WHERE LocatNo=%s",(LocatNo))
    Map=cur.fetchone()[0]



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
                            "uri": Map,
                        },
                    },
                ],
                "flex": 0,
            },
        },
    )

    for userID in UserIDs:
        line.line_bot_api.push_message(userID, resMsg)

    return True


