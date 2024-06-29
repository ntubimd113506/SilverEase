from flask import Flask, request, render_template, redirect, url_for, Blueprint
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, URIAction, MessageAction)
from utils import db
import pymysql
import logging

event_bp = Blueprint("event_bp", __name__)

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
#scheduled_jobs = {}

# 設置 logger
app.logger.setLevel(logging.INFO)

# 主頁
@event_bp.route("/")
def event():
    return render_template("schedule_index.html")

# 新增表單
@event_bp.route("/create/form")
def event_create_form():
    return render_template("/event/event_create_form.html")

# 新增
@event_bp.route("/create", methods=["POST"])
def event_create():
    try:
        MemID = request.form.get("MemID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
        Cycle = request.form.get('Cycle')
        Alert = int(request.form.get('Alert', 0))

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
            FROM `113-ntub113506`.Member m 
            LEFT JOIN `113-ntub113506`.Family as f ON m.MemID = f.MainUserID 
            LEFT JOIN `113-ntub113506`.FamilyLink as l ON m.MemID = l.SubUserID
            WHERE MemID = %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID, Cycle, Alert) 
            VALUES (%s, %s, %s, '2', %s, %s, %s)
        """, (FamilyID, Title, DateTime, MemID, Cycle, Alert))
        
        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC LIMIT 1")
        memoID = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Event (MemoID, Location) 
            VALUES (%s, %s)
        """, (memoID, Location))

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
                args=[MemID, Title, Location]
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
                args=[MemID, Title, Location],
                **interval
            )

        return render_template("/event/event_create_success.html")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return render_template("/event/event_create_fail.html")

def send_line_message(MemID, Title, Location):
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
            alt_text='紀念日通知',
            template=ButtonsTemplate(
                thumbnail_image_url="https://silverease.ntub.edu.tw/static/imgs/planner.png",
                image_aspect_ratio='rectangle',
                image_size='contain',
                image_background_color='#FFFFFF',
                title='紀念日通知',
                text=f"標題: {Title}\n地點: {Location}",
                actions=[
                    MessageAction(
                        label='收到',
                        text='收到'
                    )
                ]
            )
        )

        if main_user_id != sub_user_id:
            line_bot_api.push_message(main_user_id, body)
        else:
            line_bot_api.push_message(main_user_id, body)

        app.logger.info(f"Message sent to {main_user_id} with title {Title} at {Location}")

    except Exception as e:
        app.logger.error(f"An error occurred in send_line_message: {e}")

# 查詢
@event_bp.route("/list")
def event_list():
    data = []

    MemID = request.values.get("MemID")

    conn = db.get_connection()
    cursor = conn.cursor()

    if MemID:
        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
            FROM `113-ntub113506`.Member m 
            LEFT JOIN `113-ntub113506`.Family as f ON m.MemID = f.MainUserID 
            LEFT JOIN `113-ntub113506`.FamilyLink as l ON m.MemID = l.SubUserID
            WHERE MemID = %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchall()
    else:
        return render_template("/event/event_login.html", liffid=db.LIFF_ID)
    
    if FamilyID:
        for id in FamilyID:
            cursor.execute(
            """
            SELECT m.*, e.*, 
            mu.MemName AS MainUserName, 
            eu.MemName AS EditorUserName
            FROM `113-ntub113506`.Memo m
            JOIN `113-ntub113506`.Event e ON e.MemoID = m.MemoID
            LEFT JOIN `113-ntub113506`.Family f ON f.FamilyID = m.FamilyID
            LEFT JOIN `113-ntub113506`.Member mu ON mu.MemID = f.MainUserID
            LEFT JOIN `113-ntub113506`.Member eu ON eu.MemID = m.EditorID
            WHERE m.FamilyID = %s
            """,
            (id[0],))
            data += cursor.fetchall()

    conn.close()

    if data:
        return render_template("/event/event_list.html", data=data, liff=db.LIFF_ID)
    else:
        return render_template("not_found.html")

# 更改確認
@event_bp.route("/update/confirm")
def event_update_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM 
        (SELECT * FROM `113-ntub113506`.Memo WHERE MemoID = %s) m 
        JOIN 
        (SELECT * FROM `113-ntub113506`.Event) e 
        ON e.MemoID=m.MemoID
        """,
        (MemoID,),
    )
    data = cursor.fetchone()

    connection.close()

    if data:
        return render_template("/event/event_update_confirm.html", data=data)
    else:
        return render_template("not_found.html")

# 更改
@event_bp.route("/update", methods=["POST"])
def event_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
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
            UPDATE Event 
            SET Location = %s 
            WHERE MemoID = %s
        """, (Location, MemoID))

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
                args=[EditorID, Title, Location]
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
                args=[EditorID, Title, Location],
                **interval
            )

        app.logger.info(f"Job {job_id} rescheduled at {send_time}")

        return render_template("event/event_update_success.html")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return render_template("event/event_update_fail.html")

# 刪除確認
@event_bp.route("/delete/confirm")
def event_delete_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Memo WHERE MemoID = %s", (MemoID,))
    data = cursor.fetchone()

    connection.close()

    if data:
        return render_template("/event/event_delete_confirm.html", data=data)
    else:
        return render_template("not_found.html")

# 刪除
@event_bp.route("/delete", methods=["POST"])
def event_delete():
    try:
        MemoID = request.values.get("MemoID")

        connection = db.get_connection()
        cursor = connection.cursor()

        cursor.execute("DELETE FROM Event WHERE MemoID = %s", (MemoID,))
        cursor.execute("DELETE FROM Memo WHERE MemoID = %s", (MemoID,))

        connection.commit()
        connection.close()

        if scheduler.get_job(MemoID)!=None:
            scheduler.remove_job(MemoID)
        app.logger.info(f"Job send_message_{MemoID} deleted")

        return render_template("event/event_delete_success.html")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return render_template("event/event_delete_fail.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
