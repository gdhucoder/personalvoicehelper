import socketio
from datetime import datetime
import time

class WebSocketClient:
    def __init__(self, on_event_callback=None):
        """
        初始化 WebSocket 客户端。

        :param server_url: WebSocket 服务器地址，默认为 'http://127.0.0.1:5000'
        """
        self.server_url = 'http://10.1.51.67:5001?user_id=voicehelperon'
        self.on_event_callback = on_event_callback  # 保存回调函数
        self.sio = socketio.Client()
        self._setup_events()
        print('init')

    def _setup_events(self):
        """设置事件监听器"""

        @self.sio.event
        def connect():
            print(f"成功连接到服务器: {self.server_url}")

        # 接收消息
        @self.sio.event
        def receive_message(message):
            print(f"收到消息: {message['message']}")
            if self.on_event_callback:  # 如果回调函数存在，调用它
                self.on_event_callback(message['message'])

        @self.sio.event
        def disconnect():
            print("与服务器断开连接")

        @self.sio.event
        def connect_error(error):
            print(f"连接失败: {error}")

    def connect(self):
        """连接到服务器"""
        try:
            self.sio.connect(self.server_url)
        except Exception as e:
            print(f"连接时发生错误: {e}")

    def disconnect(self):
        """断开与服务器的连接"""
        self.sio.disconnect()

    def send_status_update(self, status_type, message):
        """
        发送状态更新消息到服务器。

        :param status_type: 状态类型（如 'info', 'warning', 'error'）
        :param message: 状态消息内容
        """
        data = {
            'type': status_type,
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        try:
            self.sio.emit('status_update', data)
            print(f"已发送状态更新: {data}")
        except Exception as e:
            print(f"发送消息时发生错误: {e}")

    def wait(self):
        """保持连接，等待事件"""
        self.sio.wait()

    def send_socket_info(self, info):

        # 连接到服务器
        self.connect()

        # 发送状态更新
        self.send_status_update('info', info)

        # 断开连接
        self.disconnect()

# 示例用法
if __name__ == "__main__":
    client = WebSocketClient()

    # 连接到服务器
    client.connect()

    # 发送状态更新

    while True:
        time.sleep(1)
        client.send_status_update('info', '系统启动成功')
    client.send_status_update('warning', '磁盘空间不足')

    # 保持连接（可选）
    # client.wait()

    # 断开连接
    client.disconnect()