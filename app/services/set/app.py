import json
from flask import request, render_template, Blueprint
from utils import db
from utils.dbFunc import get_codeID

set_bp = Blueprint('set_bp',__name__)

#-----登入-----
@set_bp.route('/')
def setting():
    return render_template('/set/identity.html', liffid=db.LIFF_ID)

def check_member_exists(MemID):  #確認使用者資料是否存在資料庫中
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM Member WHERE MemID = %s', (MemID,))
    member = cursor.fetchone()  # 使用 fetchone() 取得查詢結果的第一行資料，如果沒有符合的資料會返回 None

    conn.close()

    return member is not None 

@set_bp.route('/oy' ,methods=['POST'])
def identity():
    if request.form.get('option') == 'old':
        #建立資料庫連線   
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor1 = conn.cursor()

        MemID = request.values.get('MemID')
        MemName = request.values.get('MemName')

        while 1:
            cursor.execute('SELECT FamilyID FROM Family where MainUserID = %s',(MemID))
            data = cursor.fetchone()
        
            if data!=None:
                code_id = get_codeID(data[0])
                break
            else:
                cursor.execute('INSERT INTO Member (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))
                conn.commit()
                cursor1.execute('INSERT INTO Family (MainUserID) VALUES (%s)', (MemID))
                conn.commit()

        conn.close()
        return  render_template('/set/old.html', data=data, code_id=code_id)
    
    if request.form.get('option') == 'young':
        # 資料加入資料庫
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor1 = conn.cursor()

        MemID = request.values.get('MemID')
        MemName = request.values.get('MemName')

        if check_member_exists(MemID):
            # 資料已存在，執行相應的處理
            return render_template('/set/young.html', MemID=MemID)
        else:
            # 資料不存在，將使用者資料新增至資料庫
            cursor.execute('INSERT INTO Member (MemID, MemName) VALUES (%s, %s)', (MemID, MemName))
            conn.commit()

        conn.close()
        return render_template('/set/young.html', MemID=MemID)
    
@set_bp.route('/young')
def young():
    return render_template('/set/young.html')
    
@set_bp.route("/CodeID", methods=['POST'])
def CodeID():
    conn = db.get_connection()

    cursor = conn.cursor()
    cursor1 = conn.cursor()
    cursor2 = conn.cursor()

    MemID = request.values.get('MemID')
    CodeID = request.values.get("CodeID")

    # 檢查 CodeID 是否存在於 FamilyCode 表中
    cursor.execute('SELECT FamilyID FROM FamilyCode WHERE CodeID = %s', (CodeID,))
    res = cursor.fetchone()
    
    if res is None:
        conn.close()
        return render_template('/set/noCodeID.html')

    FamilyID = res[0]
    
    # 檢查在 FamilyLink 表中是否已經存在此 CodeID 和 MemID 的連結
    cursor.execute('SELECT * FROM FamilyLink WHERE FamilyID = %s AND SubUserID = %s', (FamilyID, MemID))
    che = cursor.fetchone()

    if che:
        conn.close()
        return render_template('/set/repet.html')
    else:
        cursor.execute('INSERT INTO FamilyLink (FamilyID, SubUserID) VALUES (%s, %s)', (FamilyID, MemID))
        cursor1.execute('SELECT MainUserID FROM Family WHERE FamilyID = %s', (FamilyID,))
        old1 = cursor1.fetchone()
        oldID = old1[0]
        cursor2.execute('SELECT MemName FROM Member WHERE MemID = %s', (oldID,))
        old2 = cursor2.fetchone()
        old = old2[0]
        conn.commit()
        conn.close()
        return render_template('/set/YesCodeID.html' , old=old)

@set_bp.route("/checkid", methods=['POST']) #確認使用者資料
def checkid():
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # 獲取使用者的MemID
        data = json.loads(request.get_data(as_text=True))
        MemID = data['MemID']

        # ==================  ==================
        
        '''https://ithelp.ithome.com.tw/m/articles/10300064'''

        #==================  ==================
        cursor.execute('SELECT MainUserID FROM Family WHERE MainUserID = %s', (MemID))
        member_data = cursor.fetchone()
        cursor.execute('SELECT SubUserID FROM FamilyLink WHERE SubUserID = %s', (MemID))
        family_link_data = cursor.fetchone()
        
        conn.close()
        # 檢查是否是長輩
        if member_data!=None:
            return json.dumps({
                "result":1,
                "option":"old"})
        # 檢查是否是子女
        if family_link_data!=None:
            return json.dumps({
                "result":1,
                "option":"young"})
        else:
            return json.dumps({"result": 0},ensure_ascii=False)
      
    except Exception as e:
        return json.dumps({"error": "TryError"},ensure_ascii=False)