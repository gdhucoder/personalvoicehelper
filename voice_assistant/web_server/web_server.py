import eventlet

eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import base64


clients = {}

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    print(f"Client connected with sid: {sid}")
    # 假设客户端在连接时发送了一个 user_id
    user_id = request.args.get('user_id')
    clients[user_id] = sid

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"Client disconnected with sid: {sid}")
    # 从客户端列表中移除
    if sid in clients:
        del clients[sid]

# 接收音频数据
@socketio.on('audio_data')
def handle_audio_data(data):
    print("收到音频数据")
    # 解码音频数据
    audio_bytes = base64.b64decode(data['audio'])
    # 广播给指定客户端
    emit('play_audio', {'audio': data['audio']}, room=data['target_client'])

# 接收文本数据
@socketio.on('text_data')
def handle_text_data(data):
    print(request.args.get('user_id'))
    print(f"收到文本数据: {data['text']}")
    socketio.emit('receive_message', {'message': data['text']})

@socketio.on('status_update')
def handle_status_update(data):
    print(f"收到状态更新: {data}")
    # 广播给所有客户端
    socketio.emit('update_status', data)

if __name__ == "__main__":
    socketio.run(app, host='10.1.51.67',
                 # keyfile='/home/hugd/privateprojects/winpycharmdev/voicehelperdemo/sslcert/voicehelper.key',
                 # certfile='/home/hugd/privateprojects/winpycharmdev/voicehelperdemo/sslcert/voicehelper.crt',
                 port=5001, debug=True)