from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from datetime import datetime
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
        return render_template("/analyze/analyze_index.html", Title="資料彙整", Index="", IndexName="", All="All", AllName="週報", SOS="SOS", SOSName="求救", Location="Location", LocationName="足跡", Create="Create", CreateName="新增排程", Respond="", RespondName="")
    else:
        return render_template("/analyze/analyze_index.html", Title="資料彙整", Index="", IndexName="", All="All", AllName="週報", SOS="SOS", SOSName="求救", Location="Location", LocationName="足跡", Create="Create", CreateName="新增排程", Respond="Respond", RespondName="接收通知")

@analyze_bp.route("/all_weekly")
@login_required
def get_weekly_data():
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

    conn.close()

    return jsonify({
        "sos_data": sos_data,
        "memo_data": memo_data
    })

