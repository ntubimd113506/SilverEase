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
                {"name": "惡性腫瘤(癌症)", "image": "cancel.png"},
                {"name": "心臟疾病", "image": "code.png"},
                {"name": "肺炎", "image": "c.png"},
                {"name": "腦血管疾病", "image": "d.png"},
                {"name": "糖尿病", "image": "e.png"},
                {"name": "嚴重特殊傳染性肺炎(COVID-19)", "image": "f.png"},
                {"name": "高血壓性疾病", "image": "g.png"},
                {"name": "事故傷害", "image": "h.png"},
                {"name": "慢性下呼吸道疾病", "image": "i.png"},
                {"name": "腎炎、腎病症候群及腎病變", "image": "j.png"},
            ]
        },
        "chronic": {
            "title": "十大慢性病",
            "items": [
                {"name": "高血壓", "image": "1.png"},
                {"name": "糖尿病", "image": "2.png"},
                {"name": "高血脂", "image": "3.png"},
                {"name": "冠心病", "image": "4.png"},
                {"name": "腦中風", "image": "5.png"},
                {"name": "腎臟疾病", "image": "6.png"},
                {"name": "慢性阻塞性肺病（COPD）", "image": "7.png"},
                {"name": "癌症", "image": "8.png"},
                {"name": "肝病", "image": "9.png"},
                {"name": "骨質疏鬆症", "image": "10.png"},
            ]
        },
        "precaution": {
            "title": "防疫注意事項",
            "items": [
                {"name": "手部清潔", "image": "y.png"},
                {"name": "如何正確配戴口罩", "image": "z.png"},
            ]
        }
    }

    return render_template("/health/health.html", title=data[category]["title"], items=data[category]["items"])
