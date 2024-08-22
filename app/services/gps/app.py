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

    base_url = "https://www.google.com/maps/search/?api=1&query="
    url = base_url+latest_location[0] if latest_location else "no_data"
    return jsonify({'url': url})

@gps_bp.route('/foot', methods=['POST'])
def foot():
    MainUserID = request.form.get("MainUserID")

    return render_template('/GPS/my_map.html', MainUserID = MainUserID)
    
@gps_bp.route('/road', methods=['GET'])
def road():
    try:
        MainUserID = request.args.get("MainUserID")
        timePeriod = request.args.get("time")  # 獲取時間範圍參數
        conn = db.get_connection()
        cursor = conn.cursor()

        # 查詢 FamilyID
        cursor.execute("SELECT FamilyID FROM `113-ntub113506`.Family WHERE MainUserID = %s", (MainUserID,))
        FamID = cursor.fetchone()
        if not FamID:
            return jsonify({"urls": []}), 404
        
        # 根據時間範圍查詢位置數據
        if timePeriod == 'all':
            query = "SELECT Location FROM `113-ntub113506`.Location WHERE FamilyID = %s"
            cursor.execute(query, (FamID[0],))
        else:
            days = int(timePeriod)  # 將 timePeriod 轉換為整數天數
            query = """
                SELECT Location FROM `113-ntub113506`.Location 
                WHERE FamilyID = %s AND LocationTime >= NOW() - INTERVAL %s DAY
            """
            cursor.execute(query, (FamID[0], days))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # 提取 Location 列的數據
        base_url = "https://www.google.com/maps/search/?api=1&query="
        urls = []
        for loc in rows:
            location = loc[0]
            if location.startswith("http://") or location.startswith("https://"):
                urls.append(location)  # 若為網址，直接使用
            else:
                urls.append(base_url + location)  # 若為座標，組合成Google Maps URL

        return jsonify({"urls": urls})
    
    except Exception as e:
        print("Error occurred:", str(e))  # 打印詳細錯誤信息
        return jsonify({"error": str(e)}), 500
    


