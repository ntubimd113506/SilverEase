# $pip install pymysql
import pymysql
from random import random

line_use = "Main"

DB_HOST = "HOST_IP"
DB_NAME = "HOST_DB_NAME"
DB_USER = "USER_NAME"
DB_PASSWORD = "USER_PASSWORD"
SECRET_KEY = "Secret Key"
LINE_TOKEN = {"Main":"Channel Access Token", "Test":"Channel Access Token"}
LINE_HANDLER = {"Main":"Channel Secret", "Test":"Channel Secret"}
LIFF_ID = "LIFF ID (Tall)"
LIFF_ID_FULL = "LIFF ID (FULL)"

LINE_TOKEN = LINE_TOKEN[line_use]
LINE_HANDLER = LINE_HANDLER[line_use]

#prompt 輸出範例(已移除範例資料之個資)
medOcrData="""輸入範例1:
    ###
    [文字辨識內容]
    ### 
    輸出範例1:
    {
        "hospital": "範例醫院",
        "age": 99,
        "gender": "男",
        "medType": "其他",
        "medicine": {
            "藥名": ["藥品名稱"],
            "數量": [999],
            "用法": ["每天四次，三餐飯後及睡前"],
            "天數": [3],
            "備註": ["備註1","備註2","備註3"]
            }
    } 
    """


def get_connection():
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASSWORD,
        database=DB_NAME)
    return connection


def get_codeID(familyID):
    conn = get_connection()
    cur = conn.cursor()
    res = cur.execute(
        "select CodeID from FamilyCode where FamilyID=%s", (familyID))

    while not res:
        codeID = int(1000000 * random())
        try:
            cur.execute(
                "insert into FamilyCode (CodeID,FamilyID) value (%s,%s)",
                (codeID, familyID),
            )
            cur.execute(
                """CREATE EVENT IF NOT EXISTS Del_CodeID_%s 
                ON SCHEDULE AT CURRENT_TIMESTAMP + INTERVAL 30 MINUTE 
                DO 
                DELETE FROM `113-ntub113506`.`FamilyCode` WHERE CodeID='%s'""",
                (codeID, codeID),
            )
            conn.commit()
            break
        except:
            pass
    else:
        codeID = cur.fetchone()[0]

    conn.close
    return codeID

def get_memo_info(MemoID):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Memo WHERE MemoID=%s", MemoID)
    res = cur.fetchone()
    data = {cur.description[i][0]: res[i] for i in range(len(res))}

    subMemo = data["MemoType"]

    if subMemo == "1":
        cur.execute("SELECT * FROM Med WHERE MemoID=%s", MemoID)
    elif subMemo == "2":
        cur.execute("SELECT * FROM Hos WHERE MemoID=%s", MemoID)
    elif subMemo == "3":
        cur.execute("SELECT * FROM EventMemo WHERE MemoID=%s", MemoID)

    res = cur.fetchone()
    for i in range(len(res)):
        data[cur.description[i][0]] = res[i]

    cur.execute("SELECT MainUserID FROM Family WHERE FamilyID=%s", data["FamilyID"])
    res = cur.fetchone()
    data["MainUser"] = res[0]

    cur.execute(
        "SELECT MemName FROM Member m LEFT JOIN Family f on m.MemID = f.MainUserID WHERE FamilyID=%s",
        data["FamilyID"],
    )
    res = cur.fetchone()
    data["MainUserName"] = res[0]

    cur.execute("SELECT SubUserID FROM FamilyLink WHERE FamilyID=%s", data["FamilyID"])
    data["SubUser"] = [k[0] for k in cur.fetchall()]

    return data


def get_connection():
    connection = pymysql.connect(
        host=DB_HOST, user=DB_USER, passwd=DB_PASSWORD, database=DB_NAME
    )
    return connection


def get_codeID(familyID):
    conn = get_connection()
    cur = conn.cursor()
    res = cur.execute("select CodeID from FamilyCode where FamilyID=%s", (familyID))

    while not res:
        codeID = int(1000000 * random())
        try:
            cur.execute(
                "insert into FamilyCode (CodeID,FamilyID) value (%s,%s)",
                (codeID, familyID),
            )
            cur.execute(
                """CREATE EVENT IF NOT EXISTS Del_CodeID_%s 
                ON SCHEDULE AT CURRENT_TIMESTAMP + INTERVAL 30 MINUTE 
                DO 
                DELETE FROM `113-ntub113506`.`FamilyCode` WHERE CodeID='%s'""",
                (codeID, codeID),
            )
            conn.commit()
            break
        except:
            pass
    else:
        codeID = cur.fetchone()[0]

    conn.close
    return codeID


def get_memo_info(MemoID):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Memo WHERE MemoID=%s", MemoID)
    res = cur.fetchone()
    data = {cur.description[i][0]: res[i] for i in range(len(res))}

    subMemo = data["MemoType"]

    if subMemo == "1":
        cur.execute("SELECT * FROM Med WHERE MemoID=%s", MemoID)
    elif subMemo == "2":
        cur.execute("SELECT * FROM Hos WHERE MemoID=%s", MemoID)
    elif subMemo == "3":
        cur.execute("SELECT * FROM EventMemo WHERE MemoID=%s", MemoID)

    res = cur.fetchone()
    for i in range(len(res)):
        data[cur.description[i][0]] = res[i]

    cur.execute("SELECT MainUserID FROM Family WHERE FamilyID=%s", data["FamilyID"])
    res = cur.fetchone()
    data["MainUser"] = res[0]

    cur.execute(
        "SELECT MemName FROM Member m LEFT JOIN Family f on m.MemID = f.MainUserID WHERE FamilyID=%s",
        data["FamilyID"],
    )
    res = cur.fetchone()
    data["MainUserName"] = res[0]

    cur.execute("SELECT SubUserID FROM FamilyLink WHERE FamilyID=%s", data["FamilyID"])
    data["SubUser"] = [k[0] for k in cur.fetchall()]

    return data


def get_family_id(MemID):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(f.FamilyID, fl.FamilyID) AS FamilyID
            FROM `113-ntub113506`.Member m
            LEFT JOIN `113-ntub113506`.Family f ON f.MainUserID = m.MemID
            LEFT JOIN `113-ntub113506`.FamilyLink fl ON fl.SubUserID = m.MemID
            WHERE m.MemID = %s
            """,
            (MemID,),
        )
        FamilyID = cursor.fetchone()
        return FamilyID[0] if FamilyID else None
