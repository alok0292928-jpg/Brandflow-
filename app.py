import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import requests  # Firebase se baat karne ke liye
import json
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 1. CONFIGURATION & FIREBASE SETUP
# ==========================================
st.set_page_config(page_title="BrandFlow Pro", page_icon="🔥", layout="centered")

# Aapka Firebase Config (Jo aapne diya tha)
FIREBASE_DB_URL = "https://brandflow-9c883-default-rtdb.firebaseio.com"
FIREBASE_API_KEY = "AIzaSyB4jSKGqvu280FuNNYb2yZyA--nC9Kv6Ew"

# Temp folder
if not os.path.exists("temp"):
    os.makedirs("temp")

# ==========================================
# 2. BACKEND LOGIC (Dimag)
# ==========================================

def save_to_firebase(video_title, video_id, status):
    """Data ko Firebase Database mein save karta hai"""
    url = f"{FIREBASE_DB_URL}/uploads.json?auth={FIREBASE_API_KEY}"
    data = {
        "title": video_title,
        "video_id": video_id,
        "status": status,
        "timestamp": {".sv": "timestamp"} # Server time
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return True
        else:
            print(f"Firebase Error: {response.text}")
            return False
    except Exception as e:
        print(f"Connection Error: {e}")
        return False

def ai_generate_script(api_key, topic):
    """Gemini se Script likhwata hai"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"""
        Write a YouTube Shorts script about '{topic}'.
        Format:
        TITLE: [Title under 50 chars]
        DESCRIPTION: [Description with hashtags]
        SCRIPT: [Spoken text only, approx 300 chars]
        """)
        return response.text
    except Exception as e:
        st.error(f"Brain Error: {str(e)}")
        return None

async def text_to_speech(text, output_file):
    """Text se Audio banata hai"""
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def render_video(audio_path, image_path, output_path):
    """Audio + Image jodkar Video banata hai"""
    try:
        audio = AudioFileClip(audio_path)
        image = ImageClip(image_path).set_duration(audio.duration)
        video = image.set_audio(audio)
        video.write_videofile(output_path, fps=1, codec="libx264", audio_codec="aac")
        return True
    except Exception as e:
        st.error(f"Rendering Error: {e}")
        return False

def upload_video(client_secret, video_path, title, description):
    """YouTube par upload karta hai"""
    try:
        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
        credentials = flow.run_local_server(port=8501, prompt='consent')
        
        youtube = build("youtube", "v3", credentials=credentials)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["BrandFlow"],
                    "categoryId": "22"
                },
                "status": {"privacyStatus": "private"}
            },
            media_body=MediaFileUpload(video_path)
        )
        response = request.execute()
        return response['id']
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return None

# ==========================================
# 3. FRONTEND (User Interface)
# ==========================================
st.title("🔥 BrandFlow Manager")

# Sidebar
with st.sidebar:
    st.header("🔑 Keys")
    gemini_key = st.text_input("Gemini API Key", type="password")
    
    # Check Files
    if os.path.exists("client_secret.json"):
        st.success("✅ Client Secret Found")
    else:
        st.error("❌ 'client_secret.json' missing!")

# Main Screen
topic = st.text_input("Video Topic", placeholder="e.g. Future of AI")
bg_image = st.file_uploader("Background Image", type=["jpg", "png"])

if st.button("🚀 Start Auto-Pilot"):
    if not gemini_key or not topic or not bg_image:
        st.warning("Sabhi details fill karein!")
    else:
        status = st.status("🤖 AI Processing...", expanded=True)
        
        # 1. Script
        status.write("🧠 Generating Script...")
        ai_data = ai_generate_script(gemini_key, topic)
        
        if ai_data:
            try:
                title = ai_data.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
                desc = ai_data.split("DESCRIPTION:")[1].split("SCRIPT:")[0].strip()
                script = ai_data.split("SCRIPT:")[1].strip()
                status.write(f"📝 Script: {title}")
                
                # 2. Audio
                status.write("🗣️ Generating Voice...")
                audio_path = "temp/audio.mp3"
                asyncio.run(text_to_speech(script, audio_path))
                
                # 3. Video
                status.write("🎥 Rendering Video...")
                image_path = "temp/bg.jpg"
                with open(image_path, "wb") as f:
                    f.write(bg_image.getbuffer())
                
                video_out = "temp/final.mp4"
                if render_video(audio_path, image_path, video_out):
                    status.write("✅ Video Ready!")
                    st.video(video_out)
                    
                    # 4. Upload & Database Save
                    if os.path.exists("client_secret.json"):
                        status.write("🚀 Uploading to YouTube...")
                        vid_id = upload_video("client_secret.json", video_out, title, desc)
                        
                        if vid_id:
                            # 5. Save to Firebase
                            status.write("💾 Saving to Firebase Database...")
                            if save_to_firebase(title, vid_id, "Uploaded"):
                                st.success(f"Success! Video ID: {vid_id} saved to DB.")
                            else:
                                st.warning("Video uploaded but DB save failed.")
                            
                            status.update(label="Mission Complete!", state="complete")
                    else:
                        status.write("⚠️ Upload Skipped (No Secret File)")
            except Exception as e:
                st.error(f"Processing Error: {e}")
