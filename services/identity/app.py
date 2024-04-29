from flask import request, render_template, abort
from flask import Blueprint
from linebot import LineBotApi, WebhookHandler, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from utlis import db

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

# 服務藍圖
identity_bp = Blueprint('identity_bp', __name__)

# Webhook 路由，用於處理 Line Bot 的事件
@identity_bp.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        events = handler.parse(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            # 處理接收到的文字訊息事件
            if event.message.text == '老摳摳':
                handle_old(event)
            elif event.message.text == '年輕的小夥子':
                handle_young(event)
    
    return 'OK'

def handle_old(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name
    
    # 在這裡處理老摳摳身份的相關邏輯
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO User (MemID, MemName) VALUES (%s, %s)', (user_id, user_name))
    cursor.execute('SELECT GroupID FROM Group where GroupID = %s', (data,))
    data = cursor.fetchone()
    conn.commit()
    conn.close()

def handle_young(event):
    user_id = event.source.user_id
    profile = line_bot_api.get_profile(user_id)
    user_name = profile.display_name
    
    # 在這裡處理年輕的小夥子身份的相關邏輯
    subno = request.form.get('SubUserID')  # 這裡可能需要修改，視你的需求而定
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO User (MemID, MemName) VALUES (%s, %s)', (user_id, user_name))
    cursor.execute('INSERT INTO GroupLink (SubUserID) VALUES (%s)', (subno,))
    conn.commit()
    conn.close()

# 選擇身分
@identity_bp.route('/identity', methods=['GET'])
def identity():
    return render_template('identity.html')

# 老摳摳
@identity_bp.route('/old', methods=['GET'])
def old():
    return render_template('old.html')

# 年輕的小夥子
@identity_bp.route('/young', methods=['GET'])
def young():
    return render_template('young.html')
