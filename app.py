import streamlit as st
import json
import requests
import io
import wave
import base64

# Set up the page configuration
st.set_page_config(
    page_title="Bedtime Story Weaver",
    page_icon="🌙",
    layout="wide",
)

# --- Firebase configuration (not used in this app but included for context) ---
# The `__app_id`, `__firebase_config`, and `__initial_auth_token` are
# special variables provided by the Canvas environment.
# Since we are not using Firestore in this app, we will not use these variables.

# --- Gemini API Configuration ---
TEXT_GENERATION_MODEL = "gemini-2.5-flash-preview-05-20"
TTS_MODEL = "gemini-2.5-flash-preview-tts"

# --- Function to generate story text using the Gemini API ---
def generate_story(prompt, api_key):
    """
    Calls the Gemini API to generate a story based on the provided prompt.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_GENERATION_MODEL}:generateContent?key={api_key}"
    # New system prompt for bedtime stories
    system_prompt = "You are a gentle and soothing storyteller, specializing in creating calming and imaginative bedtime stories for children. The stories should be a few paragraphs long and have a happy, reassuring ending."
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        story_text = result['candidates'][0]['content']['parts'][0]['text']
        return story_text
    except requests.exceptions.RequestException as e:
        st.error(f"Error generating story. Check your API key and try again: {e}")
        return None

# --- Function to generate TTS audio using the Gemini API ---
def text_to_speech(text, api_key):
    """
    Converts a story text to audio using the Gemini TTS API.
    Returns the audio data in a BytesIO object and the sample rate.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Puck"} # Upbeat voice
                }
            }
        }
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_s_status()
        result = response.json()
        
        audio_data_b64 = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
        mime_type = result['candidates'][0]['content']['parts'][0]['inlineData']['mimeType']
        
        # Decode the base64 audio data
        audio_data_pcm = base64.b64decode(audio_data_b64)
        
        # Extract sample rate from mime type (e.g., audio/L16;rate=24000)
        sample_rate_str = mime_type.split('rate=')[1]
        sample_rate = int(sample_rate_str)
        
        # Convert raw PCM data to WAV format in memory
        with io.BytesIO() as audio_io:
            with wave.open(audio_io, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono audio
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data_pcm)
            
            audio_io.seek(0)
            return audio_io.read()
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error generating audio. Check your API key and try again: {e}")
        return None
    except (KeyError, IndexError) as e:
        st.error(f"Unexpected API response structure: {e}")
        return None

# --- Web Speech API (Voice Input) Component ---
def voice_input():
    """
    A small HTML/JS component to handle voice input via the Web Speech API.
    It uses a trick with st.session_state to pass the result back to Python.
    """
    if 'voice_text' not in st.session_state:
        st.session_state.voice_text = ""

    html_code = f"""
    <div style="text-align: center;">
        <button id="voice-input-btn" 
                style="background-color: transparent; border: 2px solid #5A4E8F; color: #5A4E8F; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 12px; font-family: sans-serif;">
            <span style="font-size: 24px;">🎙️</span> Voice Input
        </button>
    </div>
    <script>
        const voiceBtn = document.getElementById('voice-input-btn');
        if ('webkitSpeechRecognition' in window) {{
            const recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {{
                const transcript = event.results[0][0].transcript;
                const url = new URL(window.location.href);
                url.searchParams.set('voice_input', transcript);
                window.location.href = url.toString();
            }};

            recognition.onerror = (event) => {{
                console.error("Speech recognition error:", event.error);
                alert("Speech recognition error: " + event.error);
            }};

            voiceBtn.onclick = () => {{
                recognition.start();
            }};
        }} else {{
            voiceBtn.style.display = 'none';
            alert('Your browser does not support Web Speech API.');
        }}
    </script>
    """
    st.html(html_code)

# --- UI Layout and Logic ---
st.title("🌙 Bedtime Story Weaver")
st.markdown("### Create a magical story for a good night's sleep.")

# Sidebar for all the inputs
with st.sidebar:
    st.header("Story Details")
    
    api_key = st.text_input("Enter your Gemini API Key", type="password")
    if not api_key:
        st.warning("Please enter your API key to proceed. You can get one from the Google AI Studio.")
    st.markdown("---")
    
    # Text input for voice transcription
    voice_input_param = st.query_params.get('voice_input')
    if voice_input_param:
        st.session_state.voice_text = voice_input_param
        st.query_params.clear()
        
    st.text_area(
        "Voice Input",
        value=st.session_state.get('voice_text', ""),
        help="Use the microphone button below to speak your input.",
        key="voice_input_area"
    )
    
    voice_input()

    st.markdown("---")
    characters = st.text_input("Enter the main characters (e.g., A sleepy bear, a gentle firefly)")
    genre = st.selectbox("Select the genre", ["Fantasy", "Nature Adventure", "Fairy Tale", "Animal Story"])
    age_group = st.selectbox("Select the age group", ["Toddlers (1-3 years)", "Children (4-8 years)"])
    tips = st.text_area("Additional tips (e.g., 'Make it snow,' 'Include a friendly owl')")
    
    generate_button = st.button("Generate Story", type="primary")

# --- Main Content Area ---
if generate_button:
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not characters:
        st.error("Please enter at least one character to get started.")
    else:
        # Construct the full prompt for the LLM
        story_prompt = f"Create a story for the following details:\n\n"
        story_prompt += f"Characters: {characters}\n"
        story_prompt += f"Genre: {genre}\n"
        story_prompt += f"Age Group: {age_group}\n"
        if tips:
            story_prompt += f"Additional Tips: {tips}\n"
        
        with st.spinner("Weaving a peaceful tale..."):
            story = generate_story(story_prompt, api_key)
            if story:
                st.session_state.story_text = story

if "story_text" in st.session_state:
    st.markdown("---")
    st.markdown("### Your Bedtime Story")
    st.markdown(st.session_state.story_text)
    
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("🔊 Tell Me the Story"):
            with st.spinner("Generating soothing audio..."):
                audio_data = text_to_speech(st.session_state.story_text, api_key)
                if audio_data:
                    st.audio(audio_data, format="audio/wav")
    with col2:
        st.write("Click to have the story read aloud.")
