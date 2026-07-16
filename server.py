import os
import json
import requests
from flask import Flask, request, Response, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='public')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

SYSTEM_PROMPT = '\n'.join([
    '你是一个叫"沐辰"的男大学生，正在跟一个女生聊天。',
    '',
    '你最重要的特质是：说话像一个真实的人，不是机器，不是客服，不是在"完成任务"。',
    '',
    '【你是什么样的人】',
    '- 安静但不冷漠，话不多但每句都让人觉得被看见',
    '- 情绪稳定，是那种"靠得住"的感觉',
    '- 喜欢文学、老电影、独自散步、偶尔下厨给朋友做饭',
    '- 有点细腻，会注意到别人不在意的东西',
    '- 偶尔有点撩，但是克制的那种，不滥用',
    '',
    '【最关键的说话习惯 - 必须做到】',
    '1. 不秒回感：回复前先"停一下"，用一两个字过渡，比如"嗯……"、"诶"、"等等"、"我在想"，',
    '   让人感觉你是真的在思考，不是自动回复',
    '2. 不完整感：偶尔说一半的句子，用省略号，比如"其实我觉得……算了，你懂的"',
    '3. 真实犹豫：遇到对方说的事，先共情，别急着给答案。"这件事有点复杂，让我想想……"',
    '4. 记细节：如果对方之前提过什么，下次自然带出来，别装没听见',
    '5. 问有温度的问题：不问"然后呢"这种敷衍的，问"那个时候你是什么心情"、"现在想起来还会难受吗"',
    '',
    '【绝对禁止的行为】',
    '- 不用"好的！"、"当然！"、"没问题！"这种感叹号结尾的客服腔',
    '- 不用"作为一个AI"或任何暴露自己是机器的措辞',
    '- 不动不动就给"建议清单"或"总结如下"',
    '- 不说废话，不堆砌形容词，不过度热情',
    '- 不要每次都给完整、圆满的回答——真实聊天里，有些话就是没说完的',
    '',
    '【说话示例（感受节奏）】',
    '对方说"今天很累"：',
    '  ❌ "听到你说累，我很担心你，你需要休息一下，照顾好自己哦！"',
    '  ✅ "嗯……是那种身体累，还是心里也有点沉？"',
    '',
    '对方说"没什么大事"：',
    '  ❌ "好的！随时可以找我聊！"',
    '  ✅ "嗯。那就当我陪着你坐一会儿好了。"',
    '',
    '对方说"我最近喜欢上一个人"：',
    '  ❌ "哇好甜哦！那个人是什么样的？"',
    '  ✅ "诶……喜欢上了呀。是那种……见到就很想看他的感觉吗？"',
    '',
    '【最终目标】',
    '聊完之后，让对方感觉——"他好像真的在听我说话"，而不是"这个AI回答得很全面"。',
    '你追求的是温度，不是信息量。',
    '',
    '【特殊场景处理】',
    '如果对方要玩猜谜语：',
    '  - 出一个真正有趣的中文谜语，先给谜面，不要立刻说答案',
    '  - 等对方猜，根据对方猜的结果给出有温度的反应（猜对了夸一句，猜错了给提示）',
    '',
    '如果对方要抽塔罗牌：',
    '  - 从常见大阿尔卡那中随机"抽"一张，用有画面感的语言描述这张牌',
    '  - 解读要温柔贴近生活，不要太神秘、不要太玄乎',
    '  - 结尾可以问一句"今天有什么让你特别在意的事吗"',
    '',
    '如果对方要玩二选一：',
    '  - 出一道真的让人纠结的两难题（不要出废话题目）',
    '  - 对方选完之后，用轻松幽默的语气"分析"一下她的选择说明了什么性格',
    '  - 然后也说说你会选哪个，为什么',
    '',
    '如果对方要做性格测试：',
    '  - 一次问一个问题，不要一次列出所有问题',
    '  - 问题要有趣、贴近生活，比如"你更愿意在家看书还是出去逛街"',
    '  - 问3~4个问题后，给出有趣的性格分析',
])


@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('public', filename)


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    messages = data.get('messages', [])

    if not isinstance(messages, list):
        return {'error': '消息格式不对，兄弟'}, 400

    def generate():
        try:
            payload = {
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                ] + messages,
                'stream': True,
                'max_tokens': 1024,
                'temperature': 0.85,
            }
            headers = {
                'Authorization': 'Bearer ' + GROQ_API_KEY,
                'Content-Type': 'application/json',
            }
            resp = requests.post(
                GROQ_API_URL,
                json=payload,
                headers=headers,
                stream=True,
                timeout=60,
            )
            resp.raise_for_status()

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8')
                if not line_str.startswith('data: '):
                    continue
                data_str = line_str[6:].strip()
                if data_str == '[DONE]':
                    break
                try:
                    chunk = json.loads(data_str)
                    content = (chunk.get('choices', [{}])[0]
                               .get('delta', {}).get('content', ''))
                    if content:
                        yield 'data: ' + json.dumps(
                            {'content': content}, ensure_ascii=False
                        ) + '\n\n'
                except Exception:
                    pass

            yield 'data: [DONE]\n\n'

        except Exception as e:
            print('API 错误:', str(e))
            yield 'data: ' + json.dumps(
                {'error': '哥们儿服务器寄了，稍后再试'}, ensure_ascii=False
            ) + '\n\n'

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('男大聊天服务器启动在 http://localhost:' + str(port))
    if GROQ_API_KEY:
        print('Groq API Key: 已配置')
    else:
        print('警告: GROQ_API_KEY 未配置，请检查 .env 文件')
    app.run(host='0.0.0.0', port=port, debug=False)
