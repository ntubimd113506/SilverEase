from flask import request, render_template, Blueprint, session
from flask_login import login_required
from datetime import datetime, timedelta
from linebot.models import *
from utils import db
from services import scheduler, line_bot_api

med_bp = Blueprint("med_bp", __name__)


# 主頁
@med_bp.route("/")
def med():
    return render_template("/schedule/schedule_index.html")


# 新增表單
@med_bp.route("/create/form")
@login_required
def med_create_form():
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

    return render_template("/med/med_create_form.html", MainUsers=MainUsers)


# 新增
@med_bp.route("/create", methods=["POST"])
@login_required
def med_create():
    try:
        MemID = session.get("MemID")
        MainUserID = request.form.get("MainUserID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        MedFeature = request.form.get("MedFeature")
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
            VALUES(%s, %s, %s, '1', %s, %s, %s)
            """,
            (FamilyID, Title, DateTime, MemID, Cycle, Alert),
        )

        cursor.execute("Select MemoID from Memo order by MemoID Desc")
        MemoID = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO 
            Med (MemoID, MedFeature) 
            VALUES (%s, %s)
            """,
            (MemoID, MedFeature),
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
            args=[MainUserID, Title, MedFeature],
        )

        return render_template(
            "/schedule/result.html",
            schedule="med",
            list="",
            Title="新增用藥成功",
            img="S_create",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="med",
            list="",
            Title="新增用藥失敗",
            img="F_create",
        )


# 傳送通知
def send_line_message(MemID, Title, MedFeature):
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
            WHERE FamilyID = (SELECT FamilyID 
                              FROM FamilyLink 
                              WHERE SubUserID = %s)
            """,
            (MemID,),
        )
        cursor.execute("SELECT MemID FROM Member WHERE MemID = %s", (MemID,))
        SubUserId = cursor.fetchone()[0]

        conn.close()

        body = TemplateSendMessage(
            alt_text="用藥通知",
            template=ButtonsTemplate(
                thumbnail_image_url="https://silverease.ntub.edu.tw/static/imgs/medicine.png",
                image_aspect_ratio="rectangle",
                image_size="contain",
                image_background_color="#FFFFFF",
                title="用藥通知",
                text=f"標題: {Title}\n藥盒與藥袋外觀描述: {MedFeature}",
                actions=[MessageAction(label="收到", text="收到")],
            ),
        )

        if MainUserId != SubUserId:
            line_bot_api.push_message(MainUserId, body)
        else:
            line_bot_api.push_message(MainUserId, body)

    except Exception as e:
        print(e)


# 查詢
@med_bp.route("/list")
@login_required
def med_list():
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
                    JOIN `113-ntub113506`.Med e ON e.MemoID = m.MemoID
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
            "/med/med_list.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="用藥",
            schedule="med",
        )


# 歷史查詢
@med_bp.route("/history")
@login_required
def med_history():
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
            WHERE m.MemID = %s
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
                    JOIN `113-ntub113506`.Med e ON e.MemoID = m.MemoID
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
            "/med/med_history.html", data=data, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="用藥",
            schedule="med",
        )


# 更改確認
@med_bp.route("/update/confirm")
def med_update_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM 
        (select * from`113-ntub113506`.Memo Where MemoID = %s) m 
        join 
        (select * from `113-ntub113506`.`Med`) e 
        on e.MemoID=m.MemoID
        """,
        (MemoID),
    )
    data = cursor.fetchone()

    connection.close()

    return render_template("/med/med_update_confirm.html", data=data)


# 更改
@med_bp.route("/update", methods=["POST"])
def med_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        DateTime = request.form.get("DateTime")
        MedFeature = request.form.get("MedFeature")
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
            UPDATE Med 
            SET MedFeature = %s 
            WHERE MemoID = %s
            """,
            (MedFeature, MemoID),
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
                args=[MainUserID, Title, MedFeature],
            )
        else:
            scheduler.add_job(
                id=job_id,
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[MainUserID, Title, MedFeature],
            )

        return render_template(
            "/schedule/result.html",
            schedule="med",
            list="list",
            Title="編輯用藥成功",
            img="S_update",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="med",
            list="list",
            Title="編輯用藥成功",
            img="F_update",
        )


# 刪除確認
@med_bp.route("/delete/confirm")
def med_delete_confirm():
    MemoID = request.values.get("MemoID")

    connection = db.get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Memo WHERE MemoID = %s", (MemoID,))
    data = cursor.fetchone()

    connection.close()

    return render_template("/med/med_delete_confirm.html", data=data)


# 刪除
@med_bp.route("/delete", methods=["POST"])
def med_delete():
    try:
        MemoID = request.values.get("MemoID")

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("Delete FROM Med WHERE MemoID = %s", (MemoID,))
        cursor.execute("Delete FROM Memo WHERE MemoID = %s", (MemoID,))

        conn.commit()
        conn.close()

        job = scheduler.get_job(MemoID)
        if job:
            scheduler.remove_job(MemoID)

        return render_template(
            "/schedule/result.html",
            schedule="med",
            list="list",
            Title="刪除用藥成功",
            img="S_delete",
        )
    except:
        return render_template(
            "/schedule/result.html",
            schedule="med",
            list="list",
            Title="刪除用藥成功",
            img="F_delete",
        )
