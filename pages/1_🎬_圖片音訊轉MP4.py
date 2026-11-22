import streamlit as st
import tempfile
import os
import subprocess
from moviepy import AudioFileClip
from PIL import Image

st.set_page_config(page_title="圖片音訊雙格式合成 MP4", page_icon="🎬", layout="wide")

st.title("🎬 圖片 + 音訊 一鍵雙格式合成 MP4 (Full HD 1080p)")
st.caption("一鍵同時產出 16:9 橫向 (1920×1080) 與 9:16 手機直立式 (1080×1920) 雙版本（純白底邊、高壓縮輕巧檔案，限 3 分鐘內）")

# 1. 上傳圖片
uploaded_images = st.file_uploader(
    "1. 請選擇圖片 (可一次選多張自動輪播)：",
    accept_multiple_files=True,
    key="mp4_images_uploader"
)

# 2. 上傳音訊
uploaded_audio = st.file_uploader(
    "2. 請選擇音訊檔案：",
    key="mp4_audio_uploader"
)

def fit_image_to_canvas(pil_img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """將圖片等比例縮放並置中放入純白背景畫布，保持原圖不變形"""
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
    
    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    paste_x = (target_w - new_w) // 2
    paste_y = (target_h - new_h) // 2
    canvas.paste(resized_img, (paste_x, paste_y))
    
    return canvas

def render_single_format(pil_images: list, audio_path: str, per_img_duration: float, target_w: int, target_h: int, temp_files: list) -> bytes:
    """根據指定解析度生成單一比例的 MP4 位元組資料"""
    output_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    temp_files.append(output_mp4)

    list_txt = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
    temp_files.append(list_txt.name)

    last_img_path = ""
    for raw_pil in pil_images:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
            fitted_img = fit_image_to_canvas(raw_pil, target_w, target_h)
            fitted_img.save(tmp_img.name, format="JPEG", quality=88)
            temp_files.append(tmp_img.name)
            last_img_path = tmp_img.name

            safe_path = tmp_img.name.replace("\\", "/")
            list_txt.write(f"file '{safe_path}'\n")
            list_txt.write(f"duration {per_img_duration:.3f}\n")

    safe_last = last_img_path.replace("\\", "/")
    list_txt.write(f"file '{safe_last}'\n")
    list_txt.close()

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_txt.name,
        "-i", audio_path,
        "-vsync", "cfr",
        "-r", "24",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.0",
        "-preset", "veryfast",
        "-crf", "26",
        "-g", "48",
        "-keyint_min", "48",
        "-sc_threshold", "0",
        "-force_key_frames", "expr:gte(t,n_forced*2)",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ac", "2",
        "-ar", "48000",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        output_mp4
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with open(output_mp4, "rb") as f:
        return f.read()

if uploaded_images and uploaded_audio:
    st.audio(uploaded_audio)

    if st.button("🚀 一鍵同時合成 16:9 與 9:16 雙格式 MP4", type="primary", use_container_width=True):
        with st.spinner("正在同時生成 1920×1080 與 1080×1920 雙版本 MP4，請稍候..."):
            temp_files = []
            try:
                audio_ext = os.path.splitext(uploaded_audio.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=audio_ext) as tmp_aud:
                    tmp_aud.write(uploaded_audio.getvalue())
                    audio_path = tmp_aud.name
                    temp_files.append(audio_path)

                audio_clip = AudioFileClip(audio_path)
                total_duration = audio_clip.duration
                audio_clip.close()

                if total_duration > 180:
                    st.error(f"音訊長度為 {total_duration:.1f} 秒，超過 3 分鐘（180秒）限制，請縮短後再試。")
                else:
                    per_img_duration = total_duration / len(uploaded_images)
                    pil_list = [Image.open(img_f) for img_f in uploaded_images]

                    # 橫式 1920x1080 與 直式 1080x1920
                    bytes_16x9 = render_single_format(pil_list, audio_path, per_img_duration, 1920, 1080, temp_files)
                    bytes_9x16 = render_single_format(pil_list, audio_path, per_img_duration, 1080, 1920, temp_files)

                    st.session_state["dual_mp4_result"] = {
                        "duration": total_duration,
                        "bytes_16x9": bytes_16x9,
                        "bytes_9x16": bytes_9x16,
                    }

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

# 若已生成結果，並排顯示預覽與獨立下載按鈕
if "dual_mp4_result" in st.session_state:
    res = st.session_state["dual_mp4_result"]
    size_16x9 = len(res["bytes_16x9"]) / (1024 * 1024)
    size_9x16 = len(res["bytes_9x16"]) / (1024 * 1024)

    st.success(f"✅ 雙格式合成完成！總長度：{res['duration']:.1f} 秒")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📺 16:9 橫向寬螢幕 (1920×1080)")
        st.video(res["bytes_16x9"])
        st.download_button(
            label=f"💾 下載 16:9 MP4 ({size_16x9:.2f} MB)",
            data=res["bytes_16x9"],
            file_name="video_1920x1080.mp4",
            mime="video/mp4",
            type="primary",
            use_container_width=True,
            key="dl_16x9"
        )

    with col2:
        st.subheader("📱 9:16 手機直立式 (1080×1920)")
        st.video(res["bytes_9x16"])
        st.download_button(
            label=f"💾 下載 9:16 MP4 ({size_9x16:.2f} MB)",
            data=res["bytes_9x16"],
            file_name="video_1080x1920.mp4",
            mime="video/mp4",
            type="primary",
            use_container_width=True,
            key="dl_9x16"
        )
