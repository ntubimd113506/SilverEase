import requests, json
import pymysql
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    # 回應使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請先在設定中設定您的基本資料！")
    )

#-----登入-----
@app.route('/identity')
def page():
    return render_template('identity.html', liffid = '2004699458-OR9pkZjP')

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    mtext = event.message.text
    if mtext == 'identity':
        message = TemplateSendMessage(
                alt_text='按鈕樣板',
                # template=ButtonsTemplate(
                #     thumbnail_image_url='https://i.imgur.com/4QfKuz1.png',  #顯示的圖片
                #     title='購買PIZZA',  #主標題
                #     text='請選擇：',  #副標題
                    actions=[
                        URITemplateAction(  #開啟網頁
                            label='連結網頁',
                            title='身分確認',
                            uri='https://liff.line.me/2004699458-OR9pkZjP',
                        ),
                    ]
                )
            # )
        
        try:
            line_bot_api.reply_message(event.reply_token, message)
        except:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text='發生錯誤！'))

if __name__ == "__main__":
    app.run()