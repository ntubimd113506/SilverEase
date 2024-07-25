import json, config
from flask_mqtt import Mqtt
from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db
from services import mqtt

gps_bp = Blueprint('gps_bp',__name__)


@gps_bp.route('/')
def gps():
    mqtt.publish("/nowGPS", "Request GPS Data")
    return render_template('/GPS/gps.html', liffid=db.LIFF_ID)


