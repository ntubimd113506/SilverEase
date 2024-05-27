from flask import Flask, request, abort, render_template, redirect, url_for, session
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from utils import db
from services.med.app import med_bp
from services.hos.app import hos_bp
from services.event.app import event_bp
from services.cam.app import cam_bp
from services.set.app import set_bp

app = Flask(__name__)

app.register_blueprint(med_bp, url_prefix="/med")
app.register_blueprint(hos_bp, url_prefix="/hos")
app.register_blueprint(event_bp, url_prefix="/event")
app.register_blueprint(cam_bp, url_prefix="/cam")
app.register_blueprint(set_bp, url_prefix="/set")

# 設定你的 Line Bot 的 Channel Access Token
line_bot_api = LineBotApi(db.LINE_TOKEN_2)
handler = WebhookHandler(db.LINE_HANDLER_2)


@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


@app.route("/callback", methods=["POST"])
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

    # 回應使用者
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text="請先在設定中設定您的基本資料！")
    )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    mtext = event.message.text
    if mtext == "identity":
        message = TemplateSendMessage(
            alt_text="按鈕樣板",
            template=ButtonsTemplate(
                thumbnail_image_url="https://s.yimg.com/ny/api/res/1.2/68SLqFN3Qp1QopXUMrtSxQ--/YXBwaWQ9aGlnaGxhbmRlcjt3PTY0MDtoPTM4NA--/https://media.zenfs.com/zh-tw/commonhealth.com.tw/44dabbf75ca37b9876279e291ccf3a43",
                title="我的身分",
                text="請選擇：",
                actions=[
                    URITemplateAction(
                        label="連結網頁",
                        title="身分確認",
                        url="https://liff.line.me/2004699458-OR9pkZjP",
                    ),
                ],
            ),
        )

        try:
            line_bot_api.reply_message(event.reply_token, message)
        except:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="發生錯誤！")
            )


if __name__ == "__main__":
    app.run(debug=1)
