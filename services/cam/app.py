import requests, json
import datetime
import os
import pathlib
import filetype
from linebot.models import TextSendMessage, ImageSendMessage
from flask import Flask, flash, request, redirect, url_for, render_template, Blueprint
from utlis import db
cam_bp = Blueprint('cam_bp',__name__)

# 取得目前檔案所在的資料夾
SRC_PATH = pathlib.Path(__file__).parent.parent.parent.absolute()
UPLOAD_FOLDER = os.path.join(SRC_PATH, 'static', 'uploads')

# cam_bp.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# cam_bp.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

@cam_bp.route('/')
def index():
    return render_template('cam/index.html')

@cam_bp.route('/', methods=['POST'])
def upload_file():
    res = handle_file(request)

    if res['msg'] == 'ok':
        flash('影像上傳完畢！')
        return render_template('index.html', filename=res['filename'])
    elif res['msg'] == 'no_file':
        flash('沒有上傳檔案')

    return redirect(url_for('index'))  # 令瀏覽器跳回首頁

@cam_bp.route('/esp32cam', methods=['POST'])
def esp32cam():
    res = handle_file(request)
    sent_mess(res["filepath"])
    return res['msg']

def handle_file(request):
    if 'filename' not in request.files:
        return {"msg": 'no_file'}  # 傳回代表「沒有檔案」的訊息

    file = request.files['filename']  # 取得上傳檔

    if file.filename == '':
        return {"msg": 'empty'}       # 傳回代表「空白」的訊息

    if file:
        file_type = filetype.guess_extension(file)  # 判斷上傳檔的類型

        if file_type in ALLOWED_EXTENSIONS:
            file.stream.seek(0)
            # filename = secure_filename(file.filename)
            # 重新設定檔名：日期時間 + ‘.’ + ‘副檔名’
            filename = str(datetime.datetime.now()).replace(
                ':', '_') + '.' + file_type
            file.save(os.path.join(
                UPLOAD_FOLDER, filename
                ))
            # 傳回代表上傳成功的訊息以及檔名。
            filepath=os.path.join(
                UPLOAD_FOLDER, filename
                )
            return {"msg": 'ok', "filename": filename, "path": filepath}
        else:
            return {"msg": 'type_error'}  # 傳回代表「檔案類型錯誤」的訊息

def sent_mess(filepath):
    #取得資料庫連線
    conn = db.get_connection()

    #取得執行sql命令的cursor
    cursor = conn.cursor()  

    #取得傳入參數, 執行sql命令並取回資料
    DevID = request.values.get('DevID')

    cursor.execute('SELECT SubUserID FROM FamilyLink where FamilyID = (SELECT FamilyID FROM Family WHERE DevID=%s)', (DevID,))
    data = cursor.fetchall()

    conn.commit()
    conn.close()

    # 從資料庫檢索到的使用者資訊是一個列表，需要提取出每個使用者的 ID
    UserIDs = [row[0] for row in data]

    headers = {'Authorization':f'Bearer {db.LINE_TOKEN}','Content-Type':'application/json'}
    body = {
        'to':UserIDs,
        'messages':[{
                'type': 'text',
                'text': '緊急通知',
                'type': 'image',
                'image': filepath
            }]
        }
    # 向指定網址發送 request
    req = requests.request('POST', 'https://api.line.me/v2/bot/message/push',headers=headers,data=json.dumps(body).encode('utf-8'))
    # 印出得到的結果
    print(req.text)
    return "GOOD"

@cam_bp.route('/img/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='uploads/' + filename))
