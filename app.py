from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from utils import db
# from services.event.app import event_bp
from services.cam.app import cam_bp
from services.mqtt.app import mqtt_bp,mqtt

app = Flask(__name__)

# 設定你的 Line Bot 的 Channel Access Token 
line_bot_api = LineBotApi(db.LINE_TOKEN_2)
handler = WebhookHandler(db.LINE_HANDLER_2)

@app.route("/")
def index():
    return "Here is SilverEase"

# app.register_blueprint(event_bp, url_prefix='/event')
app.register_blueprint(mqtt_bp, url_prefix='/mqtt')
app.register_blueprint(cam_bp, url_prefix='/cam')

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
    MemID = event.source.user_id

    if event.message.text=="收到":
        mqtt.publish('myTopic',MemID )

    # 回應使用者，包括使用者名稱
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     TextSendMessage(text="你好，{}！你的使用者 ID 是：{}".format(MemName, MemID))
    # )

if __name__ == "__main__":
    app.run(debug=1)