from google import genai
from PIL import Image
import streamlit as st

st.title("靈修圖片轉文字工具 (OCR)")
uploaded_file = st.file_uploader(
    "選擇圖片檔案", type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
  # 讀取圖片
  image = Image.open(uploaded_file)

  # 【加速秘訣】將圖片限制最大寬度或高度在 1200 像素以內（檔案變小，速度大增！）
  image.thumbnail((1200, 1200))

  st.image(image, caption="上傳的圖片預覽 (已優化尺寸)", use_container_width=True)

  if st.button("開始轉錄文字"):
    with st.spinner("AI 正在高速辨識中..."):
      try:
        client = genai.Client(api_key="您的_API_KEY")
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[
                image,
                (
                    "請直接將圖片中的所有文字完整轉錄，"
                    "無論是英文、中文或任何語言都請原封不動直出，"
                    "絕對不要做任何摘要或總結。"
                ),
            ],
        )
        st.success("轉錄完成！")
        st.text_area("辨識結果", response.text, height=350)
      except Exception as e:
        st.error(f"發生錯誤：{e}")
