from flask import request, render_template, Blueprint, session
from flask_login import login_required
from datetime import datetime, timedelta
from linebot.models import *
from utils import db
from services import scheduler, line_bot_api
import time, threading

event_bp = Blueprint("event_bp", __name__)


# 主頁
@event_bp.route("/")
def event():
    return render_template("/schedule/schedule_index.html")


# 新增表單
@event_bp.route("/create/form")
@login_required
def event_create_form():
    MemID = session.get("MemID")

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT f.MainUserID, m.MemName
        FROM `113-ntub113506`.Family f
        JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
        WHERE f.MainUserID = %s
        """,
        (MemID,),
    )
    main_user_info = cursor.fetchone()

    if main_user_info:
        MainUsers = [(MemID, main_user_info[1])]
    else:
        cursor.execute(
            """
            SELECT m.MemID, m.MemName
            FROM `113-ntub113506`.FamilyLink fl
            JOIN `113-ntub113506`.Family f ON fl.FamilyID = f.FamilyID
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE fl.SubUserID = %s
            """,
            (MemID,),
        )
        MainUsers = cursor.fetchall()

    conn.commit()
    conn.close()

    return render_template("/event/event_create_form.html", MainUsers=MainUsers)


@event_bp.route("/create", methods=["POST"])
@login_required
def event_create():
    try:
        MemID = session.get("MemID")
        MainUserID = request.form.get("MainUserID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
        Cycle = request.form.get("Cycle")
        Alert = int(request.form.get("Alert", 0))

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT FamilyID
            FROM `113-ntub113506`.Family
            WHERE MainUserID = %s
            """,
            (MainUserID,),
        )
        FamilyID = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID, Cycle, Alert) 
            VALUES (%s, %s, %s, '3', %s, %s, %s)
            """,
            (FamilyID, Title, DateTime, MemID, Cycle, Alert),
        )

        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC LIMIT 1")
        MemoID = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO 
            Event (MemoID, Location) 
            VALUES (%s, %s)
            """,
            (MemoID, Location),
        )

        conn.commit()
        conn.close()

        job_id = f"{MemoID}"
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=reminder_time,
            args=[MainUserID, Title, Location, Cycle, Alert, MemoID],
        )
        return render_template(
            "/schedule/result.html",
            Title="新增紀念日成功",
            schedule="event",
            list="",
            img="S_create",
        )
    except:
        return render_template(
            "/schedule/result.html",
            Title="新增紀念日失敗",
            schedule="event",
            list="",
            img="F_create",
        )


message_status = {"received": False}


# 傳送通知
def send_line_message(MainUserID, Title, Location, Cycle, Alert, MemoID):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SubUserID FROM `113-ntub113506`.FamilyLink fl
            Left join `113-ntub113506`.Family f on fl.FamilyID = f.FamilyID
            where MainUserID = %s;
            """,
            (MainUserID,),
        )
        SubUserIDs = cursor.fetchall()

        body = TemplateSendMessage(
            alt_text="紀念日通知",
            template=ButtonsTemplate(
                thumbnail_image_url="https://silverease.ntub.edu.tw/static/imgs/planner.png",
                image_aspect_ratio="rectangle",
                image_size="contain",
                image_background_color="#FFFFFF",
                title="紀念日通知",
                text=f"標題: {Title}\n地點: {Location}",
                actions=[MessageAction(label="收到", text="收到")],
            ),
        )

        body1 = TextSendMessage(
            text=f"長者尚未收到此紀念日通知\n請儘速與長者聯繫\n\n標題: {Title}\n地點: {Location}",
        )

        max = 3

        def send_notification():
            for a in range(max):
                line_bot_api.push_message(MainUserID, body)
                time.sleep(300)
                if message_status["received"]:
                    break
            else:
                for sub_id in SubUserIDs:
                    line_bot_api.push_message(sub_id[0], body1)

        threading.Thread(target=send_notification).start()

        next_time = next_send_time(Cycle, datetime.now() + timedelta(minutes=Alert))
        next_time_format = next_time.strftime("%Y-%m-%dT%H:%M")
        reminder_time = (next_time - timedelta(minutes=Alert)).strftime(
            "%Y-%m-%dT%H:%M"
        )

        cursor.execute(
            """
            UPDATE Memo
            SET DateTime = %s
            WHERE MemoID = %s
            """,
            (next_time_format, MemoID),
        )
        conn.commit()
        conn.close()

        scheduler.add_job(
            id=f"{MemoID}",
            func=send_line_message,
            trigger="date",
            run_date=reminder_time,
            args=[MainUserID, Title, Location, Cycle, Alert, MemoID],
        )

    except:
        pass


def next_send_time(Cycle, now=datetime.now()):
    if Cycle == "一小時":
        return now + timedelta(hours=1)
    elif Cycle == "一天":
        return now + timedelta(days=1)
    elif Cycle == "一週":
        return now + timedelta(weeks=1)
    elif Cycle == "一個月":
        return now + timedelta(days=30)
    elif Cycle == "一年":
        return now + timedelta(days=365)
    else:
        return now


# 查詢
@event_bp.route("/list")
@login_required
def event_list():
    data = []

    MemID = session.get("MemID")
    year = request.args.get("year")
    month = request.args.get("month")
    MainUserID = request.args.get("MainUserID")

    conn = db.get_connection()
    cursor = conn.cursor()

    if MemID:
        cursor.execute(
            """
            SELECT m.MemID, m.MemName
            FROM `113-ntub113506`.FamilyLink fl
            JOIN `113-ntub113506`.Family f ON fl.FamilyID = f.FamilyID
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE fl.SubUserID = %s
            """,
            (MemID,),
        )
        MainUsers = cursor.fetchall()

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
            query = """
                    SELECT m.*, e.*, 
                    mu.MemName AS MainUserName, 
                    eu.MemName AS EditorUserName
                    FROM `113-ntub113506`.Memo m
                    JOIN `113-ntub113506`.Event e ON e.MemoID = m.MemoID
                    LEFT JOIN `113-ntub113506`.Family f ON f.FamilyID = m.FamilyID
                    LEFT JOIN `113-ntub113506`.Member mu ON mu.MemID = f.MainUserID
                    LEFT JOIN `113-ntub113506`.Member eu ON eu.MemID = m.EditorID
                    WHERE m.FamilyID = %s AND `DateTime` > NOW()
                    """

            params = [id[0]]

            if MainUserID and MainUserID != "all":
                query += " AND f.MainUserID = %s"
                params.append(MainUserID)

            if year and year != "all":
                query += " AND YEAR(`DateTime`) = %s"
                params.append(year)

            if month and month != "all":
                query += " AND MONTH(`DateTime`) = %s"
                params.append(month)

            cursor.execute(query, tuple(params))
            data += cursor.fetchall()

    conn.close()

    if data:
        return render_template(
            "/event/event_list.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="紀念日",
            schedule="event",
        )


# 紀錄
@event_bp.route("/history")
@login_required
def event_history():
    data = []

    MemID = session.get("MemID")
    year = request.args.get("year")
    month = request.args.get("month")
    MainUserID = request.args.get("MainUserID")

    conn = db.get_connection()
    cursor = conn.cursor()

    if MemID:
        cursor.execute(
            """
            SELECT m.MemID, m.MemName
            FROM `113-ntub113506`.FamilyLink fl
            JOIN `113-ntub113506`.Family f ON fl.FamilyID = f.FamilyID
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE fl.SubUserID = %s
            """,
            (MemID,),
        )
        MainUsers = cursor.fetchall()

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
        return render_template("/med/med_login.html", liffid=db.LIFF_ID)

    if FamilyID:
        for id in FamilyID:
            query = """
                    SELECT m.*, e.*, 
                    mu.MemName AS MainUserName, 
                    eu.MemName AS EditorUserName
                    FROM `113-ntub113506`.Memo m
                    JOIN `113-ntub113506`.Event e ON e.MemoID = m.MemoID
                    LEFT JOIN `113-ntub113506`.Family f ON f.FamilyID = m.FamilyID
                    LEFT JOIN `113-ntub113506`.Member mu ON mu.MemID = f.MainUserID
                    LEFT JOIN `113-ntub113506`.Member eu ON eu.MemID = m.EditorID
                    WHERE m.FamilyID = %s AND `DateTime` <= NOW()
                    """

            params = [id[0]]

            if MainUserID and MainUserID != "all":
                query += " AND f.MainUserID = %s"
                params.append(MainUserID)

            if year and year != "all":
                query += " AND YEAR(`DateTime`) = %s"
                params.append(year)

            if month and month != "all":
                query += " AND MONTH(`DateTime`) = %s"
                params.append(month)

            cursor.execute(query, tuple(params))
            data += cursor.fetchall()

    conn.close()

    if data:
        return render_template(
            "/event/event_history.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="紀念日",
            schedule="event",
        )


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

    return render_template("/event/event_update_confirm.html", data=data)


# 更改
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
            UPDATE 
            Event SET Location = %s WHERE MemoID = %s
            """,
            (Location, MemoID),
        )

        cursor.execute(
            """
            SELECT f.MainUserID
            FROM `113-ntub113506`.Memo m
            JOIN `113-ntub113506`.Family f ON m.FamilyID = f.FamilyID
            WHERE m.MemoID = %s
            """,
            (MemoID,),
        )
        MainUserID = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        job_id = f"{MemoID}"
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        if scheduler.get_job(MemoID) != None:
            scheduler.modify_job(
                MemoID,
                trigger="date",
                run_date=reminder_time,
                args=[MainUserID, Title, Location, Cycle, Alert, MemoID],
            )
        else:
            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[MainUserID, Title, Location, Cycle, Alert, MemoID],
            )

        return render_template(
            "/schedule/result.html",
            schedule="event",
            list="list",
            Title="編輯紀念日成功",
            img="S_update",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="event",
            list="list",
            Title="編輯紀念日失敗",
            img="F_update",
        )


# 刪除確認
@event_bp.route("/delete/confirm")
def event_delete_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Memo WHERE MemoID = %s", (MemoID,))
    data = cursor.fetchone()

    connection.close()

    return render_template("/event/event_delete_confirm.html", data=data)


# 刪除
@event_bp.route("/delete", methods=["POST"])
def event_delete():
    try:
        MemoID = request.form.get("MemoID")

        connection = db.get_connection()
        cursor = connection.cursor()

        cursor.execute("DELETE FROM Event WHERE MemoID = %s", (MemoID,))
        cursor.execute("DELETE FROM Memo WHERE MemoID = %s", (MemoID,))

        connection.commit()
        connection.close()

        scheduler.remove_job(MemoID)

        return render_template(
            "/schedule/result.html",
            Title="刪除紀念日成功",
            schedule="event",
            list="list",
            img="S_delete",
        )
    except:
        return render_template(
            "/schedule/result.html",
            Title="刪除紀念日失敗",
            schedule="event",
            list="list",
            img="F_delete",
        )
