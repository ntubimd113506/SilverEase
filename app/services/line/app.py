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
    res = requests.post(f"{host}/LineMsgHandle",
                        json=json.loads(f"{event}"))
    result = res.json()
    print(result)
    if result["Type"] != False:
        memoType = result.pop("Type")
        params = urlencode(result)
        if memoType == "event":
            alt_txt = "新增活動"
            body_txt = "是不是有人提到活動!"

        if memoType == "hos":
            alt_txt = "新增看診"
            body_txt = "祝您身體健康早日康復!"

        if memoType == "sql":
            msg = sql_handle(result)
            line_bot_api.reply_message(
                event.reply_token, messages=FlexSendMessage(alt_text="您的未來行程", contents=msg))
            return

        print(params)

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


# @handler.add(MessageEvent, message=ImageMessage)
# def handle_image(event):
#     message_content = line_bot_api.get_message_content(event.message.id)
#     with open(f"app/static/{event.message.id}.jpg", "wb") as f:
#         for chunk in message_content.iter_content():
#             f.write(chunk)

#     line_bot_api.reply_message(
#         event.reply_token, TextSendMessage(text="已收到圖片，請稍後"))


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


def sql_handle(result):
    conn = db.get_connection()
    cur = conn.cursor()

    MemoType = {"hos": (2,), "event": (3,), "all": (2,3)}

    cur.execute("""
        SELECT
            *
        FROM
            `113-ntub113506`.Memo
        WHERE
            MemoTime BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL %s DAY)
                AND MemoType IN %s
                AND FamilyID IN (SELECT
                    FamilyID
                FROM
                    (SELECT
                        FamilyID, MainUserID AS UserID
                    FROM
                        Family UNION ALL SELECT
                        FamilyID, SubUserID AS UserID
                    FROM
                        FamilyLink) f
                WHERE
                    UserID IN (%s))
        """, (result["duration"], MemoType[result["SubType"]], result["UserID"]))

    memo_datas = []
    for res in cur.fetchall():
        memo_datas.append({cur.description[i][0]: res[i] for i in range(len(res))})

    # return memo_datas
    box_cnt = 0

    responMsg = {
        "type": "carousel",
        "contents": []
    }

    for memo in memo_datas:
        if box_cnt > 12:
            break
        elif memo["MemoType"] == '2':
            cur.execute("SELECT * FROM Hos WHERE MemoID=%s", memo["MemoID"])
            res = cur.fetchone()
            sub_memo = {cur.description[i][0]: res[i] for i in range(len(res))}

            responMsg["contents"].append({
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "size": "3xl",
                    "aspectRatio": "5:5",
                    "aspectMode": "cover",
                    "url": "https://silverease.ntub.edu.tw/static/imgs/treatment.png",
                    "margin": "none"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": "您未來的回診資料",
                            "wrap": True,
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "text",
                            "text": f"📌標題: {memo['Title']}"
                        },
                        {
                            "type": "text",
                            "text": f"🕰️時間: {memo['MemoTime']}"
                        },
                        {
                            "type": "text",
                            "text": f"📍地點: {sub_memo['Location']}"
                        },
                        {
                            "type": "text",
                            "text": f"🏥科別: {sub_memo['Clinic']}"
                        },
                        {
                            "type": "text",
                            "text": f"👨‍⚕️醫師: {sub_memo['Doctor']}"
                        },
                        {
                            "type": "text",
                            "text": f"🔢看診號碼: {sub_memo['Num']}"
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
                            "style": "primary",
                            "action": {
                                "type": "uri",
                                "label": "點我編輯或刪除",
                                "uri": f"https://liff.line.me/{db.LIFF_ID}/hos/update/confirm?MemoID={memo['MemoID']}"
                            }
                        }
                    ]
                }
            })
        elif memo["MemoType"] == '3':
            cur.execute("SELECT * FROM EventMemo WHERE MemoID=%s",
                        memo["MemoID"])
            res = cur.fetchone()
            sub_memo = {cur.description[i][0]: res[i] for i in range(len(res))}
            responMsg["contents"].append({
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "size": "3xl",
                    "aspectRatio": "5:5",
                    "aspectMode": "cover",
                    "url": "https://silverease.ntub.edu.tw/static/imgs/planner.png",
                    "margin": "none"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "text",
                            "text": "您未來的紀念日資料",
                            "wrap": True,
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "text",
                            "text": f"📌標題: {memo['Title']}"
                        },
                        {
                            "type": "text",
                            "text": f"🕰️時間: {memo['MemoTime']}"
                        },
                        {
                            "type": "text",
                            "text": f"📍地點: {sub_memo['Location']}"
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
                            "style": "primary",
                            "action": {
                                "type": "uri",
                                "label": "點我編輯或刪除",
                                "uri": f"https://liff.line.me/{db.LIFF_ID}/event/update/confirm?MemoID={memo['MemoID']}"
                            }
                        }
                    ]
                }
            })
        box_cnt += 1
    
    responMsg["contents"].append({
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "flex": 1,
                    "gravity": "center",
                    "action": {
                        "type": "uri",
                        "label": "看更多回診規劃",
                        "uri": f"https://liff.line.me/{db.LIFF_ID}/hos/list"
                    },
                    "style": "link",
                    "margin": "none"
                },
                {
                    "type": "text",
                    "text": "______________________",
                    "align": "center"
                },
                {
                    "type": "button",
                    "flex": 1,
                    "gravity": "center",
                    "action": {
                        "type": "uri",
                        "label": "看更多紀念日規劃",
                        "uri": f"https://liff.line.me/{db.LIFF_ID}/event/list"
                    },
                    "style": "link"
                }
            ]
        }
    })
    return responMsg