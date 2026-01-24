import streamlit as st
import requests
import tempfile
import os
import json
import speech_recognition as sr
from pydub import AudioSegment

def transcribe_audio(audio_file_path):
    """Transcribe audio using Google Speech Recognition"""
    try:
        r = sr.Recognizer()
        
        # Try direct audio file first
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data)
                return text
        except:
            # If direct doesn't work, convert to wav
            audio = AudioSegment.from_file(audio_file_path)
            wav_path = audio_file_path.replace(os.path.splitext(audio_file_path)[1], '.wav')
            audio.export(wav_path, format="wav")
            
            with sr.AudioFile(wav_path) as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data)
            
            # Clean up
            if wav_path != audio_file_path:
                os.unlink(wav_path)
                
            return text
            
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return None

def generate_quiz_with_grok(transcript, api_key):
    """Generate quiz using Grok API"""
    url = "https://api.x.ai/v1/chat/completions"
    
    prompt = f"""Based on this transcript, create exactly 10 multiple choice questions:
- 5 easy questions (basic comprehension)
- 5 complex questions (analysis/inference)

Format as JSON:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct": "A",
      "difficulty": "easy"
    }}
  ]
}}

Transcript: {transcript}"""

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'grok-beta',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        content = response.json()['choices'][0]['message']['content']
        try:
            return json.loads(content)
        except:
            st.error("Failed to parse quiz JSON")
            return None
    else:
        st.error(f"Quiz generation failed: {response.text}")
        return None

def main():
    st.title("🎧 Audio Quiz Generator")
    st.write("Upload audio → Get transcript → Generate quiz")
    
    # API Key input
    api_key = st.text_input("Enter your Grok API Key:", type="password")
    
    if not api_key:
        st.warning("Please enter your Grok API key to continue")
        return
    
    # File upload
    uploaded_file = st.file_uploader("Upload Audio File (optional)", type=['mp3', 'wav', 'm4a', 'mp4'])
    
    # Manual transcript input
    manual_transcript = st.text_area("Or paste your transcript here:", height=150)
    
    if st.button("Generate Quiz"):
        transcript = None
        
        if uploaded_file:
            with st.spinner("Processing audio..."):
                # Save uploaded file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                
                # Transcribe audio
                transcript = transcribe_audio(tmp_path)
                os.unlink(tmp_path)
        
        # Use manual transcript if audio transcription failed
        if not transcript and manual_transcript:
            transcript = manual_transcript
        elif not transcript:
            st.error("Please upload an audio file or paste a transcript")
            return
        
        st.success("✅ Transcription complete!")
        with st.expander("View Transcript"):
            st.text_area("", transcript, height=150)
        
        with st.spinner("Generating quiz..."):
            quiz_data = generate_quiz_with_grok(transcript, api_key)
            
            if not quiz_data:
                return
            
            st.success("✅ Quiz generated!")
            
            # Display quiz
            st.header("📝 Quiz")
            
            user_answers = {}
            for i, q in enumerate(quiz_data['questions']):
                st.subheader(f"Q{i+1} ({q['difficulty'].title()})")
                st.write(q['question'])
                
                user_answers[i] = st.radio(
                    f"Select answer for Q{i+1}:",
                    q['options'],
                    key=f"q_{i}"
                )
            
            if st.button("Submit Quiz"):
                score = 0
                results = []
                
                for i, q in enumerate(quiz_data['questions']):
                    correct = q['correct']
                    user_choice = user_answers[i][0]  # Get A, B, C, or D
                    
                    if user_choice == correct:
                        score += 1
                        results.append("✅")
                    else:
                        results.append(f"❌ (Correct: {correct})")
                
                st.header("🎯 Results")
                st.write(f"**Score: {score}/10 ({score*10}%)**")
                
                for i, result in enumerate(results):
                    st.write(f"Q{i+1}: {result}")

if __name__ == "__main__":
    main()