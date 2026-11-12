import streamlit as st
import tempfile
import os
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image

st.set_page_config(page_title="圖片音訊合成 MP4", page_icon="🎬", layout="centered")

st.title("🎬 圖片 + 音訊 一鍵合成 MP4")
st.caption("支援 16:9 電腦/電視橫向格式，以及 9:16 手機直立式格式（限 3 分鐘內）")

# 1. 選擇影片比例格式
aspect_option = st.radio(
    "1. 請選擇輸出影片格式：",
    [
        "📺 16:9 橫向寬螢幕 (1280 × 720 - 適合電腦 / YouTube)",
        "📱 9:16 手機直立式 (720 × 1280 - 適合 WhatsApp / Reels / Shorts)"
    ],
    horizontal=False
)

if "16:9" in aspect_option:
    TARGET_W, TARGET_H = 1280, 720
    format_tag = "16x9"
else:
    TARGET_W, TARGET_H = 720, 1280
    format_tag = "9x16"

# 2. 上傳圖片
uploaded_images = st.file_uploader(
    "2. 請選擇圖片 (支援 JPG, PNG，可一次選多張自動輪播)：",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# 3. 上傳音訊
uploaded_audio = st.file_uploader(
    "3. 請選擇剛才生成的 MP3 或其他音訊檔 (支援 MP3, WAV, M4A)：",
    type=["mp3", "wav", "m4a", "ogg"]
)

def fit_image_to_canvas(pil_img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """將圖片等比例縮放並置中放入目標畫布，保持原圖不變形"""
    img = pil_img.convert("RGB")
    orig_w, orig_h = img.size
    
    ratio = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)
    
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    canvas.paste(resized_img, (paste_x, paste_y))
    
    return canvas

if uploaded_images and uploaded_audio:
    st.audio(uploaded_audio)

    if st.button("🚀 開始合成 MP4 影片", type="primary"):
        with st.spinner(f"正在生成 {format_tag} 格式 MP4 影片，請稍候..."):
            temp_files = []
            try:
                audio_ext = os.path.splitext(uploaded_audio.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=audio_ext) as tmp_aud:
                    tmp_aud.write(uploaded_audio.read())
                    audio_path = tmp_aud.name
                    temp_files.append(audio_path)

                audio_clip = AudioFileClip(audio_path)
                total_duration = audio_clip.duration

                if total_duration > 180:
                    st.error(f"音訊長度為 {total_duration:.1f} 秒，超過 3 分鐘（180秒）限制，請縮短後再試。")
                    audio_clip.close()
                else:
                    per_img_duration = total_duration / len(uploaded_images)
                    clips = []

                    for img_file in uploaded_images:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                            raw_pil = Image.open(img_file)
                            fitted_img = fit_image_to_canvas(raw_pil, TARGET_W, TARGET_H)
                            fitted_img.save(tmp_img.name, format="PNG")
                            temp_files.append(tmp_img.name)

                            clip = ImageClip(tmp_img.name).with_duration(per_img_duration)
                            clips.append(clip)

                    final_video = concatenate_videoclips(clips, method="compose").with_audio(audio_clip)

                    output_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    temp_files.append(output_mp4)

                    final_video.write_videofile(
                        output_mp4,
                        fps=24,
                        codec="libx264",
                        audio_codec="aac",
                        preset="ultrafast",
                        logger=None
                    )

                    final_video.close()
                    audio_clip.close()

                    with open(output_mp4, "rb") as f:
                        video_bytes = f.read()

                    st.success(f"合成完成！格式：{TARGET_W}×{TARGET_H}，總長度：{total_duration:.1f} 秒")
                    st.video(video_bytes)
                    st.download_button(
                        label=f"💾 下載 MP4 影片 ({format_tag})",
                        data=video_bytes,
                        file_name=f"video_{format_tag}.mp4",
                        mime="video/mp4",
                        type="primary"
                    )

            except Exception as e:
                st.error(f"合成過程發生錯誤：{e}")
            finally:
                for f_path in temp_files:
                    if os.path.exists(f_path):
                        try:
                            os.remove(f_path)
                        except Exception:
                            pass
