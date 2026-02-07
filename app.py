import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import requests
import time
from moviepy.editor import ImageClip, AudioFileClip
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 🔐 SYSTEM LOGIC & KEYS (Yahan Logic Set Hai)
# ==========================================

# 1. PRIMARY BRAIN (Tumhari Gemini Key Maine Laga Di Hai)
PRIMARY_KEY = "AIzaSyB1sYZSfJLRy-qpdAsCJ9rAb0sxXOzCBBk" 

# 2. BACKUP BRAIN (Hugging Face - Mistral)
# Agar Gemini fail hoga, toh ye key use hogi. (Apni HF Token yahan daal dena)
BACKUP_KEY = "hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" 

# Firebase Config (Database)
FIREBASE_DB_URL = "https://brandflow-9c883-default-rtdb.firebaseio.com"
FIREBASE_API_KEY = "AIzaSyB4jSKGqvu280FuNNYb2yZyA--nC9Kv6Ew"

st.set_page_config(page_title="BrandFlow: Hybrid AI", page_icon="🧠", layout="centered")

# Temp Folder Logic
if not os.path.exists("temp"):
    os.makedirs("temp")

# ==========================================
# 🤖 ARTIFICIAL INTELLIGENCE LOGIC (The Brain)
# ==========================================

def brain_gemini(topic):
    """PLAN A: Google Gemini 1.5 Flash"""
    try:
        genai.configure(api_key=PRIMARY_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(f"""
        You are a viral YouTube Shorts scriptwriter. Write a script about '{topic}'.
        Format strictly:
        TITLE: [Catchy Title]
        DESCRIPTION: [Description with hashtags]
        SCRIPT: [Spoken words only, approx 300 characters, NO instructions like 'Host:' or 'Camera:']
        """)
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")
        return None

def brain_mistral(topic):
    """PLAN B: Mistral-7B (Hugging Face)"""
    # Agar Backup Key nahi hai, toh ye step fail ho jayega
    if "hf_" not in BACKUP_KEY:
        return "MISSING_KEY"

    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {BACKUP_KEY}"}
    
    prompt = f"""
    <s>[INST] Write a YouTube Shorts script about '{topic}'.
    Format output as:
    TITLE: [Title]
    DESCRIPTION: [Description]
    SCRIPT: [Script text only] [/INST]
    """
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            text = response.json()[0]['generated_text']
            # Cleaning the mess from LLM
            clean_text = text.split("[/INST]")[1].strip()
            return clean_text
        else:
            print(f"⚠️ Backup Error: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Backup Connection Error: {e}")
        return None

def hybrid_manager(topic):
    """YE HAI MAIN LOGIC: Jo decide karega kaun kaam karega"""
    
    # Step 1: Try Gemini
    st.toast("🧠 Trying Primary Brain (Gemini)...", icon="⚡")
    data = brain_gemini(topic)
    
    if data:
        return "Gemini 1.5 Flash", data
    
    # Step 2: Gemini Failed? Try Mistral
    st.error("⚠️ Gemini Failed! Switching to Backup Brain (Mistral)...")
    time.sleep(1) # Thoda saans lene do system ko
    
    data = brain_mistral(topic)
    
    if data == "MISSING_KEY":
        return "ERROR", "Gemini fail ho gaya aur Backup Key (HuggingFace) nahi mili."
    elif data:
        return "Mistral 7B (Backup)", data
    else:
        return "CRITICAL FAILURE", "Dono AI fail ho gaye. Internet check karein."

# ==========================================
# 🎬 MEDIA GENERATION LOGIC
# ==========================================

async def generate_audio(text, output_file):
    """Text to Speech Logic"""
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def generate_video(audio_path, image_path, output_path):
    """Video Editing Logic"""
    try:
        audio = AudioFileClip(audio_path)
        image = ImageClip(image_path).set_duration(audio.duration)
        
        # Smart Resize Logic (Agar image choti hai toh fit karega)
        if image.w > image.h: # Agar horizontal image hai
            image = image.resize(height=1920) # Crop center logic simple rakha hai
            image = image.crop(x1=image.w/2 - 540, width=1080)
        else:
            image = image.resize(width=1080)
            
        video = image.set_audio(audio)
        video.write_videofile(output_path, fps=1, codec="libx264", audio_codec="aac")
        return True
    except Exception as e:
        st.error(f"Render Logic Error: {e}")
        return False

# ==========================================
# 🚀 UPLOAD & DATABASE LOGIC
# ==========================================

def firebase_log(title, vid_id, status):
    url = f"{FIREBASE_DB_URL}/uploads.json?auth={FIREBASE_API_KEY}"
    data = {"title": title, "video_id": vid_id, "status": status, "timestamp": {".sv": "timestamp"}}
    requests.post(url, json=data)

def youtube_upload(client_secret, video_path, title, description):
    try:
        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
        # Port 8501 for Local/Streamlit
        credentials = flow.run_local_server(port=8501, prompt='consent', authorization_prompt_message="")
        
        youtube = build("youtube", "v3", credentials=credentials)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "tags": ["AI Shorts", "BrandFlow"], "categoryId": "22"},
                "status": {"privacyStatus": "private"}
            },
            media_body=MediaFileUpload(video_path)
        )
        response = request.execute()
        return response['id']
    except Exception as e:
        st.error(f"Upload Logic Error: {e}")
        return None

# ==========================================
# 🖥️ FRONTEND (User Interface)
# ==========================================
st.title("🧠 BrandFlow: Hybrid Auto-Tuber")
st.caption("Logic: Gemini 1.5 (Primary) ➡️ Mistral 7B (Backup)")

col1, col2 = st.columns([3, 2])
with col1:
    topic = st.text_input("Video Topic", placeholder="e.g. Psychology Facts")
with col2:
    bg_image = st.file_uploader("Background Image", type=["jpg", "png"])

if st.button("🚀 Run Logic", type="primary", use_container_width=True):
    if not topic or not bg_image:
        st.warning("Data missing! Topic aur Image dono chahiye.")
    else:
        # PROGRESS UI
        status_box = st.status("⚙️ Running AI Logic...", expanded=True)
        
        # 1. BRAIN LOGIC
        status_box.write("🧠 Phase 1: Selecting Best AI Model...")
        brain_name, script_data = hybrid_manager(topic)
        
        if brain_name in ["ERROR", "CRITICAL FAILURE"]:
            status_box.update(label="❌ Brain Failure", state="error")
            st.error(script_data)
            st.stop()
            
        status_box.write(f"✅ Script Generated by: **{brain_name}**")
        
        # Parsing (Text cleaning)
        try:
            if "TITLE:" in script_data:
                title = script_data.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
                desc = script_data.split("DESCRIPTION:")[1].split("SCRIPT:")[0].strip()
                script = script_data.split("SCRIPT:")[1].strip()
            else:
                title = f"Facts about {topic}"
                desc = "#Shorts"
                script = script_data
            
            # 2. AUDIO LOGIC
            status_box.write("🗣️ Phase 2: Processing Voice...")
            audio_path = "temp/audio.mp3"
            asyncio.run(generate_audio(script, audio_path))
            
            # 3. VIDEO LOGIC
            status_box.write("🎥 Phase 3: Rendering & Resizing...")
            image_path = "temp/bg.jpg"
            with open(image_path, "wb") as f:
                f.write(bg_image.getbuffer())
            
            video_out = "temp/output.mp4"
            if generate_video(audio_path, image_path, video_out):
                st.video(video_out)
                
                # 4. UPLOAD LOGIC
                if os.path.exists("client_secret.json"):
                    status_box.write("🚀 Phase 4: Uploading to Channel...")
                    vid_id = youtube_upload("client_secret.json", video_out, title, desc)
                    
                    if vid_id:
                        firebase_log(title, vid_id, "Uploaded")
                        status_box.update(label="✅ Cycle Complete!", state="complete")
                        st.success(f"Video Live! ID: {vid_id}")
                    else:
                        status_box.update(label="⚠️ Upload Failed", state="error")
                else:
                    status_box.update(label="✅ Done (Local Mode)", state="complete")
                    st.info("Upload skipped: 'client_secret.json' not found.")
                    
        except Exception as e:
            st.error(f"System Crash: {e}")
