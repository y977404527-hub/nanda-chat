# 沐辰 · 男大聊天室 🌙

一个让女生真心喜欢聊天的 AI 男大学生网站。

---

## 🚀 免费部署（让所有人都能访问）

### 方法一：Render.com（推荐，免费）

**第一步：上传代码到 GitHub**
1. 打开 https://github.com → 新建仓库（名字随意，如 `nanda-chat`）
2. 按 GitHub 提示的命令上传代码：
   ```bash
   cd /Users/manyou/nanda-chat
   git remote add origin https://github.com/你的用户名/nanda-chat.git
   git push -u origin main
   ```

**第二步：在 Render 部署**
1. 打开 https://render.com → 注册/登录（支持 GitHub 直接登录）
2. 点击 **New → Web Service**
3. 选择刚才的 GitHub 仓库
4. 配置如下：
   - Name: `nanda-chat`（随意）
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn server:app --bind 0.0.0.0:$PORT`
5. 展开 **Environment Variables**，添加：
   - Key: `GROQ_API_KEY`
   - Value: `你的 Groq API Key`（格式：gsk_xxx...）
6. 点击 **Create Web Service**
7. 等 2~3 分钟部署完成，会得到一个 `https://xxxx.onrender.com` 的链接
8. **把这个链接发给任何人，全球都能访问！**

---

### 方法二：本地运行（仅自己电脑）

```bash
cd /Users/manyou/nanda-chat
pip3 install -r requirements.txt
PORT=3100 python3 server.py
```
浏览器打开 http://localhost:3100

---

## 技术栈
- 后端：Python Flask + Gunicorn
- AI：Groq 免费 API（Llama 3.3 70B）
- 前端：原生 HTML/CSS，奶茶粉系 UI
- 流式输出：SSE 打字机效果
