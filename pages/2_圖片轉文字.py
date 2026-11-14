from google import genai
from PIL import Image
import streamlit as st

st.title("靈修圖片轉文字工具 (OCR)")
st.write("上傳您的靈修圖片，系統將直接為您轉錄出完整的繁體中文文字。")

# 透過側邊欄輸入 Gemini API Key（或確保系統環境變數已設定 GEMINI_API_KEY）
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# 檔案上傳元件
uploaded_file = st.file_uploader(
    "選擇圖片檔案", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
  # 顯示上傳的圖片預覽
  image = Image.open(uploaded_file)
  st.image(image, caption="上傳的圖片預覽", use_container_width=True)

  if st.button("開始轉錄文字"):
    if not api_key:
      st.error("請先在左側邊欄輸入您的 Gemini API Key！")
    else:
      with st.spinner("AI 正在辨識與轉錄中..."):
        try:
          # 初始化 Google GenAI Client
          client = genai.Client(api_key=api_key)

          # 呼叫 Gemini 模型處理圖片
          response = client.models.generate_content(
              model="gemini-2.5-flash",
              contents=[
                  image,
                  (
                      "請直接將圖片中的所有文字完整轉錄為繁體中文，"
                      "原封不動直出，絕對不要做任何摘要或總結。"
                  ),
              ],
          )

          # 呈現結果
          st.success("轉錄完成！")
          st.subheader("辨識結果：")
          # 使用文字輸入框方便您一鍵複製
          st.text_area(
              "點擊下方框框即可全選複製", response.text, height=350
          )

        except Exception as e:
          st.error(f"發生錯誤：{e}")
