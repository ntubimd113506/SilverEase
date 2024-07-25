from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

analyze_bp = Blueprint("analyze_bp", __name__)

def render_analyze_template(title, analyze, is_all=True):
    data_url = "all" if is_all else "mem"
    data = {
        "Title": title,
        "analyze": analyze,
        "All": {"url": "all_weekly", "name": "週報"} if not is_all else {"url": "mem_weekly", "name": "主頁"},
        "weekly": {"url": f"{data_url}_weekly", "name": "週"},
        "monthly": {"url": f"{data_url}_monthly", "name": "月"},
        "yearly": {"url": f"{data_url}_yearly", "name": "年"},
    }
    return render_template("/analyze/analyze.html", data=data)

def get_family_id(MemID):
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, fl.FamilyID) AS FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN `113-ntub113506`.Family f ON f.MainUserID = m.MemID
            LEFT JOIN `113-ntub113506`.FamilyLink fl ON fl.SubUserID = m.MemID
            WHERE m.MemID = %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchone()
        return FamilyID[0] if FamilyID else None


@analyze_bp.route("/all_weekly")
def all_weekly():
    return render_analyze_template("全體資料彙整", "全體分析")

@analyze_bp.route("/all_monthly")
def all_monthly():
    return render_analyze_template("全體資料彙整", "全體分析")

@analyze_bp.route("/all_yearly")
def all_yearly():
    return render_analyze_template("全體資料彙整", "全體分析")

@analyze_bp.route("/mem_weekly")
@login_required
def analyze():
    return render_analyze_template("個人資料彙整", "個人分析", is_all=False)

@analyze_bp.route("/mem_monthly")
@login_required
def mem_monthly():
    return render_analyze_template("個人資料彙整", "個人分析", is_all=False)

@analyze_bp.route("/mem_yearly")
@login_required
def mem_yearly():
    return render_analyze_template("個人資料彙整", "個人分析", is_all=False)

def fetch_data(cursor, period='weekly', FamilyID=None):
    family_condition = "AND l.FamilyID = %s" if FamilyID else ""
    family_param = (FamilyID,) if FamilyID else ()

    query_templates = {
        'weekly': """
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
                SELECT DAYOFWEEK(LocationTime) AS n, COUNT(*) AS CountPerWeek
                FROM `113-ntub113506`.SOS s
                LEFT JOIN `113-ntub113506`.Location l ON s.LocatNo = l.LocatNo
                LEFT JOIN `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
                WHERE YEAR(LocationTime) = YEAR(NOW())
                AND MONTH(LocationTime) = MONTH(NOW())
                AND WEEK(LocationTime) = WEEK(NOW())
                AND a.DataAnalyze = 1
                {family_condition}
                GROUP BY n
            ) Weekly ON Days.n = Weekly.n;
        """,
        'monthly': """
            WITH RECURSIVE Days AS (
                SELECT 1 AS n
                UNION ALL
                SELECT n + 1 FROM Days WHERE n < DAY(LAST_DAY(NOW()))
            )
            SELECT 
                Days.n, IFNULL(Monthly.CountPerMonth, 0) AS CountPerMonth
            FROM 
                Days
            LEFT JOIN (
                SELECT DAYOFMONTH(LocationTime) AS n, COUNT(*) AS CountPerMonth
                FROM `113-ntub113506`.SOS s
                LEFT JOIN `113-ntub113506`.Location l ON s.LocatNo = l.LocatNo
                LEFT JOIN `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
                WHERE YEAR(LocationTime) = YEAR(NOW()) 
                AND MONTH(LocationTime) = MONTH(NOW())
                AND a.DataAnalyze = 1
                {family_condition}
                GROUP BY n
            ) Monthly ON Days.n = Monthly.n
            ORDER BY Days.n;
        """,
        'yearly': """
            WITH RECURSIVE Months AS (
                SELECT 1 AS n
                UNION ALL
                SELECT n + 1 FROM Months WHERE n < 12
            )
            SELECT 
                Months.n, IFNULL(Yearly.CountPerMonth, 0) AS CountPerMonth
            FROM 
                Months
            LEFT JOIN (
                SELECT MONTH(LocationTime) AS n, COUNT(*) AS CountPerMonth
                FROM `113-ntub113506`.SOS s
                LEFT JOIN `113-ntub113506`.Location l ON s.LocatNo = l.LocatNo
                LEFT JOIN `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
                WHERE YEAR(LocationTime) = YEAR(NOW())
                AND a.DataAnalyze = 1
                {family_condition}
                GROUP BY n
            ) Yearly ON Months.n = Yearly.n
            ORDER BY Months.n;
        """
    }

    cursor.execute(query_templates[period].format(family_condition=family_condition), family_param)
    SOSdata = cursor.fetchall()

    period_condition = {
        'weekly': 'WEEK(l.LocationTime) = WEEK(NOW())',
        'monthly': 'MONTH(l.LocationTime) = MONTH(NOW())',
        'yearly': '1=1'
    }[period]

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
            AND {period_condition}
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
            AND {period_condition}
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

def fetch_period_data(period, FamilyID=None):
    with db.get_connection() as conn:
        cursor = conn.cursor()
        return fetch_data(cursor, period, FamilyID)

def fetch_member_data(period):
    MemID = session.get("MemID")
    FamilyID = get_family_id(MemID)
    return fetch_period_data(period, FamilyID)

@analyze_bp.route("/all_weekly_data")
@login_required
def all_weekly_data():
    return jsonify(fetch_period_data('weekly'))

@analyze_bp.route("/all_monthly_data")
@login_required
def all_monthly_data():
    return jsonify(fetch_period_data('monthly'))

@analyze_bp.route("/all_yearly_data")
@login_required
def all_yearly_data():
    return jsonify(fetch_period_data('yearly'))

@analyze_bp.route("/mem_weekly_data")
@login_required
def mem_weekly_data():
    return jsonify(fetch_member_data('weekly'))

@analyze_bp.route("/mem_monthly_data")
@login_required
def mem_monthly_data():
    return jsonify(fetch_member_data('monthly'))

@analyze_bp.route("/mem_yearly_data")
@login_required
def mem_yearly_data():
    return jsonify(fetch_member_data('yearly'))
