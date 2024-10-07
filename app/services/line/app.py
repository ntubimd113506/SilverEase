import json
import requests
from urllib.parse import urlencode
from flask import Blueprint, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from datetime import datetime, timedelta
from utils import db
from services import scheduler
from services.ollama.app import host
from ..mqtt import app as MQTT

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)
linebot_bp = Blueprint("linebot_bp", __name__)

mqtt = MQTT.mqtt


@linebot_bp.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(PostbackEvent)
def handle_postback(event):
    data = json.loads(event.postback.data)

    try:
        job_id = f"{data['MemoID']}_{data['time_type']}"
        job = scheduler.get_job(job_id)

        if (
            data["got"]
            and job
            and job.next_run_time.strftime("%Y-%m-%dT%H:%M:%S") == data["time"]
        ):
            scheduler.modify_job(
                job_id,
                args=[data["MemoID"], job.args[1],
                      data["got"], data["time_type"]],
            )

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Respond (MemoID, Times, RespondTime)
                VALUES (%s, %s, %s)
                """,
                (
                    data["MemoID"],
                    job.args[1],
                    datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                ),
            )
            conn.commit()
            conn.close()

    except:
        if data.get("action") == "help":
            mqtt.publish(f"ESP32/{data['DevID']}/gotHelp", "")
            scheduler.add_job(
                id=data["DevID"],
                func=report_SOS,
                args=[data["DevID"], data["SOSNo"]],
                trigger="date",
                run_date=datetime.now() + timedelta(minutes=5),
            )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(event)
    res = requests.post(f"{host}/LineMsgHandle",
                        json=json.loads(f"{event}"))
    result = res.json()
    if result["Type"] != False:
        memoType = result.pop("Type")
        params = urlencode(result)
        if memoType == "event":
            alt_txt = "新增活動"
            body_txt = "是不是有人提到活動!"

        if memoType == "hos":
            alt_txt = "新增看診"
            body_txt = "祝您身體健康早日康復!"

        print(params)
        print(memoType)
        print(alt_txt)
        print(body_txt)

        line_bot_api.reply_message(
            event.reply_token, messages=FlexSendMessage(
                alt_text=alt_txt,
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
                                "text": body_txt,
                                "weight": "bold",
                                "size": "xl"
                            }
                        ]
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
                                    "label": "來新增一下吧",
                                    "uri": f"https://liff.line.me/{db.LIFF_ID}/{memoType}/create/form?{params}"
                                }
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [],
                                "margin": "sm"
                            }
                        ],
                        "flex": 0
                    }
                },
            )
        )


def report_SOS(DevID, SOSNo):
    msg = FlexSendMessage(
        alt_text="求救事件追蹤",
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "求救事件追蹤",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "為更了解居家危險因子，\n請協助填寫來打造更好的居家環境",
                                "wrap": True,
                            }
                        ],
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
                            "label": "填寫表單",
                            "uri": f"https://liff.line.me/{db.LIFF_ID}/sos/sos_report/{SOSNo}",
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

    FamilyID = check_device(DevID)

    if FamilyID:
        cursor = db.get_connection().cursor()
        cursor.execute(
            "SELECT SubUserID FROM FamilyLink WHERE FamilyID=%s", FamilyID)

        for SubUserID in cursor.fetchall():
            line_bot_api.push_message(SubUserID[0], msg)


def check_device(DevID):
    conn = db.get_connection()
    cur = conn.cursor()
    res = cur.execute("SELECT FamilyID FROM Family WHERE DevID=%s", DevID)
    return cur.fetchone()[0] if res else 0
