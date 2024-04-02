import tempfile, os, datetime, time, serial
from flask import Flask, request, abort

# ======這裡是呼叫的檔案內容=====
from utlis.message import *
from utlis.new import *
from utlis.function import *
from utlis.lineToken import *

app = Flask(__name__)
# static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

@app.route("/")
def index():
    return "hello SilverEase"


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


"""
serial_port = 'COM3'  # 請根據你的系統及 Arduino 連接埠進行調整
baudrate = 9600
ser = serial.Serial(serial_port, baudrate, timeout=1)
def handle_message(event):
    # 接收使用者傳送的訊息
    user_message = event.message.text
    
    # 回傳相同的訊息給使用者
    # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=user_message))
    print("已接收")
    
    # 將訊息傳送到 Arduino 顯示
    send_to_arduino(user_message)

# 將訊息傳送到 Arduino 的函式
def send_to_arduino(user_message):
    # 將訊息轉為位元組並傳送到 Arduino
    ser.write(user_message.encode())
"""

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if '最新合作廠商' in msg:
        message = imagemap_message()
        line_bot_api.reply_message(event.reply_token, message)
    elif '最新活動訊息' in msg:
        message = buttons_message()
        line_bot_api.reply_message(event.reply_token, message)
    elif '註冊會員' in msg:
        message = Confirm_Template()
        line_bot_api.reply_message(event.reply_token, message)
    elif '旋轉木馬' in msg:
        message = Carousel_Template()
        line_bot_api.reply_message(event.reply_token, message)
    elif '圖片畫廊' in msg:
        message = test()
        line_bot_api.reply_message(event.reply_token, message)
    elif '功能列表' in msg:
        message = function_list()
        line_bot_api.reply_message(event.reply_token, message)


# @handler.add(PostbackEvent)
# def handle_message(event):
#     print(event.postback.data)


# @handler.add(MemberJoinedEvent)
# def welcome(event):
#     uid = event.joined.members[0].user_id
#     gid = event.source.group_id
#     profile = line_bot_api.get_group_member_profile(gid, uid)
#     name = profile.display_name
#     message = TextSendMessage(text=f'{name}歡迎加入')
#     line_bot_api.reply_message(event.reply_token, message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
