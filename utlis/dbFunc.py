from random import random
from utlis.db import get_connection

def get_codeID(familyID):
  conn=get_connection()
  cur=conn.cursor()
  res=cur.execute("select CodeID from FamilyCode where FamilyID=%s",(familyID))
  
  while not res:
    try:
      cur.execute("insert into FamilyCode (CodeID,FamilyID) value (%s,%s)",(codeID,familyID))
      conn.commit()
      break
    except:
      codeID=int(1000000*random())
  else:
    codeID=cur.fetchone()[0]
    
  conn.close
  return codeID