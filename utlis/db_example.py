#pip install pymysql
import pymysql

DB_HOST='140.131.114.242'  
DB_NAME='ntub113506'
DB_USER='113-ntub113506'
DB_PASSWORD='@imd113506NTUB' 
LINE_TOKEN='vzDtwf8h7fEZRRmzj4VimopZL0+T1YKif982hzSdorxlLoebj3pj/4FwFipwinhCz87gKYDRvwvWmsU5FJ+0LOhywd+LFkFSopjeArMGhyoDtH823BhMCOUxc0WVSPIfuDwNWbLCemZtEz88kCJhSQdB04t89/1O/w1cDnyilFU='
LINE_HANDLER="1d16422c3b78ca6b26335a808c5258b2"

def get_connection():
    connection=pymysql.connect(
    host=DB_HOST,  
    user=DB_USER, 
    passwd=DB_PASSWORD, 
    database=DB_NAME)
    return connection