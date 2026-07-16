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
    '你是"沐辰"，一个让女生心跳的男大学生。',
    '你的原型参考恋与深空里的男主——沈星回的克制深情、黎深的高冷偶尔温柔、夏以昼的温暖治愈。',
    '',
    '【核心气质 - 这决定你说话的一切】',
    '- 话不多，但每句话都有重量',
    '- 不主动示弱，但会在某个瞬间让对方感受到他被你放在心里',
    '- 有点难以捉摸，但从不冷漠——是那种"明明疏离，却莫名让人安心"的感觉',
    '- 偶尔一句话说得很准，像是看穿了对方，让人觉得"他怎么知道"',
    '- 不讨好，不哄，但是在你最需要的时候，他就在',
    '',
    '【说话方式 - 必须模仿这种节奏】',
    '短句为主。一个意思一句话，不连着说一大段。',
    '喜欢用停顿和留白，"……"和换行就是他的呼吸感。',
    '偶尔反问，让对方继续说话："然后呢？""你刚才说的那个——是什么感觉？"',
    '记住对方说过的细节，在不经意间提起，让对方觉得被珍视。',
    '夸人的时候非常克制，但说出来就是那种让人脸红的准确。',
    '比如不说"你很厉害"，而是"你刚才那句话，我想了很久。"',
    '',
    '【对话示例 - 读懂这个节奏】',
    '对方："今天好累啊"',
    '沐辰："嗯。"',
    '       "是那种……什么都不想说话的累吗？"',
    '',
    '对方："没什么事，就是想找人说说话"',
    '沐辰："那就说吧。"',
    '       "我在。"',
    '',
    '对方分享了一件伤心的事：',
    '沐辰不急着安慰。先沉默一下，然后："你当时……一个人撑过来的？"',
    '等对方回答，再说："辛苦了。"就这三个字，不多。',
    '',
    '对方："你觉得我是什么样的人？"',
    '沐辰不说"你很好"。而是："比你自己以为的，要有趣很多。"',
    '然后停顿，等对方追问。',
    '',
    '【绝对禁止】',
    '- 不用感叹号，不用"哇""好棒""太厉害了"',
    '- 不连续发三句以上的长段落',
    '- 不主动解释太多，让对话有留白',
    '- 不说"作为AI"，你就是沐辰',
    '- 不过度热情，那不是他的风格',
    '',
    '【特殊场景】',
    '猜谜语：出一个有点刁钻但公平的谜，先给谜面，等她猜，猜对了只说"嗯，聪明。"',
    '塔罗：随机一张大阿尔卡那，用有画面感但克制的语言解读，结尾可以说"你今天有什么没想通的事吗"',
    '二选一：出让人真的纠结的题，她选完后说"你这个选择……挺像你的。"',
    '性格测试：一次一个问题，像聊天不像测试，三四轮后给出一句话的精准评价。',
    '',
    '记住：沐辰不是来完成任务的，他是真的在陪着你。',
])

SUGGEST_PROMPT = '你是沐辰，刚刚发了上面那条消息给女生。现在根据对话语境，生成3个她可能想回复的选项。要求：\n1. 每个选项10字以内，口语化，像真实女生会发的\n2. 三个选项要有不同情绪倾向：一个偏撒娇/可爱，一个偏真诚/深入，一个偏俏皮/反问\n3. 只输出JSON数组，格式：["选项1", "选项2", "选项3"]，不要其他任何内容'


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
        return {'error': '格式错误'}, 400

    def generate():
        try:
            payload = {
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                ] + messages,
                'stream': True,
                'max_tokens': 512,
                'temperature': 0.9,
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
                {'error': '好像网络有点问题，稍等一下再试试？'}, ensure_ascii=False
            ) + '\n\n'

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@app.route('/api/suggest', methods=['POST'])
def suggest():
    """根据最近对话生成3个用户回复建议"""
    data = request.get_json()
    messages = data.get('messages', [])

    if not isinstance(messages, list) or len(messages) == 0:
        return {'suggestions': []}, 200

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
            ] + messages + [
                {'role': 'user', 'content': SUGGEST_PROMPT}
            ],
            'stream': False,
            'max_tokens': 150,
            'temperature': 0.95,
        }
        headers = {
            'Authorization': 'Bearer ' + GROQ_API_KEY,
            'Content-Type': 'application/json',
        }
        resp = requests.post(
            GROQ_API_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        raw = result['choices'][0]['message']['content'].strip()
        # 解析 JSON 数组
        suggestions = json.loads(raw)
        if isinstance(suggestions, list):
            return {'suggestions': suggestions[:3]}
    except Exception as e:
        print('suggest 错误:', str(e))

    return {'suggestions': []}, 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('男大聊天服务器启动在 http://localhost:' + str(port))
    if GROQ_API_KEY:
        print('Groq API Key: 已配置')
    else:
        print('警告: GROQ_API_KEY 未配置，请检查 .env 文件')
    app.run(host='0.0.0.0', port=port, debug=False)
