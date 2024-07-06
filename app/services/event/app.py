import json
from flask import request, render_template, Blueprint, session
from flask_login import login_required
from datetime import datetime, timedelta
from linebot.models import *
from utils import db
from services import scheduler, line_bot_api

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
    MainUserInfo = cursor.fetchone()

    if MainUserInfo:
        MainUsers = [(MemID, MainUserInfo[1])]
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


# 新增
@event_bp.route("/create", methods=["POST"])
@login_required
def event_create():
    try:
        MemID = session.get("MemID")
        MainUserID = request.form.get("MainUserID")
        Title = request.form.get("Title")
        MemoTime = request.form.get("MemoTime")
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
            INSERT INTO Memo (FamilyID, Title, MemoTime, MemoType, EditorID, Cycle, Alert, Status) 
            VALUES (%s, %s, %s, '3', %s, %s, %s, '1')
            """,
            (FamilyID, Title, MemoTime, MemID, Cycle, Alert),
        )

        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC LIMIT 1")
        MemoID = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO 
            EventMemo (MemoID, Location) 
            VALUES (%s, %s)
            """,
            (MemoID, Location),
        )

        conn.commit()
        conn.close()

        job_id = f"{MemoID}"
        send_time = datetime.strptime(MemoTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        scheduler.add_job(
            id=job_id,
            func=send_line_message,
            trigger="date",
            run_date=reminder_time,
            args=[MemoID],
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


# 傳送通知
def send_line_message(MemoID, cnt=0, got=False):
    try:
        data = db.get_memo_info(MemoID)
        Title = data["Title"]
        Location = data["Location"]
        MainUserID = data["MainUser"]
        SubUserIDs = data["SubUser"]
        Cycle = data["Cycle"]
        Alert = data["Alert"]
        cnt += 1
        reminder_time = (datetime.now() + timedelta(seconds=60)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        msg = json.dumps({"MemoID": MemoID, "time": reminder_time, "got": True})
        body = TemplateSendMessage(
            alt_text="紀念日通知",
            template=ButtonsTemplate(
                thumbnail_image_url="https://silverease.ntub.edu.tw/static/imgs/planner.png",
                image_aspect_ratio="rectangle",
                image_size="contain",
                image_background_color="#FFFFFF",
                title="紀念日通知",
                text=f"標題: {Title}\n地點: {Location}",
                actions=[PostbackAction(label="收到", data=msg, text="收到")],
            ),
        )

        body1 = TextSendMessage(
            text=f"長者尚未收到此紀念日通知\n請儘速與長者聯繫\n\n標題: {Title}\n地點: {Location}",
        )

        if cnt <= 3 and not got:
            line_bot_api.push_message(MainUserID, body)
        else:
            if not got:
                for sub_id in SubUserIDs:
                    line_bot_api.push_message(sub_id, body1)

            next_time = next_send_time(Cycle, data["MemoTime"])
            next_time_format = next_time.strftime("%Y-%m-%dT%H:%M:%S")
            reminder_time = (next_time - timedelta(minutes=Alert)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            cnt = 0
            got = False

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE Memo
                SET MemoTime = %s
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
            args=[MemoID, cnt, got],
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
                    JOIN `113-ntub113506`.EventMemo e ON e.MemoID = m.MemoID
                    LEFT JOIN `113-ntub113506`.Family f ON f.FamilyID = m.FamilyID
                    LEFT JOIN `113-ntub113506`.Member mu ON mu.MemID = f.MainUserID
                    LEFT JOIN `113-ntub113506`.Member eu ON eu.MemID = m.EditorID
                    WHERE m.FamilyID = %s AND m.Status = '1' AND MemoTime > NOW()
                    """

            params = [id[0]]

            if MainUserID and MainUserID != "all":
                query += " AND f.MainUserID = %s"
                params.append(MainUserID)

            if year and year != "all":
                query += " AND YEAR(`MemoTime`) = %s"
                params.append(year)

            if month and month != "all":
                query += " AND MONTH(`MemoTime`) = %s"
                params.append(month)

            cursor.execute(query, tuple(params))
            data += cursor.fetchall()

    conn.close()

    if data:
        values = []
        for d in data:
            values.append(
                {
                    "MemoID": d[0],
                    "Title": d[2],
                    "MemoTime": d[3],
                    "Cycle": d[6],
                    "Alert": d[7],
                    "Location": d[10],
                    "MainUserName": d[11],
                    "EditorUserName": d[12],
                }
            )
        return render_template(
            "/event/event_list.html", data=values, MainUsers=MainUsers, liff=db.LIFF_ID
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
                    JOIN `113-ntub113506`.EventMemo e ON e.MemoID = m.MemoID
                    LEFT JOIN `113-ntub113506`.Family f ON f.FamilyID = m.FamilyID
                    LEFT JOIN `113-ntub113506`.Member mu ON mu.MemID = f.MainUserID
                    LEFT JOIN `113-ntub113506`.Member eu ON eu.MemID = m.EditorID
                    WHERE m.FamilyID = %s AND m.Status = '1' AND MemoTime <= NOW()
                    """

            params = [id[0]]

            if MainUserID and MainUserID != "all":
                query += " AND f.MainUserID = %s"
                params.append(MainUserID)

            if year and year != "all":
                query += " AND YEAR(`MemoTime`) = %s"
                params.append(year)

            if month and month != "all":
                query += " AND MONTH(`MemoTime`) = %s"
                params.append(month)

            cursor.execute(query, tuple(params))
            data += cursor.fetchall()

    conn.close()

    if data:
        values = []
        for d in data:
            values.append(
                {
                    "MemoID": d[0],
                    "Title": d[2],
                    "MemoTime": d[3],
                    "Cycle": d[6],
                    "Alert": d[7],
                    "Location": d[10],
                    "MainUserName": d[11],
                    "EditorUserName": d[12],
                }
            )

        return render_template(
            "/event/event_history.html",
            data=values,
            MainUsers=MainUsers,
            liff=db.LIFF_ID,
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
        (SELECT * FROM `113-ntub113506`.EventMemo) e 
        ON e.MemoID=m.MemoID
        """,
        (MemoID,),
    )
    data = cursor.fetchone()

    connection.close()

    if data:
        values = {
            "MemoID": data[0],
            "Title": data[2],
            "MemoTime": data[3],
            "Cycle": data[6],
            "Alert": data[7],
            "Location": data[10],
        }

    return render_template("/event/event_update_confirm.html", data=values)


# 更改
@event_bp.route("/update", methods=["POST"])
def event_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        MemoTime = request.form.get("MemoTime")
        Location = request.form.get("Location")
        Cycle = request.form.get("Cycle")
        Alert = int(request.form.get("Alert"))

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Memo 
            SET Title = %s, MemoTime = %s, EditorID = %s, Cycle = %s, Alert = %s 
            WHERE MemoID = %s
            """,
            (Title, MemoTime, EditorID, Cycle, Alert, MemoID),
        )

        cursor.execute(
            """
            UPDATE EventMemo 
            SET Location = %s 
            WHERE MemoID = %s
            """,
            (Location, MemoID),
        )

        conn.commit()
        conn.close()

        job_id = f"{MemoID}"
        send_time = datetime.strptime(MemoTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        if scheduler.get_job(MemoID) != None:
            scheduler.modify_job(
                MemoID,
                trigger="date",
                run_date=reminder_time,
                args=[MemoID],
            )
        else:
            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[MemoID],
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

        job = scheduler.get_job(MemoID)
        if job:
            scheduler.remove_job(MemoID)

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE Memo 
            SET Status='0'
            WHERE MemoID=%s
            """,
            (MemoID,),
        )

        conn.commit()
        conn.close()

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
