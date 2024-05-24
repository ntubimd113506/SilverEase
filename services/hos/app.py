from flask import request, render_template, redirect, url_for
#from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import sqlite3
from flask import Blueprint
from utlis import db
import pymysql

hos_bp = Blueprint('hos_bp',__name__)

#主頁
@hos_bp.route('/')
def hos():
    return render_template('schedule_index.html')

#新增表單
@hos_bp.route('/create/form')
def hos_create_form():
    return render_template('/hos/hos_create_form.html')

#新增
@hos_bp.route('/create', methods=['POST'])
def hos_create():
    try:
        #取得其他參數
        MemID =  request.form.get('MemID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')
        
        print(f'{Title}  {type(DateTime)}  ')
        #取得資料庫連線
        conn = db.get_connection()

        #將資料加入
        cursor = conn.cursor()        
        cursor.execute("""
                      SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
                        FROM `113-ntub113506`.Member m 
                        LEFT JOIN `113-ntub113506`.Family as f ON m.MemID = f.MainUserID 
                        LEFT JOIN `113-ntub113506`.FamilyLink as l ON m.MemID = l.SubUserID
                        where MemID = %s
                       """, (MemID))
        FamilyID=cursor.fetchone()[0]
        err=""
        cursor.execute("INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID) VALUES (%s, %s, %s, '3', %s)",
                        (FamilyID, Title, DateTime, MemID))
        err="INSERT MEMO"
        cursor.execute("Select MemoID from Memo order by MemoID Desc")
        memoID=cursor.fetchone()[0]
        err+="  SELECT"
        cursor.execute("INSERT INTO Hos (MemoID, Location, Doctor, Clinic, Num) VALUES (%s,%s,%s,%s,%s)", (memoID, Location, Doctor, Clinic, Num))
        err+="  hos"
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('/hos/hos_create_success.html')
    except pymysql.Error as e:
        # 渲染失敗畫面
        return f'Error {e}'
        return err
        return render_template('create_fail.html')
    
#查詢
@hos_bp.route('/list')
def hos_list():    
    data=""
    #取得資料庫連線
    conn = db.get_connection()
    
    #取得執行sql命令的cursor
    cursor = conn.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料
    # liff=request.values.get("liff.state")

    MemID =  request.values.get('MemID')
    if (MemID):
        cursor.execute("""
                        SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
                            FROM `113-ntub113506`.Member m 
                            LEFT JOIN `113-ntub113506`.Family as f ON m.MemID = f.MainUserID 
                            LEFT JOIN `113-ntub113506`.FamilyLink as l ON m.MemID = l.SubUserID
                            where MemID = %s
                        """, (MemID))
        FamilyID = cursor.fetchone()[0] 
    else:
        return render_template('login.html',liffid=db.LIFF_ID)
    
    # FamilyID = 27

    if(FamilyID):
        cursor.execute("""
                    SELECT * FROM 
                    (select * from`113-ntub113506`.Memo Where FamilyID=%s) m 
                    join 
                    (select * from `113-ntub113506`.`Hos`) e 
                    on e.MemoID=m.MemoID
                    """, (FamilyID))
        data = cursor.fetchall()

    #關閉連線 
    conn.close()  
        
    #渲染網頁
    if data:
        # return f'{data}'
        return render_template('/hos/hos_list.html', data=data, liff=db.LIFF_ID) 
    else:
        return render_template('not_found.html')
    
#更改確認
@hos_bp.route('/update/confirm')
def hos_update_confirm():
    #取得資料庫連線
    connection = db.get_connection()
    
    #取得執行sql命令的cursor
    cursor = connection.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料  
    MemoID = request.values.get('MemoID')

    cursor.execute("""
                   SELECT * FROM 
                   (select * from`113-ntub113506`.Memo Where MemoID=%s) m 
                   join 
                   (select * from `113-ntub113506`.`Hos`) e 
                   on e.MemoID=m.MemoID
                   """, (MemoID))
    data = cursor.fetchone()

    #關閉連線   
    connection.close()  
        
    #渲染網頁
    if data:
        return render_template('/hos/hos_update_confirm.html', data=data) 
    else:
        return render_template('not_found.html')
    
    
#更改
@hos_bp.route('/update', methods=['POST'])
def hos_update():
    try:
        #取得參數
        MemoID = request.values.get('MemoID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')

        #取得資料庫連線
        conn = db.get_connection()

        #將資料從hos表刪除
        cursor = conn.cursor()

        cursor.execute("UPDATE Memo SET Title=%s, DateTime=%s WHERE MemoID = %s", (Title, DateTime, MemoID))
        cursor.execute("UPDATE Hos SET Location=%s, Doctor=%s, Clinic=%s, Num=%s WHERE MemoID = %s", (Location, Doctor, Clinic, Num, MemoID))
        
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('hos/hos_update_success.html')
    except:
        # 渲染失敗畫面
        return render_template('hos/hos_update_fail.html')

#刪除確認
@hos_bp.route('/delete/confirm')
def hos_delete_confirm():
    #取得資料庫連線    
    connection = db.get_connection()  
    
    #取得執行sql命令的cursor
    cursor = connection.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料  
    MemoID = request.values.get('MemoID')
      
    cursor.execute('SELECT * FROM Memo WHERE MemoID=%s', (MemoID,))
    data = cursor.fetchone()

    #關閉連線
    connection.close()  
        
    #渲染網頁
    if data:
        return render_template('/hos/hos_delete_confirm.html', data=data) 
    else:
        return render_template('not_found.html')

#員工刪除
@hos_bp.route('/delete', methods=['POST'])
def hos_delete():
    try:
        #取得資料庫連線
        conn = db.get_connection()

        #將資料從customer表刪除
        cursor = conn.cursor()

        #取得傳入參數, 執行sql命令並取回資料  
        MemoID = request.values.get('MemoID')

        cursor.execute('Delete FROM Hos WHERE MemoID=%s', (MemoID,))    
        cursor.execute('Delete FROM Memo WHERE MemoID=%s', (MemoID,))
        
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('hos/hos_delete_success.html')
    except:
        # 渲染失敗畫面
        return render_template('hos/hos_delete_fail.html')
        