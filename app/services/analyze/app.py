from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

analyze_bp = Blueprint("analyze_bp", __name__)

# 主頁
@analyze_bp.route("/")
@login_required
def analyze():
    MemID = session.get("MemID")

    conn = db.get_connection()
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

    if MainUserID:
        data = {
            "Title": "資料彙整",
            "Index": {"url": "", "name": ""},
            "All": {"url": "all_weekly", "name": "週報"},
            "SOS": {"url": "SOS", "name": "求救"},
            "Location": {"url": "Location", "name": "足跡"},
            "Create": {"url": "Create", "name": "新增排程"},
            "Respond": {"url": "", "name": ""}
        }
        return render_template("/analyze/analyze_index.html", data = data)
    else:
        data = {
            "Title": "資料彙整",
            "All": {"url": "all_weekly", "name": "週報"},
            "SOS": {"url": "SOS", "name": "求救"},
            "Location": {"url": "Location", "name": "足跡"},
            "Create": {"url": "Create", "name": "新增排程"},
            "Respond": {"url": "Respond", "name": "回應"}
        }
        return render_template("/analyze/analyze_index.html", data=data)
    
@analyze_bp.route("/all_data")
@login_required
def all_data():
    endpoints = {
        "abc": "/analyze/all_weekly_data",
    }

    return jsonify({"endpoints": endpoints})

@analyze_bp.route("/all_weekly")
def all_weekly():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
        "SOS": {"url": "SOS", "name": "求救"},
        "Create": {"url": "Create", "name": "新增排程"},
        "Respond": {"url": "Respond", "name": "回應"}
    }
    return render_template("/analyze/analyze_index.html", data=data)

@analyze_bp.route("/all_weekly_data")
@login_required
def all_weekly_data():
    MemID = session.get("MemID")

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        WITH RECURSIVE Days AS (
        SELECT 1 AS n
        UNION ALL
        SELECT n + 1 FROM Days WHERE n < 7
        )
        SELECT ELT(Days.n, '星期天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六') CreateDate, IFNULL(Weekly.CountPerWeek, 0) CountPerWeek
        FROM Days
        LEFT JOIN (
            SELECT DAYOFWEEK(LocationTime) AS n, COUNT(*) AS CountPerWeek
            FROM `113-ntub113506`.SOS s
            LEFT JOIN `113-ntub113506`.Location l on s.LocatNo = l.LocatNo
            WHERE YEAR(LocationTime) = YEAR(NOW())
            AND MONTH(LocationTime) = MONTH(NOW())
            AND WEEK(LocationTime) = WEEK(NOW())
            GROUP BY n
        ) Weekly ON Days.n = Weekly.n;
        """
    )
    sos_data = cursor.fetchall()

    cursor.execute(
        """
        WITH RECURSIVE Days AS (
        SELECT 1 AS n
        UNION ALL
        SELECT n + 1 FROM Days WHERE n < 7
        )
        SELECT ELT(Days.n, '星期天', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六') CreateDate, IFNULL(Weekly.CountPerWeek, 0) CountPerWeek
        FROM Days
        LEFT JOIN (
            SELECT DAYOFWEEK(CreateTime) AS n, COUNT(*) AS CountPerWeek
            FROM `113-ntub113506`.Memo 
            WHERE YEAR(CreateTime) = YEAR(NOW())
            AND MONTH(CreateTime) = MONTH(NOW())
            AND WEEK(CreateTime) = WEEK(NOW())
            GROUP BY n
        ) Weekly ON Days.n = Weekly.n;
        """
    )
    memo_data = cursor.fetchall()

    cursor.execute(
        """
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
                DAYOFWEEK(RespondTime) AS n,
                Times,
                COUNT(*) AS CountPerDay
            FROM `113-ntub113506`.Respond
            WHERE YEAR(RespondTime) = YEAR(NOW())
            AND MONTH(RespondTime) = MONTH(NOW())
            AND WEEK(RespondTime) = WEEK(NOW())
            GROUP BY n, Times
        ) Weekly ON Days.n = Weekly.n
        GROUP BY Days.n;
        """
    )
    respond_data = cursor.fetchall()

    conn.close()

    return jsonify({"sos_data": sos_data, "memo_data": memo_data, "respond_data":respond_data})
