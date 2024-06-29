from flask import Flask, request, render_template, redirect, url_for, Blueprint
from services import scheduler
from datetime import datetime, timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.models import TemplateSendMessage, ButtonsTemplate, MessageAction
from utils import db
import pymysql
import logging

event_bp = Blueprint("event_bp", __name__)


line_bot_api = LineBotApi(db.LINE_TOKEN)
handler = WebhookHandler(db.LINE_HANDLER)

app = Flask(__name__)


def get_family_id(MemID):
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
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
        FamilyID = cursor.fetchone()
        return FamilyID[0] if FamilyID else None
    except Exception as e:
        app.logger.error(f"An error occurred in get_family_id: {e}")
        return None
    finally:
        conn.close()


def send_line_message(MemID, Title, Location):
    try:
        FamilyID = get_family_id(MemID)
        if not FamilyID:
            app.logger.error(f"FamilyID not found for MemID: {MemID}")
            return
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MainUserID FROM `113-ntub113506`.Family WHERE FamilyID = %s",
            (FamilyID,),
        )
        main_user_id = cursor.fetchone()[0]
        cursor.execute(
            "SELECT MemID FROM `113-ntub113506`.Member WHERE MemID = %s", (MemID,)
        )
        sub_user_id = cursor.fetchone()[0]

        body = TemplateSendMessage(
            alt_text="紀念日通知",
            template=ButtonsTemplate(
                title="紀念日通知",
                text=f"標題: {Title}\n地點: {Location}",
                actions=[MessageAction(label="收到", text="收到")],
            ),
        )
        line_bot_api.push_message(main_user_id, body)
        app.logger.info(
            f"Message sent to {main_user_id} with title {Title} at {Location}"
        )

        cursor.execute(
            """
            SELECT MemoID, DateTime, Cycle, Alert
            FROM Memo
            WHERE Title = %s AND EditorID = %s
            ORDER BY MemoID DESC LIMIT 1
            """,
            (Title, MemID),
        )

        result = cursor.fetchone()[0]
        MemoID, DateTime, Cycle, Alert = result
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        next_send_time = None

        if Cycle == "一小時":
            next_send_time = send_time + timedelta(minutes=1)
        elif Cycle == "一天":
            next_send_time = send_time + timedelta(days=1)
        elif Cycle == "一週":
            next_send_time = send_time + timedelta(weeks=1)
        elif Cycle == "一個月":
            next_send_time = send_time + timedelta(days=30)
        elif Cycle == "一年":
            next_send_time = send_time.replace(year=send_time.year + 1)

        if next_send_time:
            cursor.execute(
                """
                UPDATE Memo 
                SET DateTime = %s 
                WHERE MemoID = %s
                """,
                (next_send_time.strftime("%Y-%m-%dT%H:%M"), MemoID),
            )
            conn.commit()

            if scheduler.get_job(str(MemoID)):
                scheduler.remove_job(str(MemoID))

            scheduler.add_job(
                id=f"{MemoID}",
                func=send_line_message,
                trigger="date",
                run_date=next_send_time - timedelta(minutes=Alert),
                args=[MemID, Title, Location],
            )
            app.logger.info(
                f"Next send time for MemoID {MemoID} is updated to {next_send_time}"
            )

    except Exception as e:
        app.logger.error(f"An error occurred in send_line_message: {e}")
    finally:
        conn.close()


@event_bp.route("/")
def event():
    return render_template("schedule_index.html")


@event_bp.route("/create/form")
def event_create_form():
    return render_template("/event/event_create_form.html")


@event_bp.route("/create", methods=["POST"])
def event_create():
    try:
        MemID = request.form.get("MemID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
        Cycle = request.form.get("Cycle")
        Alert = int(request.form.get("Alert", 0))

        FamilyID = get_family_id(MemID)
        if not FamilyID:
            app.logger.error(f"FamilyID not found for MemID: {MemID}")
            return render_template("/event/event_create_fail.html")

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID, Cycle, Alert) 
            VALUES (%s, %s, %s, '2', %s, %s, %s)
            """,
            (FamilyID, Title, DateTime, MemID, Cycle, Alert),
        )

        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC LIMIT 1")
        memoID = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO Event (MemoID, Location) 
            VALUES (%s, %s)
            """,
            (memoID, Location),
        )

        conn.commit()
        conn.close()

        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        scheduler.add_job(
            id=f"{memoID}",
            func=send_line_message,
            trigger="date",
            run_date=reminder_time,
            args=[MemID, Title, Location],
        )
        app.logger.info(f"Job {memoID} scheduled at {reminder_time}")

        return render_template("/event/event_create_success.html")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return render_template("/event/event_create_fail.html")


@event_bp.route("/list")
def event_list():
    data = []

    MemID = request.values.get("MemID")

    if not MemID:
        return render_template("/event/event_login.html", liffid=db.LIFF_ID)

    FamilyID = get_family_id(MemID)

    if FamilyID:
        conn = db.get_connection()
        cursor = conn.cursor()
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
            (FamilyID,),
        )
        data = cursor.fetchall()
        conn.close()

    if data:
        return render_template("/event/event_list.html", data=data, liff=db.LIFF_ID)
    else:
        return render_template("not_found.html")


@event_bp.route("/update/confirm")
def event_update_confirm():
    MemoID = request.values.get("MemoID")

    conn = db.get_connection()
    cursor = conn.cursor()
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
    conn.close()

    if data:
        return render_template("/event/event_update_confirm.html", data=data)
    else:
        return render_template("not_found.html")


@event_bp.route("/update", methods=["POST"])
def event_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
        Cycle = request.form.get("Cycle")
        Alert = int(request.form.get("Alert", 0))

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Memo 
            SET Title = %s, DateTime = %s, EditorID = %s, Cycle = %s, Alert = %s 
            WHERE MemoID = %s
            """,
            (Title, DateTime, EditorID, Cycle, Alert, MemoID),
        )

        cursor.execute(
            """
            UPDATE Event 
            SET Location = %s 
            WHERE MemoID = %s
            """,
            (Location, MemoID),
        )

        conn.commit()
        conn.close()

        if scheduler.get_job(str(MemoID)):
            scheduler.remove_job(str(MemoID))

        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        scheduler.add_job(
            id=f"{MemoID}",
            func=send_line_message,
            trigger="date",
            run_date=reminder_time,
            args=[EditorID, Title, Location],
        )
        app.logger.info(f"Job {MemoID} rescheduled at {send_time}")

        return render_template("event/event_update_success.html")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return render_template("event/event_update_fail.html")


@event_bp.route("/delete/confirm")
def event_delete_confirm():
    MemoID = request.values.get("MemoID")

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Memo WHERE MemoID = %s", (MemoID,))
    data = cursor.fetchone()
    conn.close()

    if data:
        return render_template("/event/event_delete_confirm.html", data=data)
    else:
        return render_template("not_found.html")


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

        if scheduler.get_job(str(MemoID)):
            scheduler.remove_job(str(MemoID))
        app.logger.info(f"Job {MemoID} deleted")

        return render_template("event/event_delete_success.html")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return render_template("event/event_delete_fail.html")

