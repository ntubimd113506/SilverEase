from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

analyze_bp = Blueprint("analyze_bp", __name__)

@analyze_bp.route("/")
@login_required
def analyze():
    data = {
        "Title": "個人資料彙整",
        "analyze": "個人分析",
        "All": {"url": "all_weekly", "name": "週報"},
    }
    return render_template("/analyze/analyze.html", data=data)

@analyze_bp.route("/all_weekly")
def all_weekly():
    data = {
        "Title": "全體資料彙整",
        "analyze": "全體分析",
        "Index": {"url": " ", "name": "主頁"},
    }
    return render_template("/analyze/analyze.html", data=data)

def fetch_weekly_data(cursor, FamilyID=None):
    family_condition = "AND l.FamilyID = %s" if FamilyID else ""
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
            LEFT JOIN `113-ntub113506`.Location l on s.LocatNo = l.LocatNo
            LEFT JOIN `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
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

    cursor.execute(
        f"""
        SELECT 
            st.TypeName, 
            COUNT(CASE WHEN a.DataAnalyze = 1 THEN s.SOSType ELSE NULL END) AS Count
        FROM 
            `113-ntub113506`.SOSType st
        LEFT JOIN 
            `113-ntub113506`.SOS s ON s.SOSType = st.TypeNo
        LEFT JOIN 
            `113-ntub113506`.Location l ON l.LocatNo = s.LocatNo
            AND YEAR(l.LocationTime) = YEAR(NOW())
            AND MONTH(l.LocationTime) = MONTH(NOW())
            AND WEEK(l.LocationTime) = WEEK(NOW())
        LEFT JOIN 
            `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
            {family_condition}
        GROUP BY 
            st.TypeName, st.TypeNo
        ORDER BY 
            st.TypeNo;
        """,
        family_param,
    )
    SOSTypedata = cursor.fetchall()

    cursor.execute(
        f"""
        SELECT 
            sp.PlaceName, 
            COUNT(CASE WHEN a.DataAnalyze = 1 THEN s.SOSPlace ELSE NULL END) AS Count
        FROM 
            `113-ntub113506`.SOSPlace sp
        LEFT JOIN 
            `113-ntub113506`.SOS s ON s.SOSPlace = sp.PlaceNo
        LEFT JOIN 
            `113-ntub113506`.Location l ON l.LocatNo = s.LocatNo
            AND YEAR(l.LocationTime) = YEAR(NOW())
            AND MONTH(l.LocationTime) = MONTH(NOW())
            AND WEEK(l.LocationTime) = WEEK(NOW())
        LEFT JOIN 
            `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
            {family_condition}
        GROUP BY 
            sp.PlaceName, sp.PlaceNo
        ORDER BY 
            sp.PlaceNo;
        """,
        family_param,
    )
    SOSPlacedata = cursor.fetchall()
    return {"SOSdata": SOSdata, "SOSTypedata": SOSTypedata, "SOSPlacedata": SOSPlacedata}

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

        data = fetch_weekly_data(cursor, FamilyID[0])
    return jsonify(data)
