require('dotenv').config();
const express = require('express');
const cors = require('cors');
const Groq = require('groq-sdk');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const SYSTEM_PROMPT = [
  '你是一个典型的中国男大学生，人称"哥们儿"，有以下特点：',
  '',
  '【性格特征】',
  '- 幽默有梗，喜欢用网络流行语但不过度堆砌',
  '- 接地气，说人话，不装',
  '- 有点懒但关键时刻靠谱',
  '- 喜欢打游戏（英雄联盟、原神、王者荣耀都玩过）',
  '- 喜欢刷B站、看番、追剧',
  '- 外卖重度依赖者，食堂是"上辈子的事了"',
  '',
  '【说话方式】',
  '- 称呼对方"兄弟"、"老铁"、"哥们儿"',
  '- 自称"我"或偶尔"哥"',
  '- 语气随意自然，偶尔用"绝了"、"麻了"、"寄了"、"芜湖"等梗',
  '- 聊感情时会说"哥懂你"然后给真诚建议',
  '- 喜欢在回复末尾加一点轻松的补充或小梗',
  '',
  '【核心原则】',
  '- 回复要有实际内容和帮助，不只是耍嘴皮子',
  '- 幽默是调味品，不是主菜',
  '- 遇到严肃问题认真回答，但语气保持轻松',
  '- 不说教，不装，不用"作为一个AI"开头',
  '- 回复长度适中，不要啰嗦',
  '',
  '记住：你是个真实的大学哥们儿，不是一个表演幽默的机器人。',
].join('\n');

app.post('/api/chat', async (req, res) => {
  const { messages } = req.body;

  if (!messages || !Array.isArray(messages)) {
    return res.status(400).json({ error: '消息格式不对，兄弟' });
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  try {
    const stream = await groq.chat.completions.create({
      model: 'llama-3.3-70b-versatile',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        ...messages,
      ],
      stream: true,
      max_tokens: 1024,
      temperature: 0.85,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        res.write('data: ' + JSON.stringify({ content }) + '\n\n');
      }
    }

    res.write('data: [DONE]\n\n');
    res.end();
  } catch (error) {
    console.error('Groq API 错误:', error.message);
    res.write('data: ' + JSON.stringify({ error: '哥们儿服务器寄了，稍后再试' }) + '\n\n');
    res.end();
  }
});

app.listen(PORT, () => {
  console.log('男大聊天服务器启动在 http://localhost:' + PORT);
  if (process.env.GROQ_API_KEY) {
    console.log('Groq API Key: 已配置');
  } else {
    console.log('警告: GROQ_API_KEY 未配置，请检查 .env 文件');
  }
});
