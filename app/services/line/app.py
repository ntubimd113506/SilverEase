import json
from flask import Blueprint, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from datetime import datetime
from utils import db
from services import scheduler,mqtt

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)
linebot_bp = Blueprint("linebot_bp", __name__)

@linebot_bp.route("/joblist")
def joblist():
    return f"{scheduler.get_jobs()}"


@linebot_bp.route("deletejob")
def deletejob():
    scheduler.remove_job("job123")
    return "OK"


@linebot_bp.route("/callback", methods=["POST"])
def callback():
    # 獲取 Line Bot 的 Webhook 請求
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    # 驗證簽名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):

#     # 獲取使用者的 ID
#     MemID = event.source.user_id

#     # if event.message.text=="收到":
#     #     mqtt.publish('ESP32/got', "OK")


@handler.add(PostbackEvent)
def handle_postback(event):
    data = json.loads(event.postback.data)
    
    try:
        job = scheduler.get_job(data["MemoID"])
        if data["got"] and job.next_run_time.strftime("%Y-%m-%dT%H:%M:%S") == data["time"]:
            scheduler.modify_job(
                data["MemoID"], args=[data["MemoID"], job.args[1], data["got"]]
            )
            # line_bot_api.reply_message(event.reply_token,TextSendMessage(text=f"data={job.next_run_time.strftime("%Y-%m-%dT%H:%M:%S")==data["time"]:}"))
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Respond (MemoID, Times, RespondTime)
                VALUES (%s, %s, %s)
                """,
                (data["MemoID"], job.args[1], datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
            conn.close()
    except:
        
        if data["action"]=="help":
            # line_bot_api.reply_message(event.reply_token,TextSendMessage(text=f"data={data["action"]=="help"}"))
            mqtt.publish('ESP32/got', "OK")
            res=mqtt.publish(f"ESP32/{data["DevID"]}/gotHelp","")
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=f"data={res}"))

@linebot_bp.route("/lineMqtt")
def mqttsent():
    mqtt.publish('ESP32/got', "OK")
    return "OK"