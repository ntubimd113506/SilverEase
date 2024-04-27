from flask import request, render_template
from flask import Blueprint
from linebot import LineBotApi, WebhookHandler
from utlis import db

# 服務藍圖
identity_bp = Blueprint('identity_bp', __name__)

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

#選擇身分
@identity_bp.route('/identity')
def identity():
    return render_template('identity.html') 

#老摳摳
@identity_bp.route('/old', methods=['GET'])
def old():
    if request.headers.get('Content-Type') == 'application/json':
        # 解析 JSON 格式的請求主體
        payload = request.json

        # 確認是否成功解析JSON數據
        if payload and 'events' in payload:
            events = payload['events']

            # 遍歷每個事件
            for event in events:
                # 提取用戶 ID
                MemID= event.get('source', {}).get('userId')
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


#年輕的小夥子
@identity_bp.route('/young', methods=['GET'])
def young():
    if request.headers.get('Content-Type') == 'application/json':
        # 解析 JSON 格式的請求主體
        payload = request.json

        # 確認是否成功解析JSON數據
        if payload and 'events' in payload:
            events = payload['events']

            # 遍歷每個事件
            for event in events:
                # 提取用戶 ID
                MemID= event.get('source', {}).get('userId')
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
