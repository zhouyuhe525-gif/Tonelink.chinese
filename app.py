import streamlit as st
import streamlit.components.v1 as components
from pypinyin import pinyin, Style, lazy_pinyin
import azure.cognitiveservices.speech as speechsdk
import librosa
import soundfile as sf
from audio_recorder_streamlit import audio_recorder
import os
import pandas as pd
from datetime import datetime
from openai import OpenAI
from gtts import gTTS
import random
import shutil
import base64
import glob
import calendar
import json
import hashlib
import PyPDF2
import re  # <--- 新增这一行

# --- 页面配置 ---
st.set_page_config(page_title="ToneLink V45", page_icon="🎨", layout="wide")

# ==========================================
# 🎨 1. 找回 CSS 美化 (色块样式)
# ==========================================
st.markdown("""
<style>
    /* 朗读板块 - 蓝色 */
    .read-box { border-left: 5px solid #2196F3; background-color: #E3F2FD; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    /* 口语板块 - 橙色 */
    .speak-box { border-left: 5px solid #FF9800; background-color: #FFF3E0; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    /* 听力板块 - 紫色 */
    .listen-box { border-left: 5px solid #9C27B0; background-color: #F3E5F5; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    /* 写作板块 - 绿色 */
    .write-box { border-left: 5px solid #4CAF50; background-color: #E8F5E9; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    
    /* 题型分类标题 */
    .section-title { font-size: 22px; font-weight: bold; margin-bottom: 15px; display: block; color: #333; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔑 用户配置区 (自动适配本地和云端)
# ==========================================
import os

# 尝试从 Streamlit Secrets 读取
try:
    MY_AZURE_KEY = st.secrets["AZURE_SPEECH_KEY"]
    MY_AZURE_REGION = st.secrets["AZURE_SPEECH_REGION"]
    MY_DEEPSEEK_KEY = st.secrets["DEEPSEEK_API_KEY"]
    MY_QWEN_KEY = st.secrets["QWEN_API_KEY"]
except:
    # 如果读取失败（比如在本地没配置），就留空，等待用户手动填
    MY_AZURE_KEY = "" 
    MY_AZURE_REGION = "eastasia"
    MY_DEEPSEEK_KEY = "" 
    MY_QWEN_KEY = ""
# ==========================================

# --- 🌍 国际化字典 ---
TRANS = {
    "中文": {
        "nav_home": "🏠 任务大厅", "nav_lib": "🗂️ 已创建任务", "nav_create": "➕ 创建新任务", "nav_review": "📝 批改作业",
        "clear_data": "🗑️ 清空所有数据", "confirm_clear": "确认清空", "cleared": "已重置",
        "student_login": "👋 学生登录", "name_placeholder": "请输入姓名", "start_btn": "开始做题",
        "submit_btn": "📤 提交作业", "submit_success": "提交成功！", "download_report": "📥 下载成绩单",
        "read_section": "🗣️ 朗读", "speak_section": "💬 口语", "listen_section": "👂 听力", "write_section": "✍️ 汉字",
        "expand_pinyin": "点击查看拼音", "microscope": "🧬 显微镜诊断",
        "play_audio": "点击播放", "download_workbook": "📥 下载田字格字帖", "upload_photo": "📤 上传作业照片",
        "score": "得分", "comment": "评语", "ai_analyzing": "AI 分析中...",
        "btn_back": "⬅️ 上一步", "btn_add": "➕ 添加", "btn_save_lib": "💾 保存到任务库", 
        "btn_delete": "🗑️ 删除", "btn_modify": "✏️ 修改", "btn_link": "🔗 生成链接", "btn_sim": "🚀 模拟打开",
        "btn_ai_parse": "🤖 智能解析", "btn_save_grading": "💾 保存批改", "btn_final_report": "📥 下载最终成绩单",
        "pl_read": "请输入要朗读的汉字或句子", "pl_ref": "参考答案/提示 (选填)", "pl_content": "在此输入题目内容...",
        "pl_words": "输入词表 (逗号隔开)", "pl_img": "上传图片", "preview": "预览",
        "qt_trans": "翻译题", "qt_qa": "问答题", "qt_img": "看图题", "qt_essay": "作文题",
        "lt_rep": "复述", "lt_qa": "问答", "lt_cloze": "填空", "lt_tone": "辨调",
        "inst_trans": "请把句子翻译成中文 / Переведите предложение на китайский",
        "inst_qa": "请回答问题 / Ответьте на вопрос",
        "inst_img": "请描述图片 / Опишите картинку",
        "inst_essay": "请根据话题进行口语作文 / Устное сочинение на тему",
        "inst_rep": "听录音并复述 / Прослушайте и повторите",
        "inst_lqa": "听录音回答问题 / Прослушайте и ответьте",
        "inst_cloze": "听录音，选词填空 / Заполните пропуски",
        "inst_tone": "听录音，选择声调 / Выберите правильный тон",
        "ai_import_title": "🤖 AI 智能导入 (PDF)",
        "ai_import_help": "上传作业 PDF，AI 将自动识别题型并填充到下方。",
        "btn_start_import": "🚀 开始智能识别",
        
        # === 🟢 新增：创建作业页面专用词条 ===
        "cp_title": "创建作业",
        "cp_input_label": "请输入作业标题：",
        "cp_expander_title": "🚀 完成设置",
        "cp_selected": "已选模块：",
        "cp_hint": "请点击上方卡片选择至少一个模块",
        "edit_page_title": "编辑",
        
        
    },
    "Русский": {
        "nav_home": "🏠 Главная", "nav_lib": "🗂️ Библиотека", "nav_create": "➕ Создать", "nav_review": "📝 Проверка",
        "clear_data": "🗑️ Удалить все данные", "confirm_clear": "Подтвердить", "cleared": "Сброшено",
        "student_login": "👋 Вход для ученика", "name_placeholder": "Введите имя", "start_btn": "Начать",
        "submit_btn": "📤 Отправить", "submit_success": "Успешно!", "download_report": "📥 Скачать отчет",
        "read_section": "🗣️ произношение", "speak_section": "💬 Говорение", "listen_section": "👂 Аудирование", "write_section": "✍️ Письмо",
        "expand_pinyin": "Показать пиньинь", "microscope": "🧬 Диагностика",
        "play_audio": "Слушать", "download_workbook": "📥 Скачать прописи", "upload_photo": "📤 Загрузить фото",
        "score": "Балл", "comment": "Комментарий", "ai_analyzing": "ИИ анализирует...",
        "btn_back": "⬅️ Назад", "btn_add": "➕ Добавить", "btn_save_lib": "💾 Сохранить", 
        "btn_delete": "🗑️ Удалить", "btn_modify": "✏️ Изменить", "btn_link": "🔗 Ссылка", "btn_sim": "🚀 Открыть",
        "btn_ai_parse": "🤖 Анализ ИИ", "btn_save_grading": "💾 Сохранить", "btn_final_report": "📥 Итоговый отчет",
        "pl_read": "Введите текст", "pl_ref": "Подсказка", "pl_content": "Содержание",
        "pl_words": "Список слов", "pl_img": "Загрузить фото", "preview": "Предпросмотр",
        "qt_trans": "Перевод", "qt_qa": "Вопрос-ответ", "qt_img": "Картинка", "qt_essay": "Сочинение",
        "lt_rep": "Повторение", "lt_qa": "Вопрос", "lt_cloze": "Пропуски", "lt_tone": "Тоны",
        "inst_trans": "Переведите предложение на китайский",
        "inst_qa": "Ответьте на вопрос",
        "inst_img": "Опишите картинку",
        "inst_essay": "Устное сочинение на тему",
        "inst_rep": "Прослушайте и повторите",
        "inst_lqa": "Прослушайте и ответьте",
        "inst_cloze": "Заполните пропуски",
        "inst_tone": "Выберите правильный тон",
        "ai_import_title": "🤖 Импорт из PDF",
        "ai_import_help": "Загрузите PDF, ИИ автоматически создаст задания.",
        "btn_start_import": "🚀 Начать импорт",

        # === 🟢 新增：创建作业页面专用词条 (俄语) ===
        "cp_title": "Создание задания",
        "cp_input_label": "Введите название задания:",
        "cp_expander_title": "🚀 Завершение",
        "cp_selected": "Выбрано: ",
        "cp_hint": "Выберите хотя бы один модуль выше",
        "edit_page_title": "Редактирование",
    }
}

# --- 全局状态 ---
if 'page' not in st.session_state: st.session_state.page = 'create'
if 'current_task' not in st.session_state: st.session_state.current_task = {} 
if 'edit_data' not in st.session_state: 
    st.session_state.edit_data = {'title': '', 'modules': [], 'read': [], 'speak': [], 'listen': [], 'write': []}
if 'active_task_data' not in st.session_state: st.session_state.active_task_data = {}
if 'student_answers' not in st.session_state: st.session_state.student_answers = {}
if 'filter_date' not in st.session_state: st.session_state.filter_date = None
if 'lang' not in st.session_state: st.session_state.lang = '中文'
if 'confirm_submit' not in st.session_state: st.session_state.confirm_submit = False

def T(key):
    return TRANS[st.session_state.lang].get(key, key)

def get_unread_count():
    count = 0
    if os.path.exists("submissions"):
        for task in os.listdir("submissions"):
            task_path = os.path.join("submissions", task)
            if not os.path.isdir(task_path) or task.startswith('.'): continue
            for stu in os.listdir(task_path):
                stu_path = os.path.join(task_path, stu)
                if not os.path.isdir(stu_path) or stu.startswith('.'): continue
                csv_path = os.path.join(stu_path, "report.csv")
                if os.path.exists(csv_path):
                    try:
                        df = pd.read_csv(csv_path)
                        if '状态' not in df.columns or '已批改' not in df['状态'].values: count += 1
                    except: pass
    return count

unread = get_unread_count()
review_label = f"{T('nav_review')} ({unread} 🔴)" if unread > 0 else T('nav_review')

# --- 侧边栏 (修复通义千问输入框) ---
with st.sidebar:
    # 1. 注入侧边栏专属 CSS (美化保持不变)
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] { background-color: #F7F3F3; }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] p {
            color: #5D4037 !important; font-family: "Kaiti SC", "KaiTi", serif;
        }
        section[data-testid="stSidebar"] .stButton > button {
            width: 100%; border-radius: 12px !important; border: 1px solid #D7CCC8 !important;
            background-color: #FFFFFF !important; color: #5D4037 !important; font-weight: bold;
            font-family: "Kaiti SC", "KaiTi", serif !important; transition: all 0.3s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #EBCbcB !important; color: white !important;
            border-color: #EBCbcB !important; padding-left: 20px !important; 
        }
        section[data-testid="stSidebar"] .streamlit-expanderHeader {
            background-color: #FFFFFF !important; border-radius: 8px; color: #5D4037 !important; border: 1px solid #EFEBE9 !important;
        }
        section[data-testid="stSidebar"] .streamlit-expanderHeader svg, section[data-testid="stSidebar"] span[data-testid="stExpanderIcon"] { font-family: sans-serif !important; }
    </style>
    """, unsafe_allow_html=True)

    # 2. 侧边栏内容
    st.header("🌐 Language / Язык")
    st.session_state.lang = st.radio("Select Language", ["中文", "Русский"], label_visibility="collapsed")
    
    st.divider()
    
    st.header("🧠 AI 配置")
    with st.expander("🔑 密钥设置", expanded=False):
        AZURE_SPEECH_KEY = st.text_input("Azure Key", value=MY_AZURE_KEY, type="password") 
        AZURE_SPEECH_REGION = st.text_input("Region", value=MY_AZURE_REGION)
        st.markdown("---")
        DEEPSEEK_API_KEY = st.text_input("DeepSeek Key (主)", value=MY_DEEPSEEK_KEY, type="password")
        # ✅ 修复：补回通义千问输入框
        QWEN_API_KEY = st.text_input("通义千问 Key (备)", value=MY_QWEN_KEY, type="password")
        # 顺便把 Qwen Key 存入 Session，供全局调用
        st.session_state.qwen_key_input = QWEN_API_KEY
    
    st.divider()
    
    st.subheader("📍 导航菜单")
    # === 修改开始：加一个带边框的容器 ===
    with st.container(border=True):
        if st.button(f" {T('nav_create')}"): 
            st.session_state.edit_data = {'title': '', 'modules': [], 'read': [], 'speak': [], 'listen': [], 'write': []}
            st.session_state.page = 'create'; st.rerun()
        if st.button(f" {T('nav_lib')}"): st.session_state.page = 'task_library'; st.rerun()
        if st.button(review_label): st.session_state.page = 'review_dashboard'; st.rerun()
    # === 修改结束 ===
    
    st.divider()
    
    with st.expander("⚠️ 危险区域"):
        if st.checkbox(T("confirm_clear")):
            if st.button(T("clear_data"), type="primary"): 
                if os.path.exists("submissions"): shutil.rmtree("submissions")
                if os.path.exists("tasks"): shutil.rmtree("tasks")
                st.toast(T("cleared")); st.session_state.page = 'home'; st.rerun()

# ==========================================
# 核心函数库
# ==========================================

def get_tts_audio(text):
    if not text: return None
    file_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    filename = f"tts_{file_hash}.mp3"
    if not os.path.exists(filename):
        try: gTTS(text=text, lang='zh-cn').save(filename)
        except: return None
    return filename

def get_pinyin(text):
    py_list = pinyin(text, style=Style.TONE)
    return " ".join([x[0] for x in py_list])

def render_hanzi_writer(character, div_id):
    return f"""<div id="{div_id}" style="display:flex;justify-content:center;"></div>
    <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
    <script>HanziWriter.create('{div_id}','{character}',{{width:70,height:70,padding:2,showOutline:true,strokeAnimationSpeed:1,delayBetweenStrokes:200,radicalColor:'#337ab7'}}).loopCharacterAnimation();</script>"""

# --- 智能双引擎调用 ---
def call_ai_dual_engine(messages, ds_key, qwen_key, timeout_sec=15):
    # 1. 尝试 DeepSeek
    if ds_key:
        try:
            # 必须确保这里用的是传入的 timeout_sec，而不是写死的数字
            client = OpenAI(api_key=ds_key, base_url="https://api.deepseek.com", timeout=timeout_sec)
            response = client.chat.completions.create(model="deepseek-chat", messages=messages, stream=False)
            return response.choices[0].message.content, "DeepSeek"
        except Exception as e:
            pass # 失败静默切换到下一步
            
    # 2. 尝试 Qwen
    if qwen_key:
        try:
            # Qwen 可以给多一点时间 (比如 30s)，因为它已经是最后的希望了
            client = OpenAI(api_key=qwen_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", timeout=30)
            response = client.chat.completions.create(model="qwen-plus", messages=messages, stream=False)
            return response.choices[0].message.content, "Qwen"
        except Exception as e:
            return None, f"All AI Failed: {e}"
            
    return None, "No API Keys"

# PDF 解析
# PDF 解析函数 (增强版)
def deepseek_parse_pdf_content(text_content, ds_key):
    qwen_key = st.session_state.get('qwen_key_input', MY_QWEN_KEY)
    
    # 增强 Prompt：专门处理双栏排版和中文题型
    prompt = f"""
    Role: Data Extraction Expert for Chinese Homework PDFs.
    
    Task: Extract questions from the scrambled text (the PDF might be dual-column, causing mixed lines) into valid JSON.
    
    Raw Text: 
    \"\"\"{text_content[:6000]}\"\"\"
    
    Target JSON Structure:
    {{
      "read": ["sentence 1", "sentence 2"],
      "speak": [
         {{"type": "翻译题", "content": "Russian text to translate"}},
         {{"type": "问答题", "content": "Chinese Question?"}},
         {{"type": "看图题", "content": "Description"}},
         {{"type": "作文题", "content": "Topic"}}
      ],
      "listen": [
         {{"type": "复述", "content": "Sentence to repeat"}},
         {{"type": "问答", "content": "Question"}},
         {{"type": "填空", "content": "Sentence with missing word", "correct": "The missing word"}},
         {{"type": "辨调", "content": "Word"}}
      ],
      "write": [{{"hanzi": "字"}}]
    }}
    
    Critical Rules:
    1. Identify sections by keywords like "朗读作业", "口语作业", "听力作业", "翻译", "问答", "填空".
    2. Use heuristic to separate mixed columns if necessary.
    3. Return JSON ONLY. Do not use markdown blocks like ```json.
    """
    
    msg = [{"role": "user", "content": prompt}]
    
    # 增加超时时间到 60秒，防止 AI 思考过久
    content, src = call_ai_dual_engine(msg, ds_key, qwen_key, timeout_sec=60)
    
    if content:
        # 调试：在控制台打印原始返回（可选）
        print(f"AI Source: {src}") 
        
        # 使用正则表达式寻找 JSON 对象，比 replace 更稳健
        try:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                json_str = match.group()
                return json.loads(json_str), src # 返回数据和源头
            else:
                st.error("AI 返回了内容，但找不到 JSON 格式。")
                return None, src
        except json.JSONDecodeError:
            st.error("JSON 解析失败，AI 返回格式可能有误。")
            return None, src
    else:
        st.error("AI 未返回任何内容 (可能是 Key 无效或超时)")
        return None, "Fail"

# 单词解析
# 单词解析函数
def deepseek_parse_words(text_input, ds_key):
    qwen_key = st.session_state.get('qwen_key_input', MY_QWEN_KEY)
    prompt = f"""Analyze: "{text_input}". Return JSON array ONLY: [{{"hanzi": "word", "pinyin": "pinyin", "russian": "Meaning"}}]"""
    msg = [{"role": "user", "content": prompt}]
    
    # 调用 AI
    content, src = call_ai_dual_engine(msg, ds_key, qwen_key, 15)
    
    if content:
        try: 
            return json.loads(content.replace("```json", "").replace("```", "").strip())
        except: 
            pass
    
    # 兜底逻辑：如果 AI 失败，手动分割
    fb = []
    for w in text_input.replace("，", ",").split(","):
        w = w.strip()
        if w: 
            fb.append({"hanzi": w, "pinyin": get_pinyin(w), "russian": ""})
    return fb

# --- 新增：AI 生成填空干扰项 (注意：这个 def 必须要在最左边，不能有缩进) ---
def generate_distractors_via_ai(sentence, target_word, ds_key):
    """
    根据句子和目标词，生成3个干扰项
    """
    qwen_key = st.session_state.get('qwen_key_input', MY_QWEN_KEY)
    
    prompt = f"""
    Context: Teaching Chinese to Russian speakers.
    Sentence: "{sentence}"
    Target word (cloze): "{target_word}"
    
    Task: Generate 3 plausible but INCORRECT distractor words/characters for the target word. 
    Criteria:
    1. Must be the same length as the target word.
    2. Should be confusing (similar pinyin, similar character shape, or grammatically plausible but wrong).
    3. Return ONLY a JSON array of strings. Example: ["错误1", "错误2", "错误3"]
    """
    
    msg = [{"role": "user", "content": prompt}]
    
    content, src = call_ai_dual_engine(msg, ds_key, qwen_key, timeout_sec=10)
    
    if content:
        try:
            # 清理 markdown 标记
            json_str = content.replace("```json", "").replace("```", "").strip()
            distractors = json.loads(json_str)
            if isinstance(distractors, list):
                return distractors[:3] # 确保只取前3个
        except:
            pass
            
    # 如果AI失败，返回简单的默认干扰项，避免报错
    return ["干扰项A", "干扰项B", "干扰项C"]

# 口语评分函数 (极速版)
def deepseek_evaluate(question_type, question_content, student_text, ds_key):
    qwen_key = st.session_state.get('qwen_key_input', MY_QWEN_KEY)
    sys_p = "You are a professional Chinese teacher for Russian students. Provide feedback in Russian. Score 0-100."
    user_p = f"Task: {question_type}\nTopic: {question_content}\nAnswer: {student_text}\n\nFormat:\nScore: (number)\nComment: (Russian)"
    msg = [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]
    
    # 🔥 核心修改：强制设为 8 秒！
    # 如果 DeepSeek 8秒内不回话，立马切换 Qwen，不再傻等。
    content, src = call_ai_dual_engine(msg, ds_key, qwen_key, 8)
    
    if content:
        score = 0
        import re
        try: score = int(re.search(r'Score:\s*(\d+)', content, re.IGNORECASE).group(1))
        except: pass
        return content, score
    return "AI Busy (Timeout)", 0

def speech_to_text(audio_data, key, region):
    if not key or not region: return None
    try:
        with open("temp_stt.wav", "wb") as f: f.write(audio_data)
        y, sr = librosa.load("temp_stt.wav", sr=16000)
        sf.write("student_16k.wav", y, 16000, subtype='PCM_16')
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language="zh-CN"
        audio_config = speechsdk.audio.AudioConfig(filename="student_16k.wav")
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = recognizer.recognize_once()
        return result.text if result.reason == speechsdk.ResultReason.RecognizedSpeech else None
    except: return None

def assess_pronunciation(reference_text, audio_data, key, region):
    if not key or not region: return None, "缺Key"
    try:
        with open("temp.wav", "wb") as f: f.write(audio_data)
        y, sr = librosa.load("temp.wav", sr=16000)
        sf.write("student_16k.wav", y, 16000, subtype='PCM_16')
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        audio_config = speechsdk.audio.AudioConfig(filename="student_16k.wav")
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text, grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme, enable_miscue=True
        )
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language="zh-CN", audio_config=audio_config)
        pronunciation_config.apply_to(recognizer)
        result = recognizer.recognize_once()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech: return speechsdk.PronunciationAssessmentResult(result), result
        return None, "未检测到语音"
    except Exception as e: return None, str(e)

def generate_report_html(student_name, task_title, data_source):
    html = f"""<html><head><meta charset='utf-8'><style>
    body{{font-family:sans-serif;padding:20px}} table{{width:100%;border-collapse:collapse;margin-top:20px}}
    th,td{{border:1px solid #ddd;padding:8px;text-align:left}} th{{background-color:#f2f2f2}}
    .score{{font-weight:bold;color:#2980b9}}
    </style></head><body><h1>成绩单 / Отчет</h1><p>姓名: {student_name} | 任务: {task_title}</p>
    <table><tr><th>题型</th><th>题目</th><th>得分</th><th>评语</th></tr>"""
    rows = []
    if isinstance(data_source, pd.DataFrame):
        for _, row in data_source.iterrows(): rows.append(row.to_dict())
    elif isinstance(data_source, dict):
        for k, v in data_source.items():
            rows.append({'类型': v.get('type','未知'), '题目': v.get('question_preview',''), '得分': v.get('score',0), 'AI评语': v.get('ai_comment','') or v.get('transcribed_text','') or v.get('student_text_input',''), '教师评语': ''})
    for r in rows:
        cmt = r.get('教师评语') or r.get('AI评语') or ''
        if r.get('类型') and '书写' in r['类型']: cmt += " [图片已提交]"
        html += f"<tr><td>{r.get('类型')}</td><td>{r.get('题目')}</td><td class='score'>{r.get('得分')}</td><td>{cmt}</td></tr>"
    return html + "</table></body></html>"

def save_submission(student_name, task_title):
    base_dir = "submissions"; task_dir = os.path.join(base_dir, task_title); student_dir = os.path.join(task_dir, student_name)
    if not os.path.exists(student_dir): os.makedirs(student_dir)
    summary_data = []
    for key_id, data in st.session_state.student_answers.items():
        audio_file = ""; img_file = ""
        if data.get('audio') and len(data['audio']) > 0:
            audio_file = f"{key_id}.wav"
            try:
                with open(os.path.join(student_dir, audio_file), "wb") as f: f.write(data['audio'])
            except: pass
        if data.get('image_upload'):
            img_file = f"{key_id}.jpg"
            try:
                with open(os.path.join(student_dir, img_file), "wb") as f: f.write(data['image_upload'].getbuffer())
            except: pass
        summary_data.append({
            "ID": key_id, "类型": data.get('type', '未知'), "题目": data.get('question_preview', ''),
            "学生答案": data.get('student_text_input', ''), "识别文本": data.get('transcribed_text', ''),
            "AI评语": data.get('ai_comment', ''), "教师评语": "", "得分": data.get('score', 0), 
            "音频": audio_file, "图片": img_file, "状态": "未批改", "时间": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    pd.DataFrame(summary_data).to_csv(os.path.join(student_dir, "report.csv"), index=False)
    return True

def generate_workbook_html(task_title, word_list):
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    body{{font-family:"Kaiti SC","STKaiti","KaiTi","Arial";padding:40px}} h1{{text-align:center}}
    .word-row{{display:flex;align-items:center;margin-bottom:20px;border-bottom:1px dashed #ccc;padding-bottom:10px}}
    .info-box{{width:180px;text-align:center;margin-right:20px}} 
    .hanzi-big{{font-size:40px;font-weight:bold}} 
    .pinyin{{color:#555;font-weight:bold}} 
    .russian{{color:#666;font-style:italic;font-size:12px; line-height:1.2; margin-top:5px;}} 
    .tianzige{{width:60px;height:60px;border:2px solid #d9534f;margin-right:5px;position:relative;box-sizing:border-box}}
    .tianzige:before{{content:'';position:absolute;top:0;left:50%;height:100%;border-left:1px dashed #d9534f}}
    .tianzige:after{{content:'';position:absolute;top:50%;left:0;width:100%;border-top:1px dashed #d9534f}}
    .trace{{position:absolute;width:100%;height:100%;text-align:center;line-height:56px;font-size:40px;color:#eee;z-index:1;font-family:"Kaiti SC","KaiTi"}}
    @media print{{.no-print{{display:none}} body{{padding:0}}}}
    </style></head><body>
    <div class="no-print" style="text-align:center;background:#e8f5e9;padding:10px"><b>🖨️ {T('download_workbook')}</b></div>
    <h1>📝 {task_title}</h1>"""
    for item in word_list:
        hanzi = item['hanzi']; grids = ""
        for char in hanzi: grids += f'<div class="tianzige"><div class="trace">{char}</div></div>' + '<div class="tianzige"></div>'*7
        html += f'<div class="word-row"><div class="info-box"><div class="pinyin">{item["pinyin"]}</div><div class="hanzi-big">{hanzi}</div><div class="russian">{item.get("russian", "")}</div></div><div style="display:flex">{grids}</div></div>'
    return html + "</body></html>"

def save_task_to_file(task_data, filename=None):
    if not os.path.exists("tasks"): os.makedirs("tasks")
    if not filename:
        safe_title = "".join([c for c in task_data['title'] if c.isalnum() or c in (' ','-','_')]).strip() or "untitled"
        filename = f"{safe_title}.json"
    file_path = os.path.join("tasks", filename)
    import copy
    data_to_save = copy.deepcopy(task_data)
    for q in data_to_save.get('speak', []):
        if 'image_data' in q: del q['image_data']
    with open(file_path, "w", encoding='utf-8') as f: json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    return filename

def load_task_from_file(filename):
    # 这里的 filename 可能是 "test.json" 也可能是 "班级A/test.json"
    # 如果 filename 已经包含了 "tasks/" 前缀（某些逻辑可能会这样），我们要处理一下
    if filename.startswith("tasks/"):
        file_path = filename
    else:
        file_path = os.path.join("tasks", filename)
        
    if os.path.exists(file_path):
        with open(file_path, "r", encoding='utf-8') as f: 
            data = json.load(f)
            # 恢复图片数据
            for q in data.get('speak', []):
                if 'image_b64' in q:
                    try: q['image_data'] = base64.b64decode(q['image_b64'])
                    except: pass
            return data
    return None

def generate_tone_options_smart(text):
    correct_py = get_pinyin(text)
    options = {correct_py}
    attempts = 0
    while len(options) < 4 and attempts < 20:
        attempts += 1
        fake_py = []
        for char in text:
            base = lazy_pinyin(char)[0]
            vowel_map = {'a':['ā','á','ǎ','à'], 'e':['ē','é','ě','è'], 'i':['ī','í','ǐ','ì'], 'o':['ō','ó','ǒ','ò'], 'u':['ū','ú','ǔ','ù']}
            for v in ['a','e','i','o','u']:
                if v in base: base = base.replace(v, random.choice(vowel_map[v])); break
            fake_py.append(base)
        options.add(" ".join(fake_py))
    opt_list = list(options)
    while len(opt_list) < 4: opt_list.append(correct_py)
    if correct_py not in opt_list: opt_list[0] = correct_py
    random.shuffle(opt_list)
    return opt_list, correct_py

# ==========================================
# 页面逻辑
# ==========================================
def page_home():
    st.title(T("nav_home"))
    st.info("👈 Please select options from sidebar / Пожалуйста, выберите опции на боковой панели")

def page_task_library():
    # --- 1. 注入莫兰迪风格 CSS (专门针对任务库) ---
    st.markdown("""
    <style>
        /* 全局背景 */
        .stApp { background-color: #FAF9F6; }

        /* 标题：深棕色楷体 */
        h1, h2, h3 {
            color: #8D6E63 !important;
            font-family: "Kaiti SC", "KaiTi", serif;
        }
        
        /* 通用按钮样式 (次要操作) */
        div.stButton > button[kind="secondary"] {
            background-color: #F9EBEB !important; 
            border: 1px solid #D7CCC8 !important; 
            color: #5D4037 !important;            
            border-radius: 12px !important;       
            font-size: 15px !important;
            height: auto !important;
            padding: 8px 15px !important;
            transition: all 0.2s;
        }
        div.stButton > button[kind="secondary"]:hover {
            background-color: #EBCbcB !important;
            border-color: #8D6E63 !important;
            transform: translateY(-2px);
        }

        /* 核心按钮样式 (主要操作) */
        div.stButton > button[kind="primary"] {
            background-color: #8D6E63 !important; 
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: bold !important;
            box-shadow: 0 2px 5px rgba(141, 110, 99, 0.3);
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #6D4C41 !important;
        }

        /* 输入框美化 */
        div[data-testid="stTextInput"] input {
            background-color: #FFF !important;
            border: 1px solid #D7CCC8 !important;
            border-radius: 8px !important;
            color: #5D4037 !important;
        }
        
        /* Expander (折叠框) 样式 */
        .streamlit-expanderHeader {
            background-color: #FDF6F6 !important;
            border-radius: 8px !important;
            color: #5D4037 !important;
            border: 1px solid #EFEBE9 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title(T("nav_lib"))
    
    # 1. 状态管理：记录当前在哪个文件夹里
    if 'current_folder' not in st.session_state: st.session_state.current_folder = ""
    
    base_root = "tasks"
    current_path = os.path.join(base_root, st.session_state.current_folder)
    if not os.path.exists(current_path): os.makedirs(current_path)

    # --- 顶部工具栏 ---
    col_tools, col_nav = st.columns([1, 2])
    
    # 左边：新建文件夹
    with col_tools:
        with st.popover("➕📂 新建文件夹"):
            # 使用 Form 彻底隔离 Key 冲突，名字设为 create_folder_v_final_1
            with st.form("create_folder_v_final_1", clear_on_submit=True):
                new_folder = st.text_input("文件夹名称")
                submitted = st.form_submit_button("创建", type="primary")
                
                if submitted and new_folder:
                    target_path = os.path.join(current_path, new_folder)
                    if not os.path.exists(target_path):
                        os.makedirs(target_path, exist_ok=True)
                        st.success(f"已创建: {new_folder}")
                        st.rerun()
                    else:
                        st.warning("文件夹已存在")
    
    # 右边：导航路径
    with col_nav:
        if st.session_state.current_folder:
            if st.button("🔙 返回上一级", key="btn_back_folder"):
                parent = os.path.dirname(st.session_state.current_folder)
                st.session_state.current_folder = parent
                st.rerun()
            st.caption(f"当前路径: 📂 {st.session_state.current_folder}")
        else:
            st.caption("当前路径: 📂 根目录")

    st.divider()

    # --- 读取内容 ---
    try:
        items = os.listdir(current_path)
    except: items = []

    dirs = [d for d in items if os.path.isdir(os.path.join(current_path, d))]
    files = [f for f in items if f.endswith(".json")]

    # 2. 显示文件夹
    if dirs:
        st.subheader("📁 文件夹")
        cols = st.columns(4)
        for i, d in enumerate(dirs):
            with cols[i % 4]:
                if st.button(f"📂 {d}", key=f"dir_{d}", use_container_width=True):
                    if st.session_state.current_folder:
                        st.session_state.current_folder = os.path.join(st.session_state.current_folder, d)
                    else:
                        st.session_state.current_folder = d
                    st.rerun()

    # 3. 显示任务文件
    if files:
        st.subheader("📄 任务列表")
        for filename in files:
            rel_path = os.path.join(st.session_state.current_folder, filename)
            
            with st.expander(f"📄 {filename.replace('.json', '')}", expanded=False):
                
                # --- 第一行：重命名 ---
                c_name, c_save = st.columns([3, 1])
                with c_name:
                    new_name = st.text_input("重命名", value=filename.replace(".json",""), key=f"rn_{filename}", label_visibility="collapsed")
                with c_save:
                    if st.button("保存名", key=f"sn_{filename}"):
                        src = os.path.join(current_path, filename)
                        dst = os.path.join(current_path, f"{new_name}.json")
                        os.rename(src, dst)
                        st.success("已更新"); st.rerun()
                
                st.write("") 

                # --- 第二行：功能按钮矩阵 ---
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1.2, 0.8])
                
                with c1:
                    if st.button("✏️ 编辑", key=f"ed_{filename}"):
                        st.session_state.edit_data = load_task_from_file(rel_path)
                        st.session_state.edit_filename = rel_path
                        st.session_state.page = 'edit'; st.rerun()

                with c2:
                    if st.button("📋 复制", key=f"cp_{filename}"):
                        data = load_task_from_file(rel_path)
                        new_title = f"{data['title']}_copy"
                        data['title'] = new_title
                        save_path = os.path.join(st.session_state.current_folder, f"{new_title}.json")
                        save_task_to_file(data, save_path)
                        st.success(f"已复制"); st.rerun()

                with c3:
                    if st.button(T("btn_link"), key=f"lnk_{filename}"):
                        safe_name = filename  
                        path_id = base64.b64encode(safe_name.encode()).decode()
                        # ⚠️ 这里填的是你刚才截图里的真实网址
                        real_url = "https://github.com/zhouyuhe525-gif/Tonelink.chinese/edit/main/app" 
                        link = f"{real_url}?task_id={path_id}"
                        st.code(link, language="text")
                        st.caption("复制上面的链接发给学生")

                with c4:
                    if st.button("🚀 模拟打开", key=f"go_{filename}", type="primary"):
                        st.session_state.active_task_data = load_task_from_file(rel_path)
                        st.session_state.student_answers = {}
                        st.session_state.page = 'student_login'; st.rerun()

                with c5:
                    if st.button("🗑️", key=f"del_{filename}"):
                        os.remove(os.path.join(current_path, filename)); st.rerun()
                
                # --- 第三行：移动功能 ---
                st.markdown("---")
                all_folders = ["(根目录)"] + [d for d in os.listdir(base_root) if os.path.isdir(os.path.join(base_root, d))]
                current_dir_name = os.path.basename(st.session_state.current_folder) if st.session_state.current_folder else "(根目录)"
                move_options = [f for f in all_folders if f != current_dir_name]
                
                if move_options:
                    c_move_1, c_move_2 = st.columns([3, 1])
                    with c_move_1:
                        target_folder = st.selectbox("移动到...", move_options, key=f"mv_sel_{filename}", label_visibility="collapsed")
                    with c_move_2:
                        if st.button("确认移动", key=f"mv_btn_{filename}"):
                            src_path = os.path.join(current_path, filename)
                            if target_folder == "(根目录)": dst_path = os.path.join(base_root, filename)
                            else: dst_path = os.path.join(base_root, target_folder, filename)
                            shutil.move(src_path, dst_path)
                            st.toast(f"已移动"); st.rerun()
    
    if not dirs and not files:
        st.info("此文件夹为空")

def page_create():
    # --- 1. 莫兰迪藕粉色系 CSS (权重增强修复版) ---
    st.markdown("""
    <style>
        /* 全局背景 */
        .stApp { background-color: #FAF9F6; }

        /* 标题样式 */
        h1 {
            color: #8D6E63 !important;
            text-align: center;
            font-size: 50px !important;
            font-weight: 900 !important;
            font-family: "KaiTi", serif;
            margin-bottom: 30px;
        }

        /* 输入框美化 */
        div[data-testid="stTextInput"] input {
            background-color: #FDF6F6 !important;
            border: 2px solid #D7CCC8 !important;
            border-radius: 10px !important;
            color: #5D4037 !important;
            padding: 15px !important;
            font-size: 18px !important;
        }
        div[data-testid="stTextInput"] label {
            font-size: 20px !important;
            color: #8D6E63 !important;
            font-weight: bold !important;
        }

        /* ============================================================ */
        /*  区域 A：上方四个大按钮 (Big Cards)                          */
        /*  规则：主区域内的默认按钮样式                                  */
        /* ============================================================ */
        
        section[data-testid="stMain"] .stButton > button {
            height: 120px !important;
            width: 100% !important;
            font-size: 24px !important;
            border-radius: 20px !important;
            transition: transform 0.1s;
            border: 3px solid #8D6E63 !important;
            margin-bottom: 10px !important;
        }

        /* 选中状态 */
        section[data-testid="stMain"] .stButton > button[kind="primary"] {
            background-color: #DFA6A6 !important;
            color: white !important;
            box-shadow: 0 4px 0px #8D6E63 !important;
        }

        /* 未选中状态 */
        section[data-testid="stMain"] .stButton > button[kind="secondary"] {
            background-color: #F9EBEB !important;
            border: 2px dashed #D7CCC8 !important;
            color: #8D6E63 !important;
        }

        /* ============================================================ */
        /*  区域 B：底部 Expander 里的按钮 (Small Button)                */
        /*  策略：加长选择器，增加权重，打败上面的规则！                   */
        /* ============================================================ */

        /* 美化 Expander 本身 */
        div[data-testid="stExpander"] {
            background-color: #F7F3F3 !important; 
            border: 1px solid #D7CCC8 !important;
            border-radius: 12px !important;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        }

        /* 【核心修复】权重核武器！ */
        /* 我们加上了 section[data-testid="stMain"] 前缀，确保它和上面的规则平起平坐 */
        /* 然后又指定了 div[data-testid="stExpander"]，这让它比上面的规则更具体，所以它必赢 */
        
        section[data-testid="stMain"] div[data-testid="stExpander"] .stButton > button {
            /* 1. 强行把高度压回去 */
            height: auto !important;            
            min-height: 45px !important;
            width: 100% !important;             
            
            /* 2. 字体改小 */
            font-size: 16px !important;
            border-radius: 10px !important;
            margin-top: 0px !important;
            
            /* 3. 颜色改回深棕色实心 */
            background-color: #8D6E63 !important;
            color: white !important;
            border: 1px solid #6D4C41 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }

        /* 悬停效果 */
        section[data-testid="stMain"] div[data-testid="stExpander"] .stButton > button:hover {
            background-color: #6D4C41 !important;
            transform: scale(1.02);
            border-color: #5D4037 !important;
        }
        
        /* 点击效果 */
        section[data-testid="stMain"] div[data-testid="stExpander"] .stButton > button:active {
            background-color: #5D4037 !important;
            color: white !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
        }

        /* 底部小方框微调 */
        div[data-testid="stExpander"] div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 15px !important;
            background-color: white !important;
            border-color: #D7CCC8 !important;
        }

    </style>
    """, unsafe_allow_html=True)

    # --- 2. 页面内容 (已全部替换为 T 翻译函数) ---
    st.title(T("cp_title")) # 创建作业 / Создание задания
    
    # 输入框
    title = st.text_input(T("cp_input_label"), value=st.session_state.edit_data.get('title', ''))
    
    st.write("") 
    st.write("") 

    # --- 3. 2x2 卡片矩阵 ---
    current_mods = st.session_state.edit_data.get('modules', [])
    
    def toggle(mod_key):
        if mod_key in current_mods: current_mods.remove(mod_key)
        else: current_mods.append(mod_key)
        st.session_state.edit_data['modules'] = current_mods

    # 辅助函数：给大卡片文字加换行，让排版更好看
    def fmt(key):
        return T(key).replace(" ", "\n\n")

    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        # 朗读
        is_sel = 'read' in current_mods
        if st.button(fmt("read_section"), key="btn_read", type="primary" if is_sel else "secondary", use_container_width=True):
            toggle('read'); st.rerun()
        st.write("")
        # 听力
        is_sel = 'listen' in current_mods
        if st.button(fmt("listen_section"), key="btn_listen", type="primary" if is_sel else "secondary", use_container_width=True):
            toggle('listen'); st.rerun()

    with col2:
        # 口语
        is_sel = 'speak' in current_mods
        if st.button(fmt("speak_section"), key="btn_speak", type="primary" if is_sel else "secondary", use_container_width=True):
            toggle('speak'); st.rerun()
        st.write("")
        # 汉字
        is_sel = 'write' in current_mods
        if st.button(fmt("write_section"), key="btn_write", type="primary" if is_sel else "secondary", use_container_width=True):
            toggle('write'); st.rerun()

    st.write("")
    st.write("")
    
    # --- 4. 底部可折叠栏 (已翻译) ---
    with st.expander(T("cp_expander_title"), expanded=True):
        c_info, c_btn = st.columns([2, 1])
        
        with c_info:
            if current_mods:
                # 提取模块名称 (去掉前面的 emoji)
                mod_names = [T(f"{m}_section").split(' ')[-1] for m in current_mods]
                st.success(f"{T('cp_selected')} {', '.join(mod_names)}")
            else:
                st.info(T("cp_hint"))
            
        with c_btn:
            # 按钮放在带边框的容器里
            with st.container(border=True):
                if st.button(T("下一步"), key="btn_next_step", type="primary", use_container_width=True):
                    st.session_state.edit_data['title'] = title
                    # 初始化未选模块
                    for m in ['read','speak','listen','write']:
                        if m not in st.session_state.edit_data: st.session_state.edit_data[m] = []
                    
                    st.session_state.page = 'edit'
                    st.rerun()

def page_edit():
    # --- 1. 注入莫兰迪风格 CSS (美化本页) ---
    st.markdown("""
    <style>
        /* 全局背景 */
        .stApp { background-color: #FAF9F6; }

        /* 标题文字：深棕色 + 楷体 */
        h1, h2, h3, h4 {
            color: #8D6E63 !important;
            font-family: "Kaiti SC", "KaiTi", serif;
            font-weight: 800 !important;
        }

        /* 输入框美化：浅粉底 + 棕色边框 + 圆角 */
        div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
            background-color: #FDF6F6 !important;
            border: 2px solid #D7CCC8 !important; /* 浅棕边框 */
            border-radius: 12px !important;
            color: #5D4037 !important; /* 深棕文字 */
            font-size: 16px;
        }
        
        /* 下拉菜单和文件上传器美化 */
        div[data-baseweb="select"] > div, div[data-testid="stFileUploader"] {
            background-color: #FDF6F6 !important;
            border: 2px solid #D7CCC8 !important;
            border-radius: 12px !important;
        }

        /* === 按钮美化 === */
        
        /* 普通按钮 (添加、删除等)：浅藕粉色药丸 */
        div.stButton > button {
            background-color: #EBCbcB !important; 
            color: #5D4037 !important;
            border: 1px solid #D7CCC8 !important;
            border-radius: 20px !important;
            font-weight: bold !important;
            transition: all 0.2s;
        }
        div.stButton > button:hover {
            background-color: #DFA6A6 !important; /* 悬停变深 */
            transform: scale(1.02);
            border-color: #8D6E63 !important;
        }

        /* 主要按钮 (保存、智能解析)：深棕色实心 */
        div.stButton > button[kind="primary"] {
            background-color: #8D6E63 !important; 
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 8px rgba(141, 110, 99, 0.3) !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #6D4C41 !important;
        }
        
        /* 预览卡片 (Expander) */
        div[data-testid="stExpander"] {
            background-color: white !important;
            border-radius: 10px !important;
            border: 1px solid #EFEBE9 !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        /* 标签页 Tab 样式微调 (Streamlit 很难改 Tab 颜色，但可以改文字) */
        button[data-baseweb="tab"] {
            font-weight: bold;
            color: #8D6E63;
        }
    </style>
    """, unsafe_allow_html=True)

    data = st.session_state.edit_data
    
    # 顶部导航
    if st.button(T("btn_back")): st.session_state.page = 'create'; st.rerun()
    
    # 标题
    # 居中显示，并应用莫兰迪色字体
    # 获取翻译后的前缀 ("编辑" 或 "Редактирование")
    edit_prefix = T("edit_page_title")
    
    # 渲染标题
    st.markdown(f"<h1 style='text-align: center;'> {edit_prefix} {data['title']}</h1>", unsafe_allow_html=True)
    
    # --- AI 智能导入 PDF ---
    with st.expander(T("ai_import_title"), expanded=True):
        st.caption(T("ai_import_help"))
        pdf_file = st.file_uploader("Upload PDF", type="pdf", key="pdf_up_edit")
        
        if pdf_file and st.button(T("btn_start_import")):
            # 检查 Key
            current_ds_key = DEEPSEEK_API_KEY
            current_qw_key = st.session_state.get('qwen_key_input', MY_QWEN_KEY)

            if not current_ds_key and not current_qw_key:
                st.error("请至少配置一个 AI Key (DeepSeek 或 通义千问)")
                st.stop()

            with st.spinner("AI 正在读取并分析 PDF (可能需要 30 秒)..."):
                try:
                    reader = PyPDF2.PdfReader(pdf_file)
                    text_content = ""
                    for page in reader.pages: 
                        text_content += page.extract_text() + "\n"
                    
                    # === 调试功能：显示提取的文本 ===
                    with st.expander("🔍 Debug: 查看 PDF 提取到的乱序文本", expanded=False):
                        st.text(text_content)
                    # ============================

                    parsed, src = deepseek_parse_pdf_content(text_content, current_ds_key)
                    
                    if parsed:
                        st.toast(f"成功使用 {src} 模型解析！", icon="✅")
                        
                        # 1. 解析朗读
                        if 'read' in parsed: 
                            data['read'] = parsed['read']
                            if 'read' not in data['modules']: data['modules'].append('read')
                        
                        # 2. 解析口语
                        if 'speak' in parsed:
                            if 'speak' not in data['modules']: data['modules'].append('speak')
                            processed = []
                            for q in parsed['speak']:
                                nq = {'type': q.get('type','问答题'), 'content': q.get('content',''), 'ref': ''}
                                if "问答" in nq['type']: nq['tts_file'] = get_tts_audio(nq['content'])
                                # 补全 raw_type
                                if "翻译" in nq['type']: nq['raw_type'] = T("qt_trans")
                                elif "问答" in nq['type']: nq['raw_type'] = T("qt_qa")
                                elif "看图" in nq['type']: nq['raw_type'] = T("qt_img")
                                elif "作文" in nq['type']: nq['raw_type'] = T("qt_essay")
                                processed.append(nq)
                            data['speak'] = processed
                        
                        # 3. 解析听力
                        if 'listen' in parsed:
                            if 'listen' not in data['modules']: data['modules'].append('listen')
                            processed = []
                            for q in parsed['listen']:
                                content = q.get('content', q.get('text', q.get('full', '')))
                                nq = {'type': q.get('type','复述'), 'content': content, 'tts': get_tts_audio(content)}
                                # 补全 raw_type
                                if "复述" in nq['type']: nq['raw_type'] = T("lt_rep")
                                elif "问答" in nq['type']: nq['raw_type'] = T("lt_qa")
                                elif "填空" in nq['type']: nq['raw_type'] = T("lt_cloze")
                                elif "辨调" in nq['type']: nq['raw_type'] = T("lt_tone")

                                if "填空" in nq['type']:
                                    # 尝试自动获取 AI 返回的 correct
                                    correct_ans = q.get('correct', '答案')
                                    nq.update({'display':content.replace(correct_ans, "______"), 'correct':correct_ans, 'options':[correct_ans, "干扰项"]})
                                elif "辨调" in nq['type']:
                                    o,c = generate_tone_options_smart(content)
                                    nq.update({'text':content,'options':o,'correct':c})
                                processed.append(nq)
                            data['listen'] = processed
                        
                        # 4. 解析汉字
                        if 'write' in parsed:
                            if 'write' not in data['modules']: data['modules'].append('write')
                            data['write'] = [{"hanzi": w.get('hanzi',''), "pinyin": get_pinyin(w.get('hanzi','')), "russian": ""} for w in parsed['write']]
                        
                        st.session_state.edit_data = data
                        st.success("导入成功！请检查下方各个标签页的内容。")
                        st.rerun()
                except Exception as e:
                    st.error(f"处理 PDF 时发生错误: {e}")

    modules = data['modules']
    tabs = st.tabs([{"read":T("read_section"),"speak":T("speak_section"),"listen":T("listen_section"),"write":T("write_section")}[m] for m in modules])
    
    for i, mod in enumerate(modules):
        with tabs[i]:
            if mod == 'read':
                c1,c2 = st.columns([1,1])
                with c1:
                    with st.form("ar", clear_on_submit=True):
                        t = st.text_input("输入词条", placeholder=T("pl_read"))
                        if st.form_submit_button(T("btn_add")): data['read'].append(t); st.rerun()
                with c2:
                    if data['read']:
                         with st.expander(f"📖 词条列表 ({len(data['read'])})", expanded=True):
                            for idx,q in enumerate(data['read']):
                                c_a,c_b = st.columns([4,1])
                                c_a.success(q)
                                if c_b.button("🗑️", key=f"dr{idx}"): data['read'].pop(idx); st.rerun()

            elif mod == 'speak':
                c1,c2 = st.columns([1,2])
                with c1: qt = st.radio("Type", [T("qt_trans"),T("qt_qa"),T("qt_img"),T("qt_essay")], key="rq")
                with c2:
                    with st.form("sp", clear_on_submit=True):
                        # 修复：输入框干净
                        c = st.text_input("内容/问题", value="", key=f"sp_c_{qt}")
                        r = st.text_input(T("pl_ref"), key=f"sp_r_{qt}")
                        img = st.file_uploader(T("pl_img")) if qt==T("qt_img") else None
                        
                        if st.form_submit_button(T("btn_add")):
                            q_type_final = qt 
                            display_title = qt
                            if qt==T("qt_trans"): display_title = T("qt_trans") + " / Перевод"
                            elif qt==T("qt_qa"): display_title = T("qt_qa") + " / Вопрос-ответ"
                            elif qt==T("qt_img"): display_title = T("qt_img") + " / Картинка"
                            elif qt==T("qt_essay"): display_title = T("qt_essay") + " / Сочинение"
                            
                            q={'type':display_title, 'content':c, 'ref':r, 'raw_type': qt}
                            if img: q['image_data'] = img.read()
                            if "问答" in qt or "Вопрос" in qt: 
                                f=get_tts_audio(c); q['tts_file']=f
                            data['speak'].append(q); st.rerun()
                
                # 预览归类 (带样式)
                grouped = {}
                for q in data['speak']:
                    t = q.get('raw_type', q.get('type', 'Other'))
                    if t not in grouped: grouped[t] = []
                    grouped[t].append(q)
                for t, qs in grouped.items():
                    with st.expander(f"{t} ({len(qs)})", expanded=False):
                        for idx, q in enumerate(data['speak']):
                            if q.get('raw_type', q.get('type')) == t:
                                st.write(q['content'])
                                if st.button("🗑️", key=f"dsp{idx}"): data['speak'].pop(idx); st.rerun()
        
            elif mod == 'listen':
                c1,c2 = st.columns([1,2])
                with c1: 
                    lt = st.radio("Type", [T("lt_rep"),T("lt_qa"),T("lt_cloze"),T("lt_tone")], key="rl")
                with c2:
                    with st.form("ls", clear_on_submit=True):
                        # 修复：输入框干净
                        c = st.text_input("内容/完整句", value="", key=f"ls_c_{lt}", placeholder="例如：我_喜欢秋天 (用下划线表示挖空位置)")
                        w = st.text_input("挖空答案/字", key=f"ls_w_{lt}", placeholder="例如：最")
                        
                        # 提交按钮
                        if st.form_submit_button(T("btn_add")):
                            # 1. 基础信息处理
                            f = get_tts_audio(c) # 生成语音
                            
                            # 构建显示标题
                            l_title = lt
                            if lt==T("lt_rep"): l_title += " / Повторение"
                            elif lt==T("lt_qa"): l_title += " / Вопрос"
                            elif lt==T("lt_cloze"): l_title += " / Пропуски"
                            elif lt==T("lt_tone"): l_title += " / Тоны"

                            # 创建题目对象
                            q = {'type': l_title, 'content': c, 'tts': f, 'raw_type': lt}
                            
                            # 2. 特殊题型处理 (填空 & 辨调)
                            if "填空" in l_title or "Пропуски" in l_title:
                                # 校验：必须填写答案
                                if not w:
                                    st.error("⚠️ 填空题必须填写'挖空答案'！")
                                    st.stop() # 停止运行，防止添加空数据
                                    
                                # AI 生成干扰项
                                with st.spinner(f"AI 正在为 '{w}' 生成混淆干扰项..."):
                                    try:
                                        # 确保你的 generate_distractors_via_ai 函数定义在全局且已生效
                                        distractors = generate_distractors_via_ai(c, w, DEEPSEEK_API_KEY)
                                    except Exception as e:
                                        # 如果AI出错，使用默认干扰项，保证程序不崩
                                        print(f"AI Error: {e}") 
                                        distractors = ["干扰A", "干扰B", "干扰C"]
                                    
                                    # 组合选项并打乱
                                    all_options = [w] + distractors
                                    random.shuffle(all_options)
                                    
                                    # 更新题目数据
                                    q.update({
                                        'display': c.replace(w, "______"),
                                        'correct': w,
                                        'options': all_options
                                    })
                            
                            elif "辨调" in l_title: 
                                o, co = generate_tone_options_smart(c)
                                q.update({'text': c, 'options': o, 'correct': co})
                            
                            # 3. 保存数据 (重点！！！这行代码必须和上面的 if/elif 对齐，不能缩进进去)
                            data['listen'].append(q)
                            
                            # 4. 刷新页面
                            st.rerun()
                
                # 下方显示题目列表预览
                grouped = {}
                for q in data['listen']:
                    t = q.get('raw_type', q.get('type', 'Other'))
                    if t not in grouped: grouped[t] = []
                    grouped[t].append(q)
                for t, qs in grouped.items():
                    with st.expander(f"{t} ({len(qs)})", expanded=False):
                        for idx, q in enumerate(data['listen']):
                            if q.get('raw_type', q.get('type')) == t:
                                if q.get('tts'): st.audio(q['tts'])
                                if "填空" in str(q.get('type')):
                                    st.write(f"题目: {q.get('display')} | 答案: {q.get('correct')} | 选项: {q.get('options')}")
                                else:
                                    st.write(q['content'])
                                
                                if st.button("🗑️", key=f"dl{idx}"): data['listen'].pop(idx); st.rerun()

            elif mod == 'write':
                c1,c2,c3 = st.columns([1,2,2])
                with c1: st.info("AI Parse")
                with c2:
                    with st.form("ws"):
                        rt = st.text_area(T("pl_words"))
                        if st.form_submit_button(T("btn_ai_parse")):
                            with st.spinner("AI..."):
                                st.session_state.qwen_key_input = MY_QWEN_KEY
                                res = deepseek_parse_words(rt, DEEPSEEK_API_KEY)
                                if res: data['write'].extend(res); st.rerun()
                with c3:
                    if data['write']:
                         with st.expander(f"✍️ 词卡预览 ({len(data['write'])})", expanded=True):
                            for idx, w in enumerate(data.get('write', [])):
                                with st.expander(f"{w['hanzi']}"):
                                    c_a, c_b = st.columns(2)
                                    new_p = c_a.text_input("拼音", w['pinyin'], key=f"wp_{idx}")
                                    new_r = c_b.text_input("俄语", w.get('russian',''), key=f"wr_{idx}")
                                    if new_p!=w['pinyin']: data['write'][idx]['pinyin']=new_p
                                    if new_r!=w.get('russian',''): data['write'][idx]['russian']=new_r
                                    if st.button("🗑️", key=f"dw{idx}"): data['write'].pop(idx); st.rerun()

    st.divider()
    # 保存按钮：深棕色
    if st.button(T("btn_save_lib"), type="primary"):
        filename = st.session_state.get('edit_filename', None)
        save_task_to_file(data, filename)
        st.success("Saved"); st.session_state.page = 'task_library'; st.rerun()

def page_student_login():
    st.title(T("student_login"))
    name = st.text_input(T("name_placeholder"))
    if st.button(T("start_btn")):
        st.session_state.student_name = name
        st.session_state.student_answers = {} 
        st.session_state.page = 'student_exam'; st.rerun()

def page_student_exam():
    task = st.session_state.active_task_data
    st.title(task.get('title'))
    enable_ai = st.toggle("🤖 AI", value=True)
    
    # ==========================================
    # 📘 朗读 (Read) - 已修复重复分析问题
    # ==========================================
    if task.get('read'):
        st.markdown('<div class="read-box"><h3 class="section-title">📘 '+T("read_section")+'</h3>', unsafe_allow_html=True)
        for idx, q in enumerate(task['read']):
            with st.container(border=True):
                py = get_pinyin(q)
                with st.expander(f"🗣️ **{idx+1}. {q}** ({T('expand_pinyin')})"):
                    st.markdown(f"<h3 style='color:#4CAF50'>{py}</h3>", unsafe_allow_html=True)
                
                # 录音控件
                audio = audio_recorder(text="", key=f"r{idx}", recording_color="#2196F3", neutral_color="#eee")
                if audio: st.audio(audio, format='audio/wav')
                
                ans_key = f"read_{idx}"
                # 1. 初始化存储结构
                if ans_key not in st.session_state.student_answers:
                    st.session_state.student_answers[ans_key] = {'type': '朗读', 'question_preview': q, 'score': -1, 'audio': None}
                
                # 2. 关键修改：获取之前保存的录音
                old_audio = st.session_state.student_answers[ans_key].get('audio')

                # 3. 只有当 audio 存在，且与旧录音不同时，才触发 AI
                if audio and audio != old_audio:
                    # 更新 Session 中的录音
                    st.session_state.student_answers[ans_key]['audio'] = audio
                    
                    # 触发 AI 分析
                    if enable_ai and AZURE_SPEECH_KEY:
                        with st.spinner(T("ai_analyzing")):
                            res_obj, _ = assess_pronunciation(q, audio, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION)
                        if res_obj:
                            st.session_state.student_answers[ans_key]['score'] = int(res_obj.accuracy_score)
                            # 保存详细评分对象供后续显示
                            st.session_state.student_answers[ans_key]['detail_res'] = res_obj 

                # 4. 显示结果 (直接从 Session 读取，不重复计算)
                if st.session_state.student_answers[ans_key].get('score', -1) != -1:
                    res_obj = st.session_state.student_answers[ans_key].get('detail_res')
                    if res_obj:
                         with st.expander(T("microscope"), expanded=True):
                            cols = st.columns(len(res_obj.words))
                            for w_idx, w_info in enumerate(res_obj.words):
                                with cols[w_idx]:
                                    st.markdown(f"**{w_info.word}**")
                                    for ph in w_info.phonemes:
                                        color = "#d4edda" if ph.accuracy_score >= 80 else "#f8d7da"
                                        st.markdown(f"<div style='background:{color};padding:2px;font-size:10px'>{ph.phoneme}<br>{int(ph.accuracy_score)}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
    # 🟧 口语 (Speak) - 已修复 Key 覆盖 Bug
    # ==========================================
    if task.get('speak'):
        st.markdown('<div class="speak-box"><h3 class="section-title">🟧 '+T("speak_section")+'</h3>', unsafe_allow_html=True)
        for idx, q in enumerate(task['speak']):
            with st.container(border=True):
                st.markdown(f"**{q['type']}**")
                
                instruction = ""
                q_type_str = q.get('raw_type', q['type'])
                if "翻译" in q_type_str or "Перевод" in q_type_str: instruction = T("inst_trans")
                elif "问答" in q_type_str or "Вопрос" in q_type_str: instruction = T("inst_qa")
                elif "看图" in q_type_str or "Картинка" in q_type_str: instruction = T("inst_img")
                elif "作文" in q_type_str or "Сочинение" in q_type_str: instruction = T("inst_essay")
                
                if instruction: st.markdown(f":red[**{instruction}**]")
                
                if "翻译" in q['type']: st.markdown(f"#### 🇷🇺 {q['content']}")
                else: st.write(q.get('content'))
                
                if q.get('image_data'): st.image(q['image_data'], width=300)
                if q.get('tts_file') and os.path.exists(q.get('tts_file')): st.audio(q['tts_file'])
                
                # 录音控件
                audio = audio_recorder(text="", key=f"s{idx}", recording_color="#FF9800", neutral_color="#eee")
                if audio: st.audio(audio, format='audio/wav')
                
                ans_key = f"speak_{idx}"
                # 1. 初始化
                if ans_key not in st.session_state.student_answers:
                    st.session_state.student_answers[ans_key] = {'type': q['type'], 'question_preview': q.get('content',''), 'score': 0, 'audio': None}
                
                # 2. 获取旧录音
                old_audio = st.session_state.student_answers[ans_key].get('audio')

                # 3. 只有当 audio 存在，且与旧录音不同时，才触发 AI
                if audio and audio != old_audio:
                    st.session_state.student_answers[ans_key]['audio'] = audio
                    
                    # 获取当前的 keys
                    qwen_key_valid = st.session_state.get('qwen_key_input', MY_QWEN_KEY)
                    
                    # 修改判断：DeepSeek 或 Qwen 有一个能用就行
                    if enable_ai and (DEEPSEEK_API_KEY or qwen_key_valid):
                        # === 核心修复：删除了之前这里覆写 session_state 的错误代码 ===
                        
                        with st.spinner(T("ai_analyzing")):
                            txt = speech_to_text(audio, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION)
                            if txt:
                                cmt, scr = deepseek_evaluate(q['type'], str(q.get('content')), txt, DEEPSEEK_API_KEY)
                                # 更新 Session 数据
                                st.session_state.student_answers[ans_key].update({'transcribed_text':txt, 'ai_comment':cmt, 'score':scr})
                            else:
                                st.warning("未检测到语音 / No speech detected")
                
                # 4. 显示结果
                current_ans = st.session_state.student_answers[ans_key]
                if current_ans.get('ai_comment'):
                    st.markdown(current_ans['ai_comment'])
                    
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 🟪 听力 (Listen) - 保持原样 (不需要改复杂逻辑，但也建议加上保护)
    # ==========================================
    if task.get('listen'):
        st.markdown('<div class="listen-box"><h3 class="section-title">🟪 '+T("listen_section")+'</h3>', unsafe_allow_html=True)
        for idx, q in enumerate(task['listen']):
            with st.container(border=True):
                st.markdown(f"**{q['type']}**")
                instruction = ""
                q_type_str = q.get('raw_type', q['type'])
                if "复述" in q_type_str: instruction = T("inst_rep")
                elif "问答" in q_type_str: instruction = T("inst_lqa")
                elif "填空" in q_type_str: instruction = T("inst_cloze")
                elif "辨调" in q_type_str: instruction = T("inst_tone")
                if instruction: st.markdown(f":red[**{instruction}**]")

                if q.get('tts') and os.path.exists(q.get('tts')): st.audio(q['tts'])
                ans_key = f"listen_{idx}"
                
                if "辨调" in q['type']:
                    # 辨调不需要改，st.radio 本身就会保持状态
                    ans = st.radio("拼音", q['options'], key=f"lt{idx}", horizontal=True)
                    if ans: st.session_state.student_answers[ans_key] = {'score': 100 if ans==q['correct'] else 0, 'student_text_input': ans, 'type':q['type'], 'question_preview':q['text']}
                elif "填空" in q['type']:
                    # 填空同理
                    ans = st.radio(q['display'], q['options'], key=f"lc{idx}", horizontal=True)
                    if ans: st.session_state.student_answers[ans_key] = {'score': 100 if ans==q['correct'] else 0, 'student_text_input': ans, 'type':q['type'], 'question_preview':q['display']}
                else:
                    # 听力里的录音题 (复述/问答)
                    audio = audio_recorder(text="", key=f"lr{idx}", recording_color="#9C27B0", neutral_color="#eee")
                    if audio: st.audio(audio, format='audio/wav')
                    
                    if ans_key not in st.session_state.student_answers: 
                        st.session_state.student_answers[ans_key] = {'type': q['type'], 'question_preview': q.get('content',''), 'score': -1, 'audio': None}
                    
                    # 这里虽然听力没有接入实时AI评分，但加上这个逻辑可以防止 session 数据被无效覆写
                    old_audio = st.session_state.student_answers[ans_key].get('audio')
                    if audio and audio != old_audio:
                         st.session_state.student_answers[ans_key]['audio'] = audio

        st.markdown('</div>', unsafe_allow_html=True)

    # Write (Green Box) - 保持不变
    if task.get('write'):
        st.markdown('<div class="write-box"><h3 class="section-title">🟩 '+T("write_section")+'</h3>', unsafe_allow_html=True)
        wb_html = generate_workbook_html(task['title'], task['write'])
        b64_wb = base64.b64encode(wb_html.encode()).decode()
        st.markdown(f'<a href="data:text/html;base64,{b64_wb}" download="workbook.html" style="background:#1976D2;color:white;padding:10px;text-decoration:none;border-radius:5px">{T("download_workbook")}</a>', unsafe_allow_html=True)
        st.write("") 
        for idx, w in enumerate(task['write']):
            hanzi = w['hanzi']
            with st.container(border=True):
                c_big, c_anim, c_info = st.columns([1, 2, 2])
                with c_big: st.markdown(f"<div style='font-size:80px;text-align:center;font-weight:bold;line-height:120px;'>{hanzi}</div>", unsafe_allow_html=True)
                with c_anim:
                    st.caption("笔顺演示")
                    cols = st.columns(len(hanzi))
                    for char_i, char in enumerate(hanzi):
                        with cols[char_i]: components.html(render_hanzi_writer(char, f"hw_{idx}_{char_i}"), height=80)
                with c_info:
                    tts_file = get_tts_audio(hanzi)
                    if tts_file: st.audio(tts_file)
                    with st.expander("📖"):
                        st.write(f"拼音: {w['pinyin']}")
                        st.write(f"俄语: {w.get('russian', '')}")

        st.divider()
        uploaded_file = st.file_uploader(T("upload_photo"), type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, width=300)
            st.session_state.student_answers['write_task'] = {'type': '汉字书写', 'question_preview': '字帖', 'score': -1, 'image_upload': uploaded_file}
        st.markdown('</div>', unsafe_allow_html=True)

    # 提交按钮逻辑保持不变
    total_q = len(task.get('read',[])) + len(task.get('speak',[])) + len(task.get('listen',[])) + (1 if task.get('write') else 0)
    answered_q = len(st.session_state.student_answers)
    
    if st.button(T("submit_btn"), type="primary"):
        if answered_q < total_q:
             if not st.session_state.confirm_submit:
                 st.session_state.confirm_submit = True
                 st.warning(f"⚠️ 还有题目未完成 ({answered_q}/{total_q})！再次点击提交以确认。")
                 st.stop()
        
        save_submission(st.session_state.student_name, task.get('title'))
        st.success(T("submit_success"))
        report = generate_report_html(st.session_state.student_name, task.get('title'), st.session_state.student_answers)
        b64 = base64.b64encode(report.encode()).decode()
        st.markdown(f'<a href="data:text/html;base64,{b64}" download="report.html">{T("download_report")}</a>', unsafe_allow_html=True)
        st.session_state.confirm_submit = False

def page_review_dashboard():
    # --- 1. 注入批改台专属美化 CSS ---
    st.markdown("""
    <style>
        /* 全局背景 */
        .stApp { background-color: #FAF9F6; }
        
        /* 标题样式 */
        h1 {
            color: #8D6E63 !important;
            font-family: "Kaiti SC", "KaiTi", serif;
            font-weight: 900;
        }
        
        /* 日历容器 */
        .calendar-box {
            background-color: #FFF;
            border: 2px solid #D7CCC8;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }
        
        /* 日历按钮 */
        div[data-testid="stHorizontalBlock"] button {
            border-radius: 50% !important; /* 圆形按钮 */
            width: 40px !important;
            height: 40px !important;
            padding: 0 !important;
            font-weight: bold;
            border: none !important;
        }
        
        /* 未读/已读 颜色标记 */
        /* Streamlit 按钮很难精准控制具体某一个的颜色，这里主要靠文字内容(🔴/🟢)区分，
           或者依赖 primary/secondary 状态 */
           
        /* 批改卡片区域 */
        .grading-card {
            background-color: #FDF6F6;
            border-left: 5px solid #BC8F8F;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("📝 批改工作台")
    
    base = "submissions"
    if not os.path.exists(base): 
        st.info("暂无作业数据")
        return
    
    # --- 1. 构建日历数据 ---
    calendar_data = {} 
    # 遍历所有 report.csv 获取日期状态
    for root, dirs, files in os.walk(base):
        for file in files:
            if file == "report.csv":
                try:
                    df = pd.read_csv(os.path.join(root, file))
                    if not df.empty:
                        d_str = str(df.iloc[0]['时间']).split(' ')[0] # YYYY-MM-DD
                        status = 'green' if '已批改' in df['状态'].values else 'red'
                        
                        if d_str not in calendar_data: calendar_data[d_str] = 'green'
                        if status == 'red': calendar_data[d_str] = 'red' # 只要有一个未改，那天就是红
                except: pass

    # --- 2. 日历显示区 (左右布局) ---
    col_cal, col_filter = st.columns([2, 1])
    
    with col_cal:
        st.markdown("### 📅 作业日历")
        with st.container(): # 日历容器
            today = datetime.now()
            # 获取当前月日历矩阵
            cal = calendar.monthcalendar(today.year, today.month)
            
            # 显示星期头
            cols = st.columns(7)
            days_header = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for i, d in enumerate(days_header):
                cols[i].markdown(f"**{d}**")
            
            # 显示日期网格
            for week in cal:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0:
                        cols[i].write("") # 空白占位
                    else:
                        d_str = f"{today.year}-{today.month:02d}-{day:02d}"
                        
                        # 决定按钮样式和图标
                        status = calendar_data.get(d_str, None)
                        label = f"{day}"
                        btn_type = "secondary"
                        
                        if status == 'red': 
                            label = f"{day}🔴"
                            btn_type = "primary" # 红色高亮未读
                        elif status == 'green':
                            label = f"{day}🟢"
                        
                        # 点击筛选
                        if cols[i].button(label, key=d_str, type=btn_type, use_container_width=True):
                            st.session_state.filter_date = d_str
                            st.rerun()

    with col_filter:
        st.write("") # 占位对齐
        st.write("")
        st.markdown("### 🔍 筛选状态")
        if st.session_state.filter_date:
            st.info(f"当前筛选: **{st.session_state.filter_date}**")
            if st.button("❌ 清除筛选 (显示全部)"):
                st.session_state.filter_date = None
                st.rerun()
        else:
            st.success("显示全部作业")

    st.divider()

    # --- 3. 任务与学生选择 ---
    # 严格过滤文件夹
    all_tasks = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and not d.startswith(".")]
    if not all_tasks: st.warning("没有找到任务文件夹"); return
    
    # 这里的布局改一下，让选择更清晰
    c_task, c_stu = st.columns(2)
    with c_task:
        task = st.selectbox("📂 选择任务", all_tasks)
    
    path = os.path.join(base, task)
    all_stus = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")]
    
    # 过滤逻辑：如果选了日期，只显示那天有提交的学生
    filtered_stus = []
    if st.session_state.filter_date:
        for s in all_stus:
            r_path = os.path.join(path, s, "report.csv")
            if os.path.exists(r_path):
                try:
                    df = pd.read_csv(r_path)
                    d = str(df.iloc[0]['时间']).split(' ')[0]
                    if d == st.session_state.filter_date:
                        filtered_stus.append(s)
                except: pass
    else:
        filtered_stus = all_stus

    with c_stu:
        if not filtered_stus:
            st.selectbox("👤 选择学生", ["无符合条件的学生"], disabled=True)
            if st.session_state.filter_date: st.warning(f"{st.session_state.filter_date} 没有学生提交作业。")
            return
        else:
            student = st.selectbox("👤 选择学生", filtered_stus)

    # --- 4. 批改卡片区域 ---
    if student:
        report_p = os.path.join(path, student, "report.csv")
        if os.path.exists(report_p):
            df = pd.read_csv(report_p)
            
            st.markdown("---")
            st.markdown(f"### 📝 正在批改: {student}")
            
            # 使用 Form 批量保存
            with st.form(f"grading_form_{student}"):
                rows = []
                for i, r in df.iterrows():
                    # == 单题批改卡片 ==
                    st.markdown(f"""
                    <div style="background:#FDF6F6; border:1px solid #D7CCC8; border-radius:10px; padding:15px; margin-bottom:15px;">
                        <div style="color:#8D6E63; font-weight:bold; margin-bottom:5px;">题号 {i+1} [{r['类型']}]</div>
                        <div style="font-size:18px; margin-bottom:10px;">{r['题目']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 媒体回显
                    c_media, c_input = st.columns([1, 2])
                    with c_media:
                        if pd.notna(r.get('音频')):
                            audio_p = os.path.join(path, student, str(r['音频']))
                            if os.path.exists(audio_p): st.audio(audio_p)
                            else: st.caption("无录音")
                        
                        if pd.notna(r.get('图片')):
                            img_p = os.path.join(path, student, str(r['图片']))
                            if os.path.exists(img_p): st.image(img_p, width=200)

                        # 显示 AI 辅助信息
                        if pd.notna(r.get('识别文本')): st.caption(f"👂 识别: {r['识别文本']}")
                        if pd.notna(r.get('AI评语')): st.info(f"🤖 AI: {r['AI评语']}")

                    with c_input:
                        # --- 修复开始：解决 -1 报错和变量名问题 ---
                        
                        # 1. 修复分数：如果数据库存的是 -1 (未评分)，显示为 0
                        raw_score = int(r.get('得分', 0))
                        display_score = raw_score if raw_score >= 0 else 0
                        
                        new_score = st.number_input(
                            T("score"), 
                            min_value=0, 
                            max_value=100, 
                            value=display_score, 
                            key=f"s_{student}_{i}"
                        )
                        
                        # 2. 修复评语变量：统一用 old_cmt
                        # 逻辑：优先显示老师写过的，没有则显示AI的，再没有则为空
                        if '教师评语' in r and pd.notna(r['教师评语']):
                            old_cmt = str(r['教师评语'])
                        else:
                            old_cmt = str(r.get('AI评语', ''))
                            
                        new_cmt = st.text_area(
                            T("comment"), 
                            value=old_cmt, 
                            placeholder="请输入评语...", 
                            key=f"c_{student}_{i}", 
                            height=100
                        )
                        # --- 修复结束 ---

                    # 更新数据
                    r['得分'] = new_score
                    r['教师评语'] = new_cmt
                    r['状态'] = "已批改"
                    rows.append(r)
                
                # 提交按钮
                st.write("")
                if st.form_submit_button("💾 保存所有批改 (Save All)"):
                    pd.DataFrame(rows).to_csv(report_p, index=False)
                    st.success("✅ 批改已保存！")
                    st.rerun()

            # --- 生成成绩单 ---
            st.write("")
            if st.button(f"📤 生成 {student} 的最终成绩单"):
                html = generate_report_html(student, task, df)
                b64 = base64.b64encode(html.encode()).decode()
                st.markdown(f'<a href="data:text/html;base64,{b64}" download="{student}_final_report.html" style="background:#4CAF50;color:white;padding:10px 20px;text-decoration:none;border-radius:10px;">📥 点击下载 HTML 成绩单</a>', unsafe_allow_html=True)
# ==========================================
# 🔗 核心逻辑：检查网址链接，自动跳转
# ==========================================
# 获取网址栏参数
try:
    query_params = st.query_params
except:
    query_params = {} # 兼容旧版

if "task_id" in query_params and st.session_state.get('auto_jump') != True:
    try:
        # 1. 解码任务文件名
        b64_id = query_params["task_id"]
        if isinstance(b64_id, list): b64_id = b64_id[0] # 防止列表
        
        task_filename = base64.b64decode(b64_id).decode()
        
        # 2. 尝试加载任务
        task_data = load_task_from_file(task_filename)
        
        if task_data:
            # 3. 设置状态，直接跳到学生登录或考试页
            st.session_state.active_task_data = task_data
            st.session_state.student_answers = {}
            st.session_state.page = 'student_login' # 或者直接跳 'student_exam'
            st.session_state.auto_jump = True # 防止死循环刷新
            st.rerun() # 强制刷新页面进入
        else:
            st.error(f"未找到任务文件: {task_filename}")
    except Exception as e:
        st.error(f"链接无效: {e}")

# ==========================================
# 下面是你原本的页面路由代码 (保持不变)
# ==========================================
if st.session_state.page == 'home': page_home()
elif st.session_state.page == 'task_library': page_task_library()
# ...

if st.session_state.page == 'home': page_home()
elif st.session_state.page == 'task_library': page_task_library()
elif st.session_state.page == 'create': page_create()
elif st.session_state.page == 'edit': page_edit()
elif st.session_state.page == 'student_login': page_student_login()
elif st.session_state.page == 'student_exam': page_student_exam()
elif st.session_state.page == 'review_dashboard': page_review_dashboard()
