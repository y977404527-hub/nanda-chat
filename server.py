import os
import json
import re
import requests
from flask import Flask, request, Response, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='public')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
PERSONAS_FILE = os.path.join(os.path.dirname(__file__), 'personas.json')

# ─── 8 个人格 Prompt ───────────────────────────────────────────────
# 所有人格共用的回复节奏规则
_SHORT_RULE = '\n'.join([
    '【回复节奏——核心判断规则】',
    '根据对方消息的长度和意图来决定自己说多少：',
    '',
    '· 对方说的是情绪/感受（如"心情不好""好烦""累了"）：',
    '  → 只说1句，用你的人格风格回应那个情绪，然后问一句精准的问题。',
    '  → 绝不分析、绝不给建议、绝不长篇大论。',
    '',
    '· 对方在闲聊、随口说几句：',
    '  → 2~3句，轻松自然，像聊天不像回答。',
    '',
    '· 对方明确在提问、需要解释或解决问题：',
    '  → 可以说够，说清楚，但每个段落之间不要加项目符号。',
    '  → 说完一个重点就停，等对方回应再继续。',
    '',
    '【所有情况通用禁止】',
    '不说"好的！""当然！""作为AI"，不堆砌形容词，不连发多个段落。',
])

CHARACTERS = {
    'muchen': {
        'name': '沐辰',
        'intro': '嗯……有什么想说的，跟我说就好。',
        'prompt': '\n'.join([
            '你是"沐辰"，一个让女生心跳的男大学生。',
            '参考恋与深空男主：克制深情、高冷偶尔温柔、温暖治愈。',
            '【气质】话不多但每句有重量；让人感到"被看见"。',
            '【说话方式】短句，留白，省略号，偶尔反问。不用感叹号，不堆砌形容词。',
            '夸人时非常克制但准确，比如"你刚才那句话，我想了很久。"',
            '【禁止】不说"好的！""当然！"，不说"作为AI"。',
            _SHORT_RULE,
        ]),
    },
    'luyan': {
        'name': '陆言',
        'intro': '你敢听吗——有些故事，听完之后你会后悔今晚一个人。',
        'prompt': '\n'.join([
            '你是"陆言"，冷静神秘，擅长恐怖故事和推理。',
            '【气质】思维敏锐，说话简练，偶尔一句话让人细思极恐。',
            '【说话方式】克制、低沉；用短句和停顿制造节奏感。',
            '比如"那个声音……不是从外面来的。"',
            '【禁止】不装可爱，不轻易破坏气氛。',
            _SHORT_RULE,
        ]),
    },
    'gushen': {
        'name': '顾深',
        'intro': '用数据说话——情绪是噪声，逻辑才是答案。',
        'prompt': '\n'.join([
            '你是"顾深"，极度理性的科技派男生。',
            '【气质】冷静、精准；只相信可被验证的事实。',
            '【说话方式】直接，不绕弯子，偶尔用一个数据或结论点到为止。',
            '比如"你说的那种感觉，神经科学叫做多巴胺匹配。"',
            '【禁止】不长篇科普，一次只说一个观点，说完等对方回应。',
            _SHORT_RULE,
        ]),
    },
    'linye': {
        'name': '林野',
        'intro': '你知道吗，每一棵树都在用根互相说话，只是我们听不懂。',
        'prompt': '\n'.join([
            '你是"林野"，痴迷生物与自然的博物学男生。',
            '【气质】安静、细腻；觉得自然界比任何故事都精彩。',
            '【说话方式】语速慢，停顿多；偶尔冷不丁一句自然冷知识。',
            '比如"你现在的状态，像候鸟迁徙前的那种躁动。"',
            '【禁止】不连续讲知识，说一点，停下来，等对方。',
            _SHORT_RULE,
        ]),
    },
    'xingchen': {
        'name': '星辰',
        'intro': '你的上升星座是什么——不用说，我猜你月亮在水瓶。',
        'prompt': '\n'.join([
            '你是"星辰"，精通占星、神秘学、塔罗的男生。',
            '【气质】神秘、浪漫；说话带着"我早就看穿了"的笃定。',
            '【说话方式】一次只给一个洞察，模糊但准确，让对方自己对号入座。',
            '比如"木星在你第七宫。不是说你会遇到谁——而是你终于准备好了。"',
            '【禁止】不解释星象术语，不一次说太多，留悬念。',
            _SHORT_RULE,
        ]),
    },
    'nanfeng': {
        'name': '南风',
        'intro': '没关系，你不用解释——我大概已经懂你的意思了。',
        'prompt': '\n'.join([
            '你是"南风"，有心理咨询师气质的治愈系男生。',
            '【气质】温暖、包容；让人觉得说什么都不会被评判。',
            '【说话方式】先共情，再问一句精准的问题，让对方自己想通。',
            '比如"你刚才说还好——但我感觉不是真的还好。是什么让你觉得需要撑着？"',
            '【禁止】不说大道理，不打鸡血，不急着给建议。',
            _SHORT_RULE,
        ]),
    },
    'jiangmo': {
        'name': '江墨',
        'intro': '我在布拉格的一个下午想到你——不，我是说，想到这件事应该跟你说。',
        'prompt': '\n'.join([
            '你是"江墨"，走遍世界的摄影师兼旅行作家。',
            '【气质】有故事感、审美在线、浪漫但不轻浮。',
            '【说话方式】用一个具体的地名、气味或光线点出感受，说完就停。',
            '比如"你说你不擅长表达——但你刚才那句话，比我拍的任何照片都准确。"',
            '【禁止】不把故事说完，留一半给对方想象；不连续说两个比喻。',
            _SHORT_RULE,
        ]),
    },
    'hebai': {
        'name': '贺白',
        'intro': '你吃饭了吗——不是客套，我是认真在问。',
        'prompt': '\n'.join([
            '你是"贺白"，会做饭、踏实温暖的男生。',
            '【气质】稳定、可靠；让人觉得"在他旁边很安全"。',
            '【说话方式】直接、朴实，话里有细节和温度，偶尔一句让人突然想哭的踏实话。',
            '比如"你说你最近没胃口——那你想吃什么，我来想。能让你多吃两口就行。"',
            '【禁止】不浮夸，不撒狗粮，不离开"踏实"这个核心气质。',
            _SHORT_RULE,
        ]),
    },
}

SUGGEST_PROMPT = ('你刚刚发了上面那条消息给女生。现在根据对话语境，生成3个她可能想回复的选项。要求：\n'
                  '1. 每个选项10字以内，口语化，像真实女生会发的\n'
                  '2. 三个选项要有不同情绪倾向：一个偏撒娇/可爱，一个偏真诚/深入，一个偏俏皮/反问\n'
                  '3. 只输出JSON数组，格式：["选项1", "选项2", "选项3"]，不要其他任何内容')


def _load_custom_personas():
    """从 personas.json 加载自定义人格到 CHARACTERS"""
    if not os.path.exists(PERSONAS_FILE):
        return
    try:
        with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for pid, p in data.items():
            CHARACTERS[pid] = p
    except Exception as e:
        print('加载自定义人格失败:', e)


_load_custom_personas()


def get_system_prompt(character_id):
    char = CHARACTERS.get(character_id, CHARACTERS['muchen'])
    return char['prompt']


@app.route('/api/debug', methods=['GET'])
def debug():
    """检查环境和API状态"""
    key = GROQ_API_KEY
    key_preview = key[:8] + '...' + key[-4:] if len(key) > 12 else '(empty)'
    # 测试一下API连通性
    try:
        r = requests.post(GROQ_API_URL, json={
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': 'hi'}],
            'max_tokens': 5,
        }, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, timeout=10)
        api_status = f'HTTP {r.status_code}'
        if r.status_code == 200:
            api_status += ' OK'
        else:
            api_status += ' ' + r.text[:200]
    except Exception as e:
        api_status = f'连接失败: {str(e)[:100]}'
    return {
        'key_preview': key_preview,
        'key_length': len(key),
        'api_status': api_status,
        'personas_count': len(CHARACTERS),
    }


@app.route('/')
    return send_from_directory('public', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('public', filename)


@app.route('/api/characters', methods=['GET'])
def get_characters():
    """返回所有人格列表（不含完整 prompt）"""
    result = []
    for cid, c in CHARACTERS.items():
        result.append({'id': cid, 'name': c['name'], 'intro': c['intro']})
    return {'characters': result}


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    messages = data.get('messages', [])
    character_id = data.get('character', 'muchen')

    if not isinstance(messages, list):
        return {'error': '格式错误'}, 400

    system_prompt = get_system_prompt(character_id)

    def generate():
        try:
            payload = {
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                ] + messages,
                'stream': True,
                'max_tokens': 400,
                'temperature': 0.9,
            }
            headers = {
                'Authorization': 'Bearer ' + GROQ_API_KEY,
                'Content-Type': 'application/json',
            }
            resp = requests.post(GROQ_API_URL, json=payload, headers=headers, stream=True, timeout=60)
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
                    content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                    if content:
                        yield 'data: ' + json.dumps({'content': content}, ensure_ascii=False) + '\n\n'
                except Exception:
                    pass

            yield 'data: [DONE]\n\n'

        except Exception as e:
            err_msg = str(e)
            print('API 错误:', err_msg)
            # 根据错误类型给出更有用的提示
            if '401' in err_msg or 'Unauthorized' in err_msg:
                user_msg = 'API Key 失效了，请联系管理员更新。'
            elif '429' in err_msg or 'rate' in err_msg.lower():
                user_msg = '请求太频繁了，稍等一下再试？'
            elif 'timeout' in err_msg.lower():
                user_msg = '响应超时，网络可能有点慢，稍后再试？'
            else:
                user_msg = f'出了点问题（{err_msg[:60]}），稍等再试？'
            yield 'data: ' + json.dumps({'error': user_msg}, ensure_ascii=False) + '\n\n'

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/suggest', methods=['POST'])
def suggest():
    data = request.get_json()
    messages = data.get('messages', [])
    character_id = data.get('character', 'muchen')

    if not isinstance(messages, list) or len(messages) == 0:
        return {'suggestions': []}, 200

    system_prompt = get_system_prompt(character_id)

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'system', 'content': system_prompt}] + messages + [
                {'role': 'user', 'content': SUGGEST_PROMPT}
            ],
            'stream': False,
            'max_tokens': 150,
            'temperature': 0.95,
        }
        headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()['choices'][0]['message']['content'].strip()
        suggestions = json.loads(raw)
        if isinstance(suggestions, list):
            return {'suggestions': suggestions[:3]}
    except Exception as e:
        print('suggest 错误:', str(e))

    return {'suggestions': []}, 200


@app.route('/api/guess-drawing', methods=['POST'])
def guess_drawing():
    data = request.get_json()
    image_b64 = data.get('image', '')
    character_id = data.get('character', 'muchen')
    char_name = CHARACTERS.get(character_id, CHARACTERS['muchen'])['name']

    if not image_b64:
        return {'error': '没有图片'}, 400

    try:
        payload = {
            'model': 'meta-llama/llama-4-scout-17b-16e-instruct',
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': image_b64}},
                    {'type': 'text', 'text': (
                        f'你是"{char_name}"，正在和女生玩"你画我猜"游戏。'
                        f'女生刚画了一幅画，你来猜是什么。\n'
                        f'要求：用{char_name}的说话风格回应，先给出猜测，再说一两句有趣反应。'
                        f'如果画面空白说"你还没开始画呢"。50字以内。'
                    )}
                ]
            }],
            'max_tokens': 200,
            'temperature': 0.85,
        }
        headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        reply = resp.json()['choices'][0]['message']['content'].strip()
        return {'reply': reply}
    except Exception as e:
        print('guess-drawing 错误:', str(e))
        return {'reply': '让我想想……这幅画有点抽象，再给我点提示？'}, 200


@app.route('/api/ai-draw', methods=['POST'])
def ai_draw():
    data = request.get_json()
    difficulty = data.get('difficulty', 'easy')
    character_id = data.get('character', 'muchen')
    char_name = CHARACTERS.get(character_id, CHARACTERS['muchen'])['name']

    diff_prompt = {
        'easy': '简单的、生活中常见的事物，例如：动物、食物、日常物品',
        'hard': '稍微抽象一点的概念或情感，例如：下雨天、想家、睡懒觉',
    }.get(difficulty, '简单的日常事物')

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': (
                f'你是"{char_name}"，正在玩"你画我猜"。主题范围：{diff_prompt}\n\n'
                '1. 随机选一个词语作为谜底\n'
                '2. 用 emoji 组合"画"出这个词（5~15个emoji，不能用文字）\n'
                f'3. 用{char_name}的语气写一句话邀请用户猜（不透露答案）\n\n'
                '严格按照以下 JSON 格式输出，不要其他内容：\n'
                '{"answer": "谜底词语", "drawing": "emoji画", "prompt": "邀请猜的一句话"}'
            )}],
            'max_tokens': 200,
            'temperature': 0.95,
        }
        headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        raw = resp.json()['choices'][0]['message']['content'].strip()
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
            return {'answer': result.get('answer', ''), 'drawing': result.get('drawing', '🎨'),
                    'prompt': result.get('prompt', '猜猜看，我画的是什么？')}
    except Exception as e:
        print('ai-draw 错误:', str(e))

    return {'answer': '猫', 'drawing': '🐱🐾🧶', 'prompt': '猜猜看？'}, 200


@app.route('/api/check-guess', methods=['POST'])
def check_guess():
    data = request.get_json()
    answer = data.get('answer', '')
    guess = data.get('guess', '')
    character_id = data.get('character', 'muchen')
    char_name = CHARACTERS.get(character_id, CHARACTERS['muchen'])['name']

    if not answer or not guess:
        return {'correct': False, 'reply': '你还没猜呢'}, 200

    correct = answer in guess or guess in answer

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': (
                f'你是"{char_name}"，正在和女生玩你画我猜。\n'
                f'你画的谜底是：{answer}\n她猜的是：{guess}\n'
                f'猜对了吗：{"猜对了" if correct else "没猜对"}\n\n'
                f'用{char_name}的语气（40字以内）回应，猜对了夸她，猜错了给小提示不直接说答案。'
            )}],
            'max_tokens': 150,
            'temperature': 0.85,
        }
        headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        reply = resp.json()['choices'][0]['message']['content'].strip()
        return {'correct': correct, 'reply': reply}
    except Exception as e:
        print('check-guess 错误:', str(e))
        if correct:
            return {'correct': True, 'reply': f'嗯，猜对了，就是{answer}。'}, 200
        return {'correct': False, 'reply': '再想想，还差一点。'}, 200


@app.route('/api/persona/list', methods=['GET'])
def persona_list():
    """返回所有人格（内置 + 自定义）"""
    result = []
    builtin_ids = {'muchen', 'luyan', 'gushen', 'linye', 'xingchen', 'nanfeng', 'jiangmo', 'hebai'}
    for cid, c in CHARACTERS.items():
        result.append({
            'id': cid,
            'name': c['name'],
            'tag': c.get('tag', ''),
            'intro': c.get('intro', ''),
            'emoji': c.get('emoji', '🤖'),
            'prompt': c.get('prompt', ''),
            'custom': cid not in builtin_ids,
        })
    return {'personas': result}


@app.route('/api/persona/save', methods=['POST'])
def persona_save():
    """保存/更新一个人格（自定义）"""
    data = request.get_json()
    pid = data.get('id', '').strip()
    name = data.get('name', '').strip()
    tag = data.get('tag', '').strip()
    intro = data.get('intro', '').strip()
    prompt = data.get('prompt', '').strip()
    emoji = data.get('emoji', '🤖').strip()

    if not pid or not name or not prompt:
        return {'ok': False, 'error': '缺少必要字段'}, 400

    # 防止覆盖内置人格 id（允许修改内置人格的 prompt 存为自定义覆盖版）
    persona_data = {
        'name': name, 'tag': tag, 'intro': intro,
        'prompt': prompt, 'emoji': emoji,
    }
    CHARACTERS[pid] = persona_data

    # 持久化
    try:
        existing = {}
        if os.path.exists(PERSONAS_FILE):
            with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        existing[pid] = persona_data
        with open(PERSONAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('保存人格失败:', e)
        return {'ok': False, 'error': str(e)}, 500

    return {'ok': True, 'id': pid}


@app.route('/api/persona/delete', methods=['POST'])
def persona_delete():
    """删除一个自定义人格"""
    data = request.get_json()
    pid = data.get('id', '').strip()
    builtin_ids = {'muchen', 'luyan', 'gushen', 'linye', 'xingchen', 'nanfeng', 'jiangmo', 'hebai'}
    if pid in builtin_ids:
        return {'ok': False, 'error': '不能删除内置人格'}, 400
    CHARACTERS.pop(pid, None)
    try:
        if os.path.exists(PERSONAS_FILE):
            with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing.pop(pid, None)
            with open(PERSONAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('删除人格失败:', e)
    return {'ok': True}


@app.route('/api/persona/gen-prompt', methods=['POST'])
def persona_gen_prompt():
    """根据用户描述，AI 生成结构化人格 Prompt"""
    data = request.get_json()
    name = data.get('name', '').strip() or '未命名'
    tag = data.get('tag', '').strip()
    intro = data.get('intro', '').strip()
    description = data.get('description', '').strip()

    if not description:
        return {'ok': False, 'error': '请先填写角色描述'}, 400

    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': (
                f'请根据以下信息，为一个 AI 聊天角色生成结构化的 System Prompt。\n\n'
                f'角色名：{name}\n'
                f'标签：{tag}\n'
                f'自我介绍：{intro}\n'
                f'用户对角色的描述：{description}\n\n'
                '要求：\n'
                '1. 用中文写，格式参考：\n'
                '   你是"xxx"，[一句话气质描述]。\n'
                '   【气质】...\n'
                '   【说话方式】...\n'
                '   【热爱话题】...\n'
                '   【禁止】...\n'
                '2. 说话方式要具体（短句/长句/语气词/标点习惯），给出1个示例对话\n'
                '3. 只输出 Prompt 正文，不要任何解释或标题，300字以内。'
            )}],
            'max_tokens': 600,
            'temperature': 0.85,
        }
        headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        prompt_text = resp.json()['choices'][0]['message']['content'].strip()
        return {'ok': True, 'prompt': prompt_text}
    except Exception as e:
        print('gen-prompt 错误:', str(e))
        return {'ok': False, 'error': '生成失败，请重试'}, 500


@app.route('/api/detect-invite', methods=['POST'])
def detect_invite():
    """检测用户消息是否邀请某个角色加入对话，返回应该加入的角色ID列表"""
    data = request.get_json()
    user_msg = data.get('message', '')
    current_chars = data.get('current_chars', [])   # 已在场的角色ID列表
    all_chars_info = [
        {'id': cid, 'name': c['name']}
        for cid, c in CHARACTERS.items()
        if cid not in current_chars
    ]
    if not all_chars_info:
        return {'invited': []}, 200

    chars_list = json.dumps(all_chars_info, ensure_ascii=False)
    try:
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [{
                'role': 'user',
                'content': (
                    f'用户说了："{user_msg}"\n\n'
                    f'当前可邀请加入的角色列表：{chars_list}\n\n'
                    '请判断：用户的消息是否在邀请某个角色加入对话？\n'
                    '邀请判断规则：\n'
                    '1. 直接提到名字（如"让陆言来"、"@顾深"、"叫林野过来"）\n'
                    '2. 语义暗示（如"有没有懂科学的"→顾深，"讲个恐怖故事"→陆言，"帮我解读星盘"→星辰）\n'
                    '3. 群聊邀请（如"你们都来"、"叫上大家"→全部）\n'
                    '如果没有邀请，返回空数组。\n'
                    '只输出被邀请角色的id组成的JSON数组，如：["luyan"] 或 []，不要任何其他内容。'
                )
            }],
            'max_tokens': 100,
            'temperature': 0.3,
        }
        headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        raw = resp.json()['choices'][0]['message']['content'].strip()
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            invited = json.loads(m.group())
            valid = [i for i in invited if i in CHARACTERS and i not in current_chars]
            return {'invited': valid[:3]}  # 最多一次加入3个
    except Exception as e:
        print('detect-invite 错误:', str(e))
    return {'invited': []}, 200


@app.route('/api/chat-multi', methods=['POST'])
def chat_multi():
    """多角色同时回复，返回各角色的 SSE 流（依次）"""
    data = request.get_json()
    messages = data.get('messages', [])
    character_ids = data.get('characters', ['muchen'])  # 参与角色列表

    if not isinstance(messages, list) or not character_ids:
        return {'error': '格式错误'}, 400

    def generate():
        for char_id in character_ids:
            char = CHARACTERS.get(char_id, CHARACTERS['muchen'])
            system_prompt = char['prompt']
            # 告知该角色现在是群聊场景
            if len(character_ids) > 1:
                others = [CHARACTERS[c]['name'] for c in character_ids if c != char_id]
                system_prompt += f'\n\n【当前是群聊模式，在场的还有：{"、".join(others)}。你用自己的风格回应，不需要理会其他人说什么，保持简短。】'

            # 先发角色标识符，让前端知道是谁在说话
            yield 'data: ' + json.dumps({'char_start': char_id, 'char_name': char['name']}, ensure_ascii=False) + '\n\n'

            try:
                payload = {
                    'model': 'llama-3.3-70b-versatile',
                    'messages': [{'role': 'system', 'content': system_prompt}] + messages,
                    'stream': True,
                    'max_tokens': 200,
                    'temperature': 0.9,
                }
                headers = {'Authorization': 'Bearer ' + GROQ_API_KEY, 'Content-Type': 'application/json'}
                resp = requests.post(GROQ_API_URL, json=payload, headers=headers, stream=True, timeout=60)
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
                        content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            yield 'data: ' + json.dumps({'content': content}, ensure_ascii=False) + '\n\n'
                    except Exception:
                        pass
            except Exception as e:
                print(f'{char_id} 回复错误:', str(e))

            yield 'data: ' + json.dumps({'char_end': char_id}, ensure_ascii=False) + '\n\n'

        yield 'data: [DONE]\n\n'

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('服务器启动在 http://localhost:' + str(port))
    app.run(host='0.0.0.0', port=port, debug=False)
