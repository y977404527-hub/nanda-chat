# 哥们儿 - 男大 AI 聊天室

一个幽默接地气的男大学生风格 AI 聊天网站，基于 Groq 免费 API + Llama 3.3 70B。

## 快速启动

### 1. 获取免费 Groq API Key
1. 访问 https://console.groq.com
2. 注册账号（完全免费）
3. 创建 API Key

### 2. 配置环境变量
编辑 `.env` 文件，填入你的 Key：
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

### 3. 安装依赖并启动
```bash
pip3 install -r requirements.txt
python3 server.py
```

浏览器打开 http://localhost:3000 即可开聊！

## 技术栈
- 后端：Python + Flask
- AI：Groq API（免费）+ Llama 3.3 70B
- 前端：原生 HTML/CSS/JS，暗黑风 UI
- 流式输出：SSE（Server-Sent Events）
