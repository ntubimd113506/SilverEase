import json,requests
from flask import Blueprint, jsonify, request
from utils import db

ollama_bp = Blueprint("ollama", __name__)
host="http://127.0.0.1:80"

@ollama_bp.route("/accessCheck",methods=["POST"])
def accessCheck():
    MainUserID = request.form.get("MainUserID")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT FamilyID, Gender, Age
        FROM `113-ntub113506`.Family
        WHERE MainUserID = %s
        """,
        (MainUserID,),
    )

    res = cursor.fetchone()
    FamilyID = res[0]
    gender = True if res[1] is not None else False
    age = True if res[2] is not None else False
    
    cursor.execute("Select DataAnalyze from Access Where FamilyID = %s", FamilyID)
    conn.close()

    if res:
        return jsonify({"analyze": True,"gender":gender,"age":age})
    else:
        return jsonify({"analyze": False,"gender":gender,"age":age})

@ollama_bp.route("/analyzeImage",methods=["POST"])
def analyzeImage():
    file = request.files.get("Pic")
    res=requests.request("POST",f"{host}/medOcr",files={"Pic":file})
    res=json.loads(res.text)
    print(res)
    print(type(res))
    return jsonify(res)