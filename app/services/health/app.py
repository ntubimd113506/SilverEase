from flask import request, render_template, Blueprint, session, jsonify
from flask_login import login_required
from utils import db

health_bp = Blueprint("health_bp", __name__)


@health_bp.route("/")
def health():
    return render_template("/health/health_index.html")


@health_bp.route("/self")
@login_required
def health_self():
    MemID = session.get("MemID")

    conn = db.get_connection()
    cursor = conn.cursor()

    if MemID:
        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, l.FamilyID) AS A_FamilyID
            FROM `113-ntub113506`.Member m 
            LEFT JOIN `113-ntub113506`.Family as f ON m.MemID = f.MainUserID 
            LEFT JOIN `113-ntub113506`.FamilyLink as l ON m.MemID = l.SubUserID
            WHERE MemID = %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchone()[0]

    cursor.execute(
        """
            SELECT Title, COUNT(*) AS Count 
            FROM `113-ntub113506`.Memo 
            WHERE Title IN ('感冒藥', '頭痛藥', '止痛藥', '高血壓藥物', '糖尿病藥物', '心臟病藥物', '降膽固醇藥物', '抗凝劑', '抗血小板藥物', '癌症藥物') 
            AND FamilyID = %s
            GROUP BY Title 
            ORDER BY Count DESC;
            """,
        (FamilyID,),
    )
    medicine_counts = cursor.fetchall()

    cursor.execute(
        """
            SELECT Clinic, COUNT(*) AS Count 
            FROM `113-ntub113506`.Memo m
            LEFT JOIN `113-ntub113506`.Hos h ON m.MemoID = h.MemoID
            WHERE Clinic IN ('耳鼻喉科', '一般內科', '心臟內科', '內分泌新陳代謝科', '腫瘤科', '胸腔內科', '神經內科', '腎臟內科', '外科', '骨科', '復健科', '呼吸內科', '精神科', '中醫') 
            AND FamilyID = %s
            GROUP BY Clinic 
            ORDER BY Count DESC;
            """,
        (FamilyID,),
    )
    clinic_counts = cursor.fetchall()

    conn.close()

    symptom_mapping = {
        "惡性腫瘤(癌症)": {"腫瘤科": "癌症藥物"},
        "心臟疾病": {"心臟內科": "心臟病藥物"},
        "肺炎": {"胸腔內科": ""},
        "腦血管疾病": {"神經內科": ""},
        "糖尿病": {"內分泌新陳代謝科": "糖尿病藥物"},
        "事故傷害": {"外科": "止痛藥", "復健科": "止痛藥"},
        "慢性下呼吸道疾病": {"胸腔內科": "", "呼吸內科": ""},
        "腎炎、腎病症候群及腎病變": {"腎臟內科": ""},
        "高血壓": {"心臟內科": "高血壓藥物", "內分泌新陳代謝科": "高血壓藥物"},
        "高血脂": {"心臟內科": "降膽固醇藥物", "內分泌新陳代謝科": "降膽固醇藥物"},
        "冠心病": {"心臟內科": "心臟病藥物"},
        "腦中風": {"神經內科": "抗凝劑", "神經內科": "抗血小板藥物"},
        "腎臟疾病": {"腎臟內科": ""},
        "慢性阻塞性肺病（COPD）": {"胸腔內科": "", "呼吸內科": ""},
        "癌症": {"腫瘤科": "癌症藥物"},
        "骨質疏鬆症": {"內分泌新陳代謝科": "", "骨科": ""},
    }

    symptom_counts = {}
    for symptom, clinics in symptom_mapping.items():
        total_count = 0
        for clinic, medicine in clinics.items():
            clinic_count = next((c[1] for c in clinic_counts if c[0] == clinic), 0)
            medicine_count = next(
                (m[1] for m in medicine_counts if m[0] == medicine), 0
            )
            total_count += clinic_count + medicine_count
        if total_count > 0:
            symptom_counts[symptom] = total_count

    sorted_symptom_counts = sorted(
        symptom_counts.items(), key=lambda x: x[1], reverse=True
    )

    if len(sorted_symptom_counts) < 3:
        sorted_symptom_counts.append(("手部清潔", 0))
        sorted_symptom_counts.append(("如何正確配戴口罩", 0))

    image_data = {
        "惡性腫瘤(癌症)": "D1.png",
        "心臟疾病": "D2.png",
        "肺炎": "D3.png",
        "腦血管疾病": "D4.png",
        "糖尿病": "C5.png",
        "事故傷害": "D8.png",
        "慢性下呼吸道疾病": "D9.png",
        "腎炎、腎病症候群及腎病變": "D10.png",
        "高血壓": "C1.png",
        "高血脂": "C3.png",
        "冠心病": "C4.png",
        "腦中風": "C5.png",
        "腎臟疾病": "C6.png",
        "慢性阻塞性肺病（COPD）": "C7.png",
        "癌症": "C8.png",
        "骨質疏鬆症": "C10.png",
        "手部清潔": "P1.png",
        "如何正確配戴口罩": "P2.png",
    }

    image_items = [
        {"name": symptom, "image": image_data.get(symptom, "")}
        for symptom, count in sorted_symptom_counts
    ]

    return render_template("/health/self_health.html", image_items=image_items)


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
            ],
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
            ],
        },
        "precaution": {
            "title": "防疫專區",
            "items": [
                {"name": "手部清潔", "image": "P1.png"},
                {"name": "如何正確配戴口罩", "image": "P2.png"},
            ],
        },
    }

    return render_template(
        "/health/health.html",
        title=data[category]["title"],
        items=data[category]["items"],
    )
