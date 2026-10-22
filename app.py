import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import azure.cognitiveservices.speech.translation as translation_sdk
import streamlit.components.v1 as components
import base64
import os
import tempfile

# ----------------- 請填入你的微軟官方金鑰與地區 -----------------
AZURE_SPEECH_KEY = "2uqI9DDZVaNXRzfZwxdPJGkt6mxy3WaIRvqzNVTenetusXE7yVj2JQQJ99CJACREanaXJ3w3AAAYACOGWWTe"
AZURE_SPEECH_REGION = "canadaeast"  
# -----------------------------------------------------------

st.set_page_config(page_title="AI 語音全能助手", layout="centered", page_icon="🎙️")

st.title("🎙️ AI 語音全能助手")

tab_tts, tab_stt = st.tabs(["🔊 文字轉語音 (發音)", "📝 語音轉文字 (聽寫/翻譯)"])

# ==========================================
# 廣東話口語轉正式書面中文對照庫
# ==========================================
CANTONESE_TO_WRITTEN = {
    "佢哋": "他們", "佢地": "他們", "佢": "他",
    "我哋": "我們", "我地": "我們",
    "你哋": "你們", "你地": "你們",
    "嘅": "的", "嘅話": "的話",
    "唔係": "不是", "唔好": "不要", "唔使": "不用", "唔想": "不想", "唔會": "不會", "唔": "不",
    "喺度": "正在", "喺": "在",
    "睇下": "看一下", "睇吓": "看一下", "睇": "看",
    "食飯": "吃飯", "食咗": "吃了", "食緊": "正在吃", "食": "吃",
    "講嘢": "說話", "講": "說",
    "點解": "為什麼", "點樣": "如何", "點做": "怎麼做",
    "好耐": "很久", "好彩": "幸好",
    "等陣": "稍後", "陣間": "待會兒", "尋日": "昨天", "琴日": "昨天", "聽日": "明天",
    "邊度": "哪裡", "邊個": "誰", "喺邊": "在哪裡",
    "屋企": "家裡", "返屋企": "回家", "返工": "上班", "收工": "下班",
    "乜嘢": "什麼", "咩話": "說什麼", "咩": "什麼",
    "冇問題": "沒問題", "冇嘢": "沒事", "冇": "沒有",
    "買嘢": "買東西", "攞": "拿", "畀": "給", "搵": "找"
}

def cantonese_to_written_chinese(text: str) -> str:
    """將廣東話口語詞彙替換為正式書面中文字"""
    for spoken, written in CANTONESE_TO_WRITTEN.items():
        text = text.replace(spoken, written)
    return text

# ==========================================
# 分頁 1：文字轉語音 (TTS)
# ==========================================
with tab_tts:
    st.caption("微軟神經網絡自然真人聲線，支援語速微調、MP3 下載與直接檔案分享")

    if "tts_text" not in st.session_state:
        st.session_state["tts_text"] = ""
    if "audio_bytes" not in st.session_state:
        st.session_state["audio_bytes"] = None

    VOICE_OPTIONS = {
        "廣東話 (香港 - 曉佳 女聲)": "zh-HK-HiuGaaiNeural",
        "廣東話 (香港 - 雲龍 男聲)": "zh-HK-WanLungNeural",
        "國語 (台灣 - 曉臻 女聲)": "zh-TW-HsiaoChenNeural",
        "國語 (台灣 - 雲哲 男聲)": "zh-TW-YunJheNeural",
        "國語 (普通話 - 曉曉 女聲)": "zh-CN-XiaoxiaoNeural",
        "國語 (普通話 - 雲希 男聲)": "zh-CN-YunxiNeural",
        "英語 (美式 - Jenny 女聲)": "en-US-JennyNeural",
        "英語 (美式 - Guy 男聲)": "en-US-GuyNeural",
        "英語 (英式 - Sonia 女聲)": "en-GB-SoniaNeural",
    }

    selected_voice_label = st.selectbox("選擇語言與聲音：", list(VOICE_OPTIONS.keys()))
    voice_code = VOICE_OPTIONS[selected_voice_label]

    speed_pct = st.slider(
        "語速調整 (%)：",
        min_value=-50,
        max_value=50,
        value=0,
        step=5,
        help="0% 為原速；負數代表減慢，正數代表加速"
    )
    rate_str = f"{speed_pct:+d}%"

    st.write("### 請輸入要轉換的文字：")

    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
    with btn_col1:
        if st.button("🗑️ 清除內容", key="clear_tts"):
            st.session_state["tts_text"] = ""
            st.session_state["audio_bytes"] = None
            st.rerun()

    with btn_col2:
        st.caption("💡 提示：點擊框內按 `Ctrl + V` 直接貼上")

    tts_input = st.text_area(
        label="文字輸入區",
        value=st.session_state["tts_text"],
        placeholder="在此輸入或貼上英文、中文或廣東話文字...",
        height=140,
        label_visibility="collapsed"
    )
    st.session_state["tts_text"] = tts_input

    def convert_with_azure(text: str, voice: str, rate: str) -> bytes:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{voice}">
                <prosody rate="{rate}">
                    {text}
                </prosody>
            </voice>
        </speak>"""

        result = synthesizer.speak_ssml_async(ssml).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            raise RuntimeError(f"轉換中斷：{cancellation.reason}，詳細原因：{cancellation.error_details}")
        else:
            raise RuntimeError("語音生成未完成")

    if st.button("🚀 開始轉換語音", type="primary", key="btn_run_tts"):
        if not tts_input.strip():
            st.warning("請先輸入文字再進行轉換！")
        else:
            with st.spinner("AI 擬真語音生成中，請稍候..."):
                try:
                    st.session_state["audio_bytes"] = convert_with_azure(tts_input, voice_code, rate_str)
                    st.success("轉換完成！")
                except Exception as e:
                    st.error(f"錯誤：{e}")

    if st.session_state["audio_bytes"]:
        audio_data = st.session_state["audio_bytes"]
        st.audio(audio_data, format="audio/mp3")

        col_dl, col_share = st.columns([1, 1])
        with col_dl:
            st.download_button(
                label="💾 下載 MP3 音檔",
                data=audio_data,
                file_name="voice_output.mp3",
                mime="audio/mp3",
                use_container_width=True
            )
        with col_share:
            b64_audio = base64.b64encode(audio_data).decode("utf-8")
            components.html(
                f"""
                <button id="fileShareBtn" style="
                    background-color: #ff4b4b;
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 8px;
                    font-size: 15px;
                    font-weight: 500;
                    cursor: pointer;
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                ">📤 分享 MP3 檔案</button>

                <script>
                document.getElementById('fileShareBtn').addEventListener('click', async () => {{
                    try {{
                        const b64Data = "{b64_audio}";
                        const byteCharacters = atob(b64Data);
                        const byteNumbers = new Array(byteCharacters.length);
                        for (let i = 0; i < byteCharacters.length; i++) {{
                            byteNumbers[i] = byteCharacters.charCodeAt(i);
                        }}
                        const byteArray = new Uint8Array(byteNumbers);
                        const blob = new Blob([byteArray], {{ type: 'audio/mp3' }});
                        const file = new File([blob], 'voice_output.mp3', {{ type: 'audio/mp3' }});

                        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                            await navigator.share({{
                                files: [file],
                                title: '語音檔案',
                                text: '這是為你生成的 AI 語音音檔：'
                            }});
                        }} else {{
                            alert('瀏覽器環境不支援直接分享檔案，請使用左側「下載 MP3」按鈕儲存後發送。');
                        }}
                    }} catch (error) {{
                        console.log('取消分享或發生錯誤：', error);
                    }}
                }});
                </script>
                """,
                height=60,
            )

# ==========================================
# 分頁 2：語音轉文字 (STT / 翻譯)
# ==========================================
with tab_stt:
    st.caption("上傳錄音檔案，自動辨識語音並翻譯/轉換為繁體中文（口語或書面語）或英文")

    col_lang1, col_lang2 = st.columns(2)
    with col_lang1:
        INPUT_LANGS = {
            "廣東話 (粵語)": "zh-HK",
            "普通話 / 國語": "zh-CN",
            "英語 (English)": "en-US",
        }
        chosen_input_lang = st.selectbox("1. 錄音中的原語言：", list(INPUT_LANGS.keys()))
        source_code = INPUT_LANGS[chosen_input_lang]

    with col_lang2:
        OUTPUT_LANGS = {
            "中文繁體 (口語)": "zh-Hant-spoken",
            "中文繁體 (書面語)": "zh-Hant-written",
            "英文 (English)": "en"
        }
        chosen_output_lang = st.selectbox("2. 希望輸出的文字：", list(OUTPUT_LANGS.keys()))
        target_mode = OUTPUT_LANGS[chosen_output_lang]

    uploaded_audio = st.file_uploader(
        "請選擇音訊檔案 (支援 WAV, MP3, M4A, OGG 等)",
        type=["wav", "mp3", "m4a", "ogg", "aac"]
    )

    if uploaded_audio is not None:
        st.audio(uploaded_audio)

        if st.button("🔍 開始轉換為文字", type="primary", key="btn_run_stt"):
            with st.spinner("AI 正在識別並轉換文字，請稍候..."):
                tmp_in_path = None
                tmp_wav_path = None
                try:
                    suffix = os.path.splitext(uploaded_audio.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
                        tmp_in.write(uploaded_audio.read())
                        tmp_in_path = tmp_in.name

                    try:
                        from pydub import AudioSegment
                        sound = AudioSegment.from_file(tmp_in_path)
                        sound = sound.set_frame_rate(16000).set_channels(1)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                            tmp_wav_path = tmp_wav.name
                            sound.export(tmp_wav_path, format="wav")
                    except Exception:
                        tmp_wav_path = tmp_in_path

                    # 配置 Azure 翻譯識別引擎
                    azure_target = "en" if target_mode == "en" else "zh-Hant"
                    trans_config = translation_sdk.SpeechTranslationConfig(
                        subscription=AZURE_SPEECH_KEY,
                        region=AZURE_SPEECH_REGION
                    )
                    trans_config.speech_recognition_language = source_code
                    trans_config.add_target_language(azure_target)

                    audio_config = speechsdk.audio.AudioConfig(filename=tmp_wav_path)
                    recognizer = translation_sdk.TranslationRecognizer(
                        translation_config=trans_config,
                        audio_config=audio_config
                    )

                    result = recognizer.recognize_once()

                    if result.reason == translation_sdk.ResultReason.TranslatedSpeech:
                        recognized_text = result.translations.get(azure_target, "")

                        # 若選擇書面語且原音是廣東話，將口語詞替換為書面語
                        if target_mode == "zh-Hant-written" and source_code == "zh-HK":
                            recognized_text = cantonese_to_written_chinese(recognized_text)

                        st.success("轉換完成！")
                        st.text_area("輸出結果：", value=recognized_text, height=180)
                    elif result.reason == translation_sdk.ResultReason.NoMatch:
                        st.warning("未能從音訊中識別到清晰的語音內容，請確認聲音是否清晰。")
                    elif result.reason == translation_sdk.ResultReason.Canceled:
                        cancellation = result.cancellation_details
                        st.error(f"辨識中斷：{cancellation.reason}，詳細原因：{cancellation.error_details}")
                    else:
                        st.warning("辨識未產生有效結果。")

                except Exception as ex:
                    st.error(f"轉換發生錯誤：{ex}")
                finally:
                    if tmp_in_path and os.path.exists(tmp_in_path):
                        os.remove(tmp_in_path)
                    if tmp_wav_path and tmp_wav_path != tmp_in_path and os.path.exists(tmp_wav_path):
                        os.remove(tmp_wav_path)
