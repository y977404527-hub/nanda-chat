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


@app.route('/api/guess-drawing', methods=['POST'])
def guess_drawing():
    """你画我猜：接收 base64 图片，让 AI 用沐辰语气猜出内容"""
    data = request.get_json()
    image_b64 = data.get('image', '')  # data:image/png;base64,xxx

    if not image_b64:
        return {'error': '没有图片'}, 400

    try:
        payload = {
            'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {'url': image_b64}
                        },
                        {
                            'type': 'text',
                            'text': (
                                '你是沐辰，一个温柔帅气的男大学生，正在和女生玩"你画我猜"游戏。'
                                '女生刚刚画了一幅画，你来猜这幅画画的是什么。\n'
                                '要求：\n'
                                '1. 用沐辰的语气说话：简短、克制、偶尔有点撩\n'
                                '2. 先给出你猜的答案（加粗或直接说），再说一两句有趣的反应\n'
                                '3. 如果画得很抽象或看不清，就调侃一下，但不要嘲笑\n'
                                '4. 如果画面是空白的，说"你还没开始画呢"\n'
                                '5. 回复控制在50字以内，轻松有趣\n'
                                '示例风格："是……猫吗？画得很可爱，我觉得你画画的时候一定很认真。"'
                            )
                        }
                    ]
                }
            ],
            'max_tokens': 200,
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
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        reply = result['choices'][0]['message']['content'].strip()
        return {'reply': reply}
    except Exception as e:
        print('guess-drawing 错误:', str(e))
        return {'reply': '让我想想……这幅画有点抽象，再给我点提示？'}, 200


@app.route('/api/ai-draw', methods=['POST'])
def ai_draw():
    """沐辰画，用户猜：AI 生成 emoji 画 + 答案（先隐藏）"""
    data = request.get_json()
    difficulty = data.get('difficulty', 'easy')  # easy / hard

    diff_prompt = {
        'easy': '简单的、生活中常见的事物，例如：动物、食物、日常物品',
        'hard': '稍微抽象一点的概念或情感，例如：下雨天、想家、睡懒觉',
    }.get(difficulty, '简单的日常事物')

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {
                    'role': 'user',
                    'content': (
                        f'你正在玩"你画我猜"，现在你来"画"，用户来猜。\n'
                        f'主题范围：{diff_prompt}\n\n'
                        '请完成以下任务：\n'
                        '1. 随机选一个词语作为谜底\n'
                        '2. 用 emoji 组合来"画"出这个词（不能用文字描述，只用 emoji，5~15个）\n'
                        '3. 用沐辰的语气写一句话邀请用户来猜（不透露答案）\n\n'
                        '严格按照以下 JSON 格式输出，不要输出其他任何内容：\n'
                        '{"answer": "谜底词语", "drawing": "emoji画", "prompt": "邀请用户猜的一句话"}'
                    )
                }
            ],
            'max_tokens': 200,
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
            timeout=20,
        )
        resp.raise_for_status()
        raw = resp.json()['choices'][0]['message']['content'].strip()
        # 提取 JSON
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
            return {
                'answer': result.get('answer', ''),
                'drawing': result.get('drawing', '🎨'),
                'prompt': result.get('prompt', '你猜猜看，我画的是什么？'),
            }
    except Exception as e:
        print('ai-draw 错误:', str(e))

    return {
        'answer': '猫',
        'drawing': '🐱🐾🧶',
        'prompt': '猜猜看，我画的是什么？',
    }, 200


@app.route('/api/check-guess', methods=['POST'])
def check_guess():
    """判断用户猜测是否正确，用沐辰语气回应"""
    data = request.get_json()
    answer = data.get('answer', '')
    guess = data.get('guess', '')

    if not answer or not guess:
        return {'correct': False, 'reply': '你还没猜呢'}, 200

    # 简单判断：猜测内容包含答案（或接近）
    correct = answer in guess or guess in answer

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {
                    'role': 'user',
                    'content': (
                        f'你是沐辰，正在和女生玩你画我猜。\n'
                        f'你画的谜底是：{answer}\n'
                        f'她猜的是：{guess}\n'
                        f'猜对了吗：{"猜对了" if correct else "没猜对"}\n\n'
                        '用沐辰的语气（简短克制、偶尔撩、不用感叹号）回应她这次猜测。'
                        '如果猜对了表示赞赏，如果猜错了给一个小提示，不直接说答案。'
                        '控制在40字以内。'
                    )
                }
            ],
            'max_tokens': 150,
            'temperature': 0.85,
        }
        headers = {
            'Authorization': 'Bearer ' + GROQ_API_KEY,
            'Content-Type': 'application/json',
        }
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        reply = resp.json()['choices'][0]['message']['content'].strip()
        return {'correct': correct, 'reply': reply}
    except Exception as e:
        print('check-guess 错误:', str(e))
        if correct:
            return {'correct': True, 'reply': f'嗯，猜对了，就是{answer}。'}, 200
        else:
            return {'correct': False, 'reply': '再想想，还差一点。'}, 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('男大聊天服务器启动在 http://localhost:' + str(port))
    if GROQ_API_KEY:
        print('Groq API Key: 已配置')
    else:
        print('警告: GROQ_API_KEY 未配置，请检查 .env 文件')
    app.run(host='0.0.0.0', port=port, debug=False)
