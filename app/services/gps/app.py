import json, config
from flask_mqtt import Mqtt
from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db
from services import mqtt

gps_bp = Blueprint('gps_bp',__name__)


@gps_bp.route('/')
def gps():

    # 發布 MQTT 消息以請求 GPS 數據
    mqtt.publish("/nowGPS", "Request GPS Data")

    # 從資料庫獲取最新的 GPS URL
    conn = db.get_connection()
    cursor = conn.cursor()
    family_id = request.args.get('FamilyID')  # 從URL參數獲取FamilyID
    cursor.execute('SELECT Location FROM Location WHERE FamilyID = %s ORDER BY LocationTime DESC LIMIT 1', (family_id,))
    latest_location = cursor.fetchone()
    cursor.close()
    conn.close()

    # 如果資料庫中有數據，將最新的 GPS URL 傳遞給模板，否則傳遞 "no_data"
    url = latest_location[0] if latest_location else "no_data"

    return render_template('/GPS/gps.html', liffid=db.LIFF_ID, url=url)