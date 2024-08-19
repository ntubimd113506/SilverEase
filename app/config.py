import os
from utils import db
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


class Config:
    MQTT_BROKER_URL = 'silverease.ntub.edu.tw'  # 您的 MQTT 代理地址
    MQTT_BROKER_PORT = 8883  # MQTT 代理端口
    MQTT_USERNAME = ''  # MQTT 用戶名
    MQTT_PASSWORD = ''  # MQTT 密碼
    MQTT_KEEPALIVE = 60  # KeepAlive 週期，以秒為單位
    MQTT_TLS_ENABLED = True  # 啟用 TLS 加密
    MQTT_TLS_CA_CERTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ca', 'my-ca.crt')
    MQTT_TLS_VERSION = 5
    # MQTT_CLIENT_ID = 'flask_mqtt'
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOBSTORES  = {'default':SQLAlchemyJobStore(url=f'sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)),"services","scheduler","jobstore","scheduler.db")}')}
    SECRET_KEY = db.SECRET_KEY
