import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import streamlit.components.v1 as components
import base64

# ----------------- 請填入你的微軟官方免費金鑰 -----------------
AZURE_SPEECH_KEY = "2uqI9DDZVaNXRzfZwxdPJGkt6mxy3WaIRvqzNVTenetusXE7yVj2JQQJ99CJACREanaXJ3w3AAAYACOGWWTe"
AZURE_SPEECH_REGION = "canadaeast"  
# -----------------------------------------------------------

st.set_page_config(page_title="AI 文字轉語音 (TTS)", layout="centered")

st.title("🎙️ 高音質 AI 文字轉語音")
st.caption("微軟神經網絡自然真人聲線，支援語速微調、MP3 下載與直接檔案分享")

# 初始化文字框與音訊狀態
if "text_content" not in st.session_state:
    st.session_state["text_content"] = ""
if "audio_bytes" not in st.session_state:
    st.session_state["audio_bytes"] = None

# 語音清單
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
    if st.button("🗑️ 清除內容"):
        st.session_state["text_content"] = ""
        st.session_state["audio_bytes"] = None
        st.rerun()

with btn_col2:
    st.caption("💡 提示：點擊框內按 `Ctrl + V` 直接貼上")

text_input = st.text_area(
    label="文字輸入區",
    value=st.session_state["text_content"],
    placeholder="在此輸入或貼上英文、中文或廣東話文字...",
    height=160,
    label_visibility="collapsed"
)

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
                st.session_state["audio_bytes"] = convert_with_azure(text_input, voice_code, rate_str)
                st.success("轉換完成！")
            except Exception as e:
                st.error(f"錯誤：{e}")

# 轉換完成後顯示播放器與下載/分享按鈕
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
        # 將音訊二進位資料轉為 Base64，傳給瀏覽器 JavaScript 封裝成檔案
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

                    // 檢查瀏覽器是否支援檔案分享
                    if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                        await navigator.share({{
                            files: [file],
                            title: '語音檔案',
                            text: '這是為你生成的 AI 語音 MP3 音檔：'
                        }});
                    }} else {{
                        alert('目前瀏覽器環境不支援直接分享檔案，請使用左側「下載 MP3」按鈕儲存後發送。');
                    }}
                }} catch (error) {{
                    console.log('取消分享或發生錯誤：', error);
                }}
            }});
            </script>
            """,
            height=60,
        )
