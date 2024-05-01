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
        actions=[
                PostbackTemplateAction(  # 按鈕回傳動作
                    label='我是長輩',
                    data='old'
                ),
                PostbackTemplateAction(  # 按鈕回傳動作
                    label='我是年輕人',
                    data='young',
                    uri='https://liff.line.me/2004699458-OR9pkZjP'
                )
            ]
        )
        if event.postback.data == 'old':
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                # 獲取使用者的資訊，包括名稱
                MemID = event.source.user_id
                profile = line_bot_api.get_profile(MemID)
                MemName = profile.display_name
                cursor.execute('INSERT INTO User (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))

                #取出MainUserID
                cursor.execute('SELECT GroupID FROM Group where GroupID = MemID')

                #取出資料
                data = cursor.fetchone()
                print(data)

                conn.commit()
                conn.close()

                line_bot_api.reply_message(event.MemID, TextSendMessage(text="資料已成功加入資料庫！"))
            except Exception as e:
                # 處理資料庫操作異常
                print("An error occurred:", e)
                line_bot_api.reply_message(event.MemID, TextSendMessage(text="資料加入資料庫時發生錯誤！"))

        elif event.postback.data == 'young':
                conn = db.get_connection()
                cursor = conn.cursor()
                # 獲取使用者的資訊，包括名稱
                MemID = event.source.user_id
                profile = line_bot_api.get_profile(MemID)
                MemName = profile.display_name
                try:
                    #取得其他參數
                    subno = request.form.get('SubUserID')
                    
                finally:
                    print(subno)
                cursor.execute('INSERT INTO User (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))
                #新增長輩編號
                cursor.execute('INSERT INTO GroupLink (SubUserID) VALUES (%s)', (subno))
        
        try:
            line_bot_api.reply_message(event.reply_token, message)
        except:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text='發生錯誤！'))


if __name__ == "__main__":
    app.run()