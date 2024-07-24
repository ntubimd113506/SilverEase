from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

analyze_bp = Blueprint("analyze_bp", __name__)

@analyze_bp.route("/")
@login_required
def analyze():
    data = {
        "Title": "資料彙整",
        "All": {"url": "all_weekly", "name": "週報"},
    }
    return render_template("/analyze/analyze.html", data=data)

@analyze_bp.route("/all_weekly")
def all_weekly():
    data = {
        "Title": "資料彙整",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze.html", data=data)

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
    SOSdata = cursor.fetchall()

    return {"SOSdata": SOSdata}

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

        if FamilyID:
            data = fetch_weekly_data(cursor, FamilyID[0])
        else:
            data = {"SOSdata": []}  # 沒有資料時返回空數據
    return jsonify(data)
