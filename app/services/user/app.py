# 匯入模組
import requests
from flask import Blueprint, render_template, request, session, jsonify,url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user 
from flask import Blueprint

from utils import db

# 產生使用者服務藍圖
user_bp = Blueprint('user_bp', __name__)

#---------------------------
# (登入管理)使用者的類別
#---------------------------
class User(UserMixin):
    def __init__(self, id):
        self.id = id
        
#---------------------------
# (登入管理)產生一個管理者
#---------------------------
login_manager = LoginManager()

#------------------------------
# (登入管理)取出登入者物件
#------------------------------
@login_manager.user_loader  
def user_loader(id): 
    return User(id) 
    
#---------------------------
# (登入管理)未授權頁面
#---------------------------
@login_manager.unauthorized_handler
def unauthorized():
    return render_template('login.html', liffid = db.LIFF_ID)

#---------------------------
# 使用者登入表單
#---------------------------
@user_bp.route('/login/form')
def login_form():
    return render_template('login.html', liffid = db.LIFF_ID)

#--------------------------
# 使用者登入
#--------------------------
@user_bp.route('/login', methods=['POST'])
def user_login():
    access_token = request.get_json()['access_token']
    headers = {
        'Authorization': 'Bearer ' + access_token
    }
    res = requests.get('https://api.line.me/v2/profile', headers={'Authorization': 'Bearer ' + access_token})

    if res.status_code == 200:
        data = res.json()
        print(data)
        user_id = data['userId']
        user_name = data['displayName']
        print(user_id)
        print(user_name)

        conn = db.get_connection()
        cursor = conn.cursor()
        if not cursor.execute("SELECT MemID FROM Member WHERE MemID = %s", (user_id,)):
            cursor.execute("INSERT INTO Member (MemID, MemName) VALUES (%s, %s)", (user_id, user_name))
            conn.commit()
           
        user = User(user_id)
        login_user(user)
    
        session['MemID'] = user_id
        session['MemName'] = user_name
        return jsonify({"msg": "ok"})

#---------------------------
# 登出
#---------------------------
@user_bp.route('/logout', methods=['GET'])
def logout():        
    logout_user()   #(登入管理)從session清除user物件
    session.clear()
    return "登出成功"

@user_bp.route('/test')
def test():
    return f'{session}'