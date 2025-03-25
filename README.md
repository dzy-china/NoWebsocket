
# NoWebsocket 库 使用文档
**一个Python WebSocket服务端框架，支持零配置多文件路由管理，实现高效、模块化的实时通信开发。**

## 安装指南

### 环境要求
- Python 3.7+
- 依赖库：无额外依赖

### 安装步骤
1. 将库代码克隆到项目目录：
   ```bash
   git clone git@github.com:dzy-china/NoWebsocket.git
   ```
2. pip安装：
   ```python
   pip install NoWebsocket
   ```

---

## 快速开始

### 创建一个简单的WebSocket服务器
```python
from NoWebsocket import WebSocketServer, WebSocketRouter, WebSocketApplication

# 定义应用类
class EchoApp(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"Echo: {message}")

# 配置路由
router = WebSocketRouter()
router.add_route("/echo", EchoApp)

# 启动服务器
server = WebSocketServer(("0.0.0.0", 8765), router)
print("Server running on ws://localhost:8765/echo")
server.serve_forever()
```

### 测试连接
使用WebSocket客户端工具（如`websocat`）连接：
```bash
websocat ws://localhost:8765/echo
```

## 优雅开始

> 入口文件：main.py

```python
from NoWebsocket import WebSocketServer, WebSocketRouter, Blueprint


def create_app():
    router = WebSocketRouter()

    # 自动注册所有蓝图
    Blueprint.auto_register(
        router,
        package_path='blueprints',
        bp_suffix='_bp'
    )

    return WebSocketServer(("0.0.0.0", 9000), router)


if __name__ == "__main__":
    server = create_app()
    print("WebSocket server running on ws://localhost:9000")
    try:
        server.serve_forever()  # 启动服务
    except KeyboardInterrupt:
        server.shutdown()  # 优雅关闭
        print("\n🛑 Server stopped")
```

> 路由控制器处理文件：blueprints/chat/Uer.py
>
> blueprints包下必须存在`__init__.py`,该文件可以为空，
> 一个目录必须包含`__init__.py`文件才能被识别为**包**（Package），这是Python模块系统的约定

```python
from NoWebsocket import WebSocketApplication, Blueprint

chat_bp = Blueprint(prefix='/chat')

@chat_bp.route("/youmi")
class User(WebSocketApplication):
    def on_open(self):
        """连接建立时触发"""
        pass

    def on_message(self, message):
        print(message)
        self.connection.send_text(f"你好，我是悠米系统服务，收到了你的信息：\'{message}\'")

    def on_binary(self, data):
        """收到二进制消息时触发"""
        print(data)

    def on_close(self):
        """连接关闭时触发"""
        print("on_close")
```

> 测试连接 index.html

```html
<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <title>WebSocket 示例</title>
</head>
<body>
<div>
    <p>连接状态: <span id="status">未连接</span></p>
    <input type="text" id="messageInput" placeholder="输入消息">
    <button onclick="sendMessage()">发送</button>
</div>
<div id="messages"></div>

<script>
    // 创建 WebSocket 连接
    const socket = new WebSocket('ws://localhost:9000/chat/youmi'); // 使用公开测试服务器

    // 连接打开时触发
    socket.addEventListener('open', (event) => {
        updateStatus('已连接');
        logMessage('系统: 连接已建立');

        // 发送初始测试消息
        socket.send('你好，服务器!');
    });

    // 接收消息时触发
    socket.addEventListener('message', (event) => {
        logMessage(`服务器: ${event.data}`);
    });

    // 错误处理
    socket.addEventListener('error', (event) => {
        updateStatus('连接错误');
        console.error('WebSocket 错误:', event);
    });

    // 连接关闭时触发
    socket.addEventListener('close', (event) => {
        updateStatus('连接已关闭');
        logMessage(`系统: 连接关闭 (代码 ${event.code})`);
    });

    // 发送消息
    function sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value;

        if (message) {
            socket.send(message);
            logMessage(`你: ${message}`);
            input.value = '';
        }
    }

    // 更新状态显示
    function updateStatus(status) {
        document.getElementById('status').textContent = status;
    }

    // 记录消息到页面
    function logMessage(message) {
        const messagesDiv = document.getElementById('messages');
        const p = document.createElement('p');
        p.textContent = message;
        messagesDiv.appendChild(p);
    }
</script>
</body>
</html>
```

### 配置选项
在服务器初始化时设置：
```python
server = WebSocketServer(
    ("0.0.0.0", 8765),
    router,
    max_header_size=8192,       # 最大请求头大小
    max_message_size=4*1024*1024, # 最大消息大小（4MB）
    read_timeout=60              # 等待读取信息超时（秒）
)
```

---

## 路由管理

### 装饰器路由

> blueprints/chat/Uer.py

```python
from NoWebsocket import WebSocketApplication, Blueprint

chat_bp = Blueprint(prefix='/chat')  # 蓝图实例


@chat_bp.route("/youmi")
class User(WebSocketApplication):
    def on_open(self):
        """连接建立时触发"""
        pass

    def on_message(self, message):
        print(message)
        self.connection.send_text(f"你好，我是悠米服务，收到了你的信息：\'{message}\'")

    def on_binary(self, data):
        """收到二进制消息时触发"""
        print(data)

    def on_close(self):
        """连接关闭时触发"""
        print("on_close")
```

### 约定配置
> main.py

```python
from NoWebsocket import Blueprint

Blueprint.auto_register(
    router,
    package_path="blueprints", # 指定路由文件存放的包，包内必须存在`__init__.py`文件，该文件可以为空
    # 指定蓝图实例变量后缀，不写默认为'_bp'
    # 如：'chat_bp = Blueprint(prefix='/chat')'
    bp_suffix="_bp"
)
```

> `bp_suffix`参数的存在是**为了平衡灵活性与规范性**，它通过命名约定帮助开发者更精确地控制哪些蓝图实例应被自动注册



**目录结构示例**：

```
project/
├── blueprints/
	__init__.py  # 必须存在，可以为空
│   └── chat/
│       └── User.py   # 包含 chat_bp = Blueprint()
└── main.py
```

---

## 高级配置

### 自定义路由前缀
```python
api_bp = Blueprint(prefix="/api/v2")

@api_bp.route("/status")
class StatusHandler(WebSocketApplication):
    def on_open(self):
        self.connection.send_text("API v2 Ready")
```

### 参数化路由
**定义动态路径**：

```python
router.add_route("/user/{user_id:int}", UserHandler)
```

**在应用中获取参数**：

```python
class UserHandler(WebSocketApplication):
    def on_open(self):
        user_id = self.path_params["user_id"]
        self.connection.send_text(f"User ID: {user_id}")
```

---

## 示例应用

### 聊天应用

```python
# blueprints/chat/handlers.py
from NoWebsocket import WebSocketApplication, Blueprint

chat_bp = Blueprint(prefix="/chat")


@chat_bp.route("/public")
class PublicChat(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"[Public] {message}")


@chat_bp.route("/private/{room}")
class PrivateChat(WebSocketApplication):
    def on_message(self, message):
        room = self.path_params["room"]
        self.connection.send_text(f"[{room}] {message}")
```

### 文件传输

```python
# blueprints/file/handlers.py
from NoWebsocket import WebSocketApplication, Blueprint

file_bp = Blueprint(prefix="/file")


@file_bp.route("/upload")
class FileUpload(WebSocketApplication):
    def on_binary(self, data):
        with open("received_file.bin", "ab") as f:
            f.write(data)
```

---

## 常见问题

### 1. 如何处理连接中断？
- **现象**：客户端意外断开。
- **解决**：在`on_close`中清理资源：
  ```python
  class MyApp(WebSocketApplication):
      def on_close(self):
          print("Connection closed")
  ```

### 2. 如何调试协议错误？
- **步骤**：
  1. 启用详细日志：
     ```python
     import logging
     logging.basicConfig(level=logging.DEBUG)
     ```
  2. 检查握手头和帧格式是否符合RFC6455。

### 3. 如何扩展应用基类？
- **示例**：添加身份验证：
  
  ```python
  class AuthApp(WebSocketApplication):
      def on_open(self):
          token = self.connection.request.headers.get("token")
          if not validate_token(token):
              self.connection.close(1008, "Invalid token")
  ```

---

