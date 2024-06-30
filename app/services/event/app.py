from flask import request, render_template, Blueprint, session
from flask_login import login_required
from datetime import datetime, timedelta
from linebot.models import *
from utils import db
from services import scheduler, line_bot_api

event_bp = Blueprint("event_bp", __name__)


# 主頁
@event_bp.route("/")
@login_required
def event():
    return render_template("schedule_index.html")


# 新增表單
@event_bp.route("/create/form")
def event_create_form():
    MemID = session.get("MemID")

    conn = db.get_connection()
    cursor = conn.cursor()

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


# 新增
@event_bp.route("/create", methods=["POST"])
@login_required
def event_create():
    try:
        MemID = session.get("MemID")
        MainUserID = request.form.get("MainUserID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")

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
            "INSERT INTO Memo (FamilyID, Title, DateTime, Type, EditorID) VALUES (%s, %s, %s, '3', %s)",
            (FamilyID, Title, DateTime, MemID),
        )
        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC LIMIT 1")
        memoID = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO Event (MemoID, Location) VALUES (%s, %s)", (memoID, Location)
        )

        conn.commit()
        conn.close()

        # return "OK"

        job_id = f"{memoID}"
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=send_time,
            args=[MemID, Title, Location],
        )

        return render_template("/event/event_create_success.html")
    except Exception as e:
        return render_template("/event/event_create_fail.html")


@event_bp.route("/create/job/<string:jobID>/<int:time>")
def create_job(jobID, time):
    send_time = datetime.now() + timedelta(minutes=time)
    scheduler.add_job(
        id=jobID,
        func=send_line_message,
        trigger="date",
        run_date=send_time,
        args=["U1d38cccc9cc22a5538e2fd9cc71a32a5", "hi", "here"],
    )
    return f"{scheduler.get_jobs()}"


@event_bp.route("/modify/job/<int:time>")
def modify_job(time):
    send_time = datetime.now() + timedelta(minutes=time)
    scheduler.modify_job("job123", trigger="date", run_date=send_time)
    return f"{scheduler.get_job('job123')}"


@event_bp.route("/del/job")
def del_job():
    scheduler.remove_job("job123")
    return "OK"
    # return f"{scheduler.get_job('job123')}"


@event_bp.route("/joblist")
def job_list():
    return f"{scheduler.get_jobs()}"


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

        if main_user_id != sub_user_id:
            line_bot_api.push_message(main_user_id, body)
        else:
            line_bot_api.push_message(main_user_id, body)

    except Exception as e:
        pass


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
        return render_template("/event/event_list.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID)
    else:
        return render_template("/event/event_not_found.html", MainUsers=MainUsers)
    

# 歷史查詢
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
        return render_template("/event/event_history.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID)
    else:
        return render_template("/event/event_not_found.html", MainUsers=MainUsers)


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
        return render_template("/event/event_not_found.html")


# 更改
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

        job_id = MemoID
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")

        if scheduler.get_job(MemoID) != None:
            scheduler.modify_job(
                MemoID,
                trigger="date",
                run_date=send_time,
                args=[EditorID, Title, Location],
            )

        return render_template("event/event_update_success.html")
    except Exception as e:
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
        return render_template("/event/event_not_found.html")


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

        return render_template("event/event_delete_success.html")
    except Exception as e:

        return render_template("event/event_delete_fail.html")
