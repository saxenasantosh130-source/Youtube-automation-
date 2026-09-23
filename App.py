 import os
import requests
import imageio_ffmpeg
from flask import Flask, render_template_string, request, send_file, send_from_directory
from gtts import gTTS
from google import genai
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ImageIO se FFmpeg path set karein
ffmpeg_executable = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_executable

app = Flask(__name__)
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Environment variables se keys uthayega
PEXELS_API_KEY = os.environ.get('ELlbnrqmKO7JH4ms1NElyzWcxZog5N4TsNqnmMBVj7p41ctxjnOakPq4', '')
GEMINI_API_KEY = os.environ.get('AQ.Ab8RN6JNn8tFpCTXGz5SDIc9Mrkek-Gdh4o175bY7SX6j7QcKg', '')

ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Automation Studio</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 20px 10px; background: #0f0f0f; color: #ffffff; }
        .card { background-color: #1f1f1f; padding: 25px; border-radius: 14px; max-width: 480px; margin: 0 auto; box-shadow: 0 8px 20px rgba(0,0,0,0.6); text-align: left; }
        h2 { text-align: center; margin-bottom: 20px; color: #ff3333; }
        input[type="text"], textarea, select { width: 100%; padding: 12px; margin: 8px 0; font-size: 15px; border-radius: 8px; border: 1px solid #333; color: #fff; background: #2b2b2b; box-sizing: border-box; }
        textarea { height: 110px; resize: vertical; }
        .btn-container { display: flex; gap: 12px; justify-content: center; margin-top: 15px; }
        .btn { padding: 14px; font-size: 15px; color: white; border: none; font-weight: bold; cursor: pointer; border-radius: 8px; flex: 1; text-align: center; text-decoration: none; display: inline-block; }
        .btn-ai { background-color: #7b1fa2; width: 100%; margin-top: 6px; }
        .btn-render { background-color: #ff9800; width: 100%; margin-top: 10px; }
        .btn-download { background-color: #0288d1; }
        .btn-upload { background-color: #d32f2f; }
        .res { margin-top: 18px; color: #00e676; font-size: 15px; font-weight: bold; text-align: center; }
        label { font-size: 13px; color: #bbb; margin-top: 12px; display: block; font-weight: 600; }
        .video-player { margin-top: 20px; text-align: center; border-top: 1px solid #333; padding-top: 15px; }
        video { width: 100%; max-height: 400px; border-radius: 10px; border: 2px solid #ff3333; margin-top: 10px; background: #000; }
    </style>
</head>
<body>
    <div class="card">
        <h2>YouTube Automation Studio</h2>
        
        <!-- Step 1: AI Prompt -->
        <form method="POST">
            <label>1. AI Prompt (Script & Concept):</label>
            <input type="text" name="ai_prompt" placeholder="e.g. Space Mystery, Horror Story, Facts" value="{{ prompt_val }}">
            <button type="submit" name="action" value="generate_script" class="btn btn-ai">✨ AI Script Generate Karein</button>
        </form>

        <hr style="border-color:#333; margin:22px 0;">

        <!-- Step 2: Video Render & Actions -->
        <form method="POST">
            <label>Title / Video Overlay Topic:</label>
            <input type="text" name="topic" placeholder="Topic Title" value="{{ topic_val }}" required>

            <label>Script (Hindi Voiceover):</label>
            <textarea name="script_text" required>{{ script_val }}</textarea>

            <label>Duration Select Karein:</label>
            <select name="duration">
                <option value="10" {% if dur_val == '10' %}selected{% endif %}>10 Seconds</option>
                <option value="20" {% if dur_val == '20' %}selected{% endif %}>20 Seconds</option>
                <option value="30" {% if dur_val == '30' or not dur_val %}selected{% endif %}>30 Seconds</option>
            </select>

            <button type="submit" name="action" value="create_video" class="btn btn-render">🎬 Video Make & Preview</button>

            {% if show_video %}
            <div class="video-player">
                <label>📹 Generated Video Preview:</label>
                <video controls autoplay loop>
                    <source src="/get_video" type="video/mp4">
                    Your browser does not support video playback.
                </video>
                <div class="btn-container">
                    <a href="/get_video" download="Shorts_Video.mp4" class="btn btn-download">📥 Download Video</a>
                    <button type="submit" name="action" value="upload" class="btn btn-upload">🚀 YouTube Par Upload Karein</button>
                </div>
            </div>
            {% endif %}
        </form>

        {% if message %}<div class="res">{{ message }}</div>{% endif %}
    </div>
</body>
</html>
'''

def generate_ai_script(user_prompt):
    try:
        if not ai_client:
            return "Error: GEMINI_API_KEY missing in Environment Variables"
        response = ai_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=f"Write a short, viral YouTube Shorts script in simple Hindi/Hinglish based on prompt: '{user_prompt}'. Keep it crisp, engaging, and suitable for voiceover under 40 words."
        )
        return response.text.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"

def download_pexels_video(topic):
    if os.path.exists("bg.mp4"):
        try: os.remove("bg.mp4")
        except: pass
        
    headers = {'Authorization': PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={topic}&per_page=3&orientation=portrait"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get('videos') and len(data['videos']) > 0:
            video_files = data['videos'][0]['video_files']
            video_url = video_files[0]['link']
            video_bytes = requests.get(video_url, timeout=15).content
            with open("bg.mp4", "wb") as f:
                f.write(video_bytes)
            return True
    except Exception as e:
        print(f"Pexels Error: {e}")
    return False

def make_story_video(topic, script_text):
    if os.path.exists("final.mp4"):
        try: os.remove("final.mp4")
        except: pass

    tts = gTTS(text=script_text, lang='hi')
    tts.save("voice.mp3")
    
    has_video = download_pexels_video(topic)
    
    # Safe FFmpeg execution without requiring background music dependency
    if has_video and os.path.exists("bg.mp4"):
        cmd = f'{ffmpeg_executable} -y -i voice.mp3 -stream_loop -1 -i bg.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,drawtext=text=\'{topic}\':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2" -c:v libx264 -c:a aac -shortest final.mp4'
    else:
        cmd = f'{ffmpeg_executable} -y -i voice.mp3 -f lavfi -i color=c=black:s=1080x1920:r=25 -vf "drawtext=text=\'{topic}\':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2" -c:v libx264 -c:a aac -shortest final.mp4'
        
    os.system(cmd)

def get_youtube_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\n[LOGIN REQUIRED] Open link in Chrome:\n{auth_url}\n")
            code = input("Enter Auth Code: ")
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

@app.route('/get_video')
def get_video():
    if os.path.exists("final.mp4"):
        return send_file('final.mp4', mimetype='video/mp4')
    return "Video not found", 404

@app.route('/', methods=['GET', 'POST'])
def home():
    message = ""
    prompt_val = ""
    script_val = ""
    topic_val = ""
    dur_val = "30"
    show_video = False

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate_script':
            prompt_val = request.form.get('ai_prompt', '')
            topic_val = prompt_val
            script_val = generate_ai_script(prompt_val)
            message = "✨ AI Script Ready!"

        elif action in ['create_video', 'upload']:
            topic_val = request.form.get('topic', '')
            script_val = request.form.get('script_text', '')
            dur_val = request.form.get('duration', '30')
            
            try:
                make_story_video(topic_val, script_val)
                if os.path.exists("final.mp4"):
                    show_video = True
                    message = "✅ Video Generation Complete!"
                else:
                    message = "❌ Error rendering video"
                
                if action == 'upload':
                    yt = get_youtube_service()
                    body = {
                        'snippet': {'title': f"{topic_val} #Shorts", 'description': script_val, 'tags': [topic_val, 'Shorts']},
                        'status': {'privacyStatus': 'public'}
                    }
                    media = MediaFileUpload('final.mp4', chunksize=-1, resumable=True)
                    yt.videos().insert(part='snippet,status', body=body, media_body=media).execute()
                    message = "YouTube par Upload Ho Gaya!"

            except Exception as e:
                message = f"Error: {str(e)}"

    return render_template_string(
        HTML_TEMPLATE, 
        message=message, 
        prompt_val=prompt_val, 
        script_val=script_val, 
        topic_val=topic_val,
        dur_val=dur_val,
        show_video=show_video
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
