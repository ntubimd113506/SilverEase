from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

analyze_bp = Blueprint("analyze_bp", __name__)

@analyze_bp.route('/update_main_user_id', methods=['POST'])
def update_main_user_id():
    main_user_id = request.json.get('mainUserID')
    session['MainUserID'] = main_user_id
    return jsonify({'status': 'success'})

def render_analyze_template(title, analyze, is_all=True):
    MemID = session.get("MemID")
    MainUser = session.get("MainUserID")
    DataAnalyze = True

    conn = db.get_connection()
    cursor = conn.cursor()

    if MemID:
        cursor.execute(
            """
            SELECT m.MemID, m.MemName, IFNULL(a.DataAnalyze, 0)
            FROM `113-ntub113506`.FamilyLink fl
            JOIN `113-ntub113506`.Family f ON fl.FamilyID = f.FamilyID
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            LEFT JOIN `113-ntub113506`.Access a ON f.FamilyID = a.FamilyID
            WHERE fl.SubUserID = %s
            """,
            (MemID,),
        )
        MainUsers = cursor.fetchall()

        if not MainUsers:
            cursor.execute(
                """
                SELECT m.MemID, m.MemName, IFNULL(a.DataAnalyze, 0) 
                FROM `113-ntub113506`.Member m
                LEFT JOIN `113-ntub113506`.Access a ON f.FamilyID = a.FamilyID
                WHERE m.MemID = %s
                """,
                (MemID,),
            )
            MainUsers = cursor.fetchall()
            DataAnalyze = 0
        else:
            for user in MainUsers:
                if user[0] == MainUser:
                    DataAnalyze = user[2]
                    break

    data_url = "all" if is_all else "mem"
    data = {
        "Title": title,
        "analyze": analyze,
        "All": {"url": "all_weekly", "name": "週報"} if not is_all else {"url": "mem_weekly", "name": "主頁"},
        "weekly": {"url": f"{data_url}_weekly", "name": "週"},
        "monthly": {"url": f"{data_url}_monthly", "name": "月"},
        "yearly": {"url": f"{data_url}_yearly", "name": "年"},
        "DataAnalyze": DataAnalyze,
    }
    return render_template("/analyze/analyze.html", data=data, MainUsers=MainUsers, Whose=MainUser, is_all=is_all)

def register_routes():
    analysis_routes = [
        ('all_weekly', '全體資料彙整', '當週全體分析', True),
        ('all_monthly', '全體資料彙整', '當月全體分析', True),
        ('all_yearly', '全體資料彙整', '當年全體分析', True),
        ('mem_weekly', '個人資料彙整', '當週個人分析', False),
        ('mem_monthly', '個人資料彙整', '當月個人分析', False),
        ('mem_yearly', '個人資料彙整', '當年個人分析', False),
        ('all_weekly_prev', '全體資料彙整', '上週全體分析', True),
        ('all_monthly_prev', '全體資料彙整', '上個月全體分析', True),
        ('all_yearly_prev', '全體資料彙整', '去年全體分析', True),
        ('mem_weekly_prev', '個人資料彙整', '上週個人分析', False),
        ('mem_monthly_prev', '個人資料彙整', '上個月個人分析', False),
        ('mem_yearly_prev', '個人資料彙整', '去年個人分析', False),
    ]

    data_routes = [
        ('all_weekly_data', 'weekly', True, False),
        ('all_monthly_data', 'monthly', True, False),
        ('all_yearly_data', 'yearly', True, False),
        ('mem_weekly_data', 'weekly', False, False),
        ('mem_monthly_data', 'monthly', False, False),
        ('mem_yearly_data', 'yearly', False, False),
        ('all_prev_weekly_data', 'weekly', True, True),
        ('all_prev_monthly_data', 'monthly', True, True),
        ('all_prev_yearly_data', 'yearly', True, True),
        ('mem_prev_weekly_data', 'weekly', False, True),
        ('mem_prev_monthly_data', 'monthly', False, True),
        ('mem_prev_yearly_data', 'yearly', False, True),
    ]

    for route, title, analyze, is_all in analysis_routes:
        view_func = (
            lambda title=title, analyze=analyze, is_all=is_all: render_analyze_template(title, analyze, is_all)
        )
        view_func.__name__ = route
        analyze_bp.route(f"/{route}")(login_required(view_func) if not is_all else view_func)

    for route, period, is_all, prev_period in data_routes:
        view_func = (
            lambda period=period, is_all=is_all, prev_period=prev_period: (
                jsonify(fetch_period_data(period, None, prev_period) if is_all else fetch_member_data(period, prev_period))
            )
        )
        view_func.__name__ = route
        analyze_bp.route(f"/{route}")(login_required(view_func))

register_routes()

def fetch_data(cursor, period='weekly', FamilyID=None, prev_period=False):
    family_condition = "AND l.FamilyID = %s" if FamilyID else ""
    family_param = (FamilyID,) if FamilyID else ()

    period_condition = {
        'weekly': 'WEEK(l.LocationTime, 1) = WEEK(CURRENT_DATE, 1) - 1' if prev_period else 'WEEK(l.LocationTime, 1) = WEEK(CURRENT_DATE, 1)',
        'monthly': 'MONTH(l.LocationTime) = MONTH(CURRENT_DATE) - 1' if prev_period else 'MONTH(l.LocationTime) = MONTH(CURRENT_DATE)',
        'yearly': 'YEAR(l.LocationTime) = YEAR(CURRENT_DATE) - 1' if prev_period else 'YEAR(l.LocationTime) = YEAR(CURRENT_DATE)',
    }[period]

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
                WHERE YEAR(LocationTime) = YEAR(CURRENT_DATE)
                AND {period_condition}
                AND a.DataAnalyze = 1
                {family_condition}
                GROUP BY n
            ) Weekly ON Days.n = Weekly.n;
        """,
        'monthly': """
            WITH RECURSIVE Days AS (
                SELECT 1 AS n
                UNION ALL
                SELECT n + 1 FROM Days WHERE n <= DAY(LAST_DAY(NOW()))
            )
            SELECT 
                Days.n, 
                IFNULL(Monthly.CountPerMonth, 0) AS CountPerMonth
            FROM 
                Days
            LEFT JOIN (
                SELECT DAYOFMONTH(LocationTime) AS n, COUNT(*) AS CountPerMonth
                FROM `113-ntub113506`.SOS s
                LEFT JOIN `113-ntub113506`.Location l ON s.LocatNo = l.LocatNo
                LEFT JOIN `113-ntub113506`.Access a ON l.FamilyID = a.FamilyID
                WHERE YEAR(LocationTime) = YEAR(NOW()) 
                AND {period_condition}
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
                WHERE {period_condition}
                AND a.DataAnalyze = 1
                {family_condition}
                GROUP BY n
            ) Yearly ON Months.n = Yearly.n
            ORDER BY Months.n;
        """
    }

    cursor.execute(query_templates[period].format(family_condition=family_condition, period_condition=period_condition), family_param)
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
            AND YEAR(l.LocationTime) = YEAR(CURRENT_DATE)
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
            AND YEAR(l.LocationTime) = YEAR(CURRENT_DATE)
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

def fetch_period_data(period, FamilyID=None, prev_period=False):
    with db.get_connection() as conn:
        cursor = conn.cursor()
        return fetch_data(cursor, period, FamilyID, prev_period)

def fetch_member_data(period='weekly', prev_period=False):
    MainUserID = session.get("MainUserID")

    if MainUserID:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT FamilyID
                FROM `113-ntub113506`.Family
                WHERE MainUserID = %s
                """,
                (MainUserID,),
            )
            FamilyID = cursor.fetchone()
            return fetch_data(cursor, period, FamilyID, prev_period)
    else:
        MemID = session.get("MemID")
        FamilyID = db.get_family_id(MemID)
        return fetch_period_data(period, FamilyID, prev_period)
