from flask import Flask, request, render_template, redirect, url_for, Blueprint
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, URIAction, MessageAction)
from utils import db
# from ..schedule.app import scheduler

# from flask_apscheduler import APScheduler
# from flask import Flask

app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

hos_bp = Blueprint('hos_bp',__name__)

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

app = Flask(__name__)

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
        MemID = request.form.get('MemID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')
        Cycle = request.form.get('Cycle')
        Alert = int(request.form.get('Alert', 0))

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN `113-ntub113506`.Family AS f ON m.MemID = f.MainUserID
            LEFT JOIN `113-ntub113506`.FamilyLink AS l ON m.MemID = l.SubUserID
            WHERE MemID = %s
        """, (MemID,))
        FamilyID = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID, Cycle, Alert) 
            VALUES (%s, %s, %s, '2', %s, %s, %s)
        """, (FamilyID, Title, DateTime, MemID, Cycle, Alert))
        
        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC")
        memoID = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Hos (MemoID, Location, Doctor, Clinic, Num) 
            VALUES (%s, %s, %s, %s, %s)
        """, (memoID, Location, Doctor, Clinic, Num))

        conn.commit()
        conn.close()
        
        job_id = f'{memoID}'
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        if Cycle == '不重複':
            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[MemID, Title, Location, Doctor, Clinic, Num]
            )
        else:
            trigger = None
            interval = {}

            if Cycle == '一小時':
                trigger = 'interval'
                interval = {'hours': 1}
            elif Cycle == '一天':
                trigger = 'interval'
                interval = {'days': 1}
            elif Cycle == '一週':
                trigger = 'interval'
                interval = {'weeks': 1}
            elif Cycle == '一個月':
                trigger = 'cron'
                interval = {'day': send_time.day, 'hour': send_time.hour, 'minute': send_time.minute}
            elif Cycle == '一年':
                trigger = 'cron'
                interval = {'month': send_time.month, 'day': send_time.day, 'hour': send_time.hour, 'minute': send_time.minute}

            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger=trigger,
                start_date=reminder_time,
                args=[MemID, Title, Location, Doctor, Clinic, Num],
                **interval
            )

        return render_template('/hos/hos_create_success.html')
    except Exception as e:
        print(e)
        return render_template('/hos/hos_create_fail.html')

def send_line_message(MemID, Title, Location, Doctor, Clinic, Num):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, l.FamilyID) AS FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN `113-ntub113506`.Family f ON m.MemID = f.MainUserID
            LEFT JOIN `113-ntub113506`.FamilyLink l ON m.MemID = l.SubUserID
            WHERE m.MemID = %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT MainUserID
            FROM `113-ntub113506`.Family
            WHERE FamilyID = %s
            """,
            (FamilyID,),
        )
        main_user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT MainUserID 
            FROM Family 
            WHERE FamilyID = (SELECT FamilyID 
                              FROM FamilyLink 
                              WHERE SubUserID = %s)
        """,
            (MemID,),
        )
        cursor.execute("SELECT MemID FROM Member WHERE MemID = %s", (MemID,))
        sub_user_id = cursor.fetchone()[0]    

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

        if main_user_id != sub_user_id:
            line_bot_api.push_message(main_user_id, body)
        else: line_bot_api.push_message(main_user_id, body)

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
            cursor.execute(
                """
                SELECT m.*, e.*, 
                mu.MemName AS MainUserName, 
                eu.MemName AS EditorUserName
                FROM `113-ntub113506`.Memo m
                JOIN `113-ntub113506`.Hos e ON e.MemoID = m.MemoID
                LEFT JOIN `113-ntub113506`.Family f ON f.FamilyID = m.FamilyID
                LEFT JOIN `113-ntub113506`.Member mu ON mu.MemID = f.MainUserID
                LEFT JOIN `113-ntub113506`.Member eu ON eu.MemID = m.EditorID
                WHERE m.FamilyID = %s
                """,
                (id[0]))
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
        EditorID = request.values.get('EditorID')
        MemoID = request.values.get('MemoID')
        Title = request.form.get('Title')
        DateTime = request.form.get('DateTime')
        Location = request.form.get('Location')
        Doctor = request.form.get('Doctor')
        Clinic = request.form.get('Clinic')
        Num = request.form.get('Num')
        Cycle = request.form.get('Cycle')
        Alert = int(request.form.get('Alert', 0))

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Memo 
            SET Title = %s, DateTime = %s, EditorID = %s, Cycle = %s, Alert = %s 
            WHERE MemoID = %s
        """, (Title, DateTime, EditorID, Cycle, Alert, MemoID))

        cursor.execute("""
            UPDATE Hos 
            SET Location = %s, Doctor = %s, Clinic = %s, Num = %s 
            WHERE MemoID = %s
        """, (Location, Doctor, Clinic, Num, MemoID))

        conn.commit()
        conn.close()

        if scheduler.get_job(MemoID) is not None:
            scheduler.remove_job(MemoID)

        job_id = MemoID
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        if Cycle == '不重複':
            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[EditorID, Title, Location, Doctor, Clinic, Num]
            )
        else:
            trigger = None
            interval = {}

            if Cycle == '一小時':
                trigger = 'interval'
                interval = {'hours': 1}
            elif Cycle == '一天':
                trigger = 'interval'
                interval = {'days': 1}
            elif Cycle == '一週':
                trigger = 'interval'
                interval = {'weeks': 1}
            elif Cycle == '一個月':
                trigger = 'cron'
                interval = {'day': send_time.day, 'hour': send_time.hour, 'minute': send_time.minute}
            elif Cycle == '一年':
                trigger = 'cron'
                interval = {'month': send_time.month, 'day': send_time.day, 'hour': send_time.hour, 'minute': send_time.minute}

            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger=trigger,
                start_date=reminder_time,
                args=[EditorID, Title, Location, Doctor, Clinic, Num],
                **interval
            )

        return render_template('hos/hos_update_success.html')
    except Exception as e:
        print(e)
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

        if scheduler.get_job(MemoID)!=None:
            scheduler.remove_job(MemoID)
        
        conn.commit()
        conn.close()

        return render_template('hos/hos_delete_success.html')
    except:
        return render_template('hos/hos_delete_fail.html')
    
if __name__ == '__main__':
    app.run(debug=True)
        