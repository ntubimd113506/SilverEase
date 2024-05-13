from random import random
from utlis.db import get_connection


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
