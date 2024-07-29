import json, config
from flask_mqtt import Mqtt
from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db
from services import mqtt

gps_bp = Blueprint('gps_bp',__name__)

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
            SELECT m.MemID, m.MemName
            FROM `113-ntub113506`.FamilyLink fl
            JOIN `113-ntub113506`.Family f ON fl.FamilyID = f.FamilyID
            JOIN `113-ntub113506`.Member m ON f.MainUserID = m.MemID
            WHERE fl.SubUserID = %s
            """,
            (MemID,),
        )
        MainUsers = cursor.fetchall() #長輩中文名

    cursor.close()
    conn.close()
    return render_template('/GPS/gps.html', liffid=db.LIFF_ID, MainUsers=MainUsers)

@gps_bp.route('/check')
@login_required
def check():
    MainUserID = request.args.get("MainUserID")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT FamilyID FROM Family WHERE MainUserID = %s',(MainUserID,))
    famID = cursor.fetchall() #取得familyID
    if famID:
        famID = famID[0]
    else:
        famID = None

    if famID:
        cursor.execute('SELECT Location FROM Location WHERE FamilyID = %s ORDER BY LocatNo DESC LIMIT 1', (famID,))
        latest_location = cursor.fetchone()
    else:
        latest_location = None
            
    cursor.close()
    conn.close()

    # 如果資料庫中有數據，將最新的 GPS URL 傳遞給模板，否則傳遞 "no_data"
    url = latest_location[0] if latest_location else "no_data"
    render_template('/GPS/gpsurl.html', liffid=db.LIFF_ID, url=url)