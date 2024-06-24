from flask import Blueprint
from .med.app import med_bp
from .hos.app import hos_bp
from .event.app import event_bp
from .cam.app import cam_bp
from .set.app import set_bp
from .mqtt.app import mqtt_bp
from .line.app import linebot_bp

services_bp = Blueprint('services_bp', __name__)

services_bp.register_blueprint(med_bp, url_prefix="/med")
services_bp.register_blueprint(hos_bp, url_prefix="/hos")
services_bp.register_blueprint(event_bp, url_prefix="/event")
services_bp.register_blueprint(cam_bp, url_prefix="/cam")
services_bp.register_blueprint(set_bp, url_prefix="/set")
services_bp.register_blueprint(mqtt_bp, url_prefix='/mqtt')
services_bp.register_blueprint(linebot_bp, url_prefix="/linebot")