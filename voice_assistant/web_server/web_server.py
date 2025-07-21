import eventlet

eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import base64
from datetime import datetime
import os
from voice_assistant.utils.image_utils import resize_for_image_understand

UPLOAD_DIR = '/home/hugd/privateprojects/personalvoicehelper/voice_assistant/web_server/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)


clients = {}

app = Flask(__name__)
socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    max_http_buffer_size=100 * 1024 * 1024  # 100MB buffer
                    )

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

# 新增：接收图片数据
@socketio.on('image_data')
def handle_image_data(data):
    """
        前端发送：
            socket.emit('image_data', {image: <Base64>})
        """
    try:
        # 取出 Base64 字符串
        base64_str = data['image'].split(',', 1)[1]  # 去掉 data:image/xxx;base64,
        img_bytes = base64.b64decode(base64_str)

        # 生成文件名
        fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}.jpg"
        fpath = os.path.join(UPLOAD_DIR, fname)
        print(f"Writing image to {fpath}")

        # 写入磁盘
        with open(fpath, 'wb') as f:
            f.write(img_bytes)

        print(f"[image] saved -> {fpath}")
        resized_image = resize_for_image_understand(fpath, 336)
        socketio.emit('image_reply', {'message': f"图片已收到"})


    except Exception as e:
        print("保存图片失败：", e)
        socketio.emit('image_reply', {'error': '图片处理失败'})

@socketio.on('status_update')
def handle_status_update(data):
    print(f"收到状态更新: {data}")
    # 广播给所有客户端
    socketio.emit('update_status', data)

# 放在所有 @socketio.on(...) 之后
@socketio.on('*')
def catch_all(event, data):
    print(f"[catch-all] 收到事件 {event}，数据长度：{len(str(data))}")

if __name__ == "__main__":
    socketio.run(app, host='10.1.51.67',
                 # keyfile='/home/hugd/privateprojects/winpycharmdev/voicehelperdemo/sslcert/voicehelper.key',
                 # certfile='/home/hugd/privateprojects/winpycharmdev/voicehelperdemo/sslcert/voicehelper.crt',
                 port=5001, debug=True)