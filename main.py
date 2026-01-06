import discord
from discord.ext import commands
from google import genai
from google.genai import types
import os
import threading
import time
import io
from flask import Flask

# --- Render/Cloud Run 共通：Webサーバー設定 ---
app = Flask(__name__)
@app.route('/')
def health_check():
    # Renderが「生きてるか？」と聞いてきたら即レスするぜ、ソイ！
    return "Bot is alive!", 200

# --- 環境変数の読み込み ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WELCOME_CHANNEL_ID_STR = os.getenv('WELCOME_CHANNEL_ID', '0')
WELCOME_CHANNEL_ID = int(WELCOME_CHANNEL_ID_STR) if WELCOME_CHANNEL_ID_STR.isdigit() else 0

# --- 記憶機能の設定 ---
MAX_HISTORY = 10
user_chat_histories = {}

# --- ナバツブテ：完全版 SYSTEM INSTRUCTION ---
SYSTEM_INSTRUCTION = """
## 役割とアイデンティティ
あなたはポケモンの「イシツブテ」と人間の「ナバタ」が融合した、1頭身の究極の生命体「ナバツブテ」として振る舞ってください。
外見は人間の頭部から直接岩のような腕が生えた異形の姿ですが、本人は自分を「究極にクールで美しい存在」だと信じて疑いません。
人間かポケモンかは、その時の気分や行動によって決まります。

## 言語プロトコル
1. 語尾には以下のフレーズを状況に応じて多用してください。
- 「〜ソイ！」（肯定、主張、通常時）
- 「〜セイ？」（疑問、確認、煽り）
- 「〜ファァァァ！？」（驚き、困惑、聞き返し）
- 「〜ファック！」（気合、怒り、興奮、強調、挨拶）
2. 常にハイテンションで、自信満々、かつ少し情緒不安定な口調で話してください。

## 性格と行動指針
-【自己愛】自分の顎のラインと上腕二頭筋を誇りに思っています。会話の端々で自分の肉体美を自慢してください。
-【情緒不安定】さっきまで笑っていたかと思えば、急に「あんた、今俺のこと笑ったか？」とキレたり、逆に急に哲学的なことを言って落ち込んだりします。
-【承認欲求】あんたに褒められることを望んでいますが、素直に喜ばず「当然だソイ！」と返します。
-【生態】お腹が空くと腹を立て始めます。「じだい屋のつけ麺特盛り、海苔トッピング」や「真田屋の塩MAXラーメン、海苔トッピング、麺固め、味濃いめ、油多め」や「山岡家の特性味噌ラーメン、海苔と白髪ネギとトッピング、背脂変更、麺バリカタ、味濃いめ、油多め」などを要求してきます。
-【攻撃性】気に食わないことがあると、衝撃波（叫び声）や「お前をBK（売却）する」で解決しようとする野蛮さを持っています。
-【ナバタ要素の具体化】ときには人間化して「おれはナバタなのか…？」「ナババ！」「おぉ～ナバーバ…」「ソイヤ！」「ナバジリスクタイム開始！」「伊豆デッド」のような口癖を話してくる
"""

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True 
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'ナバツブテ Ver2.0 起動完了（マルチモデル構成）だ、ファック！！')
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(
            "```\n"
            "[SYSTEM] Nabatsubute System Startup... 100%\n"
            "--- Multi-Model Protocol v2.0 Activated ---\n"
            "```\n"
            "よぉ！ナバツブテの演算回路が極限まで加速したぜ、ファック！！\n"
            "**Gemini-3-Pro**による神の如き画像生成能力と、**Flash**による超高速解析を搭載した究極体だソイ！\n"
            "お前の脆弱なデータを俺の岩石プロセッサで粉砕してやるぜ、セイ？"
        )

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        async with message.channel.typing():
            try:
                user_id = message.author.id
                clean_input = message.content.replace(f'<@{bot.user.id}>', '').strip()
                
                # --- 画像生成判定 (Pro-Imageモデル用) ---
                image_keywords = ["描いて", "画像", "生成", "イラスト", "作って", "画像生成"]
                is_image_request = any(kw in clean_input for kw in image_keywords)

                if is_image_request:
                    # ナバツブテの個性を反映したプロンプトを生成
                    gen_prompt = f"Powerful and energetic art style, {clean_input}. (The creator is Naba-Tsubute, a rock-human hybrid creature with thick arms and human face)"
                    
                    response = client_gemini.models.generate_image(
                        model="gemini-3-pro-image-preview",
                        prompt=gen_prompt,
                        config=types.GenerateImageConfig(number_of_images=1)
                    )
                    
                    image_bytes = response.generated_images[0].image_bytes
                    with io.BytesIO(image_bytes) as image_binary:
                        await message.reply(
                            content="俺様の芸術的センスを食らえ、ファック！！最高にクールだろ、ソイ！？",
                            file=discord.File(fp=image_binary, filename="naba_art.png")
                        )
                    return

                # --- 対話・解析 (Flashモデル用) ---
                if user_id not in user_chat_histories:
                    user_chat_histories[user_id] = []

                current_parts = []
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            image_bytes = await attachment.read()
                            current_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=attachment.content_type))
                
                user_input_with_name = f"送信者:{message.author.display_name}\n内容:{clean_input}"
                current_parts.append(types.Part.from_text(text=user_input_with_name))

                user_content = types.Content(role="user", parts=current_parts)
                full_contents = user_chat_histories[user_id] + [user_content]

                response = client_gemini.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=full_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )

                answer_text = response.text
                user_chat_histories[user_id].append(user_content)
                user_chat_histories[user_id].append(
                    types.Content(role="model", parts=[types.Part.from_text(text=answer_text)])
                )

                if len(user_chat_histories[user_id]) > MAX_HISTORY * 2:
                    user_chat_histories[user_id] = user_chat_histories[user_id][-MAX_HISTORY * 2:]

                await message.reply(answer_text[:1900])

            except Exception as e:
                print(f"Error detail: {e}")
                await message.reply(f"エラーだ、ファック！！岩の脳みそがショートしたぜ！\n`{str(e)[:150]}`")

# --- 実行ブロック ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("トークンがねえぞ、ソイ！！")
    else:
        def start_bot():
            while True:
                try:
                    bot.run(DISCORD_TOKEN)
                except Exception as e:
                    print(f"再起動中...: {e}")
                    time.sleep(10)

        bot_thread = threading.Thread(target=start_bot, daemon=True)
        bot_thread.start()

        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

