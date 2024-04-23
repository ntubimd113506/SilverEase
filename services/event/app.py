from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from flask import Blueprint
from datetime import date
from utlis import db, common

event_bp = Blueprint('event_bp',__name__)

#新增表單
@event_bp.route('/create/form')
def event_create_form():
    return render_template('/event/event_create_form.html')

#新增
@event_bp.route('/create', methods=['POST'])
def event_create():
    try:
        #取得其他參數
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Type = request.form.get('Type')
        Location = request.form.get('Location')
        
        #取得資料庫連線
        conn = db.get_connection()

        #將資料加入
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Memo (Title, DateTime, Type) VALUES (%s, %s, %s)",
                        (Title, DateTime, Type))
        cursor.execute("INSERT INTO Event (Location) VALUES (%s)", (Location))
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('create_success.html')
    except Exception as e:
        #印出錯誤原因
        print(e)
        
        # 渲染失敗畫面
        return render_template('create_fail.html')

#刪除表單
@event_bp.route('/delete/form')
def event_delete_form():
    return render_template('/event/event_delete_form.html') 

#刪除確認
@event_bp.route('/delete/confirm', methods=['GET'])
def event_delete_confirm():
    #取得資料庫連線    
    connection = db.get_connection()  
    
    #取得執行sql命令的cursor
    cursor = connection.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料  
    MemoID = request.values.get('MemoID').strip().upper()
      
    cursor.execute('SELECT * FROM Event WHERE MemoID=%s', (MemoID,))
    data = cursor.fetchone()

    #關閉連線   
    connection.close()  
        
    #渲染網頁
    if data:
        return render_template('/event/event_delete_confirm.html', data=data) 
    else:
        return render_template('not_found.html')
    
#刪除
@event_bp.route('/delete', methods=['POST'])
def event_delete():
    try:
        #取得參數
        MemoID = request.form.get('MemoID')

        #取得資料庫連線
        conn = db.get_connection()

        #將資料從event表刪除
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Event WHERE MemoID = %s", (MemoID,))
        
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('delete_success.html')
    except Exception as e:
        #印出錯誤原因
        print(e)
        
        # 渲染失敗畫面
        return render_template('delete_fail.html')
    
#更改表單
@event_bp.route('/update/form')
def event_update_form():
    return render_template('/event/event_update_form.html') 

#更改確認
@event_bp.route('/update/confirm', methods=['GET'])
def event_update_confirm():
    #取得資料庫連線    
    connection = db.get_connection()  
    
    #取得執行sql命令的cursor
    cursor = connection.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料  
    MemoID = request.values.get('MemoID').strip().upper()
      
    cursor.execute('SELECT * FROM Event WHERE MemoID=%s', (MemoID,))
    data = cursor.fetchone()

    #關閉連線   
    connection.close()  
        
    #渲染網頁
    if data:
        return render_template('/event/event_update_confirm.html', data=data) 
    else:
        return render_template('not_found.html')
    
    
#更改
@event_bp.route('/update', methods=['POST'])
def event_update():
    try:
        #取得參數
        MemoID = request.values.get('MemoID').strip().upper()
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')

        #取得資料庫連線
        conn = db.get_connection()

        #將資料從event表刪除
        cursor = conn.cursor()
        cursor.execute("UPDATE Memo SET Title=%s, DateTime=%s WHERE MemoID = %s", (Title, DateTime, MemoID))
        cursor.execute("UPDATE Event SET Location=%sWHERE MemoID = %s", (Location, MemoID))
        
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('update_success.html')
    except Exception as e:
        #印出錯誤原因
        print(e)
        
        # 渲染失敗畫面
        return render_template('update_fail.html')

#查詢表單
@event_bp.route('/read/form')
def event_read_form():
    return render_template('/event/event_read_form.html') 


#查詢
@event_bp.route('/read', methods=['GET'])
def event_read():    
    #取得資料庫連線    
    conn = db.get_connection()
    
    #取得執行sql命令的cursor
    cursor = conn.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料  
    MemoID = request.values.get('MemoID').strip().upper()
      
    cursor.execute('SELECT * FROM Memo WHERE MemoID=%s', (MemoID,)and 'SELECT * FROM Event WHERE MemoID=%s', (MemoID,))
    data = cursor.fetchone()

    #關閉連線 
    conn.close()  
        
    #渲染網頁
    if data:
        return render_template('/event/event_read.html', data=data) 
    else:
        return render_template('not_found.html')