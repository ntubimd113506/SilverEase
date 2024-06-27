# $pip install pymysql
import pymysql

DB_HOST='HOST_IP'  
DB_NAME='HOST_DB_NAME'
DB_USER='USER_NAME'
DB_PASSWORD='USER_PASSWORD' 
LINE_TOKEN='Channel Access Token'
LINE_HANDLER="Channel Secret"

def get_connection():
    connection=pymysql.connect(
    host=DB_HOST,  
    user=DB_USER, 
    passwd=DB_PASSWORD, 
    database=DB_NAME)
    return connection