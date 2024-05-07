import requests, json
import sqlite3
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from utlis import db
from services.event.app import event_bp
from services.cam.app import cam_bp

app = Flask(__name__)

# 設定你的 Line Bot 的 Channel Access Token 
line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

@app.route("/")
def index():
    return "Here is SilverEase"

app.register_blueprint(event_bp, url_prefix='/event')
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
    user_id = event.source.user_id

    # 獲取使用者的資訊，包括名稱
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name

    # 將使用者資料加入資料庫
    add_user_to_database(user_id, user_name)

    # 回應使用者，包括使用者名稱和 ID
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="你好，{}！你的使用者 ID 是：{}".format(user_name, user_id))
    )

def add_user_to_database(user_id, user_name):
    # 連接到 SQLite 資料庫
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()

    # 定義 SQL 指令，插入使用者資料
    sql = '''INSERT OR REPLACE INTO Users (MemID, MemName) VALUES (?, ?)'''
    data = (user_id, user_name)

    # 執行 SQL 指令
    cursor.execute(sql, data)

    # 儲存變更
    conn.commit()

    # 關閉資料庫連線
    conn.close()

# @handler.add(MessageEvent, message=TextMessage)
# def add_user_to_database(MemID, MemName, event):

#     MemID = event.source.user_id
#     profile = line_bot_api.get_profile(MemID)
#     MemName = profile.display_name

#     # 連接到 SQLite 資料庫
#     conn = db.get_connection()

#     # 定義 SQL 指令，插入使用者資料
#     cursor = conn.cursor()
#     cursor.execute("INSERT INTO User (MemID, MemName) VALUES (%s, %s)",
#                 (MemID, MemName))

#     # 儲存變更
#     conn.commit()

#     # 關閉資料庫連線
#     conn.close()

#     # 回應使用者，包括使用者名稱
#     line_bot_api.reply_message(
#         event.reply_token,
#         TextSendMessage(text="你好，{}！你的使用者 ID 是：{}".format(MemID, MemName))
#     )



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