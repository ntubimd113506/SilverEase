from flask import Blueprint, render_template, request, session
from datetime import datetime
from utils import db

sos_bp = Blueprint("sos_bp", __name__)

@sos_bp.route("/sos_report/<SOSNo>")
def sos_report(SOSNo):
    session["SOSNo"] = SOSNo
    conn=db.get_connection()
    cur=conn.cursor()
    cur.execute("SELECT SOSType,SOSPlace,SOSDes,LocatNo FROM SOS WHERE SOSNo=%s",SOSNo)
    report=cur.fetchone()
    cur.execute("SELECT LocationTime From Location WHERE LocatNo=%s", report[-1])
    Time=cur.fetchone()[0].strftime("%Y.%m.%d %H:%M")
    cur.execute("SELECT * FROM SOSPlace")
    Place=cur.fetchall()
    cur.execute("SELECT * FROM SOSType")
    Type=cur.fetchall()
    return render_template("/sos/sos_report.html",Place=Place,Type=Type,report=report,Time=Time)

@sos_bp.route("/sos_report",methods=["POST"])
def sos_report_post():
    conn=db.get_connection()
    cur=conn.cursor()
    SOSNo=session["SOSNo"]
    try:
        SOSPlace=request.form["Place"]
    except:
        SOSPlace=None
    SOSType=request.form["Type"]
    SOSDes=request.form["Description"]
    res=cur.execute("UPDATE SOS SET SOSPlace=%s,SOSType=%s,SOSDes=%s WHERE SOSNo=%s",(SOSPlace,SOSType,SOSDes,SOSNo))
    conn.commit()

    return render_template("/sos/result.html",result=res,liffid=db.LIFF_ID,SOSNo=SOSNo)