from flask import request, render_template, Blueprint, session
from flask_login import login_required
from datetime import datetime, timedelta
from linebot.models import *
from utils import db
from services import scheduler, line_bot_api

hos_bp = Blueprint("hos_bp", __name__)


# 主頁
@hos_bp.route("/")
def hos():
    return render_template("/schedule/schedule_index.html")


# 新增表單
@hos_bp.route("/create/form")
@login_required
def hos_create_form():
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

    return render_template("/hos/hos_create_form.html", MainUsers=MainUsers)


# 新增
@hos_bp.route("/create", methods=["POST"])
@login_required
def hos_create():
    try:
        MemID = session.get("MemID")
        MainUserID = request.form.get("MainUserID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
        Doctor = request.form.get("Doctor")
        Clinic = request.form.get("Clinic")
        Num = request.form.get("Num")
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
            VALUES (%s, %s, %s, '2', %s, %s, %s)
            """,
            (FamilyID, Title, DateTime, MemID, Cycle, Alert),
        )

        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC")
        MemoID = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO 
            Hos (MemoID, Location, Doctor, Clinic, Num) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (MemoID, Location, Doctor, Clinic, Num),
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
            args=[MainUserID, Title, Location, Doctor, Clinic, Num],
        )

        return render_template(
            "/schedule/result.html",
            schedule="hos",
            list="",
            Title="新增回診資料成功",
            img="S_create",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="hos",
            list="",
            Title="新增回診資料失敗",
            img="F_create",
        )


# 傳送通知
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
        MainUserId = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT MainUserID 
            FROM Family 
            WHERE FamilyID = (SELECT FamilyID FROM FamilyLink WHERE SubUserID = %s)
            """,
            (MemID,),
        )
        cursor.execute("SELECT MemID FROM Member WHERE MemID = %s", (MemID,))
        SubUserId = cursor.fetchone()[0]

        conn.close()

        body = TemplateSendMessage(
            alt_text="回診通知",
            template=ButtonsTemplate(
                thumbnail_image_url="https://silverease.ntub.edu.tw/static/imgs/treatment.png",
                image_aspect_ratio="rectangle",
                image_size="contain",
                image_background_color="#FFFFFF",
                title="回診通知",
                text=f"標題: {Title}\n醫院地點: {Location}\n看診醫生: {Doctor}\n門診: {Clinic}\n號碼: {Num}",
                actions=[MessageAction(label="收到", text="收到")],
            ),
        )

        if MainUserId != SubUserId:
            line_bot_api.push_message(MainUserId, body)
        else:
            line_bot_api.push_message(MainUserId, body)

    except:
        pass


# 查詢
@hos_bp.route("/list")
@login_required
def hos_list():
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
        return render_template("/hos/hos_login.html", liffid=db.LIFF_ID)

    if FamilyID:
        for id in FamilyID:
            query = """
                    SELECT m.*, e.*, 
                    mu.MemName AS MainUserName, 
                    eu.MemName AS EditorUserName
                    FROM `113-ntub113506`.Memo m
                    JOIN `113-ntub113506`.Hos e ON e.MemoID = m.MemoID
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
            "/hos/hos_list.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="回診資料",
            schedule="hos",
        )


# 紀錄
@hos_bp.route("/history")
@login_required
def hos_history():
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
        return render_template("/hos/hos_login.html", liffid=db.LIFF_ID)

    if FamilyID:
        for id in FamilyID:
            query = """
                    SELECT m.*, e.*, 
                    mu.MemName AS MainUserName, 
                    eu.MemName AS EditorUserName
                    FROM `113-ntub113506`.Memo m
                    JOIN `113-ntub113506`.Hos e ON e.MemoID = m.MemoID
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
            "/hos/hos_history.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="回診資料",
            schedule="hos",
        )


# 更改確認
@hos_bp.route("/update/confirm")
def hos_update_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM 
        (select * from`113-ntub113506`.Memo Where MemoID = %s) m 
        join 
        (select * from `113-ntub113506`.`Hos`) e 
        on e.MemoID = m.MemoID
        """,
        (MemoID),
    )
    data = cursor.fetchone()

    connection.close()

    return render_template("/hos/hos_update_confirm.html", data=data)


# 更改
@hos_bp.route("/update", methods=["POST"])
def hos_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        Location = request.form.get("Location")
        Doctor = request.form.get("Doctor")
        Clinic = request.form.get("Clinic")
        Num = request.form.get("Num")
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
            UPDATE Hos 
            SET Location = %s, Doctor = %s, Clinic = %s, Num = %s 
            WHERE MemoID = %s
            """,
            (Location, Doctor, Clinic, Num, MemoID),
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

        if scheduler.get_job(MemoID) is not None:
            scheduler.remove_job(MemoID)

        job_id = f"{MemoID}"
        send_time = datetime.strptime(DateTime, "%Y-%m-%dT%H:%M")
        reminder_time = send_time - timedelta(minutes=Alert)

        if scheduler.get_job(MemoID) != None:
            scheduler.modify_job(
                MemoID,
                trigger="date",
                run_date=reminder_time,
                args=[MainUserID, Title, Location, Doctor, Clinic, Num],
            )
        else:
            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[MainUserID, Title, Location, Doctor, Clinic, Num],
            )

        return render_template(
            "/schedule/result.html",
            schedule="hos",
            list="list",
            Title="編輯回診資料成功",
            img="S_update",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="hos",
            list="list",
            Title="編輯回診資料成功",
            img="F_update",
        )


# 刪除確認
@hos_bp.route("/delete/confirm")
def hos_delete_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Memo WHERE MemoID = %s", (MemoID,))
    data = cursor.fetchone()

    connection.close()

    return render_template("/hos/hos_delete_confirm.html", data=data)


# 刪除
@hos_bp.route("/delete", methods=["POST"])
def hos_delete():
    try:
        MemoID = request.values.get("MemoID")

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("Delete FROM Hos WHERE MemoID = %s", (MemoID,))
        cursor.execute("Delete FROM Memo WHERE MemoID = %s", (MemoID,))

        if scheduler.get_job(MemoID) != None:
            scheduler.remove_job(MemoID)

        conn.commit()
        conn.close()

        return render_template(
            "/schedule/result.html",
            schedule="hos",
            list="list",
            Title="刪除回診資料成功",
            img="S_delete",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="hos",
            list="list",
            Title="刪除回診資料失敗",
            img="F_delete",
        )
