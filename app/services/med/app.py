import json
import random
import os
from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from linebot.models import *
from utils import db
from services import scheduler, line_bot_api

med_bp = Blueprint("med_bp", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
UPLOAD_FOLDER = "static/imgs/med/"


def allowed_file(filename, file):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        and file.mimetype.startswith("image/")
    )


def save_file(file, memo_id):
    if file and allowed_file(file.filename, file):
        extension = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{memo_id}.{extension}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return extension
    return None


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
    MainUserInfo = cursor.fetchone()

    MainUsers = []

    if MainUserInfo:
        MainUsers.append((MainUserInfo[0], MainUserInfo[1]))

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
    additional_users = cursor.fetchall()

    MainUsers.extend(additional_users)

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
        OtherTitle = request.form.get("OtherTitle")
        MemoTime = request.form.get("MemoTime")
        SecondTime = request.form.get("SecondTime")
        ThirdTime = request.form.get("ThirdTime")
        EndDate = request.form.get("EndDate")
        Alert = int(request.form.get("Alert", 0))
        CreateTime = datetime.now()
        file = request.files.get("Pic")
        infoCheck = request.form.get("infoCheck")
        age = request.form.get("age")
        gender = request.form.get("gender")

        EndDate = EndDate if EndDate else None

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

        if infoCheck:
            if gender:
                cursor.execute(
                    "UPDATE Family SET Gender = %s WHERE FamilyID = %s",
                    (gender, FamilyID),
                )

            if age:
                cursor.execute(
                    "UPDATE Family SET Age = %s WHERE FamilyID = %s", (age, FamilyID)
                )

        TitleValue = OtherTitle if Title == "其他" else Title

        cursor.execute(
            """
            INSERT INTO Memo (FamilyID, Title, MemoTime, MemoType, EditorID, Alert, Status, CreateTime)
            VALUES(%s, %s, %s, '1', %s, %s, '1', %s)
            """,
            (FamilyID, TitleValue, MemoTime, MemID, Alert, CreateTime),
        )

        cursor.execute("SELECT MemoID FROM Memo ORDER BY MemoID DESC")
        MemoID = cursor.fetchone()[0]

        save_file(file, MemoID) if file else None

        cursor.execute(
            """
            INSERT INTO Med (MemoID, SecondTime, ThirdTime, EndDate)
            VALUES (%s, %s, %s, %s)
            """,
            (MemoID, SecondTime, ThirdTime, EndDate),
        )

        conn.commit()
        conn.close()

        send_time = datetime.strptime(MemoTime, "%Y-%m-%dT%H:%M")
        end_date = datetime.strptime(EndDate, "%Y-%m-%dT%H:%M") if EndDate else None
        reminder_time = send_time - timedelta(minutes=Alert)
        now = datetime.now()

        if send_time > now:
            scheduler.add_job(
                id=f"{MemoID}_MemoTime",
                func=send_line_message,
                trigger="date",
                run_date=reminder_time,
                args=[MemoID],
            )
        else:
            if end_date is None or (reminder_time + timedelta(days=1)) <= end_date:
                new_send_time = send_time + timedelta(days=1)
                new_reminder_time = new_send_time - timedelta(minutes=Alert)
                scheduler.add_job(
                    id=f"{MemoID}_MemoTime",
                    func=send_line_message,
                    trigger="date",
                    run_date=new_reminder_time,
                    args=[MemoID],
                )

        if SecondTime:
            second_time_combined = datetime.strptime(
                f"{send_time.strftime('%Y-%m-%d')}T{SecondTime}", "%Y-%m-%dT%H:%M"
            )
            second_reminder_time = second_time_combined - timedelta(minutes=Alert)

            if second_reminder_time > now:
                scheduler.add_job(
                    id=f"{MemoID}_SecondTime",
                    func=send_line_message,
                    trigger="date",
                    run_date=second_reminder_time,
                    args=[MemoID, 0, False, "SecondTime"],
                )
            else:
                if end_date is None or (second_reminder_time + timedelta(days=1)) <= end_date:
                    new_second_time_combined = second_time_combined + timedelta(days=1)
                    new_second_reminder_time = new_second_time_combined - timedelta(minutes=Alert)
                    scheduler.add_job(
                        id=f"{MemoID}_SecondTime",
                        func=send_line_message,
                        trigger="date",
                        run_date=new_second_reminder_time,
                        args=[MemoID, 0, False, "SecondTime"],
                    )

        if ThirdTime:
            third_time_combined = datetime.strptime(
                f"{send_time.strftime('%Y-%m-%d')}T{ThirdTime}", "%Y-%m-%dT%H:%M"
            )
            third_reminder_time = third_time_combined - timedelta(minutes=Alert)

            if third_reminder_time > now:
                scheduler.add_job(
                    id=f"{MemoID}_ThirdTime",
                    func=send_line_message,
                    trigger="date",
                    run_date=third_reminder_time,
                    args=[MemoID, 0, False, "ThirdTime"],
                )
            else:
                if end_date is None or (third_reminder_time + timedelta(days=1)) <= end_date:
                    new_third_time_combined = third_time_combined + timedelta(days=1)
                    new_third_reminder_time = new_third_time_combined - timedelta(minutes=Alert)
                    scheduler.add_job(
                        id=f"{MemoID}_ThirdTime",
                        func=send_line_message,
                        trigger="date",
                        run_date=new_third_reminder_time,
                        args=[MemoID, 0, False, "ThirdTime"],
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
def send_line_message(MemoID, cnt=0, got=False, time_type="MemoTime"):
    try:
        data = db.get_memo_info(MemoID)
        Title = data["Title"]
        MainUserID = data["MainUser"]
        MainUserName = data["MainUserName"]
        SubUserIDs = data["SubUser"]
        Alert = data["Alert"]
        cnt += 1

        reminder_time = (
            datetime.now()
            + timedelta(seconds=20)
            + timedelta(seconds=random.uniform(-0.5, 0.5))
        ).strftime("%Y-%m-%dT%H:%M:%S")

        msg = json.dumps(
            {
                "MemoID": MemoID,
                "time": reminder_time,
                "got": True,
                "time_type": time_type,
            }
        )

        thumbnail_url = f"https://silverease.ntub.edu.tw/static/imgs/medicine.png"
        for ext in ALLOWED_EXTENSIONS:
            image_path = os.path.join(UPLOAD_FOLDER, f"{MemoID}.{ext}")
            if os.path.exists(image_path):
                thumbnail_url = (
                    f"https://silverease.ntub.edu.tw/static/imgs/med/{MemoID}.{ext}"
                )
                break

        body = TemplateSendMessage(
            alt_text="用藥通知",
            template=ButtonsTemplate(
                thumbnail_image_url=thumbnail_url,
                image_aspect_ratio="rectangle",
                image_size="contain",
                image_background_color="#FFFFFF",
                title="用藥通知",
                text=f"📌標題: {Title}\n",
                actions=[PostbackAction(label="收到", data=msg, text="收到")],
            ),
        )
        
        """
        txtbody=TextSendMessage(f"📌記得服用:{Title}")
        imgbody=TemplateSendMessage(
            alt_text="用藥通知",
            template=ButtonsTemplate(
                thumbnail_image_url=thumbnail_url,
                image_aspect_ratio="rectangle",
                image_size="contain",
                image_background_color="#FFFFFF",
                title="用藥通知"
                actions=[PostbackAction(label="收到", data=msg, text="收到")],
            ),
        )
        """

        body1 = TextSendMessage(
            text=f"{MainUserName}長者尚未收到此用藥通知\n請儘速與長者聯繫\n\n💊標題: {Title}\n",
        )

        conn = db.get_connection()
        cursor = conn.cursor()

        if cnt <= 3 and not got:
            line_bot_api.push_message(MainUserID, body)
            """
            line_bot_api.push_message(MainUserID, txtbody)
            line_bot_api.push_message(MainUserID, imgbody)
            """
        else:
            if not got:
                for sub_id in SubUserIDs:
                    line_bot_api.push_message(sub_id, body1)

                cursor.execute(
                    """
                    INSERT INTO Respond (MemoID, Times, RespondTime)
                    VALUES (%s, %s, %s)
                    """,
                    (MemoID, 0, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                )
                conn.commit()

            if time_type == "MemoTime":
                next_time = data["MemoTime"] + timedelta(days=1)
            elif time_type == "SecondTime":
                next_time = datetime.strptime(
                    f"{data['MemoTime'].strftime('%Y-%m-%d')} {data['SecondTime']}",
                    "%Y-%m-%d %H:%M:%S",
                )
            elif time_type == "ThirdTime":
                next_time = datetime.strptime(
                    f"{data['MemoTime'].strftime('%Y-%m-%d')} {data['ThirdTime']}",
                    "%Y-%m-%d %H:%M:%S",
                )

            if data["EndDate"] and data["EndDate"] < next_time:
                return

            next_time_format = next_time.strftime("%Y-%m-%dT%H:%M:%S")
            reminder_time = (next_time - timedelta(minutes=Alert)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            cnt = 0
            got = False

            if time_type == "MemoTime":
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
            id=f"{MemoID}_{time_type}",
            func=send_line_message,
            trigger="date",
            run_date=reminder_time,
            args=[MemoID, cnt, got, time_type],
        )
    except:
        pass


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
            SELECT f.MainUserID, m.MemName
            FROM `113-ntub113506`.Family f
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE f.MainUserID = %s
            """,
            (MemID,),
        )
        MainUserInfo = cursor.fetchone()

        MainUsers = []

        if MainUserInfo:
            MainUsers.append((MainUserInfo[0], MainUserInfo[1]))

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
        additional_users = cursor.fetchall()

        MainUsers.extend(additional_users)

        cursor.execute(
            """
            SELECT fl.FamilyID AS A_FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN (
                SELECT MainUserID AS UserID, FamilyID
                FROM `113-ntub113506`.Family
                UNION
                SELECT SubUserID AS UserID, FamilyID
                FROM `113-ntub113506`.FamilyLink
            ) AS fl ON m.MemID = fl.UserID
            WHERE m.MemID = %s
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
                    WHERE m.FamilyID = %s AND m.Status = '1' AND GREATEST(m.MemoTime, 
                    COALESCE(CONCAT(DATE(m.MemoTime), ' ', e.SecondTime), '0000-00-00 00:00:00'), 
                    COALESCE(CONCAT(DATE(m.MemoTime), ' ', e.ThirdTime), '0000-00-00 00:00:00')) > NOW()
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
                    "Alert": d[7],
                    "SecondTime": d[11],
                    "ThirdTime": d[12],
                    "EndDate": d[13],
                    "MainUserName": d[14],
                    "EditorUserName": d[15],
                }
            )
        return render_template(
            "/med/med_list.html", data=values, MainUsers=MainUsers, liff=db.LIFF_ID
        )
    else:
        return render_template(
            "/schedule/not_found.html",
            MainUsers=MainUsers,
            Title="用藥",
            schedule="med",
        )


# 紀錄
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
            SELECT f.MainUserID, m.MemName
            FROM `113-ntub113506`.Family f
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE f.MainUserID = %s
            """,
            (MemID,),
        )
        MainUserInfo = cursor.fetchone()

        MainUsers = []

        if MainUserInfo:
            MainUsers.append((MainUserInfo[0], MainUserInfo[1]))

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
        additional_users = cursor.fetchall()

        MainUsers.extend(additional_users)

        cursor.execute(
            """
            SELECT fl.FamilyID AS A_FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN (
                SELECT MainUserID AS UserID, FamilyID
                FROM `113-ntub113506`.Family
                UNION
                SELECT SubUserID AS UserID, FamilyID
                FROM `113-ntub113506`.FamilyLink
            ) AS fl ON m.MemID = fl.UserID
            WHERE m.MemID = %s
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
                    WHERE m.FamilyID = %s AND m.Status = '1' AND GREATEST(m.MemoTime, 
                    COALESCE(CONCAT(DATE(m.MemoTime), ' ', e.SecondTime), '0000-00-00 00:00:00'), 
                    COALESCE(CONCAT(DATE(m.MemoTime), ' ', e.ThirdTime), '0000-00-00 00:00:00')) <= NOW()
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
                    "Alert": d[7],
                    "SecondTime": d[11],
                    "ThirdTime": d[12],
                    "EndDate": d[13],
                    "MainUserName": d[14],
                    "EditorUserName": d[15],
                }
            )
        return render_template(
            "/med/med_history.html", data=values, MainUsers=MainUsers, liff=db.LIFF_ID
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
        (SELECT * FROM `113-ntub113506`.Memo WHERE MemoID = %s) m 
        JOIN 
        (SELECT * FROM `113-ntub113506`.Med) e 
        ON e.MemoID = m.MemoID
        """,
        (MemoID,),
    )
    data = cursor.fetchone()

    connection.close()

    if data:
        department_list = [
            "感冒藥",
            "頭痛藥",
            "止痛藥",
            "高血壓藥物",
            "糖尿病藥物",
            "心臟病藥物",
            "降膽固醇藥物",
            "抗凝劑",
            "抗血小板藥物",
            "癌症藥物",
            "",
        ]

        department = data[2] if data[2] in department_list else "其他"

    values = {
        "MemoID": data[0],
        "Title": department,
        "OtherTitle": data[2],
        "MemoTime": data[3],
        "Alert": data[7],
        "SecondTime": data[11],
        "ThirdTime": data[12],
        "EndDate": data[13],
    }

    return render_template("/med/med_update_confirm.html", data=values)


# 更改
@med_bp.route("/update", methods=["POST"])
def med_update():
    try:
        EditorID = request.values.get("EditorID")
        MemoID = request.values.get("MemoID")
        Title = request.form.get("Title")
        OtherTitle = request.form.get("OtherTitle")
        MemoTime = request.form.get("MemoTime")
        SecondTime = request.form.get("SecondTime")
        ThirdTime = request.form.get("ThirdTime")
        EndDate = request.form.get("EndDate")
        Alert = int(request.form.get("Alert"))
        file = request.files.get("Pic")

        EndDate = EndDate if EndDate else None

        if file:
            for ext in ALLOWED_EXTENSIONS:
                existing_file_path = os.path.join(UPLOAD_FOLDER, f"{MemoID}.{ext}")
                if os.path.exists(existing_file_path):
                    os.remove(existing_file_path)
                    break

        conn = db.get_connection()
        cursor = conn.cursor()

        TitleValue = OtherTitle if Title == "其他" else Title

        cursor.execute(
            """
            UPDATE Memo 
            SET Title = %s, MemoTime = %s, EditorID = %s, Alert = %s 
            WHERE MemoID = %s
            """,
            (TitleValue, MemoTime, EditorID, Alert, MemoID),
        )

        if file:
            save_file(file, MemoID)

        cursor.execute(
            """
            UPDATE Med 
            SET SecondTime = %s, ThirdTime = %s, EndDate = %s
            WHERE MemoID = %s
            """,
            (SecondTime, ThirdTime, EndDate, MemoID),
        )

        conn.commit()
        conn.close()

        send_time = datetime.strptime(MemoTime, "%Y-%m-%dT%H:%M")
        end_date = datetime.strptime(EndDate, "%Y-%m-%dT%H:%M") if EndDate else None
        reminder_time = send_time - timedelta(minutes=Alert)
        now = datetime.now()

        if send_time > now:
            if scheduler.get_job(f"{MemoID}_MemoTime"):
                scheduler.modify_job(
                    f"{MemoID}_MemoTime",
                    trigger="date",
                    run_date=reminder_time,
                    args=[MemoID],
                )
            else:
                scheduler.add_job(
                    id=f"{MemoID}_MemoTime",
                    func=send_line_message,
                    trigger="date",
                    run_date=reminder_time,
                    args=[MemoID],
                )
        else:
            if end_date is None or (reminder_time + timedelta(days=1)) <= end_date:
                new_send_time = send_time + timedelta(days=1)
                new_reminder_time = new_send_time - timedelta(minutes=Alert)
                if scheduler.get_job(f"{MemoID}_MemoTime"):
                    scheduler.modify_job(
                        f"{MemoID}_MemoTime",
                        trigger="date",
                        run_date=new_reminder_time,
                        args=[MemoID],
                    )
                else:
                    scheduler.add_job(
                        id=f"{MemoID}_MemoTime",
                        func=send_line_message,
                        trigger="date",
                        run_date=new_reminder_time,
                        args=[MemoID],
                    )

        if SecondTime:
            second_time_combined = datetime.strptime(
                f"{send_time.strftime('%Y-%m-%d')}T{SecondTime}", "%Y-%m-%dT%H:%M"
            )
            second_reminder_time = second_time_combined - timedelta(minutes=Alert)

            if second_reminder_time > now:
                if scheduler.get_job(f"{MemoID}_SecondTime"):
                    scheduler.modify_job(
                        f"{MemoID}_SecondTime",
                        trigger="date",
                        run_date=second_reminder_time,
                        args=[MemoID, 0, False, "SecondTime"],
                    )
                else:
                    scheduler.add_job(
                        id=f"{MemoID}_SecondTime",
                        func=send_line_message,
                        trigger="date",
                        run_date=second_reminder_time,
                        args=[MemoID, 0, False, "SecondTime"],
                    )
            else:
                if end_date is None or (second_reminder_time + timedelta(days=1)) <= end_date:
                    new_second_time_combined = second_time_combined + timedelta(days=1)
                    new_second_reminder_time = new_second_time_combined - timedelta(minutes=Alert)
                    if scheduler.get_job(f"{MemoID}_SecondTime"):
                        scheduler.modify_job(
                            f"{MemoID}_SecondTime",
                            trigger="date",
                            run_date=new_second_reminder_time,
                            args=[MemoID, 0, False, "SecondTime"],
                        )
                    else:
                        scheduler.add_job(
                            id=f"{MemoID}_SecondTime",
                            func=send_line_message,
                            trigger="date",
                            run_date=new_second_reminder_time,
                            args=[MemoID, 0, False, "SecondTime"],
                        )

        if ThirdTime:
            third_time_combined = datetime.strptime(
                f"{send_time.strftime('%Y-%m-%d')}T{ThirdTime}", "%Y-%m-%dT%H:%M"
            )
            third_reminder_time = third_time_combined - timedelta(minutes=Alert)

            if third_reminder_time > now:
                if scheduler.get_job(f"{MemoID}_ThirdTime"):
                    scheduler.modify_job(
                        f"{MemoID}_ThirdTime",
                        trigger="date",
                        run_date=third_reminder_time,
                        args=[MemoID, 0, False, "ThirdTime"],
                    )
                else:
                    scheduler.add_job(
                        id=f"{MemoID}_ThirdTime",
                        func=send_line_message,
                        trigger="date",
                        run_date=third_reminder_time,
                        args=[MemoID, 0, False, "ThirdTime"],
                    )
            else:
                if end_date is None or (third_reminder_time + timedelta(days=1)) <= end_date:
                    new_third_time_combined = third_time_combined + timedelta(days=1)
                    new_third_reminder_time = new_third_time_combined - timedelta(minutes=Alert)
                    if scheduler.get_job(f"{MemoID}_ThirdTime"):
                        scheduler.modify_job(
                            f"{MemoID}_ThirdTime",
                            trigger="date",
                            run_date=new_third_reminder_time,
                            args=[MemoID, 0, False, "ThirdTime"],
                        )
                    else:
                        scheduler.add_job(
                            id=f"{MemoID}_ThirdTime",
                            func=send_line_message,
                            trigger="date",
                            run_date=new_third_reminder_time,
                            args=[MemoID, 0, False, "ThirdTime"],
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
            Title="編輯用藥失敗",
            img="F_update",
        )


# 刪除圖片
@med_bp.route("/delete/image/<int:memo_id>", methods=["DELETE"])
def delete_image(memo_id):
    for ext in ALLOWED_EXTENSIONS:
        filepath = os.path.join(UPLOAD_FOLDER, f"{memo_id}.{ext}")
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "圖片文件不存在"})


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

        for time_type in ["MemoTime", "SecondTime", "ThirdTime"]:
            job = scheduler.get_job(f"{MemoID}_{time_type}")
            if job:
                scheduler.remove_job(f"{MemoID}_{time_type}")

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
            Title="刪除用藥失敗",
            img="F_delete",
        )
