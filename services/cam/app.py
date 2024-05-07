import datetime
import os
import pathlib
import filetype
from flask import Flask, flash, request, redirect, url_for, render_template, Blueprint
# from werkzeug.utils import secure_filename
cam_bp = Blueprint('cam_bp',__name__)

# 取得目前檔案所在的資料夾
SRC_PATH = pathlib.Path(__file__).parent.parent.parent.absolute()
UPLOAD_FOLDER = os.path.join(SRC_PATH, 'static', 'uploads')

app = Flask(__name__)
# app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
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
    elif res['msg'] == 'type_error':
        flash('僅允許上傳png, jpg, jpeg和gif影像檔')
    elif res['msg'] == 'empty':
        flash('請選擇要上傳的影像')
    elif res['msg'] == 'no_file':
        flash('沒有上傳檔案')

    return redirect(url_for('index'))  # 令瀏覽器跳回首頁


@cam_bp.route('/esp32cam', methods=['POST'])
def esp32cam():
    res = handle_file(request)
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
                app.config['UPLOAD_FOLDER'], filename
                ))
            # 傳回代表上傳成功的訊息以及檔名。
            return {"msg": 'ok', "filename": filename}
        else:
            return {"msg": 'type_error'}  # 傳回代表「檔案類型錯誤」的訊息


@cam_bp.route('/img/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename='uploads/' + filename))
