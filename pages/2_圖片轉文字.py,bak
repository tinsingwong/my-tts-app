from google import genai
from PIL import Image
import streamlit as st

st.title("靈修圖片轉文字工具 (OCR)")
st.write("上傳您的靈修圖片，系統將直接為您轉錄出完整的繁體中文或英文文字。")

# 透過側邊欄輸入 Gemini API Key（或確保環境變數已設定）
api_key = st.sidebar.text_input("Gemini API Key", type="password")

uploaded_file = st.file_uploader(
    "選擇圖片檔案", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
  # 讀取圖片並優化尺寸以加快傳輸速度
  image = Image.open(uploaded_file)
  image.thumbnail((1200, 1200))
  st.image(image, caption="上傳的圖片預覽 (已優化尺寸)", use_container_width=True)

  if st.button("開始轉錄文字"):
    if not api_key:
      st.error("請先在左側邊欄輸入您的 Gemini API Key！")
    else:
      with st.spinner("AI 正在辨識與轉錄中..."):
        try:
          client = genai.Client(api_key=api_key)

          # 呼叫 Gemini 模型處理圖片
          response = client.models.generate_content(
              model="gemini-3.8-flash",
              contents=[
                  image,
                  (
                      "Please transcribe all text from this image faithfully,"
                      " keeping the original layout and language (Traditional"
                      " Chinese or English), without any summaries."
                  ),
              ],
          )

          st.success("轉錄完成！")
          st.subheader("辨識結果：")
          st.text_area(
              "點擊下方框框即可全選複製", response.text, height=350
          )

        except Exception as e:
          # 使用更安全的錯誤訊息輸出，避免編碼崩潰
          st.error("發生錯誤，請檢查 API Key 或網路連線。")
