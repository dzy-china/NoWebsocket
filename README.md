# `NoWebsocket` 完整使用文档

> **一个Python WebSocket服务端框架，支持零配置多文件路由管理，实现高效、模块化的实时通信开发。**

---

## 快速开始

### 1. 环境准备
```bash
# 确认 Python 版本 ≥ 3.7
python --version

# pip安装
pip install NoWebsocket

```

### 2. 创建蓝图文件
在 `blueprints` 目录下新建 `echo_bp.py`：  
```python
# blueprints/echo_bp.py
from NoWebsocket import Blueprint,WebSocketApplication

echo_bp = Blueprint('/echo')

@echo_bp.route('/{message:str}')
class EchoHandler(WebSocketApplication):
    def on_open(self):
        # 正确获取路径参数（类型为 str，无需转换）
        initial_message = self.path_params.get('message', '')
        self.connection.send_text(f"初始消息: {initial_message}")

    def on_message(self, message):
        print(message)
        self.connection.send_text(f"{message}")

    def on_close(self):
        # 正确获取关闭状态码和原因
        code = self.connection.close_code
        reason = self.connection.close_reason or "未知原因"
        print(f"连接关闭 → 状态码: {code}, 原因: {reason}")
```

### 3. 编写服务器启动代码
创建 `main.py`：  
```python
# main.py
import logging
from NoWebsocket import WebSocketServer,setup_logging

# 初始化日志系统（INFO 级别）
setup_logging(logging.INFO)

if __name__ == '__main__':
    # 自动注册蓝图（扫描 blueprints 目录）
    server = WebSocketServer.create_with_blueprints(
        host='0.0.0.0',  # 监听所有网络接口
        port=8765        # 绑定端口
    )
    print("Server running → ws://0.0.0.0:8765")
    try:
        server.serve_forever()  # 启动服务
    except KeyboardInterrupt:
        server.shutdown()  # 优雅关闭
        print("\n🛑 Server stopped")
```

### 4. 客户端测试
创建 `test_client.html`：  
```html
<!DOCTYPE html>
<html>
<body>
    <div id="output"></div>
    <input id="message" placeholder="输入消息">
    <button onclick="send()">发送</button>
    <script>
        // 连接地址必须与路由匹配（/echo/Hello 对应动态参数）
        const ws = new WebSocket('ws://localhost:8765/echo/Hello');
        
        // 消息接收处理
        ws.onmessage = (event) => {
            const output = document.getElementById('output');
            output.innerHTML += `<p>${event.data}</p>`;
        };

        // 发送消息（仅文本）
        const send = () => {
            const input = document.getElementById('message');
            if (input.value.trim()) {
                ws.send(input.value);
                input.value = '';
            }
        };

        // 错误处理
        ws.onerror = (error) => {
            console.error("连接错误:", error);
            alert("连接失败，请检查服务器是否运行！");
        };
    </script>
</body>
</html>
```

---

## 核心配置详解

### 1. **快速创建方法（`create_with_blueprints`）**
| 参数                | 类型   | 默认值       | 说明                                                                 |
|---------------------|--------|--------------|--------------------------------------------------------------------|
| `host`              | str    | 必填         | 服务器绑定地址（如 `0.0.0.0` 表示监听所有接口）                          |
| `port`              | int    | 必填         | 服务器绑定端口                                                        |
| `blueprint_package` | str    | `'blueprints'` | 蓝图文件存放的包名（目录名）                                            |

### 2. **自定义创建方法（构造函数）**
```python
from NoWebsocket.server import WebSocketServer,WebSocketRouter

router = WebSocketRouter()
server = WebSocketServer(
    server_address=('0.0.0.0', 8765),
    router=router,
    max_header_size=8192,               # HTTP请求头最大字节数（默认 4096）
    max_message_size=10 * 1024 * 1024,  # 单条消息最大字节数（默认 2MB）
    read_timeout=300                    # 无数据交互的超时断开时间（秒，默认 1800）
)
```

---

## 生命周期钩子全解

### 1. **`on_open()`**
- **触发时机**：连接建立后立即调用。  
- **正确示例**：  
  ```python
  def on_open(self):
      # 获取客户端IP
      client_ip = self.connection.sock.getpeername()[0]
      message = self.path_params.get('message', '')
      print(f"新连接来自 {client_ip}，初始参数: {message}")
  ```

### 2. **`on_message(message: str)`**
- **触发时机**：收到完整的文本消息。  
- **正确示例**：  
  ```python
  def on_message(self, message):
      if not isinstance(message, str):
          self.connection.close(1007, "仅支持文本消息")
          return
      self.connection.send_text(f"处理后的消息: {message.upper()}")
  ```

### 3. **`on_binary(data: bytes)`**
- **触发时机**：收到完整的二进制消息。  
- **正确示例**：  
  ```python
  def on_binary(self, data):
      try:
          with open('upload.bin', 'wb') as f:
              f.write(data)
          self.connection.send_text("文件保存成功")
      except Exception as e:
          self.connection.close(1011, f"保存失败: {str(e)}")
  ```

### 4. **`on_close()`**
- **触发时机**：连接关闭时调用。  
- **正确示例**：  
  ```python
  def on_close(self):
      code = self.connection.close_code
      reason = self.connection.close_reason or "未知原因"
      logger.info(f"连接关闭 → 状态码: {code}, 原因: {reason}")
  ```

---

## RFC6455 标准错误代码

| 状态码 | 中文名称               | 触发场景                                                                 | 解决方案                                                                 |
|--------|-----------------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------|
| **1000** | 正常关闭               | 客户端或服务器主动关闭连接                                                | 无需处理，属于正常操作。                                                   |
| **1002** | 协议错误               | 非法帧格式、握手失败、RSV位非零                                           | 检查客户端数据格式，确保符合 WebSocket 协议。                                |
| **1007** | 数据格式无效           | 文本消息包含非 UTF-8 编码数据                                             | 客户端发送纯文本消息，或改用 `send_binary` 发送原始字节。                     |
| **1009** | 消息过大               | 消息长度超过 `max_message_size` 配置                                      | 调整服务器配置：`max_message_size=50 * 1024 * 1024`（50MB）。                |
| **1011** | 内部错误               | 服务器未捕获的异常（如代码逻辑错误）                                       | 检查服务器日志，修复异常逻辑。                                               |

---

## 路由与蓝图系统

---

#### 1. 蓝图基本概念
蓝图（`Blueprint`）用于模块化组织 WebSocket 路由，允许将不同功能的路由拆分到独立模块中。所有蓝图文件需以 `_bp.py`或`Bp.py`  结尾，并保存在指定的包目录（默认为 `blueprints`）。

---

#### 2. 创建蓝图
**步骤 1：定义蓝图实例**  
在模块中创建 `Blueprint` 实例，可指定 URL 前缀：

```python
# blueprints/ChatBp.py
from NoWebsocket import Blueprint

bp = Blueprint(prefix="/chat")  # 所有路由自动添加 /chat 前缀
```

**步骤 2：定义路由处理类**  
继承 `WebSocketApplication` 实现业务逻辑：

```python
from NoWebsocket import WebSocketApplication
class ChatHandler(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"Echo: {message}")
```

**步骤 3：添加路由装饰器**  
使用 `@bp.route` 绑定路径与处理类：

```python
@bp.route("/room/{str:room_id}")
class ChatHandler:
    pass  # 处理类需在此处定义
```

---

#### 3. 自动注册蓝图
**目录结构示例**  
```ini
your_project/
├── blueprints/
│   ├── __init__.py    # 必须，可为空
│   ├── ChatBp.py      # 自动发现
│   └── NotifyBp.py   # 自动发现
└── main.py
```

**启动服务器时自动加载**  
```python
from NoWebsocket import WebSocketServer

server = WebSocketServer.create_with_blueprints(
    host="0.0.0.0", 
    port=8765,
    blueprint_package="blueprints"  # 指定蓝图包名
)
server.serve_forever()
```

---

#### 4. 手动注册蓝图
若需手动控制注册流程：
```python
from NoWebsocket import WebSocketRouter, Blueprint

router = WebSocketRouter()
bp = Blueprint(prefix="/api")

@bp.route("/status")
class StatusHandler(WebSocketApplication):
    def on_open(self):
        print("Client connected")

bp.register(router)  # 手动注册到路由器
```

---

#### 5. 路径参数与类型
- **语法**：`{类型:参数名}`（类型支持 `int`/`str`，默认为 `str`）
- **示例**：  
  
  ```python
  @bp.route("/user/{int:user_id}")
  class UserHandler:
      def on_message(self, message):
          user_id = self.path_params["user_id"]  # 获取 int 类型参数
  ```

---

#### 6. 注意事项
1. **冲突检测**  
   - 若路径重复，后注册的蓝图会跳过并输出警告。
   - 自动发现时，冲突的整个模块会被忽略。

2. **模块命名规范**  
   - 蓝图文件必须命名为 `*_bp.py`（如 `chat_bp.py`）。
   - 包内需包含 `__init__.py`（可为空文件）。

3. **错误排查**  
   - 若蓝图未加载，检查日志中的模块导入错误。
   - 确保处理类继承 `WebSocketApplication`。

---

#### 7. 完整示例
**文件：`blueprints/ChatBp.py`**

```python
from NoWebsocket import Blueprint, WebSocketApplication

bp = Blueprint(prefix="/echo")

@bp.route("/simple")
class ChatBp(WebSocketApplication):
    def on_message(self, message):
        self.connection.send_text(f"Received: {message}")
```

启动服务后，客户端可通过 `ws://localhost:8765/echo/simple` 连接。

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

## 高级场景配置

### 1. **消息分片发送**
```python
def send_large_message(self, data: bytes):
    chunk_size = 1024  # 每片 1KB
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        self.connection.send_binary(chunk)
```

### 2. **心跳检测实现**
```python
class HeartbeatHandler(WebSocketApplication):
    def on_open(self):
        self.last_ping = time.time()
        threading.Thread(target=self._check_heartbeat, daemon=True).start()

    def _check_heartbeat(self):
        while self.connection.connected:
            if time.time() - self.last_ping > 30:  # 30秒无心跳
                self.connection.close(1001, "心跳超时")
            time.sleep(5)

    def on_message(self, message):
        if message == "ping":
            self.last_ping = time.time()
            self.connection.send_text("pong")
```

---

## 故障排查与最佳实践

### 1. **常见问题修正**
| 现象                  | 错误原因               | 修正方案                                                                 |
|-----------------------|----------------------|-------------------------------------------------------------------------|
| 客户端无法连接         | 路由路径不匹配          | 检查客户端连接地址是否与服务器路由定义一致（如 `/echo/Hello` vs `/echo/{message:str}`） |
| 二进制消息未处理       | 未实现 `on_binary`     | 在处理器中实现 `on_binary` 方法                                           |
| 消息过大被关闭         | 未调整 `max_message_size` | 在服务器配置中增加 `max_message_size` 参数                                 |

### 2. **安全增强建议**
- **输入过滤**：  
  
  ```python
  def on_message(self, message):
      # 防止 SQL 注入
      if ';' in message or '--' in message:
          self.connection.close(1008, "非法字符")
  ```
- **频率限制**：  
  
  ```python
  from collections import defaultdict
  request_count = defaultdict(int)
  
  def on_message(self, message):
      ip = self.connection.client_address[0]
      request_count[ip] += 1
      if request_count[ip] > 100:
          self.connection.close(1008, "请求过于频繁")
  ```

---

**文档版本**: 10.0.0  
**更新日期**: 2025年03月30日  
**维护团队**: 技术架构组  