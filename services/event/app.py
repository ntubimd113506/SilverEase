from flask import request, render_template, redirect, url_for
#from flask_apscheduler import APScheduler
# from datetime import datetime, timedelta
# import sqlite3
from flask import Blueprint
from utlis import db
import pymysql

event_bp = Blueprint('event_bp',__name__)

#主頁
@event_bp.route('/')
def event():
    return render_template('schedule_index.html')

#新增表單
@event_bp.route('/create/form')
def event_create_form():
    return render_template('/event/event_create_form.html')

#新增
@event_bp.route('/create', methods=['POST'])
def event_create():
    try:
        MemID =  request.form.get('MemID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')

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
        cursor.execute("INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID) VALUES (%s, %s, %s, '3', %s)",
                        (FamilyID, Title, DateTime, MemID))
        cursor.execute("Select MemoID from Memo order by MemoID Desc")
        memoID=cursor.fetchone()[0]
        cursor.execute("INSERT INTO Event (MemoID, Location) VALUES (%s, %s)", (memoID, Location))

        conn.commit()
        conn.close()

        return render_template('/event/event_create_success.html')
    except:
        return render_template('/event/event_create_fail.html')
    
#查詢
@event_bp.route('/list')
def event_list():    
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
        return render_template('/event/event_login.html',liffid = db.LIFF_ID)

    if(FamilyID):
        cursor.execute("""
                    SELECT * FROM 
                    (select * from`113-ntub113506`.Memo Where FamilyID = %s) m 
                    join 
                    (select * from `113-ntub113506`.`Event`) e 
                    on e.MemoID = m.MemoID
                    """, (FamilyID))
        data = cursor.fetchall()

    conn.close()  
        
    if data:
        return render_template('/event/event_list.html', data = data, liff = db.LIFF_ID) 
    else:
        return render_template('not_found.html')
    
#更改確認
@event_bp.route('/update/confirm')
def event_update_confirm():
    MemoID = request.values.get('MemoID')

    connection = db.get_connection()
    
    cursor = connection.cursor()   

    cursor.execute("""
                   SELECT * FROM 
                   (select * from`113-ntub113506`.Memo Where MemoID = %s) m 
                   join 
                   (select * from `113-ntub113506`.`Event`) e 
                   on e.MemoID=m.MemoID
                   """, (MemoID))
    data = cursor.fetchone()

    connection.close()  
        
    if data:
        return render_template('/event/event_update_confirm.html', data = data) 
    else:
        return render_template('not_found.html')
    
    
#更改
@event_bp.route('/update', methods=['POST'])
def event_update():
    try:
        EditorID =  request.values.get('EditorID')
        MemoID = request.values.get('MemoID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')

        conn = db.get_connection()

        cursor = conn.cursor()

        cursor.execute("UPDATE Memo SET Title = %s, DateTime = %s, EditorID = %s WHERE MemoID = %s", (Title, DateTime, EditorID, MemoID))
        cursor.execute("UPDATE Event SET Location = %s WHERE MemoID = %s", (Location, MemoID))
        
        conn.commit()
        conn.close()

        return render_template('event/event_update_success.html')
    except:
        return render_template('event/event_update_fail.html')

#刪除確認
@event_bp.route('/delete/confirm')
def event_delete_confirm():   
    MemoID = request.values.get('MemoID')
    
    connection = db.get_connection()  
    
    cursor = connection.cursor()
         
    cursor.execute('SELECT * FROM Memo WHERE MemoID = %s', (MemoID,))
    data = cursor.fetchone()

    connection.close()  
        
    if data:
        return render_template('/event/event_delete_confirm.html', data = data) 
    else:
        return render_template('not_found.html')

#員工刪除
@event_bp.route('/delete', methods=['POST'])
def event_delete():
    try:
        MemoID = request.values.get('MemoID')

        conn = db.get_connection()

        cursor = conn.cursor()

        cursor.execute('Delete FROM Event WHERE MemoID = %s', (MemoID,))    
        cursor.execute('Delete FROM Memo WHERE MemoID = %s', (MemoID,))
        
        conn.commit()
        conn.close()

        return render_template('event/event_delete_success.html')
    except:
        return render_template('event/event_delete_fail.html')
        