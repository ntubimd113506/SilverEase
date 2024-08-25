from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db
from services import mqtt
import re
import folium


gps_bp = Blueprint('gps_bp', __name__)

#Line Bot定位選單
@gps_bp.route('/')
@login_required
def gps():
    MemID = session.get("MemID")
    MainUser = session.get("MainUserID")
    GPS = True
    show_full_no_access = False

    mqtt.publish("/nowGPS", "Request GPS Data")
    conn = db.get_connection()
    cursor = conn.cursor()

    if MemID:
        cursor.execute(
            """
            SELECT m.MemID, m.MemName, IFNULL(a.DataAnalyze, 0)
            FROM `113-ntub113506`.Family f
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            LEFT JOIN `113-ntub113506`.Access a ON f.FamilyID = a.FamilyID
            WHERE f.MainUserID = %s
            UNION
            SELECT m.MemID, m.MemName, IFNULL(a.DataAnalyze, 0)
            FROM `113-ntub113506`.FamilyLink fl
            JOIN `113-ntub113506`.Family f ON fl.FamilyID = f.FamilyID
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            LEFT JOIN `113-ntub113506`.Access a ON f.FamilyID = a.FamilyID
            WHERE fl.SubUserID = %s
            """,
            (MemID, MemID),
        )
        MainUsers = cursor.fetchall()

        if not MainUsers:
            cursor.execute(
                """
                SELECT m.MemID, m.MemName, IFNULL(a.DataAnalyze, 0) 
                FROM `113-ntub113506`.Member m
                LEFT JOIN `113-ntub113506`.Family f ON f.MainUserID = m.MemID
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

        if MainUser == MemID and not DataAnalyze:
            show_full_no_access = True


    cursor.close()
    conn.close()

    data = {
        "show_full_no_access": show_full_no_access,
        "GPS": GPS,
    }

    return render_template(
        "/GPS/gps.html",
        MainUsers=MainUsers,
        Whose=MainUser,
        data=data
    )

#即時定位
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

#查看長輩足跡
@gps_bp.route('/foot', methods=['POST'])
def foot():
    MainUserID = request.form.get("MainUserID")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT MemName FROM `113-ntub113506`.Member WHERE MemID = %s', (MainUserID,))
    result = cursor.fetchone()

    if result:
        name = result[0]
    else:
        name = "未知用戶"
    
    cursor.close()
    conn.close()
    
    return render_template('GPS/my_map.html', MainUserID=MainUserID, name=name)

#時間按鈕、清單處理
@gps_bp.route('/road', methods=['GET'])
def road():
    try:
        MainUserID = request.args.get("MainUserID")
        timePeriod = request.args.get("time")
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT FamilyID FROM `113-ntub113506`.Family WHERE MainUserID = %s", (MainUserID,))
        FamID = cursor.fetchone()
        if not FamID:
            return jsonify({"urls": []}), 404
        
        if timePeriod == 'all':
            query = "SELECT Location FROM `113-ntub113506`.Location WHERE FamilyID = %s"
            cursor.execute(query, (FamID[0],))
        else:
            days = int(timePeriod)
            query = """
                SELECT Location FROM `113-ntub113506`.Location 
                WHERE FamilyID = %s AND LocationTime >= NOW() - INTERVAL %s DAY
            """
            cursor.execute(query, (FamID[0], days))

        rows = cursor.fetchall()

        base_url = "https://www.google.com/maps/search/?api=1&query="
        urls = []
        for loc in rows:
            location = loc[0]
            if location.startswith("http://") or location.startswith("https://"):
                urls.append(location)
            else:
                urls.append(base_url + location)

        top_query = """
            SELECT Location, COUNT(*) as visit
            FROM `113-ntub113506`.Location
            WHERE FamilyID = %s
            GROUP BY Location
            ORDER BY visit DESC
        """
        cursor.execute(top_query, (FamID[0],))
        Location = cursor.fetchall()

        distinct_locations = []
        visited_set = set()

# 過濾掉重複的地點
        for loc in Location:
            if len(distinct_locations) >= 3:
                break
            coords = loc[0]
            if coords not in visited_set:
                distinct_locations.append({"Location": coords})
                visited_set.add(coords)

        cursor.close()
        conn.close()

        return jsonify({"urls": urls, "top_list": distinct_locations})
    
    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"error": str(e)}), 500
    


