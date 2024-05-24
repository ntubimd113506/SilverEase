from flask import request, render_template, redirect, url_for
#from flask_apscheduler import APScheduler
# from datetime import datetime, timedelta
# import sqlite3
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
        MemID =  request.form.get('MemID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')
        
        conn = db.get_connection()

        cursor = conn.cursor()        
        cursor.execute("""
                      SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
                        FROM `113-ntub113506`.Member m 
                        LEFT JOIN `113-ntub113506`.Family as f ON m.MemID = f.MainUserID 
                        LEFT JOIN `113-ntub113506`.FamilyLink as l ON m.MemID = l.SubUserID
                        where MemID = %s
                       """, (MemID))
        FamilyID=cursor.fetchone()[0]
        cursor.execute("INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID) VALUES (%s, %s, %s, '2', %s)",
                        (FamilyID, Title, DateTime, MemID))
        cursor.execute("Select MemoID from Memo order by MemoID Desc")
        memoID=cursor.fetchone()[0]
        cursor.execute("INSERT INTO Hos (MemoID, Location, Doctor, Clinic, Num) VALUES (%s, %s, %s, %s, %s)", (memoID, Location, Doctor, Clinic, Num))
        conn.commit()
        conn.close()

        return render_template('/hos/hos_create_success.html')
    except:
        return render_template('create_fail.html')
    
#查詢
@hos_bp.route('/list')
def hos_list():    
    data=""

    MemID =  request.values.get('MemID')

    conn = db.get_connection()

    cursor = conn.cursor()   

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
        return render_template('/hos/hos_login.html',liffid = db.LIFF_ID)

    if(FamilyID):
        cursor.execute("""
                    SELECT * FROM 
                    (select * from`113-ntub113506`.Memo Where FamilyID = %s) m 
                    join 
                    (select * from `113-ntub113506`.`Hos`) e 
                    on e.MemoID=m.MemoID
                    """, (FamilyID))
        data = cursor.fetchall()

    conn.close()  
        
    if data:
        return render_template('/hos/hos_list.html', data = data, liff = db.LIFF_ID) 
    else:
        return render_template('not_found.html')
    
#更改確認
@hos_bp.route('/update/confirm')
def hos_update_confirm():
    MemoID = request.values.get('MemoID')

    connection = db.get_connection()
    
    cursor = connection.cursor()   
    
    cursor.execute("""
                   SELECT * FROM 
                   (select * from`113-ntub113506`.Memo Where MemoID = %s) m 
                   join 
                   (select * from `113-ntub113506`.`Hos`) e 
                   on e.MemoID = m.MemoID
                   """, (MemoID))
    data = cursor.fetchone()

    connection.close()  
        
    if data:
        return render_template('/hos/hos_update_confirm.html', data = data) 
    else:
        return render_template('not_found.html')
    
    
#更改
@hos_bp.route('/update', methods=['POST'])
def hos_update():
    try:
        MemoID = request.values.get('MemoID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')

        conn = db.get_connection()

        cursor = conn.cursor()

        cursor.execute("UPDATE Memo SET Title = %s, DateTime = %s WHERE MemoID = %s", (Title, DateTime, MemoID))
        cursor.execute("UPDATE Hos SET Location = %s, Doctor = %s, Clinic = %s, Num = %s WHERE MemoID = %s", (Location, Doctor, Clinic, Num, MemoID))
        
        conn.commit()
        conn.close()

        return render_template('hos/hos_update_success.html')
    except:
        return render_template('hos/hos_update_fail.html')

#刪除確認
@hos_bp.route('/delete/confirm')
def hos_delete_confirm():
    MemoID = request.values.get('MemoID')

    connection = db.get_connection()  
    
    cursor = connection.cursor()   
    
    cursor.execute('SELECT * FROM Memo WHERE MemoID = %s', (MemoID,))
    data = cursor.fetchone()

    connection.close()  
        
    if data:
        return render_template('/hos/hos_delete_confirm.html', data = data) 
    else:
        return render_template('not_found.html')

#員工刪除
@hos_bp.route('/delete', methods=['POST'])
def hos_delete():
    try:
        MemoID = request.values.get('MemoID')
        
        conn = db.get_connection()

        cursor = conn.cursor()

        cursor.execute('Delete FROM Hos WHERE MemoID = %s', (MemoID,))    
        cursor.execute('Delete FROM Memo WHERE MemoID = %s', (MemoID,))
        
        conn.commit()
        conn.close()

        return render_template('hos/hos_delete_success.html')
    except:
        return render_template('hos/hos_delete_fail.html')
        