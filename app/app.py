import os
import cv2
import json
import random
from PIL import Image
from ollama import Client
from datetime import datetime
from paddleocr import PaddleOCR

from flask import Flask, render_template, session, request, jsonify, redirect, url_for
from flask_login import login_required
from linebot.models import FlexSendMessage
from utils import db
from services import (
    event_bp,
    hos_bp,
    analyze_bp,
    health_bp,
    linebot_bp,
    med_bp,
    set_bp,
    user_bp,
    scheduler,
    mqtt,
    login_manager,
    gps_bp,
    line_bot_api,
    sos_bp,
    ollama_bp
)
from config import Config

app = Flask(__name__)

app.config.from_object(Config())
app.register_blueprint(med_bp, url_prefix="/med")
app.register_blueprint(hos_bp, url_prefix="/hos")
app.register_blueprint(event_bp, url_prefix="/event")
app.register_blueprint(analyze_bp, url_prefix="/analyze")
app.register_blueprint(health_bp, url_prefix="/health")
app.register_blueprint(set_bp, url_prefix="/set")
app.register_blueprint(linebot_bp, url_prefix="/")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(gps_bp, url_prefix="/gps")
app.register_blueprint(sos_bp, url_prefix="/sos")
app.register_blueprint(ollama_bp, url_prefix="/ollama")

scheduler.init_app(app)
# mqtt.init_app(app)
login_manager.init_app(app)
clientAI = Client(host="http://localhost:11434")

@app.route("/")
def index():
    return render_template("index.html", intro="Here is SilverEase", liffid=db.LIFF_ID)


@app.route("/lostAndFound")
def lostAndFound():
    DevID = session.get("DevID")
    mqtt.publish(f"ESP32/{DevID}/newGPS", "")
    return render_template("lostAndFound.html")


@app.route("/lost_report", methods=["POST"])
def lost_report():
    DevID = session.get("DevID")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("select FamilyID,MainUserID from Family where DevID=%s",(DevID))
    res=cur.fetchone()
    FamilyID=res[0]
    MainUserID=res[1]
    cur.execute(
        "select SubUserID from FamilyLink Where FamilyID = %s", FamilyID)
        
    SubUserID = cur.fetchall()
    message = request.json["message"]
    userPro=line_bot_api.get_profile(MainUserID).as_json_dict()
    userName=userPro["displayName"]
    msg = FlexSendMessage(
        alt_text="遺失/走失通報",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://developers-resource.landpress.line.me/fx/img/01_1_cafe.png",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
                "action": {"type": "uri", "uri": "https://line.me/"},
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"已有人通報{userName}\n裝置遺失/長者走失",
                        "weight": "bold",
                        "size": "xl",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [{"type": "text", "text": message}],
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "查看最後位置",
                            "uri": f"https://liff.line.me/{db.LIFF_ID}/sos/gps/{FamilyID}",
                        },
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "margin": "sm",
                    },
                ],
                "flex": 0,
            },
        },
    )

    for user in SubUserID:
        line_bot_api.push_message(user[0], msg)
    return jsonify({"status": "success"})


@app.route("/img/<img>")
def display_image(img):
    try:
        with Image.open(os.path.join("static", "imgs", "upload", img)) as file:
            file.load()
        return redirect(url_for("static", filename=f"imgs/upload/{img}"))
    except:
        return redirect(url_for("static", filename="imgs/notfound.png"))

@app.route('/medOcr', methods=["POST"])
def ollama():
    file = request.files.get("Pic")
    fileName = f"temp{random.randint(0,5)}.jpg"
    file.save(fileName)
    prompt = ocr_prompt(fileName)

    response = clientAI.generate(
        model="qwen2.5",
        prompt=prompt,
        format="json")

    print(response["response"])
    res = json.loads(response["response"])
    #print(res)
    return jsonify(res)


@app.route('/LineMsgHandle', methods=["POST"])
def lineMsgHandle():
    event = request.get_json()
    print(event["message"])
    prompt = handle_msg_prompt(event)
    response = clientAI.generate(
        model="gemma2",
        prompt=prompt,
        format="json")

    res = json.loads(response["response"])
    return jsonify(res)


def handle_msg_prompt(event):
    try:
        mentions = [user["userId"]
                    for user in event["message"]["mention"]["mentionees"]]
    except:
        mentions = []
    source = event["source"]["userId"]
    content = event["message"]["text"]

    prompt = """根據輸入的內容
    處理並擷取包含活動或回診的訊息
    不符合條件輸出 
    {"Type": false}
    
    符合則以JSON格式輸出以下內容
    {
        "Type":"event/hos",
        "UserID":"userId"(source or mentions),
        "Title":"標題",
        "Place":"地點",
        "Date":datetime()
    }
    回診額外加入
    {
        "Clinic":"科別"(先對應以下科別：[耳鼻喉科,一般內科,心臟內科,內分泌新陳代謝科,腫瘤科,胸腔內科,神經內科,腎臟內科,外科,骨科,復健科,呼吸內科,精神科,中醫])
        "Doctor":"醫師",
        "Num": int() #看診號碼
    }

    若為疑問句則輸出
    {
        "Type":"sql"
        "SubType":"event"|"hos"|"all",
        "UserID": "userId"(source or mentions),
        "duration":int() #時間範圍(天) 最近=3,週|禮拜=7,月|這月=30
    }

    以下為範例:
    ###
        input1:
            today:2022-09-01
            mentions: [userId1, userId2],
            source:userId0,
            content:今天天氣真好
        output1:
            {"Type": false}

        input2:
            today:2022-09-01
            mentions: [],
            source:userId0,
            content:明天下午三去臺大看精神科的陳醫生
        output2:
        {
            "Type":"hos",
            "UserID":"userId0",
            "Title":"看精神科的陳醫生",
            "Place":"臺大醫院",
            "Date": "2022-09-02 15:00:00" week,
            "Clinic":"精神科",
            "Doctor":"陳醫生",
            "Num":
        }

        input3:
            today:2022-09-01
            mentions: [userId1],
            source:userId2,
            content: @user1_Name 後天你生日喔 12.在北商學餐喔
        output3:
        {
            "Type":"event",
            "UserID":"userId1",
            "Title":"生日慶生",
            "Place":"北商學餐",
            "Date":"2022-09-03 12:00:00"
        }

        input4: 
            today:2022-09-01
            Mentions: [userId1],
            Source: userId0,
            Content:"@user1_Name最近有沒有什麼事?"
        output4:
        {
            "Type":"sql",
            "SubType":"all",
            "UserID":"userId1",
            "duration":3
        }
    ###
        
    input:
    """+f"""today:{datetime.now()}
        mentions: {mentions},
        source:{source},
        content:{content}
    output:
    """
    return prompt


def ocr_prompt(file):
    ocr = PaddleOCR(lang='ch', use_gpu=True)
    img = cv2.imread(file, cv2.IMREAD_COLOR)
    res_img = cv2.resize(img, (0, 0), fx=.5, fy=.5)
    gray_img = cv2.cvtColor(res_img, cv2.COLOR_RGB2GRAY)
    fil = cv2.bilateralFilter(gray_img, 25, 9, 25)
    ada_inv = cv2.adaptiveThreshold(
        fil, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 20)

    cv2.imwrite(file, fil)

    img_path = file

    result = ocr.ocr(img_path)

    res = result[0]
    txts = [line[1][0] for line in res]
    print(txts)

    prompt = """你是一位藥師
    統一使用'繁體中文',英文
    1.'簡體中文'一律修改為'繁體中文'(如:医院->醫院, 后->後, 忆->憶)
    2.根據輸入資料產生正確的藥單資訊
    3.英文藥品有誤要更正
    以上越精準完成對患者越有幫助

    輸出內容:
    {
        hospital: "醫院名稱",
        age: int(),
        gender: "性別",
        medicine:{
            藥名:["藥品名稱1", "藥品名稱2", "藥品名稱3"],
            數量:[int(), int(), int()],
            用法:["用法1", "用法2", "用法3"],
            天數:[int(), int(), int()],
            備註:["備註", "備註", "備註"]
        }
    }
    請注意數量>天數

    下面是輸入範例及輸出範例
    """+f"{db.medOcrData}"+"""
    
    input:
    ###
    """+f"{txts}"+"""
    ###
    output:   
    """
    return prompt

if __name__ == "__main__":
    app.run(debug=1)
