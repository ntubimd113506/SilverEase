import requests, json
import pymysql
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from utlis import db

# from services.identity.app import identity_bp

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

#選擇身分
@app.route('/identity', methods=['GET'])
def identity():
    return render_template('identity.html') 


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    # 回應使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請先在設定中設定您的基本資料！")
    )

    @old.route('/old', methods=['GET'])
    def old():
        # 獲取使用者的 ID
        MemID = event.source.user_id

        # 獲取使用者的資訊，包括名稱
        profile = line_bot_api.get_profile(MemID)
        MemName = profile.display_name

        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO User (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))

        #取出MainUserID
        cursor.execute('SELECT GroupID FROM Group where GroupID = MemID')

        #取出資料
        data = cursor.fetchone()
        print(data)

        conn.commit()
        conn.close()
        return render_template('old.html')


    @young.route('/young', methods=['GET'])
    def young():
        MemID = event.source.user_id

        # 獲取使用者的資訊，包括名稱
        profile = line_bot_api.get_profile(MemID)
        MemName = profile.display_name

        try:
            #取得其他參數
            subno = request.form.get('SubUserID')
        
        finally:
            print(subno)


        #資料加入資料庫
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO User (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))

        #新增長輩編號
        cursor.execute('INSERT INTO GroupLink (SubUserID) VALUES (%s)', (subno))

        conn.commit()
        conn.close()
        return render_template('young.html') 


if __name__ == '__main__':
    app.run()