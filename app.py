import requests, json
import pymysql
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ConfirmTemplate, MessageAction
from utlis import db


app = Flask(__name__)

# 設定你的 Line Bot 的 Channel Access Token 
line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

@app.route("/")
def index():
    return "Here is SilverEase"

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 Line Bot 的 Webhook 請求
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    # 驗證簽名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

alt_text='ConfirmTemplate',
template=ConfirmTemplate(
        ext='設定',
        actions=[
            MessageAction(
                label='好喔',
                text='好喔'
            ),
            MessageAction(
                label='好喔',
                text='不好喔'
            )
        ]
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    MemID = event.source.user_id

    # 獲取使用者的資訊，包括名稱
    profile = line_bot_api.get_profile(MemID)
    MemName = profile.display_nam

    # 回應使用者
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     TextSendMessage(text="請先在設定中設定您的基本資料！")
    # )

if __name__ == "__main__":
    app.run()