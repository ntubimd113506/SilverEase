from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

health_bp = Blueprint("health_bp", __name__)

@health_bp.route("/")
def health():
    return render_template("/health/health_index.html")

@health_bp.route("/self")
def health_self():
    return render_template("/health/health.html")

@health_bp.route("/<category>")
def health_category(category):
    data = {
        "death": {
            "title": "十大死因",
            "items": [
                {"name": "惡性腫瘤(癌症)", "image": "D1.png"},
                {"name": "心臟疾病", "image": "D2.png"},
                {"name": "肺炎", "image": "D3.png"},
                {"name": "腦血管疾病", "image": "D4.png"},
                {"name": "糖尿病", "image": "D5.png"},
                {"name": "嚴重特殊傳染性肺炎(COVID-19)", "image": "D6.png"},
                {"name": "高血壓性疾病", "image": "D7.png"},
                {"name": "事故傷害", "image": "D8.png"},
                {"name": "慢性下呼吸道疾病", "image": "D9.png"},
                {"name": "腎炎、腎病症候群及腎病變", "image": "D10.png"},
            ]
        },
        "chronic": {
            "title": "十大慢性病",
            "items": [
                {"name": "高血壓", "image": "C1.png"},
                {"name": "糖尿病", "image": "C2.png"},
                {"name": "高血脂", "image": "C3.png"},
                {"name": "冠心病", "image": "C4.png"},
                {"name": "腦中風", "image": "C5.png"},
                {"name": "腎臟疾病", "image": "C6.png"},
                {"name": "慢性阻塞性肺病（COPD）", "image": "C7.png"},
                {"name": "癌症", "image": "C8.png"},
                {"name": "肝病", "image": "C9.png"},
                {"name": "骨質疏鬆症", "image": "C10.png"},
            ]
        },
        "precaution": {
            "title": "防疫專區",
            "items": [
                {"name": "手部清潔", "image": "P1.png"},
                {"name": "如何正確配戴口罩", "image": "P2.png"},
            ]
        }
    }

    return render_template("/health/health.html", title=data[category]["title"], items=data[category]["items"])
