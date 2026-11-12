import streamlit as st
import tempfile
import os
import subprocess
from moviepy import AudioFileClip
from PIL import Image

st.set_page_config(page_title="圖片音訊合成 MP4", page_icon="🎬", layout="centered")

st.title("🎬 圖片 + 音訊 一鍵合成 MP4")
st.caption("支援 16:9 橫向與 9:16 手機直立式格式（純白底邊、高壓縮輕巧檔案，限 3 分鐘內）")

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
    "3. 請選擇音訊檔案 (支援 MP3, WAV, M4A)：",
    type=["mp3", "wav", "m4a", "ogg"]
)

def fit_image_to_canvas(pil_img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """將圖片等比例縮放並置中放入純白背景畫布，保持原圖不變形"""
    # 若為透明背景 PNG，先合成在白底上避免變黑
    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        alpha_bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(alpha_bg, pil_img.convert("RGBA")).convert("RGB")
    else:
        img = pil_img.convert("RGB")

    orig_w, orig_h = img.size
    ratio = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)
    
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # 建立純白背景畫布 (255, 255, 255) 並將圖片貼在正中央
    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
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
                audio_clip.close()

                if total_duration > 180:
                    st.error(f"音訊長度為 {total_duration:.1f} 秒，超過 3 分鐘（180秒）限制，請縮短後再試。")
                else:
                    per_img_duration = total_duration / len(uploaded_images)
                    output_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    temp_files.append(output_mp4)

                    list_txt = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
                    temp_files.append(list_txt.name)

                    last_img_path = ""
                    for img_file in uploaded_images:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                            raw_pil = Image.open(img_file)
                            fitted_img = fit_image_to_canvas(raw_pil, TARGET_W, TARGET_H)
                            fitted_img.save(tmp_img.name, format="JPEG", quality=85)
                            temp_files.append(tmp_img.name)
                            last_img_path = tmp_img.name

                            safe_path = tmp_img.name.replace("\\", "/")
                            list_txt.write(f"file '{safe_path}'\n")
                            list_txt.write(f"duration {per_img_duration:.3f}\n")

                    safe_last = last_img_path.replace("\\", "/")
                    list_txt.write(f"file '{safe_last}'\n")
                    list_txt.close()

                    # 優化壓縮參數：crf 28 + veryfast + 單聲道 64k 音訊，大幅縮小檔案體積
                    cmd = [
                        "ffmpeg", "-y",
                        "-f", "concat", "-safe", "0", "-i", list_txt.name,
                        "-i", audio_path,
                        "-c:v", "libx264",
                        "-tune", "stillimage",
                        "-preset", "veryfast",
                        "-crf", "28",
                        "-r", "1",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-ac", "1", "-b:a", "64k",
                        "-shortest",
                        output_mp4
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    with open(output_mp4, "rb") as f:
                        video_bytes = f.read()

                    file_size_mb = len(video_bytes) / (1024 * 1024)
                    st.success(f"合成完成！格式：{TARGET_W}×{TARGET_H}，長度：{total_duration:.1f} 秒，檔案大小：{file_size_mb:.2f} MB")
                    
                    st.write("### 🎬 影片預覽：")
                    st.video(video_bytes)
                    
                    st.download_button(
                        label=f"💾 下載 MP4 影片 ({format_tag} - {file_size_mb:.2f} MB)",
                        data=video_bytes,
                        file_name=f"video_{format_tag}.mp4",
                        mime="video/mp4",
                        type="primary"
                    )

            except subprocess.CalledProcessError as cpe:
                st.error(f"FFmpeg 轉檔失敗：{cpe.stderr.decode('utf-8', errors='ignore')}")
            except Exception as e:
                st.error(f"合成過程發生錯誤：{e}")
            finally:
                for f_path in temp_files:
                    if os.path.exists(f_path):
                        try:
                            os.remove(f_path)
                        except Exception:
                            pass
