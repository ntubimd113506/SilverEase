from flask import Flask, request, render_template, redirect, url_for, Blueprint
from flask_apscheduler import APScheduler
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, URIAction, MessageAction)
from utils import db
import pymysql

hos_bp = Blueprint('hos_bp',__name__)

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
scheduled_jobs = {}

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

        job_id = f"send_message_{memoID}"
        send_time = datetime.strptime(DateTime, '%Y-%m-%dT%H:%M')
        scheduler.add_job(id = job_id, func = send_line_message, trigger = 'date', run_date = send_time, args = [MemID, Title, Location, Doctor, Clinic, Num])
        scheduled_jobs[memoID] = job_id

        return render_template('/hos/hos_create_success.html')
    except:
        return render_template('/hos/hos_create_fail.html')

def send_line_message(MemID, Title, Location, Doctor, Clinic, Num):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MainUserID 
            FROM Family 
            WHERE FamilyID = (SELECT FamilyID 
                              FROM FamilyLink 
                              WHERE SubUserID = %s)
        """, (MemID,))
        # cursor.execute("SELECT MemID FROM Member WHERE MemID = %s", (MemID,))
        user_line_id = cursor.fetchone()[0]
        conn.close()

        body = TemplateSendMessage(
            alt_text = '回診通知',
            template = ButtonsTemplate(
                thumbnail_image_url = "https://silverease.ntub.edu.tw/static/imgs/treatment.png",
                image_aspect_ratio = 'rectangle',
                image_size = 'contain',
                image_background_color = '#FFFFFF',
                title = '回診通知',
                text=f"標題: {Title}\n醫院地點: {Location}\n看診醫生: {Doctor}\n門診: {Clinic}\n號碼: {Num}",
                actions=[
                    MessageAction(
                        label = '收到',
                        text = '收到'
                    )
                ]
            )
        )

        line_bot_api.push_message(user_line_id, body)

    except Exception as e:
        print(e)
    
#查詢
@hos_bp.route('/list')
def hos_list():    
    data=[]

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
        FamilyID = cursor.fetchall()
    else:
        return render_template('/hos/hos_login.html',liffid = db.LIFF_ID)
    
    if(FamilyID):
        for id in FamilyID:
            cursor.execute("""
                        SELECT * FROM 
                        (select * from`113-ntub113506`.Memo Where FamilyID = %s) m 
                        join 
                        (select * from `113-ntub113506`.`Hos`) e 
                        on e.MemoID=m.MemoID
                        """, (id[0]))
            data += cursor.fetchall()

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
        EditorID =  request.values.get('EditorID')
        MemoID = request.values.get('MemoID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE Memo SET Title = %s, DateTime = %s, EditorID = %s WHERE MemoID = %s", (Title, DateTime, EditorID, MemoID))
        cursor.execute("UPDATE Hos SET Location = %s, Doctor = %s, Clinic = %s, Num = %s WHERE MemoID = %s", (Location, Doctor, Clinic, Num, MemoID))
        
        conn.commit()
        conn.close()

        if MemoID in scheduled_jobs:
            scheduler.remove_job(scheduled_jobs[MemoID])
            del scheduled_jobs[MemoID]

        job_id = f"send_message_{MemoID}"
        send_time = datetime.strptime(DateTime, '%Y-%m-%dT%H:%M')
        scheduler.add_job(id = job_id, func=send_line_message, trigger = 'date', run_date = send_time, args = [EditorID, Title, Location, Clinic, Num, MemoID])
        scheduled_jobs[MemoID] = job_id

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

#刪除
@hos_bp.route('/delete', methods=['POST'])
def hos_delete():
    try:
        MemoID = request.values.get('MemoID')
        
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute('Delete FROM Hos WHERE MemoID = %s', (MemoID,))    
        cursor.execute('Delete FROM Memo WHERE MemoID = %s', (MemoID,))

        if MemoID in scheduled_jobs:
            scheduler.remove_job(scheduled_jobs[MemoID])
            del scheduled_jobs[MemoID]
        
        conn.commit()
        conn.close()

        return render_template('hos/hos_delete_success.html')
    except:
        return render_template('hos/hos_delete_fail.html')
    
if __name__ == '__main__':
    app.run(debug=True)
        