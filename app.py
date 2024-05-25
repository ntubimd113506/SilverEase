import requests, json
import pymysql
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from utils import db

app = Flask(__name__)

# 設定你的 Line Bot 的 Channel Access Token 
line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

# @app.route("/")
# def index():
#     return "Here is SilverEase"

@app.route('/')
def page():
    return render_template('index.html', liffid = '2004699458-a7DORnXp')

@app.route('/<what>')
def liff(what):
    return render_template("liff.html",what=what,liffid='2004699458-a7DORnXp')

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
    mtext = event.message.text
    if mtext == 'aaa':
        message = TemplateSendMessage(
                alt_text='按鈕樣板',
                template=ButtonsTemplate(
                    thumbnail_image_url='https://i.imgur.com/4QfKuz1.png',  #顯示的圖片
                    title='購買PIZZA',  #主標題
                    text='請選擇：',  #副標題
                    actions=[
                        URITemplateAction(  #開啟網頁
                            label='連結網頁',
                            uri='https://liff.line.me/2004699458-a7DORnXp',
                        ),
                    ]
                )
            )
        
        try:
            line_bot_api.reply_message(event.reply_token, message)
        except:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text='發生錯誤！'))



'''主動訊息傳送測試
@app.route("/sent")
def sent_mess():
    USER_LINE_ID='USER_LINE_ID'
    headers = {'Authorization':f'Bearer {db.LINE_TOKEN}','Content-Type':'application/json'}
    body = {
        'to':USER_LINE_ID,
        'messages':[{
                'type': 'text',
                'text': 'hello'
            }]
        }
    # 向指定網址發送 request
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',headers=headers,data=json.dumps(body).encode('utf-8'))
    # 印出得到的結果
    print(req.text)
    return "GOOD"
'''

if __name__ == "__main__":
    app.run()