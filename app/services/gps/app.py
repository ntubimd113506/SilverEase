from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db
from services import mqtt
import re
import folium


gps_bp = Blueprint('gps_bp', __name__)

@gps_bp.route('/')
@login_required
def gps():
    MemID = session.get("MemID")
    mqtt.publish("/nowGPS", "Request GPS Data")
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

    if MainUserInfo:
        MainUsers = [(MemID, MainUserInfo[1])]
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

    cursor.close()
    conn.close()
    return render_template('/GPS/gps.html', liffid=db.LIFF_ID, MainUsers=MainUsers)

@gps_bp.route('/check', methods=['POST'])
def check():
    MainUserID = request.form.get("MainUserID")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT FamilyID FROM `113-ntub113506`.Family WHERE MainUserID = %s', (MainUserID,))
    famID = cursor.fetchone()

    if famID:
        cursor.execute('SELECT Location FROM `113-ntub113506`.Location WHERE FamilyID = %s ORDER BY LocatNo DESC LIMIT 1', (famID[0],))
        latest_location = cursor.fetchone()
    else:
        latest_location = None
    
    cursor.close()
    conn.close()

    url = latest_location[0] if latest_location else "no_data"
    return jsonify({'url': url})

@gps_bp.route('/foot', methods=['POST'])
def foot():
    try:
        MainUserID = request.form.get("MainUserID")
        conn = db.get_connection()
        cursor = conn.cursor()

        # 查询 FamilyID
        cursor.execute("SELECT FamilyID FROM `113-ntub113506`.Family WHERE MainUserID = %s", (MainUserID,))
        FamID = cursor.fetchone()
        if not FamID:
            return "FamilyID not found for the given MainUserID", 404
        
        # 查询位置数据（URL）
        cursor.execute('SELECT Location FROM `113-ntub113506`.Location WHERE FamilyID = %s', (FamID[0],))
        rows = cursor.fetchall()
        print("Fetched rows:", rows)  # 调试输出

        cursor.close()
        conn.close()

        # 将查询结果中的URL提取出来
        if rows:
            urls = [loc[0] for loc in rows]  # rows 中的每一行是一个元组，loc[0] 是 Location 列的值
        else:
            urls = []

        return render_template('/GPS/my_map.html', urls=urls)
    
    except Exception as e:
        print("Error occurred:", str(e))  # 打印详细错误信息
        return f"An error occurred: {str(e)}", 500
