from flask import Flask, request, render_template, redirect, url_for, Blueprint
from flask_apscheduler import APScheduler
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, URIAction, MessageAction)
from utils import db
# from ..schedule.app import scheduler

med_bp = Blueprint('med_bp',__name__)

line_bot_api = LineBotApi(db.LINE_TOKEN_2)
handler = WebhookHandler(db.LINE_HANDLER_2)

app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

app = Flask(__name__)

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

        job_id = f'{memoID}'
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=send_time,
            args=[MemID, Title, MedFeature, Cycle],
        )

        return render_template('/med/med_create_success.html')
    except:
        return render_template('/med/med_create_fail.html')

def send_line_message(MemID, Title, MedFeature, Cycle):
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
            alt_text = '用藥通知',
            template = ButtonsTemplate(
                thumbnail_image_url = "https://silverease.ntub.edu.tw/static/imgs/medicine.png",
                image_aspect_ratio = 'rectangle',
                image_size = 'contain',
                image_background_color = '#FFFFFF',
                title = '用藥通知',
                text=f"標題: {Title}\n藥盒與藥袋外觀描述: {MedFeature}",
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
@med_bp.route('/list')
def med_list():    
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
        return render_template('/med/med_login.html',liffid = db.LIFF_ID)
    
    if(FamilyID):
        for id in FamilyID:
            cursor.execute("""
                        SELECT * FROM 
                        (select * from`113-ntub113506`.Memo Where FamilyID = %s) m 
                        join 
                        (select * from `113-ntub113506`.`Med`) e 
                        on e.MemoID=m.MemoID
                        """, (id[0]))
            data += cursor.fetchall()

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

        if scheduler.get_job(MemoID)!=None:
            scheduler.remove_job(MemoID)

        job_id = MemoID
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=send_time,
            args=[EditorID, Title, MedFeature, Cycle],
        )

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

#刪除
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

        job = scheduler.get_job(MemoID)
        if job:
            scheduler.remove_job(MemoID)
            # app.logger.info(f"Scheduled job {MemoID} removed")

        return render_template('med/med_delete_success.html')
    except:
        return render_template('med/med_delete_fail.html')

if __name__ == '__main__':
    app.run(debug=True)
