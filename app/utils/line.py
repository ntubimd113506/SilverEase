from linebot import LineBotApi, WebhookHandler
from utils import db

line_bot_api = LineBotApi(db.LINE_TOKEN_2)
handler = WebhookHandler(db.LINE_HANDLER_2)