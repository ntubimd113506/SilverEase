import json
from flask import (
    request,
    render_template,
    Blueprint,
    session,
    url_for,
    redirect,
    jsonify,
)
from flask_login import login_required
from utils import db
from services import mqtt, line_bot_api

set_bp = Blueprint("set_bp", __name__)

# -----登入-----


@set_bp.route("/")
@login_required
def setting():
    # session["MemID"] = db.CHICHI
    MemID = session.get("MemID")
    conn = db.get_connection()
    cursor = conn.cursor()
    old = cursor.execute("SELECT FamilyID FROM Family where MainUserID = %s", (MemID))
    session["FamilyID"] = cursor.fetchone()[0] if old else None
    conn.close()
    return render_template("/set/index.html", liffid=db.LIFF_ID, old=old)


@set_bp.route("/get_code_id")
def get_code_id():
    FamilyID = session.get("FamilyID")
    if FamilyID is None:
        return redirect("/set/access_index")

    code_id = db.get_codeID(session.get("FamilyID"))
    return render_template("/set/old.html", liffid=db.LIFF_ID, code_id=code_id)


@set_bp.route("/join_family")
@set_bp.route("/join_family/<code>")
def join_family(code=""):
    return render_template("/set/young.html", code=code)


@set_bp.route("/CodeID", methods=["POST"])
def CodeID():
    conn = db.get_connection()

    cursor = conn.cursor()
    cursor1 = conn.cursor()
    cursor2 = conn.cursor()

    MemID = session.get("MemID")
    CodeID = request.values.get("CodeID")

    # 檢查 CodeID 是否存在於 FamilyCode 表中
    cursor.execute("SELECT FamilyID FROM FamilyCode WHERE CodeID = %s", (CodeID,))
    res = cursor.fetchone()

    if res is None:
        conn.close()
        return render_template("/set/noCodeID.html")

    FamilyID = res[0]

    # 檢查在 FamilyLink 表中是否已經存在此 CodeID 和 MemID 的連結
    cursor.execute(
        "SELECT * FROM FamilyLink WHERE FamilyID = %s AND SubUserID = %s",
        (FamilyID, MemID),
    )
    che = cursor.fetchone()

    if che:
        conn.close()
        return render_template("/set/repet.html")
    else:
        cursor.execute(
            "INSERT INTO FamilyLink (FamilyID, SubUserID) VALUES (%s, %s)",
            (FamilyID, MemID),
        )
        cursor1.execute(
            "SELECT MainUserID FROM Family WHERE FamilyID = %s", (FamilyID,)
        )
        old1 = cursor1.fetchone()
        oldID = old1[0]
        cursor2.execute("SELECT MemName FROM Member WHERE MemID = %s", (oldID,))
        old2 = cursor2.fetchone()
        old = old2[0]
        conn.commit()
        conn.close()
        return render_template("/set/YesCodeID.html", old=old)


@set_bp.route("/family_list")
def family_list():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Family WHERE MainUserID = %s", (session.get("MemID"),)
    )
    res = cursor.fetchone()
    MainFamily = (
        {cursor.description[i][0]: res[i] for i in range(len(res))} if res else None
    )
    SubFamilys = []
    cursor.execute(
        "SELECT * FROM Family WHERE FamilyID in (SELECT FamilyID FROM FamilyLink WHERE SubUserID = %s)",
        (session.get("MemID"),),
    )
    for res in cursor.fetchall():
        SubFamilys.append({cursor.description[i][0]: res[i] for i in range(len(res))})
    conn.close()

    if MainFamily:
        session["MainFamilyID"] = MainFamily["FamilyID"]
        MainInfo = line_bot_api.get_profile(MainFamily["MainUserID"]).as_json_dict()
        MainFamily["Name"] = MainInfo["displayName"]
        MainFamily["Picture"] = MainInfo["pictureUrl"]

    for SubFamily in SubFamilys:
        SubInfo = line_bot_api.get_profile(SubFamily["MainUserID"]).as_json_dict()
        SubFamily["Name"] = SubInfo["displayName"]
        SubFamily["Picture"] = SubInfo["pictureUrl"]

    return render_template(
        "/set/family_list.html", MainFamily=MainFamily, SubFamilys=SubFamilys
    )


@set_bp.route("/family_delete", methods=["Delete"])
def delete_family():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "Delete FROM Family WHERE FamilyID = %s", (session.get("MainFamilyID"),)
    )
    conn.commit()
    conn.close()
    session["MainFamilyID"] = ""
    return jsonify({"status": "success"})


@set_bp.route("/family_leave", methods=["Delete"])
def leave_family():
    FamilyID = request.json["FamilyID"]
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "Delete FROM FamilyLink WHERE SubUserID = %s AND FamilyID= %s",
        (session.get("MemID"), FamilyID),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@set_bp.route("/qrcode")
@login_required
def scanner():
    return render_template("scanner.html", liffid=db.LIFF_ID_FULL)


@set_bp.route("/device/<DevID>")
def device_index(DevID):
    session["DevID"] = DevID
    if devToFam(DevID):
        return redirect("/lostAndFound")
    else:
        return redirect("/set/device/setting")


@set_bp.route("/device/setting")
# @login_required
def device_setting():
    DevID = session["DevID"]
    return render_template("/set/device_setting.html", DevID=DevID, liffid=db.LIFF_ID)


@set_bp.route("/device/submit", methods=["POST"])
def add_device():
    DevID = request.form.get("DevID")
    FamilyCode = request.form.get("FamilyCode")
    mqtt.publish(f"ESP32/{DevID}/setLink", str(FamilyCode))
    return render_template("/set/device_check.html", liffid=db.LIFF_ID)


@set_bp.route("/access_index")
def access_check():
    res = ""
    if session.get("FamilyID"):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM Access WHERE FamilyID = %s", (session.get("FamilyID"),)
        )
        res = cur.fetchone()
        conn.close()
        res = {cur.description[i][0]: res[i] for i in range(len(res))}
    return render_template("/set/access_index.html", res=res)


@set_bp.route("/access/submit", methods=["POST"])
def access_submit():
    MemID = session.get("MemID")
    gps = True if request.form.get("GPS") else False
    DataAnalyze = True if request.form.get("DataAnalyze") else False
    # return f"{gps},{DataAnalyze}"
    conn = db.get_connection()
    cur = conn.cursor()
    if session.get("FamilyID"):
        cur.execute(
            "UPDATE Access SET GPS = %s, DataAnalyze=%s WHERE FamilyID = %s",
            (gps, DataAnalyze, session.get("FamilyID")),
        )
        url = "/set/family_list"
    else:
        cur.execute("INSERT INTO Family (MainUserID) VALUES (%s)", (MemID))
        cur.execute("SELECT FamilyID FROM Family WHERE MainUserID = %s", (MemID,))
        session["FamilyID"] = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO  Access (FamilyID, GPS, DataAnalyze) VALUES (%s, %s, %s)
            """,
            (session.get("FamilyID"), gps, DataAnalyze),
        )
        url = "/set/get_code_id"
    conn.commit()
    conn.close()
    return redirect(url)


def devToFam(DevID):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT FamilyID FROM Family WHERE DevID=%s", (DevID,))
    res = cur.fetchone()
    if res:
        return res[0]
    return False


@set_bp.route("/get_line_info")
def get_line_info():
    SubFamilys = session.get("SubFamilys")
    # return f"{SubFamilys}"
    for SubFamily in SubFamilys:
        SubInfo = line_bot_api.get_profile(SubFamily["MainUserID"]).as_json_dict()
        # return f"{SubInfo}"
        SubFamily["Name"] = SubInfo["displayName"]
        SubFamily["Picture"] = SubInfo["pictureUrl"]

    return jsonify(SubFamilys)


def check_member_exists(MemID):  # 確認使用者資料是否存在資料庫中
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Member WHERE MemID = %s", (MemID,))
    member = (
        cursor.fetchone()
    )  # 使用 fetchone() 取得查詢結果的第一行資料，如果沒有符合的資料會返回 None

    conn.close()

    return member is not None


@set_bp.route("/oy", methods=["POST"])
def identity():
    if request.form.get("option") == "old":
        # 建立資料庫連線
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor1 = conn.cursor()

        MemID = request.values.get("MemID")
        MemName = request.values.get("MemName")

        while 1:
            cursor.execute("SELECT FamilyID FROM Family where MainUserID = %s", (MemID))
            data = cursor.fetchone()

            if data != None:
                code_id = db.get_codeID(data[0])
                break
            else:
                cursor.execute(
                    "INSERT INTO Member (MemID, MemName) VALUES (%s, %s)",
                    (MemID, MemName),
                )
                conn.commit()
                cursor1.execute("INSERT INTO Family (MainUserID) VALUES (%s)", (MemID))
                conn.commit()

        conn.close()
        return render_template("/set/old.html", data=data, code_id=code_id)

    if request.form.get("option") == "young":
        # 資料加入資料庫
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor1 = conn.cursor()

        MemID = request.values.get("MemID")
        MemName = request.values.get("MemName")

        if check_member_exists(MemID):
            # 資料已存在，執行相應的處理
            return render_template("/set/young.html", MemID=MemID)
        else:
            # 資料不存在，將使用者資料新增至資料庫
            cursor.execute(
                "INSERT INTO Member (MemID, MemName) VALUES (%s, %s)", (MemID, MemName)
            )
            conn.commit()

        conn.close()
        return render_template("/set/young.html", MemID=MemID)


@set_bp.route("/young")
def young():
    return render_template("/set/young.html")


@set_bp.route("/checkid", methods=["POST"])  # 確認使用者資料
def checkid():
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # 獲取使用者的MemID
        data = json.loads(request.get_data(as_text=True))
        MemID = data["MemID"]

        # ==================  ==================

        """https://ithelp.ithome.com.tw/m/articles/10300064"""

        # ==================  ==================
        cursor.execute("SELECT MainUserID FROM Family WHERE MainUserID = %s", (MemID))
        member_data = cursor.fetchone()
        cursor.execute("SELECT SubUserID FROM FamilyLink WHERE SubUserID = %s", (MemID))
        family_link_data = cursor.fetchone()

        conn.close()
        # 檢查是否是長輩
        if member_data != None:
            return json.dumps({"result": 1, "option": "old"})
        # 檢查是否是子女
        if family_link_data != None:
            return json.dumps({"result": 1, "option": "young"})
        else:
            return json.dumps({"result": 0}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": "TryError"}, ensure_ascii=False)
