from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from flask import Blueprint
from datetime import date
from utlis import db_example, common

date_bp = Blueprint('date_bp',__name__)

#新增表單
@date_bp.route('/create/form')
def date_create_form():
    return render_template('/date/date_create_form.html') 

#新增
@date_bp.route('/create', methods=['POST'])
def date_create():
    try:
        #取得其他參數
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Type = request.form.get('Type')
        
        #取得資料庫連線
        conn = db_example.get_connection()

        #將資料加入
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Memo (Title, DateTime, Type) VALUES (%s, %s, %s)",
                        (Title, DateTime, Type))
        conn.commit()
        conn.close()

        # 渲染成功畫面
        return render_template('create_success.html')
    except Exception as e:
        #印出錯誤原因
        print(e)
        
        # 渲染失敗畫面
        return render_template('create_fail.html')

#查詢表單
@date_bp.route('/read/form')
def date_read_form():
    return render_template('/date/date_read_form.html') 


#查詢
@date_bp.route('/read', methods=['GET'])
def date_read():    
    #取得資料庫連線    
    conn = db_example.get_connection()
    
    #取得執行sql命令的cursor
    cursor = conn.cursor()   
    
    #取得傳入參數, 執行sql命令並取回資料  
    prono = request.values.get('prono').strip().upper()
      
    cursor.execute('SELECT * FROM Memo WHERE MemoID=%s', (MemoID,))
    data = cursor.fetchone()

    #關閉連線 
    conn.close()  
        
    #渲染網頁
    if data:
        return render_template('/date/date_read.html', data=data) 
    else:
        return render_template('not_found.html')