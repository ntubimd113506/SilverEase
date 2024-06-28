from flask import Blueprint, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from utils import db    
from services import scheduler

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)
linebot_bp = Blueprint('linebot_bp', __name__)


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


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    # 獲取使用者的 ID
    MemID = event.source.user_id

    # if event.message.text=="收到":
    #     mqtt.publish('ESP32/got', "OK")
