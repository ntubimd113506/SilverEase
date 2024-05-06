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
@app.route('/identity/')
def page():
    return render_template('identity.html', liffid='2004699458-OR9pkZjP')

@app.route('/identity/oy' ,methods=['POST'])
def identity():
    if request.form.get('option') == 'old':
        #建立資料庫連線   
        conn = db.get_connection()
        cursor = conn.cursor()

        MemID = request.values.get('MemID')
        MemName = request.values.get('MemName')

        while 1:
            cursor.execute('SELECT FamilyID FROM Family where MainUserID = %s',(MemID))
            data = cursor.fetchone()
        
            if data!=None:
                break
            else:
                cursor.execute('INSERT INTO Member (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))
                conn.commit()

        conn.close()
        
        return  render_template('old.html',data=data)
    
    if request.form.get('option') == 'young':
        # 資料加入資料庫
        conn = db.get_connection()
        cursor = conn.cursor()

        MemID = request.values.get('MemID')
        MemName = request.values.get('MemName')

        cursor.execute('INSERT INTO Member (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))
        conn.commit()

        conn.close()
        return  render_template('young.html')

@app.route("/CodeID", methods=['POST'])
def CodeID():
    conn = db.get_connection()
    cursor = conn.cursor()

    CodeID = request.form.get('CodeID')  
    cursor.execute('INSERT INTO FamilyCode (CodeID) VALUES (%s)', (CodeID))

    conn.commit()
    conn.close()
    return  '新增完成'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    mtext = event.message.text
    if mtext == 'identity':
        message = TemplateSendMessage(
        alt_text='按鈕樣板',
        template=ButtonsTemplate(
            thumbnail_image_url='https://s.yimg.com/ny/api/res/1.2/68SLqFN3Qp1QopXUMrtSxQ--/YXBwaWQ9aGlnaGxhbmRlcjt3PTY0MDtoPTM4NA--/https://media.zenfs.com/zh-tw/commonhealth.com.tw/44dabbf75ca37b9876279e291ccf3a43',
            title='我的身分',
            text='請選擇：',
        actions=[
            URITemplateAction(
                label='連結網頁',
                title='身分確認',
                url='https://liff.line.me/2004699458-OR9pkZjP'
            ),
        ]
        )
     )
        
        try:
            line_bot_api.reply_message(event.reply_token, message)
        except:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text='發生錯誤！'))


if __name__ == "__main__":
    app.run(debug=1)