from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

analyze_bp = Blueprint("analyze_bp", __name__)

@analyze_bp.route("/")
@login_required
def analyze():
    MemID = session.get("MemID")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT f.MainUserID
            FROM `113-ntub113506`.Family f
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE f.MainUserID = %s
            """,
            (MemID,),
        )
        MainUserID = cursor.fetchone()

    data = {
        "Title": "資料彙整",
        "All": {"url": "all_weekly", "name": "週報"},
        "SOS": {"url": "SOS", "name": "求救"},
        "Location": {"url": "Location", "name": "足跡"},
        "Create": {"url": "Create", "name": "新增排程"},
    }

    if MainUserID:
        data["Index"] = {"url": "", "name": ""}
        data["Respond"] = {"url": "", "name": ""}
    else:
        data["Respond"] = {"url": "Respond", "name": "回應"}

    return render_template("/analyze/analyze_index.html", data=data)

@analyze_bp.route("/all_data")
@login_required
def all_data():
    endpoints = {
        "all": "/analyze/all_weekly_data",
        "mem": "/analyze/mem_weekly_data",
    }
    return jsonify({"endpoints": endpoints})

@analyze_bp.route("/all_weekly")
def all_weekly():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze_index.html", data=data)

def fetch_weekly_data(cursor, FamilyID=None):
    family_condition = "AND m.FamilyID = %s" if FamilyID else ""
    family_param = (FamilyID,) if FamilyID else ()

    cursor.execute(
        f"""
        WITH RECURSIVE Days AS (
        SELECT 1 AS n
        UNION ALL
        SELECT n + 1 FROM Days WHERE n < 7
        )
        SELECT 
            ELT(Days.n, '星期天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六') AS CreateDate,
            IFNULL(Weekly.CountPerWeek, 0) CountPerWeek
        FROM 
            Days
        LEFT JOIN (
            SELECT DAYOFWEEK(LocationTime) AS n, COUNT(*) AS CountPerWeek
            FROM `113-ntub113506`.SOS s
            LEFT JOIN `113-ntub113506`.Location m on s.LocatNo = m.LocatNo
            LEFT JOIN `113-ntub113506`.Access a ON m.FamilyID = a.FamilyID
            WHERE YEAR(LocationTime) = YEAR(NOW())
            AND MONTH(LocationTime) = MONTH(NOW())
            AND WEEK(LocationTime) = WEEK(NOW())
            AND a.DataAnalyze = 1
            {family_condition}
            GROUP BY n
        ) Weekly ON Days.n = Weekly.n;
        """,
        family_param,
    )
    sos_data = cursor.fetchall()

    cursor.execute(
        f"""
        WITH RECURSIVE Days AS (
            SELECT 1 AS n
            UNION ALL
            SELECT n + 1 FROM Days WHERE n < 7
        )
        SELECT 
            ELT(Days.n, '星期天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六') AS CreateDate, 
            IFNULL(Weekly.CountPerWeek, 0) AS CountPerWeek
        FROM 
            Days
        LEFT JOIN (
            SELECT DAYOFWEEK(m.CreateTime) AS n, COUNT(*) AS CountPerWeek
            FROM `113-ntub113506`.Memo AS m
            JOIN `113-ntub113506`.Access AS Access 
            ON m.FamilyID = Access.FamilyID
            WHERE Access.DataAnalyze = 1
            AND YEAR(m.CreateTime) = YEAR(NOW())
            AND MONTH(m.CreateTime) = MONTH(NOW())
            AND WEEK(m.CreateTime) = WEEK(NOW())
            {family_condition}
            GROUP BY n
        ) Weekly ON Days.n = Weekly.n;
        """,
        family_param,
    )
    memo_data = cursor.fetchall()

    cursor.execute(
        f"""
        WITH RECURSIVE Days AS (
            SELECT 1 AS n
            UNION ALL
            SELECT n + 1 FROM Days WHERE n < 7
        )
        SELECT 
            ELT(Days.n, '星期天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六') AS CreateDate,
            COUNT(CASE WHEN Weekly.Times = 0 THEN 1 ELSE NULL END) AS C0,
            COUNT(CASE WHEN Weekly.Times = 1 THEN 1 ELSE NULL END) AS C1,
            COUNT(CASE WHEN Weekly.Times = 2 THEN 1 ELSE NULL END) AS C2,
            COUNT(CASE WHEN Weekly.Times = 3 THEN 1 ELSE NULL END) AS C3
        FROM Days
        LEFT JOIN (
            SELECT 
                DAYOFWEEK(r.RespondTime) AS n,
                r.Times,
                COUNT(*) AS CountPerDay
            FROM `113-ntub113506`.Respond r
            LEFT JOIN `113-ntub113506`.Memo m ON m.MemoID = r.MemoID
            LEFT JOIN `113-ntub113506`.Access a ON m.FamilyID = a.FamilyID
            WHERE YEAR(r.RespondTime) = YEAR(NOW())
            AND MONTH(r.RespondTime) = MONTH(NOW())
            AND WEEK(r.RespondTime) = WEEK(NOW())
            AND a.DataAnalyze = 1
            {family_condition}
            GROUP BY n, r.Times
        ) Weekly ON Days.n = Weekly.n
        GROUP BY Days.n;
        """,
        family_param,
    )
    respond_data = cursor.fetchall()

    return {"sos_data": sos_data, "memo_data": memo_data, "respond_data": respond_data}

@analyze_bp.route("/all_weekly_data")
@login_required
def all_weekly_data():
    with db.get_connection() as conn:
        cursor = conn.cursor()
        data = fetch_weekly_data(cursor)
    return jsonify(data)

@analyze_bp.route("/mem_weekly_data")
@login_required
def mem_weekly_data():
    MemID = session.get("MemID")

    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, fl.FamilyID) AS FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN `113-ntub113506`.Family f ON f.MainUserID = m.MemID
            LEFT JOIN `113-ntub113506`.FamilyLink fl ON fl.SubUserID = m.MemID
            WHERE MemID =  %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchone()

        data = fetch_weekly_data(cursor, FamilyID)
    return jsonify(data)

@analyze_bp.route("/SOS")
def SOS():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze_index.html", data=data)

@analyze_bp.route("/Location")
def Location():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze_index.html", data=data)

@analyze_bp.route("/Create")
def Create():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze_index.html", data=data)

@analyze_bp.route("/Respond")
def Respond():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze_index.html", data=data)
