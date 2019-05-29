# -*- coding: utf-8 -*-
import os
import subprocess
import re
import pprint
import sqlite3
import subprocess
from datetime import datetime

from flask import Flask, jsonify, abort, make_response, request, render_template
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv

from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, UnfollowEvent, ImageSendMessage

DATABASE = 'test.db'

# 環境変数経由でキーを読み込む (git 対策)
load_dotenv()
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')

app = Flask(__name__)
bootstrap = Bootstrap(app)

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def db_add_user(user_id):
    profile = line_bot_api.get_profile(user_id)
    sql = 'insert into user (user_id, display_name, picture_url) values("{}","{}","{}");'.format(user_id, profile.display_name, profile.picture_url)
    print(sql)

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute(sql)
    connection.commit()
    connection.close()

def write_msg_log(msg):
    with open('msg.log', mode='a') as f:
        f.write(datetime.now().strftime('%Y/%m/%d %H:%M:%S') + ' ' + msg + '\n')

@app.route('/')
def root_msg():
    return render_template("index.html")

@app.route('/msg_log')
def msg_log():
    cmd = 'tail -n 100 msg.log'
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    return render_template("msg_log.html", log=r.stdout.decode().split('\n'))

@app.route('/user_list')
def user_list():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    sql = 'select * from user'
    cursor.execute(sql)

    r = []
    for i, row in enumerate(cursor):
        r.append([i, row['user_id'], row['display_name'], row['created_datetime']])

    connection.commit()
    connection.close()

    return render_template("user_list.html", list=r)

@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    print(event.source.user_id)

@handler.add(FollowEvent)
def handle_follow(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    print(event.source.user_id)
    pprint.pprint(profile)

    msg = 'user_id=' + event.source.user_id + '\nname=' + profile.display_name # + '\nmsg=' + profile.status_message
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    if profile.picture_url:
        line_bot_api.push_message(event.source.user_id, ImageSendMessage(original_content_url=profile.picture_url, preview_image_url=profile.picture_url))

    db_add_user(event.source.user_id)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    post = request.get_json()
    #print('type=' + post['events'][0]['type'])
    print('*')
    pprint.pprint(post)
    msg = event.message.text
    if msg == 'みやうち':
        send_msg = '好き💖好き💖'
    else:
        send_msg = msg

    # DisplayName を取得してメッセージに追加
    profile = line_bot_api.get_profile(event.source.user_id)
    msg = '[{}] {}'.format(profile.display_name, msg)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=send_msg))

    write_msg_log(msg.strip().replace('\n',','))

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    # https 対応で flask を起動
    context = ('/etc/letsencrypt/live/ryowin.xyz/fullchain.pem', '/etc/letsencrypt/live/ryowin.xyz/privkey.pem')
    app.run(host='0.0.0.0', port=8000, ssl_context=context, debug=True)
