from flask import request, render_template, redirect, url_for
#from flask_apscheduler import APScheduler
# from datetime import datetime, timedelta
# import sqlite3
from flask import Blueprint
from utlis import db
import pymysql

med_bp = Blueprint('med_bp',__name__)

#主頁
@med_bp.route('/')
def med():
    return render_template('schedule_index.html')

#新增表單
@med_bp.route('/create/form')
def med_create_form():
    return render_template('/med/med_create_form.html')

#新增
@med_bp.route('/create', methods=['POST'])
def med_create():
    try:
        MemID =  request.form.get('MemID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        MedFeature = request.form.get('MedFeature')
        Cycle = request.form.get('Cycle')

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
        cursor.execute("INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID) VALUES (%s, %s, %s, '1', %s)",
                        (FamilyID, Title, DateTime, MemID))
        cursor.execute("Select MemoID from Memo order by MemoID Desc")
        memoID=cursor.fetchone()[0]
        cursor.execute("INSERT INTO Med (MemoID, MedFeature, Cycle) VALUES (%s, %s, %s)", (memoID, MedFeature, Cycle))
        conn.commit()
        conn.close()

        return render_template('/med/med_create_success.html')
    except:
        return render_template('create_fail.html')
    
#查詢
@med_bp.route('/list')
def med_list():    
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
        return render_template('/med/med_login.html',liffid = db.LIFF_ID)
    
    if(FamilyID):
        cursor.execute("""
                    SELECT * FROM 
                    (select * from`113-ntub113506`.Memo Where FamilyID = %s) m 
                    join 
                    (select * from `113-ntub113506`.`Med`) e 
                    on e.MemoID=m.MemoID
                    """, (FamilyID))
        data = cursor.fetchall()

    conn.close()  
        
    if data:
        return render_template('/med/med_list.html', data = data, liff = db.LIFF_ID) 
    else:
        return render_template('not_found.html')
    
#更改確認
@med_bp.route('/update/confirm')
def med_update_confirm():
    MemoID = request.values.get('MemoID')

    connection = db.get_connection()
    
    cursor = connection.cursor()   

    cursor.execute("""
                   SELECT * FROM 
                   (select * from`113-ntub113506`.Memo Where MemoID = %s) m 
                   join 
                   (select * from `113-ntub113506`.`Med`) e 
                   on e.MemoID=m.MemoID
                   """, (MemoID))
    data = cursor.fetchone()

    connection.close()  
        
    if data:
        return render_template('/med/med_update_confirm.html', data = data) 
    else:
        return render_template('not_found.html')
    
    
#更改
@med_bp.route('/update', methods=['POST'])
def med_update():
    try:
        EditorID =  request.values.get('EditorID')
        MemoID = request.values.get('MemoID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        MedFeature = request.form.get('MedFeature')
        Cycle = request.form.get('Cycle')

        conn = db.get_connection()

        cursor = conn.cursor()

        cursor.execute("UPDATE Memo SET Title = %s, DateTime = %s, EditorID = %s WHERE MemoID = %s", (Title, DateTime, EditorID, MemoID))
        cursor.execute("UPDATE Med SET MedFeature = %s, Cycle = %s WHERE MemoID = %s", (MedFeature, Cycle, MemoID))
        
        conn.commit()
        conn.close()

        return render_template('med/med_update_success.html')
    except:
        return render_template('med/med_update_fail.html')

#刪除確認
@med_bp.route('/delete/confirm')
def med_delete_confirm():
    MemoID = request.values.get('MemoID')

    connection = db.get_connection()  
    
    cursor = connection.cursor()       
      
    cursor.execute('SELECT * FROM Memo WHERE MemoID = %s', (MemoID,))
    data = cursor.fetchone()

    connection.close()  
        
    if data:
        return render_template('/med/med_delete_confirm.html', data = data) 
    else:
        return render_template('not_found.html')

#員工刪除
@med_bp.route('/delete', methods=['POST'])
def med_delete():
    try:
        MemoID = request.values.get('MemoID')

        conn = db.get_connection()

        cursor = conn.cursor()

        cursor.execute('Delete FROM Med WHERE MemoID = %s', (MemoID,))    
        cursor.execute('Delete FROM Memo WHERE MemoID = %s', (MemoID,))
        
        conn.commit()
        conn.close()

        return render_template('med/med_delete_success.html')
    except:
        return render_template('med/med_delete_fail.html')
        