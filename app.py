import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import requests
import time
import random
from moviepy.editor import ImageClip, AudioFileClip
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 🔐 CONFIGURATION
# ==========================================
# 1. PRIMARY (Gemini)
PRIMARY_KEY = "AIzaSyB1sYZSfJLRy-qpdAsCJ9rAb0sxXOzCBBk" # Aapki Key

# 2. BACKUP (Hugging Face - Optional)
BACKUP_KEY = "hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" 

st.set_page_config(page_title="BrandFlow: Unstoppable", page_icon="🛡️")

if not os.path.exists("temp"):
    os.makedirs("temp")

# ==========================================
# 🧠 BRAIN LOGIC (3-Layer Safety)
# ==========================================

def brain_gemini(topic):
    """PLAN A: Gemini 1.5 Flash"""
    try:
        genai.configure(api_key=PRIMARY_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"""
        Write a YouTube Shorts script about '{topic}'.
        Format:
        TITLE: [Title]
        DESCRIPTION: [Description]
        SCRIPT: [Script text only]
        """)
        return response.text
    except:
        return None

def brain_mistral(topic):
    """PLAN B: Mistral AI"""
    if "hf_" not in BACKUP_KEY: return None
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {BACKUP_KEY}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": f"Write a short script about {topic}."})
        return response.json()[0]['generated_text']
    except:
        return None

def brain_template(topic):
    """PLAN C: Emergency Template (No AI needed)"""
    templates = [
        f"Did you know this amazing fact about {topic}? It is truly mind-blowing. Many people are unaware of this. Subscribe for more!",
        f"Here is a quick fact about {topic}. This will change how you see the world. Stay tuned for more updates.",
        f"Top secret information about {topic} revealed! You won't believe this. Make sure to like and share."
    ]
    script = random.choice(templates)
    
    return f"""
    TITLE: Amazing Facts about {topic} #Shorts
    DESCRIPTION: Watch this #Shorts video about {topic}
    SCRIPT: {script}
    """

def unstoppable_manager(topic):
    """Ye Manager kabhi fail nahi hoga"""
    
    # 1. Try Gemini
    data = brain_gemini(topic)
    if data: return "Gemini 1.5 (Primary)", data
    
    # 2. Try Mistral
    data = brain_mistral(topic)
    if data: return "Mistral (Backup)", data
    
    # 3. Use Template (Emergency)
    data = brain_template(topic)
    return "Template Engine (Emergency Mode)", data

# ==========================================
# 🎬 MEDIA LOGIC
# ==========================================

async def generate_audio(text, output_file):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def generate_video(audio_path, image_path, output_path):
    try:
        audio = AudioFileClip(audio_path)
        image = ImageClip(image_path).set_duration(audio.duration)
        
        # Auto Resize
        if image.w > image.h:
            image = image.resize(height=1920)
            image = image.crop(x1=image.w/2 - 540, width=1080)
        else:
            image = image.resize(width=1080)
            
        video = image.set_audio(audio)
        video.write_videofile(output_path, fps=1, codec="libx264", audio_codec="aac")
        return True
    except Exception as e:
        st.error(f"Render Error: {e}")
        return False

# ==========================================
# 🚀 UPLOAD LOGIC
# ==========================================

def youtube_upload(client_secret, video_path, title, description):
    try:
        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
        credentials = flow.run_local_server(port=8501, prompt='consent', authorization_prompt_message="")
        youtube = build("youtube", "v3", credentials=credentials)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "tags": ["Shorts"], "categoryId": "22"},
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
# 🖥️ FRONTEND UI
# ==========================================
st.title("🛡️ BrandFlow: Unstoppable Mode")

col1, col2 = st.columns([3, 2])
with col1:
    topic = st.text_input("Video Topic")
with col2:
    bg_image = st.file_uploader("Image", type=["jpg", "png"])

if st.button("🚀 Force Start", type="primary"):
    if not topic or not bg_image:
        st.warning("Topic aur Image chahiye!")
    else:
        status = st.status("⚙️ Processing...", expanded=True)
        
        # 1. BRAIN
        status.write("🧠 Generating Script...")
        source, script_data = unstoppable_manager(topic)
        status.write(f"✅ Source: **{source}**")
        
        # Parsing
        try:
            if "TITLE:" in script_data:
                title = script_data.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
                desc = script_data.split("DESCRIPTION:")[1].split("SCRIPT:")[0].strip()
                script = script_data.split("SCRIPT:")[1].strip()
            else:
                title = f"Video about {topic}"
                desc = "#Shorts"
                script = script_data

            # 2. AUDIO
            status.write("🗣️ Generating Voice...")
            audio_path = "temp/audio.mp3"
            asyncio.run(generate_audio(script, audio_path))
            
            # 3. VIDEO
            status.write("🎥 Rendering Video...")
            image_path = "temp/bg.jpg"
            with open(image_path, "wb") as f:
                f.write(bg_image.getbuffer())
            
            video_out = "temp/output.mp4"
            if generate_video(audio_path, image_path, video_out):
                st.video(video_out)
                
                # 4. UPLOAD
                if os.path.exists("client_secret.json"):
                    status.write("🚀 Uploading...")
                    vid_id = youtube_upload("client_secret.json", video_out, title, desc)
                    if vid_id:
                        status.update(label="✅ Success!", state="complete")
                        st.success(f"Video ID: {vid_id}")
                else:
                    status.update(label="Done (Local)", state="complete")
                    
        except Exception as e:
            st.error(f"Error: {e}")
    
