import streamlit as st
import azure.cognitiveservices.speech as speechsdk

# ----------------- 請填入你的微軟官方免費金鑰 -----------------
AZURE_SPEECH_KEY = "2uqI9DDZVaNXRzfZwxdPJGkt6mxy3WaIRvqzNVTenetusXE7yVj2JQQJ99CJACREanaXJ3w3AAAYACOGWWTe"
AZURE_SPEECH_REGION = "canadaeast"  
# -----------------------------------------------------------

st.set_page_config(page_title="AI 文字轉語音 (TTS)", layout="centered")
st.title("🎙️ 高音質 AI 文字轉語音")
st.caption("微軟神經網絡自然真人聲線，支援語速微調與 MP3 下載")

# 初始化文字框的 session state
if "text_content" not in st.session_state:
    st.session_state["text_content"] = ""

# 語音清單（包含 HiuGaai 曉佳）
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

# --- 文字輸入區與按鈕排版 ---
st.write("### 請輸入要轉換的文字：")

# 建立兩顆輔助按鈕
btn_col1, btn_col2, _ = st.columns([1, 1, 3])

with btn_col1:
    if st.button("🗑️ 清除內容"):
        st.session_state["text_content"] = ""
        st.rerun()

with btn_col2:
    # 點擊後提示使用 Ctrl+V，亦可在此重設為範例或上次複製文字
    st.caption("💡 提示：點擊輸入框按 `Ctrl + V` 可直接貼上")

# 文字輸入框（綁定 session_state）
text_input = st.text_area(
    label="文字輸入區",
    value=st.session_state["text_content"],
    placeholder="在此輸入或貼上英文、中文或廣東話文字...",
    height=160,
    label_visibility="collapsed"
)

# 保持輸入狀態同步
st.session_state["text_content"] = text_input

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

# 轉換按鈕
if st.button("🚀 開始轉換語音", type="primary"):
    if not text_input.strip():
        st.warning("請先輸入文字再進行轉換！")
    else:
        with st.spinner("AI 擬真語音生成中，請稍候..."):
            try:
                audio_bytes = convert_with_azure(text_input, voice_code, rate_str)
                st.success("轉換完成！")
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    label="💾 下載 MP3 音檔",
                    data=audio_bytes,
                    file_name="tts_output.mp3",
                    mime="audio/mp3"
                )
            except Exception as e:
                st.error(f"錯誤：{e}")