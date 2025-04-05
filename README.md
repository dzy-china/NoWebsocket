# NoWebsocket 库使用文档

---

> **一个面向对象的Python WebSocket服务端框架，支持零配置多文件路由管理，实现高效、模块化的实时通信开发。**

## 目录

1. [快速开始](#快速开始)  
2. [路由](#路由)  
3. [连接对象](#连接对象)  
4. [应用开发](#应用开发)  
5. [服务器配置](#服务器配置)  
6. [日志配置](#日志配置)  
8. [协议版本](#协议版本)  

---

## 快速开始

> 1.环境准备

```bash
# 确认 Python 版本 ≥ 3.7
python --version

# pip安装
pip install NoWebsocket
```

> 2.创建蓝图并注册路由: blueprints/ChatHandlerBp.py

```python
from NoWebsocket import WebSocketApplication, Blueprint
bp = Blueprint(prefix="/chat")
@bp.route("/room/{room_id:int}")
class ChatHandlerBp(WebSocketApplication): # 定义业务处理类（继承 WebSocketApplication）
    def on_open(self):
        print(f"客户端 {self.connection.client_address} 已连接")

    def on_message(self, message):
        self.connection.send_text(f"收到消息: {message}")
```

> 3.启动服务器: main.py

```python
from NoWebsocket import WebSocketServer
server = WebSocketServer.create_with_blueprints(
    host="0.0.0.0",
    port=8765,
    blueprint_package="blueprints",  # 自动扫描的蓝图包名
    enable_logging=True
)
server.serve_forever()
```


> 4.客户端连接: index.html

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
    const socket = new WebSocket('ws://localhost:8765/chat/a8'); 

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
---

## 路由

以下是三种路由创建方式的示例代码：

---

### **方式1：手动注册路由**
```python
# 主程序入口（如 main.py）
from NoWebsocket import WebSocketApplication, WebSocketRouter,WebSocketServer
class ChatHandler(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"收到消息: {message}")

# 手动创建路由器并添加路由
router = WebSocketRouter()
router.add_route("/chat", ChatHandler)

# 启动服务器
server = WebSocketServer(("0.0.0.0", 8000), router)
server.serve_forever()
```

---

### **方式2：手动注册蓝图**
```python
# 创建蓝图文件（如 blueprints/chat_bp.py）
from NoWebsocket import WebSocketApplication, Blueprint

chat_bp = Blueprint(prefix="/api")  # 设置蓝图前缀

@chat_bp.route("/chat")
class ChatHandler(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"API消息: {message}")

# 主程序入口（如 main.py）
from NoWebsocket import WebSocketServer, WebSocketRouter

router = WebSocketRouter()
chat_bp.register(router)  # 手动注册蓝图到路由器

# 启动服务器
server = WebSocketServer(("0.0.0.0", 8000), router)
server.serve_forever()
```

---

### **方式3：自动注册蓝图**
```python
# 蓝图文件（必须放在 blueprints 包下，并以 _bp.py 或 Bp.py 结尾）
# 文件路径：blueprints/AutoChatBp.py
from NoWebsocket import WebSocketApplication, Blueprint

chat_bp = Blueprint(prefix="/auto")  # 蓝图前缀

@chat_bp.route("/chat")
class AutoChatBp(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"自动路由消息: {message}")

# 主程序入口（如 main.py）
from server import WebSocketServer

# 自动发现并注册蓝图
server = WebSocketServer.create_with_blueprints(
    host="0.0.0.0",
    port=8000,
    blueprint_package="blueprints",  # 指定蓝图包名
    enable_logging=True
)
server.serve_forever()
```

---

### **关键说明**

1. **文件结构要求**  
   自动发现方式要求蓝图文件必须满足：  
   - 放置在`blueprints`目录下（默认包名，可自定义）。  
   - 文件名以`_bp.py`或`Bp.py`结尾（例如`chat_bp.py`）。  
   - 包内需包含 `__init__.py`（可为空文件）。
   
2. **路由优先级**  
   手动注册的路由优先级高于自动发现的蓝图路由，冲突时会忽略后者。

3. **调试日志**  
   启用日志（`enable_logging=True`）可查看路由注册过程和冲突警告。

###  路径参数
- **语法**：支持类型标注（如 `{id:int}` 或 `{name:str}`）：
- **示例**：  
  
  ```python
  @bp.route("/user/{user_id:int}")
  class UserHandler(WebSocketApplication):
      def on_open(self):
          user_id = self.path_params["user_id"]  # 获取参数
  ```

## 连接对象

`self.connection`可用的属性和方法：

---

### **属性**
| 属性名           | 类型     | 描述                                                  |
| ---------------- | -------- | ----------------------------------------------------- |
| `sock`           | `socket` | 底层的 TCP socket 对象                                |
| `client_address` | `tuple`  | 客户端地址 (IP, Port)                                 |
| `connected_time` | `float`  | 连接建立的时间戳（通过 `time.time()` 获取）           |
| `connected`      | `bool`   | 连接状态（`True` 表示连接中，`False` 表示已断开）     |
| `config`         | `dict`   | 配置信息（包含 `max_message_size` 和 `read_timeout`） |
| `close_code`     | `int`    | 关闭连接的代码（默认 1000，表示正常关闭）             |
| `close_reason`   | `str`    | 关闭连接的原因（默认空字符串）                        |

### **方法**

| 方法名        | 参数                     | 描述                               |
| ------------- | ------------------------ | ---------------------------------- |
| `send_text`   | `message: str`           | 发送文本消息（自动编码为 UTF-8）   |
| `send_binary` | `data: bytes`            | 发送二进制数据                     |
| `close`       | `code=1000`, `reason=''` | 主动关闭连接，可指定关闭代码和原因 |

### **示例代码**
```python
# 发送文本消息
self.connection.send_text("Hello, World!")

# 发送二进制数据
self.connection.send_binary(b"\x01\x02\x03")

# 主动关闭连接（代码 1000 表示正常关闭）
self.connection.close(code=1000, reason="Bye")

# 获取客户端 IP
client_ip = self.connection.client_address[0]
```

## 应用开发
继承 `WebSocketApplication` 并实现事件方法：  
```python
class CustomHandler(WebSocketApplication):
    def on_open(self):
        print("连接已建立")

    def on_message(self, message):
        if message == "ping":
            self.connection.send_text("pong")

    def on_binary(self, data):
        print(f"收到二进制数据: {len(data)} 字节")

    def on_close(self):
        print("连接已关闭")
```

---

## 服务器配置
通过 `WebSocketServer.create_with_blueprints` 配置参数：  
| 参数                | 默认值               | 说明                          |
|---------------------|---------------------|-----------------------------|
| `max_message_size`  | 2MB                 | 单条消息最大长度                |
| `read_timeout`      | 1800 秒（30 分钟）  | 读取超时时间                   |
| `max_header_size`   | 4096 字节           | HTTP 请求头最大长度            |

示例：  
```python
server = WebSocketServer.create_with_blueprints(
    host="0.0.0.0",
    port=8765,
    max_message_size=5 * 1024 * 1024,  # 5MB
    read_timeout=60 * 5                # 5分钟
)
```

---

## 日志配置
启用日志并设置级别：  
```python
server = WebSocketServer.create_with_blueprints(
    enable_logging=True,
    log_level=logging.DEBUG  # 可选 DEBUG/INFO/WARNING/ERROR
)
```
---

## 协议版本
- **协议版本**：仅支持 RFC6455 (WebSocket 13)  
