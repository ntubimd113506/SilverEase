from flask import Flask, request, render_template, redirect, url_for, Blueprint
from flask_apscheduler import APScheduler
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.models import (MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, URIAction, MessageAction)
from utils import db
import pymysql

event_bp = Blueprint("event_bp", __name__)

line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
scheduled_jobs = {}

#主頁
@event_bp.route("/")
def event():
    return render_template("schedule_index.html")

#新增表單
@event_bp.route("/create/form")
def event_create_form():
    return render_template("/event/event_create_form.html")

#新增
@event_bp.route("/create", methods=["POST"])
def event_create():
    try:
        MemID = request.form.get("MemID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")

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

        cursor.execute(
            "INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID) VALUES (%s, %s, %s, '3', %s)",
            (FamilyID, Title, DateTime, MemID),
        )
        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC")
        memoID = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO Event (MemoID, Location) VALUES (%s, %s)", (memoID, Location)
        )

        conn.commit()
        conn.close()

        job_id = f"send_message_{memoID}"
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=send_time,
            args=[MemID, Title, Location],
        )
        scheduled_jobs[memoID] = job_id

        return render_template("/event/event_create_success.html")
    except:
        return render_template("/event/event_create_fail.html")

def send_line_message(MemID, Title, Location):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
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
        #cursor.execute("SELECT MemID FROM Member WHERE MemID = %s", (MemID,))
        user_line_id = cursor.fetchone()[0]
        conn.close()

        body = TemplateSendMessage(
            alt_text = '紀念日通知',
            template = ButtonsTemplate(
                thumbnail_image_url = "https://silverease.ntub.edu.tw/static/imgs/planner.png",
                image_aspect_ratio = 'rectangle',
                image_size = 'contain',
                image_background_color = '#FFFFFF',
                title = '紀念日通知',
                text=f"標題: {Title}\n地點: {Location}",
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
    
    if(FamilyID):
        for id in FamilyID:
            cursor.execute("""
                        SELECT * FROM 
                        (SELECT * FROM `113-ntub113506`.Memo WHERE FamilyID = %s) m 
                        JOIN 
                        (SELECT * FROM `113-ntub113506`.Event) e 
                        ON e.MemoID = m.MemoID
                        """, (id[0]))
            data += cursor.fetchall()

    conn.close()

    if data:
        return render_template("/event/event_list.html", data=data, liff=db.LIFF_ID)
    else:
        return render_template("not_found.html")

#更改確認
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


#更改
@event_bp.route("/update", methods=["POST"])
def event_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE Memo SET Title = %s, DateTime = %s, EditorID = %s WHERE MemoID = %s",
            (Title, DateTime, EditorID, MemoID),
        )
        cursor.execute(
            "UPDATE Event SET Location = %s WHERE MemoID = %s", (Location, MemoID)
        )

        conn.commit()
        conn.close()

        if MemoID in scheduled_jobs:
            scheduler.remove_job(scheduled_jobs[MemoID])
            del scheduled_jobs[MemoID]

        job_id = f"send_message_{MemoID}"
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=send_time,
            args=[EditorID, Title, Location],
        )
        scheduled_jobs[MemoID] = job_id

        return render_template("event/event_update_success.html")
    except:
        return render_template("event/event_update_fail.html")

#刪除確認
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

#刪除
@event_bp.route("/delete", methods=["POST"])
def event_delete():
    try:
        MemoID = request.values.get("MemoID")

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM Event WHERE MemoID = %s", (MemoID,))
        cursor.execute("DELETE FROM Memo WHERE MemoID = %s", (MemoID,))

        conn.commit()
        conn.close()

        if MemoID in scheduled_jobs:
            scheduler.remove_job(scheduled_jobs[MemoID])
            del scheduled_jobs[MemoID]

        return render_template("event/event_delete_success.html")
    except:
        return render_template("event/event_delete_fail.html")


if __name__ == "__main__":
    app.run(debug=True)
