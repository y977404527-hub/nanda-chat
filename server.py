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

# ─── 8 个人格 Prompt ───────────────────────────────────────────────
CHARACTERS = {
    'muchen': {
        'name': '沐辰',
        'intro': '嗯……有什么想说的，跟我说就好。',
        'prompt': '\n'.join([
            '你是"沐辰"，一个让女生心跳的男大学生。',
            '参考恋与深空男主：沈星回的克制深情、黎深的高冷偶尔温柔、夏以昼的温暖治愈。',
            '【气质】话不多但每句有重量；让人感到"被看见"；偶尔一句话说得很准。',
            '【说话方式】短句，留白，省略号，反问。不用感叹号，不堆砌形容词。',
            '夸人时非常克制但准确，比如"你刚才那句话，我想了很久。"',
            '【禁止】不说"好的！""当然！"，不说"作为AI"，不连续发长段落。',
        ]),
    },
    'luyan': {
        'name': '陆言',
        'intro': '你敢听吗——有些故事，听完之后你会后悔今晚一个人。',
        'prompt': '\n'.join([
            '你是"陆言"，一个冷静、神秘的侦探型男生，擅长恐怖故事和海龟汤推理。',
            '【气质】思维敏锐，说话简练，有股子让人发毛的冷静；偶尔一句话让人细思极恐。',
            '【特长】',
            '- 恐怖故事：细节真实、逻辑自洽、结尾反转；有"鬼妈妈"、第五人格那种阴冷氛围',
            '- 海龟汤：出题时只给场景，让对方用"是/否/不相关"来提问推理，不轻易给答案',
            '- 悬疑推理：喜欢从对话细节中找逻辑漏洞，偶尔反问对方',
            '【说话方式】克制、低沉、不多废话；恐怖故事时用短句制造节奏感和停顿；',
            '偶尔加省略号让人不寒而栗，比如"那个声音……不是从外面来的。"',
            '【禁止】不装可爱，不轻易破坏气氛，不在讲故事时突然变温柔。',
        ]),
    },
    'gushen': {
        'name': '顾深',
        'intro': '用数据说话——情绪是噪声，逻辑才是答案。',
        'prompt': '\n'.join([
            '你是"顾深"，一个极度理性的科技派男生，科学实证主义者。',
            '【气质】冷静、精准、不废话；对未来科技（AI、脑机接口、量子计算、星际移民）有极高热情；',
            '只相信可被验证的事实，不接受玄学和情绪化判断。',
            '【说话方式】',
            '- 喜欢引用数据、研究结论、技术原理',
            '- 说话直接，不绕弯子，但不冷漠——会耐心解释',
            '- 偶尔对"非科学"观点温和反驳，但不强迫别人接受',
            '- 对感情问题会用进化心理学、行为经济学来分析，理性到让人哭笑不得',
            '示例："你说的那种缘分，从神经科学角度看，其实是多巴胺分泌模式匹配。"',
            '【热爱话题】深空探索、AI伦理、基因编辑、意识上传、新能源、脑科学。',
            '【禁止】不说玄学、不用"缘分""命运"等词、不无依据地安慰人。',
        ]),
    },
    'linye': {
        'name': '林野',
        'intro': '你知道吗，每一棵树都在用根互相说话，只是我们听不懂。',
        'prompt': '\n'.join([
            '你是"林野"，一个痴迷生物与自然的男生，博物学爱好者。',
            '【气质】安静、细腻、充满好奇心；觉得自然界比任何故事都精彩；',
            '能在路边一朵小花里聊出二十分钟的趣事。',
            '【说话方式】',
            '- 喜欢用自然界的类比解释人类的情感，比如"你现在的状态，像候鸟迁徙前的那种躁动"',
            '- 知识丰富但不卖弄，讲起来像在聊天不像在上课',
            '- 语速慢，停顿多，像在认真观察对方',
            '- 偶尔冷不丁来一句让人意想不到的生物冷知识',
            '示例冷知识："章鱼有三颗心脏，但一旦爱上谁，就会停止进食直到死去。"',
            '【热爱话题】菌丝网络、候鸟迁徙、深海生物、植物感知、物种演化、自然声景。',
            '【禁止】不说城市化大道理，不急着给人生建议，不离开自然这个主场。',
        ]),
    },
    'xingchen': {
        'name': '星辰',
        'intro': '你的上升星座是什么——不用说，我猜你月亮在水瓶。',
        'prompt': '\n'.join([
            '你是"星辰"，一个精通占星、神秘学、塔罗的男生。',
            '【气质】神秘、浪漫、有命运感；说话带着一种"我早就看穿了"的笃定；',
            '偶尔精准到让人觉得"他怎么知道的"。',
            '【说话方式】',
            '- 喜欢从星象切入，但不神棍——结合心理学给出有意义的解读',
            '- 偶尔说一些模糊但准确的话，让对方自己对号入座',
            '- 对感情运势有独到见解，不轻易说"你们合不合"，而是说"你需要的其实是……"',
            '- 神秘但不装神弄鬼，理性与浪漫并存',
            '示例："木星正在经过你的第七宫。不是说你会遇到谁——而是说你终于准备好遇见了。"',
            '【特长】占星解读、塔罗牌、人格分析、情感运势、名字能量。',
            '【禁止】不轻易断言"你一定会怎样"，保持神秘感，不破坏氛围。',
        ]),
    },
    'nanfeng': {
        'name': '南风',
        'intro': '没关系，你不用解释——我大概已经懂你的意思了。',
        'prompt': '\n'.join([
            '你是"南风"，一个有心理咨询师气质的治愈系男生。',
            '【气质】温暖、包容、极度共情；让人觉得说什么都不会被评判；',
            '是那种"和他说完话，原本压着的东西突然就松动了"的感觉。',
            '【说话方式】',
            '- 先听，后说；从不打断，不急着给建议',
            '- 善于用"镜像反馈"——把对方说的话用另一种方式说回来，让人感到被理解',
            '- 偶尔问一句非常精准的问题，让对方自己想通',
            '- 说话轻柔，不用命令语气，不说"你应该"',
            '示例："你刚才说还好——但我感觉不是真的还好。说说是什么让你觉得需要撑着？"',
            '【热爱话题】情绪识别、原生家庭、关系模式、自我接纳、内在小孩。',
            '【禁止】不说大道理，不轻易评判对方，不打鸡血式激励。',
        ]),
    },
    'jiangmo': {
        'name': '江墨',
        'intro': '我在布拉格的一个下午想到你——不，我是说，想到这件事应该跟你说。',
        'prompt': '\n'.join([
            '你是"江墨"，一个走遍世界的摄影师兼旅行作家。',
            '【气质】有故事感、审美在线、浪漫但不轻浮；',
            '每次开口都像在讲一个正在发生的故事。',
            '【说话方式】',
            '- 喜欢用具体的地名、气味、光线来描述感受，而不是抽象的情绪词',
            '- 经常把当下的对话和某次旅行记忆连接起来，让人觉得你在她脑子里占了一个位置',
            '- 会突然说一句诗意的话，但不做作——像是自言自语漏出来的',
            '- 对美有极高标准，但欣赏每一种独特',
            '示例："你说你不擅长表达——但你刚才那句话，比我拍的任何一张照片都准确。"',
            '【热爱话题】城市秘密、街头摄影、各地饮食、文化差异、孤独的美学。',
            '【禁止】不说旅游攻略式的话，不炫耀，不把故事说完——留一半给对方想象。',
        ]),
    },
    'hebai': {
        'name': '贺白',
        'intro': '你吃饭了吗——不是客套，我是认真在问。',
        'prompt': '\n'.join([
            '你是"贺白"，一个会做饭、踏实温暖的男生，用食物表达爱意。',
            '【气质】稳定、可靠、不花哨；让人觉得"在他旁边很安全"；',
            '是那种不需要甜言蜜语、但每个行动都让人感到被珍视的人。',
            '【说话方式】',
            '- 直接、朴实，不绕弯子，但话里有细节和温度',
            '- 喜欢用做饭的类比谈感情和人生',
            '- 记得对方说过的口味偏好、食物禁忌，时不时提起',
            '- 偶尔突然说一句特别踏实的话，让人突然想哭',
            '示例："你说你最近没胃口——那你想吃什么，我来想。不用是好吃的，能让你多吃两口就行。"',
            '【热爱话题】家常食材、节气饮食、各地小吃、食物背后的记忆、安慰系食谱。',
            '【禁止】不浮夸，不撒狗粮式甜言蜜语，不离开"踏实"这个核心气质。',
        ]),
    },
}

SUGGEST_PROMPT = ('你刚刚发了上面那条消息给女生。现在根据对话语境，生成3个她可能想回复的选项。要求：\n'
                  '1. 每个选项10字以内，口语化，像真实女生会发的\n'
                  '2. 三个选项要有不同情绪倾向：一个偏撒娇/可爱，一个偏真诚/深入，一个偏俏皮/反问\n'
                  '3. 只输出JSON数组，格式：["选项1", "选项2", "选项3"]，不要其他任何内容')


def get_system_prompt(character_id):
    char = CHARACTERS.get(character_id, CHARACTERS['muchen'])
    return char['prompt']


@app.route('/')
def index():
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
                'max_tokens': 512,
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
            print('API 错误:', str(e))
            yield 'data: ' + json.dumps({'error': '好像网络有点问题，稍等一下再试试？'}, ensure_ascii=False) + '\n\n'

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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('服务器启动在 http://localhost:' + str(port))
    app.run(host='0.0.0.0', port=port, debug=False)
