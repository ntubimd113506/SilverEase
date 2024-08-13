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

        # 查詢 FamilyID
        cursor.execute("SELECT FamilyID FROM `113-ntub113506`.Family WHERE MainUserID = %s", (MainUserID,))
        FamID = cursor.fetchone()

        if not FamID:
            return jsonify({"success": False, "message": "Invalid MainUserID"}), 400

        # 查詢位置資料
        cursor.execute('SELECT Location FROM `113-ntub113506`.Location WHERE FamilyID = %s', (FamID[0],))
        rows = cursor.fetchall()

        pattern = r"query=(-?\d+\.\d+),(-?\d+\.\d+)"
        locations = []

        for row in rows:
            url = row[0]
            match = re.search(pattern, url)
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
                locations.append({"latitude": latitude, "longitude": longitude})

        if not locations:
            return jsonify({"success": False, "message": "No locations found"}), 404

        # 創建地圖
        mymap = folium.Map(location=[locations[0]["latitude"], locations[0]["longitude"]], zoom_start=13)

        for location in locations:
            folium.Marker(
                location=[location["latitude"], location["longitude"]],
                popup=f"Lat: {location['latitude']}, Lon: {location['longitude']}"
            ).add_to(mymap)

        folium.PolyLine([(loc["latitude"], loc["longitude"]) for loc in locations], color="blue").add_to(mymap)

        # 保存地圖
        map_dir = os.path.join('static', 'maps')
        if not os.path.exists(map_dir):
            os.makedirs(map_dir)
        
        map_path = os.path.join(map_dir, f"{MainUserID}_footprint_map.html")
        mymap.save(map_path)

        return jsonify({"success": True, "map_url": url_for('static', filename=f"maps/{MainUserID}_footprint_map.html")})

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"success": False, "message": "An error occurred while processing your request."}), 500

    finally:
        cursor.close()
        conn.close()

