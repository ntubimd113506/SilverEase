from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 設定你的 Line Bot 的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi('vzDtwf8h7fEZRRmzj4VimopZL0+T1YKif982hzSdorxlLoebj3pj/4FwFipwinhCz87gKYDRvwvWmsU5FJ+0LOhywd+LFkFSopjeArMGhyoDtH823BhMCOUxc0WVSPIfuDwNWbLCemZtEz88kCJhSQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('1d16422c3b78ca6b26335a808c5258b2')

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 獲取使用者的 ID
    user_id = event.source.user_id
    # 回應使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="你的使用者 ID 是：" + user_id)
    )

if __name__ == "__main__":
    app.run()
