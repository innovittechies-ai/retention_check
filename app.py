import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import requests
import json
import os
import time
import io
from collections import defaultdict

# Import database functions
try:
    from database import (
        init_database, get_database_url,
        save_quiz_results_db, load_quiz_results_db,
        save_authorized_emails_db, load_authorized_emails_db,
        save_quiz_history_db, load_quiz_history_db,
        save_current_quiz_db, load_current_quiz_db,
        save_attendance_cache_db, load_attendance_cache_db
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Configuration
if 'authorized_emails' not in st.session_state:
    st.session_state.authorized_emails = ["testing@gmail.com"]

# Admin credentials from secrets (secure - not visible in GitHub)
ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "testing@gmail.com")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "testing")


if 'quiz_results' not in st.session_state:
    st.session_state.quiz_results = []

QUIZ_QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "options": ["A) London", "B) Berlin", "C) Paris", "D) Madrid"],
        "correct": "C",
        "difficulty": "easy"
    },
    {
        "question": "Which programming language is known for data science?",
        "options": ["A) Java", "B) Python", "C) C++", "D) JavaScript"],
        "correct": "B",
        "difficulty": "easy"
    },
    {
        "question": "What does API stand for?",
        "options": ["A) Application Programming Interface", "B) Advanced Programming Interface", "C) Automated Programming Interface", "D) Application Process Interface"],
        "correct": "A",
        "difficulty": "easy"
    },
    {
        "question": "Which company developed React?",
        "options": ["A) Google", "B) Microsoft", "C) Facebook", "D) Amazon"],
        "correct": "C",
        "difficulty": "easy"
    },
    {
        "question": "What is the time complexity of binary search?",
        "options": ["A) O(n)", "B) O(log n)", "C) O(n²)", "D) O(1)"],
        "correct": "B",
        "difficulty": "easy"
    },
    {
        "question": "In machine learning, what does overfitting mean?",
        "options": ["A) Model performs well on training data but poorly on test data", "B) Model performs poorly on both training and test data", "C) Model performs well on both training and test data", "D) Model cannot be trained"],
        "correct": "A",
        "difficulty": "complex"
    },
    {
        "question": "Which design pattern ensures a class has only one instance?",
        "options": ["A) Factory", "B) Observer", "C) Singleton", "D) Strategy"],
        "correct": "C",
        "difficulty": "complex"
    },
    {
        "question": "What is the main advantage of microservices architecture?",
        "options": ["A) Easier debugging", "B) Better scalability and maintainability", "C) Faster development", "D) Lower costs"],
        "correct": "B",
        "difficulty": "complex"
    },
    {
        "question": "In database normalization, what is the purpose of 3NF?",
        "options": ["A) Remove duplicate data", "B) Eliminate transitive dependencies", "C) Create primary keys", "D) Improve query performance"],
        "correct": "B",
        "difficulty": "complex"
    },
    {
        "question": "What is the CAP theorem in distributed systems?",
        "options": ["A) Consistency, Availability, Partition tolerance", "B) Concurrency, Atomicity, Performance", "C) Caching, Authentication, Privacy", "D) Clustering, Aggregation, Partitioning"],
        "correct": "A",
        "difficulty": "complex"
    }
]

QUIZ_FILE = "current_quiz.json"
RESULTS_FILE = "quiz_results.json"
AUTHORIZED_EMAILS_FILE = "authorized_emails.json"
QUIZ_HISTORY_FILE = "quiz_history.json"
ATTENDANCE_CACHE_FILE = "attendance_cache.json"

# Zoom API Functions
def get_zoom_token(account_id, client_id, client_secret):
    """Get Zoom OAuth token"""
    url = "https://zoom.us/oauth/token"
    data = {'grant_type': 'account_credentials', 'account_id': account_id}
    try:
        response = requests.post(url, data=data, auth=(client_id, client_secret), timeout=10)
        if response.status_code == 200:
            return response.json()['access_token']
    except:
        pass
    return None

def get_all_meetings_in_date_range(token, start_date, end_date):
    """Get all meetings between start_date and end_date"""
    headers = {'Authorization': f'Bearer {token}'}
    all_meetings = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # Method 1: Past meetings endpoint
        past_meetings_url = "https://api.zoom.us/v2/users/me/meetings"
        params = {'type': 'past', 'page_size': 300, 'from': date_str, 'to': date_str}
        
        try:
            response = requests.get(past_meetings_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                meetings = response.json().get('meetings', [])
                for meeting in meetings:
                    meeting['date'] = date_str
                    if meeting.get('id') not in [m.get('id') for m in all_meetings]:
                        all_meetings.append(meeting)
        except:
            pass
        
        # Method 2: Report endpoint
        report_meetings_url = "https://api.zoom.us/v2/report/users/me/meetings"
        params = {'from': date_str, 'to': date_str, 'page_size': 300}
        
        try:
            response = requests.get(report_meetings_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                meetings = response.json().get('meetings', [])
                for meeting in meetings:
                    meeting['date'] = date_str
                    if meeting.get('id') not in [m.get('id') for m in all_meetings]:
                        all_meetings.append(meeting)
        except:
            pass
        
        current_date += timedelta(days=1)
    
    return all_meetings

def get_meeting_participants(token, meeting_id):
    """Get participants for a specific meeting"""
    headers = {'Authorization': f'Bearer {token}'}
    all_participants = []
    
    # Try instances API first
    instances_url = f"https://api.zoom.us/v2/past_meetings/{meeting_id}/instances"
    try:
        instances_response = requests.get(instances_url, headers=headers, timeout=10)
        if instances_response.status_code == 200:
            instances = instances_response.json().get('meetings', [])
            
            for instance in instances:
                instance_uuid = instance.get('uuid')
                participants_url = f"https://api.zoom.us/v2/report/meetings/{instance_uuid}/participants"
                
                next_page_token = None
                while True:
                    params = {'page_size': 300}
                    if next_page_token:
                        params['next_page_token'] = next_page_token
                    
                    try:
                        participants_response = requests.get(participants_url, headers=headers, params=params, timeout=10)
                        if participants_response.status_code == 200:
                            participants_data = participants_response.json()
                            participants = participants_data.get('participants', [])
                            all_participants.extend(participants)
                            
                            next_page_token = participants_data.get('next_page_token')
                            if not next_page_token:
                                break
                        else:
                            break
                    except:
                        break
    except:
        pass
    
    # Fallback: Direct meeting report
    if not all_participants:
        direct_url = f"https://api.zoom.us/v2/report/meetings/{meeting_id}/participants"
        next_page_token = None
        
        while True:
            params = {'page_size': 300}
            if next_page_token:
                params['next_page_token'] = next_page_token
            
            try:
                direct_response = requests.get(direct_url, headers=headers, params=params, timeout=10)
                if direct_response.status_code == 200:
                    participants_data = direct_response.json()
                    participants = participants_data.get('participants', [])
                    all_participants.extend(participants)
                    
                    next_page_token = participants_data.get('next_page_token')
                    if not next_page_token:
                        break
                else:
                    break
            except:
                break
    
    return all_participants

def convert_to_ist(utc_time_str):
    """Convert UTC time to IST"""
    if not utc_time_str or utc_time_str == '':
        return None
    try:
        utc_time = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        ist_time = utc_time + timedelta(hours=5, minutes=30)
        return ist_time
    except:
        return None

def fetch_attendance_data(account_id, client_id, client_secret, start_date, end_date, progress_callback=None):
    """Fetch attendance data for date range"""
    token = get_zoom_token(account_id, client_id, client_secret)
    if not token:
        return None, "Failed to authenticate with Zoom"
    
    # Get all meetings
    if progress_callback:
        progress_callback("Fetching meetings...")
    
    meetings = get_all_meetings_in_date_range(token, start_date, end_date)
    
    if not meetings:
        return None, "No meetings found in date range"
    
    # Process each meeting
    attendance_by_date = defaultdict(lambda: defaultdict(lambda: {'present': False, 'duration': 0, 'join_time': None, 'leave_time': None}))
    
    total_meetings = len(meetings)
    for idx, meeting in enumerate(meetings):
        if progress_callback:
            progress_callback(f"Processing meeting {idx+1}/{total_meetings}: {meeting.get('topic', 'Unknown')[:30]}...")
        
        meeting_id = meeting.get('id')
        meeting_date = meeting.get('date', meeting.get('start_time', '')[:10])
        
        participants = get_meeting_participants(token, meeting_id)
        
        for participant in participants:
            email = participant.get('user_email', '').lower().strip()
            if not email or email == '':
                continue
            
            duration = participant.get('duration', 0)
            join_time = convert_to_ist(participant.get('join_time', ''))
            leave_time = convert_to_ist(participant.get('leave_time', ''))
            
            # Update attendance for this date and email
            if duration > attendance_by_date[meeting_date][email]['duration']:
                attendance_by_date[meeting_date][email]['duration'] = duration
                attendance_by_date[meeting_date][email]['join_time'] = join_time
                attendance_by_date[meeting_date][email]['leave_time'] = leave_time
            
            attendance_by_date[meeting_date][email]['present'] = True
    
    return attendance_by_date, None

def load_attendance_cache():
    """Load cached attendance data"""
    # Try database first
    if DATABASE_AVAILABLE and get_database_url():
        cache = load_attendance_cache_db()
        if cache:
            # Ensure last_updated is datetime
            if 'last_updated' in cache and isinstance(cache['last_updated'], str):
                cache['last_updated'] = datetime.fromisoformat(cache['last_updated'])
            return cache
    
    # Fallback to JSON file
    if os.path.exists(ATTENDANCE_CACHE_FILE):
        try:
            with open(ATTENDANCE_CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Convert string dates back to datetime for comparison
                if 'last_updated' in data:
                    data['last_updated'] = datetime.fromisoformat(data['last_updated'])
                return data
        except:
            return None
    return None

def save_attendance_cache(data):
    """Save attendance data to cache"""
    success = False
    
    # Save to database if available
    if DATABASE_AVAILABLE and get_database_url():
        success = save_attendance_cache_db(data)
    
    # Also save to JSON file as backup
    try:
        # Convert datetime to ISO format for JSON serialization
        cache_data = {
            'last_updated': datetime.now().isoformat(),
            'data': data
        }
        with open(ATTENDANCE_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
        success = True
    except:
        pass
    
    return success

def load_authorized_emails():
    # Try database first
    if DATABASE_AVAILABLE and get_database_url():
        emails = load_authorized_emails_db()
        if emails:
            return emails
    
    # Fallback to JSON file
    if os.path.exists(AUTHORIZED_EMAILS_FILE):
        try:
            with open(AUTHORIZED_EMAILS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_authorized_emails(emails):
    success = False
    
    # Save to database if available
    if DATABASE_AVAILABLE and get_database_url():
        success = save_authorized_emails_db(emails)
    
    # Also save to JSON file as backup
    try:
        with open(AUTHORIZED_EMAILS_FILE, 'w') as f:
            json.dump(emails, f)
        success = True
    except:
        pass
    
    return success

def load_current_quiz():
    # Try database first
    if DATABASE_AVAILABLE and get_database_url():
        quiz = load_current_quiz_db()
        if quiz:
            return quiz
    
    # Fallback to JSON file
    if os.path.exists(QUIZ_FILE):
        try:
            with open(QUIZ_FILE, 'r') as f:
                return json.load(f)
        except:
            return QUIZ_QUESTIONS
    return QUIZ_QUESTIONS

def save_current_quiz(quiz_questions):
    success = False
    
    # Save to database if available
    if DATABASE_AVAILABLE and get_database_url():
        success = save_current_quiz_db(quiz_questions)
    
    # Also save to JSON file as backup
    try:
        with open(QUIZ_FILE, 'w') as f:
            json.dump(quiz_questions, f)
        success = True
    except:
        pass
    
    return success

def load_quiz_results():
    # Try database first
    if DATABASE_AVAILABLE and get_database_url():
        results = load_quiz_results_db()
        if results:
            return results
    
    # Fallback to JSON file
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r') as f:
                results = json.load(f)
                # Migrate old format to new format (Quiz_Score -> Scored)
                migrated_results = []
                for result in results:
                    migrated_result = result.copy()
                    if 'Quiz_Score' in migrated_result and 'Scored' not in migrated_result:
                        # Extract just the number from "X/Y" format if it exists
                        score_val = migrated_result.get('Quiz_Score', 0)
                        if isinstance(score_val, str) and '/' in score_val:
                            migrated_result['Scored'] = int(score_val.split('/')[0])
                        else:
                            migrated_result['Scored'] = int(score_val) if score_val else 0
                        del migrated_result['Quiz_Score']
                    migrated_results.append(migrated_result)
                return migrated_results
        except:
            return []
    return []

def save_quiz_results(results):
    success = False
    
    # Save to database if available
    if DATABASE_AVAILABLE and get_database_url():
        success = save_quiz_results_db(results)
    
    # Also save to JSON file as backup
    try:
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f)
        success = True
    except:
        pass
    
    return success

def load_quiz_history():
    # Try database first
    if DATABASE_AVAILABLE and get_database_url():
        history = load_quiz_history_db()
        if history:
            return history
    
    # Fallback to JSON file
    if os.path.exists(QUIZ_HISTORY_FILE):
        try:
            with open(QUIZ_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_quiz_history(history):
    success = False
    
    # Save to database if available
    if DATABASE_AVAILABLE and get_database_url():
        success = save_quiz_history_db(history)
    
    # Also save to JSON file as backup
    try:
        with open(QUIZ_HISTORY_FILE, 'w') as f:
            json.dump(history, f)
        success = True
    except:
        pass
    
    return success

def backup_current_results():
    """Backup current results before generating new quiz"""
    try:
        results = load_quiz_results()
        if not results:
            return True
        
        history = load_quiz_history()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to CSV backup
        df = pd.DataFrame(results)
        df.to_csv(f"quiz_backup_{timestamp}.csv", index=False)
        
        # Add to history for each user
        for result in results:
            email = result['Email']
            if email not in history:
                history[email] = []
            history[email].append(result)
        
        save_quiz_history(history)
        
        # Clear current results
        save_quiz_results([])
        st.session_state.quiz_results = []
        
        return True
    except Exception as e:
        st.error(f"Backup failed: {e}")
        return False

@st.cache_data
def get_quiz_data():
    results = load_quiz_results()
    df = pd.DataFrame(results)
    if not df.empty:
        # Ensure Scored column is integer
        if 'Scored' in df.columns:
            df['Scored'] = pd.to_numeric(df['Scored'], errors='coerce').fillna(0).astype(int)
    return df

def save_quiz_result(email, score, pass_fail):
    try:
        results = load_quiz_results()
        history = load_quiz_history()
        
        # Get attempt count from history
        attempt_count = 1
        if email in history:
            attempt_count = len(history[email]) + 1
        
        # Check if user already has a current result
        for result in results:
            if result.get("Email") == email:
                attempt_count = result.get('Attempt_Count', 1) + 1
                break
        
        existing_index = None
        for i, result in enumerate(results):
            if result.get("Email") == email:
                existing_index = i
                break
        
        # Convert IST timezone
        ist = timezone(timedelta(hours=5, minutes=30))
        dt_ist = datetime.now(ist)
        
        new_result = {
            "Timestamp": dt_ist.strftime("%Y-%m-%d %H:%M:%S"),
            "Email": email,
            "Scored": int(score),
            "Pass_Fail": pass_fail,
            "Attempt_Count": attempt_count
        }
        
        if existing_index is not None:
            results[existing_index] = new_result
        else:
            results.append(new_result)
        
        if save_quiz_results(results):
            st.session_state.quiz_results = results
            return True
        return False
    except Exception as e:
        st.error(f"Error saving result: {e}")
        return False

def generate_quiz_with_gemini(transcript, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    
    prompt = f"""Based on this transcript, create exactly 15 multiple choice questions:
- 4 easy questions (basic comprehension/discussion oriented)
- 4 moderate questions (analysis/inference/technical)
- 4 complex questions (complete technical understanding/design pattern/architecture)
- 3 programming questions (code oriented)

IMPORTANT JSON RULES:
1. Use ONLY plain text in questions and options - NO code snippets
2. For programming questions, describe the code scenario in plain text
3. Escape all special characters properly
4. Keep all text on single lines
5. Use simple quotes or describe code logic instead of actual code
6. Include an "explanation" field for each question explaining why the correct answer is right and key concepts

Format STRICTLY as valid JSON:
{{
  "questions": [
    {{
      "question": "Question text in plain English",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct": "A",
      "difficulty": "easy",
      "explanation": "Brief explanation of why the correct answer is right and key concept to remember"
    }}
  ]
}}

Transcript: {transcript}"""

    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        try:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            # Extract JSON from markdown code blocks
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].strip()
            
            # Clean up common JSON issues
            content = content.replace('\n', ' ').replace('\r', '')
            content = content.replace('\\n', ' ')
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse quiz JSON: {e}")
            st.error("The AI generated invalid JSON. Please try again or simplify your transcript.")
            return None
        except Exception as e:
            st.error(f"Error processing quiz: {e}")
            return None
    else:
        st.error(f"Quiz generation failed: {response.text}")
        return None

def explain_wrong_answers(wrong_questions, api_key):
    """Generate explanations for wrong answers using Gemini AI"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    
    questions_text = "\n\n".join([
        f"Question {i+1}: {q['question']}\nYour Answer: {q['user_answer']}\nCorrect Answer: {q['correct_answer']}\nOptions: {', '.join(q['options'])}"
        for i, q in enumerate(wrong_questions)
    ])
    
    prompt = f"""You are a helpful tutor. A student got these questions wrong in a quiz. 
For each question, explain:
1. Why the correct answer is right
2. Why the student's answer was wrong
3. Key concept to remember

Keep explanations clear, concise, and educational.

{questions_text}"""
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            return content
        else:
            return "Unable to generate explanations at this time."
    except:
        return "Unable to generate explanations at this time."

def login_page():
    # Load background image if exists
    bg_image = ""
    bg_file = None
    for ext in ['quiz background.webp', 'quiz background.jpg', 'quiz background.png']:
        if os.path.exists(ext):
            bg_file = ext
            break
    
    if bg_file:
        import base64
        with open(bg_file, "rb") as f:
            bg_image = base64.b64encode(f.read()).decode()
        if bg_file.endswith('.webp'):
            bg_url = f"data:image/webp;base64,{bg_image}"
        elif bg_file.endswith('.png'):
            bg_url = f"data:image/png;base64,{bg_image}"
        else:
            bg_url = f"data:image/jpeg;base64,{bg_image}"
    else:
        bg_url = ""
    
    # Custom CSS for split screen design
    st.markdown(f"""
        <style>
        .stApp {{
            background: white;
        }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        .block-container {{
            padding: 0 !important;
            max-width: 100% !important;
        }}
        
        /* Split screen container */
        .split-container {{
            display: flex;
            height: 100vh;
            width: 100%;
        }}
        
        /* Left side - Background image */
        .left-side {{
            flex: 1;
            background-image: url('{bg_url}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        
        /* Right side - Login form */
        .right-side {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: #f8f9fa;
            padding: 40px;
        }}
        
        .login-title {{
            text-align: center;
            color: #333;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 25px;
            margin-top: 20px;
        }}
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
            justify-content: center;
            margin-bottom: 30px;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 45px;
            background-color: #e8e8e8;
            border-radius: 10px;
            padding: 0 35px;
            font-weight: 600;
            color: #666;
            font-size: 14px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #4a5568 !important;
            color: white !important;
        }}
        
        /* Tab content alignment */
        .stTabs [data-baseweb="tab-panel"] {{
            padding-top: 20px;
        }}
        
        div[data-testid="stForm"] {{
            border: none;
            padding: 0;
            width: 100%;
            max-width: 400px;
            margin: 0 auto;
        }}
        
        .stTextInput > div > div > input {{
            border-radius: 10px;
            border: 1px solid #d0d0d0;
            padding: 14px;
            font-size: 15px;
            background: white;
        }}
        .stTextInput > label {{
            font-size: 14px;
            font-weight: 500;
            color: #555;
        }}
        
        .stButton > button {{
            width: 100%;
            background-color: #2d3748;
            color: white;
            border-radius: 10px;
            padding: 14px;
            font-weight: 600;
            border: none;
            margin-top: 25px;
            font-size: 15px;
        }}
        .stButton > button:hover {{
            background-color: #1a202c;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # Create split screen layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Left side - show background image
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if bg_file and os.path.exists(bg_file):
            st.image(bg_file)
        else:
            st.markdown("""
                <div style='height: 100vh; background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); 
                display: flex; align-items: center; justify-content: center;'>
                    <h1 style='color: white; font-size: 48px;'>QUIZ</h1>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Logo at top center
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("Logo Full.png"):
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                st.image("Logo Full.png", width=250)
        
        st.markdown('<div class="login-title">Sign In With</div>', unsafe_allow_html=True)
        
        # Login form
        tab1, tab2 = st.tabs(["ADMIN", "STUDENT"])
        
        with tab1:
            with st.form("admin_login_form"):
                st.text_input("Username", key="admin_username")
                st.text_input("Password", type="password", key="admin_password")
                admin_submit = st.form_submit_button("Sign In")
                
                if admin_submit:
                    admin_email = st.session_state.admin_username
                    admin_pass = st.session_state.admin_password
                    if admin_email == ADMIN_EMAIL and admin_pass == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.session_state.user_email = ADMIN_EMAIL
                        st.success("Admin login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid admin credentials")
        
        with tab2:
            with st.form("student_login_form"):
                st.text_input("Username", key="student_username")
                st.text_input("Password", type="password", key="student_password")
                submit = st.form_submit_button("Sign In")
                
                if submit:
                    email = st.session_state.student_username
                    password = st.session_state.student_password
                    if email in st.session_state.authorized_emails and password:
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")

def quiz_page():
    if st.session_state.user_email == ADMIN_EMAIL:
        st.title("📝 Quiz Application - Admin")
        st.write(f"Welcome, {st.session_state.user_email}!")
        
        st.header("Generate Custom Quiz")
        api_key = st.text_input("Enter Google AI Studio API Key (optional):", type="password", key="admin_api_key")
        transcript = st.text_area("Paste transcript to generate custom quiz:", height=150)
        
        if st.button("Generate Custom Quiz") and api_key and transcript:
            with st.spinner("Backing up current results..."):
                if backup_current_results():
                    with st.spinner("Generating quiz..."):
                        custom_quiz = generate_quiz_with_gemini(transcript, api_key)
                        if custom_quiz:
                            if save_current_quiz(custom_quiz['questions']):
                                st.success("Custom quiz generated! Previous results backed up.")
                                st.rerun()
                            else:
                                st.error("Failed to save quiz")
                else:
                    st.error("Failed to backup results")
        
        st.divider()
        st.info("💡 After generating a custom quiz, students will see the new questions when they take the quiz.")
    else:
        st.title("📝 Quiz")
        st.write(f"Welcome, {st.session_state.user_email}!")
    
    current_quiz = load_current_quiz()
    st.header("Take Quiz")
    
    # Initialize session state for quiz results
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False
    if 'quiz_score' not in st.session_state:
        st.session_state.quiz_score = 0
    if 'quiz_wrong_questions' not in st.session_state:
        st.session_state.quiz_wrong_questions = []
    
    # Reset results when starting a new quiz
    if st.button("🔄 Start New Quiz"):
        st.session_state.show_results = False
        st.session_state.quiz_score = 0
        st.session_state.quiz_wrong_questions = []
        st.rerun()
    
    # Only show quiz form if results are not being displayed
    if not st.session_state.show_results:
        with st.form("quiz_form"):
            user_answers = {}
            
            for i, q in enumerate(current_quiz):
                st.subheader(f"Q{i+1}")
                st.write(q['question'])
                user_answers[i] = st.radio(f"Select answer for Q{i+1}:", q['options'], key=f"q_{i}")
            
            submit_quiz = st.form_submit_button("Submit Quiz")
            
            if submit_quiz:
                score = 0
                results = []
                wrong_questions = []
                
                for i, q in enumerate(current_quiz):
                    correct = q['correct']
                    user_choice = user_answers[i][0]
                    
                    if user_choice == correct:
                        score += 1
                        results.append("✅")
                    else:
                        results.append(f"❌ (Correct: {correct})")
                        wrong_questions.append({
                            'question': q['question'],
                            'user_answer': user_choice,
                            'correct_answer': correct,
                            'options': q['options'],
                            'explanation': q.get('explanation', 'No explanation available.')
                        })
                
                percentage = (score / len(current_quiz)) * 100
                pass_fail = "Pass" if percentage >= 70 else "Fail"
                
                # Store in session state
                st.session_state.show_results = True
                st.session_state.quiz_score = score
                st.session_state.quiz_percentage = percentage
                st.session_state.quiz_pass_fail = pass_fail
                st.session_state.quiz_results = results
                st.session_state.quiz_wrong_questions = wrong_questions
                st.session_state.quiz_total = len(current_quiz)
                
                if save_quiz_result(st.session_state.user_email, score, pass_fail):
                    st.success("Results saved successfully!")
                st.rerun()
    
    # Show results outside the form
    if st.session_state.show_results:
        st.header("🎯 Results")
        st.write(f"**Score: {st.session_state.quiz_score}/{st.session_state.quiz_total} ({st.session_state.quiz_percentage:.1f}%)**")
        st.write(f"**Status: {st.session_state.quiz_pass_fail}**")
        
        for i, result in enumerate(st.session_state.quiz_results):
            st.write(f"Q{i+1}: {result}")
        
        # Show AI explanation for wrong answers (only for students)
        if st.session_state.user_email != ADMIN_EMAIL and st.session_state.quiz_wrong_questions:
            st.divider()
            st.subheader("🤖 AI Tutor - Learn from Your Mistakes")
            
            # Show explanations from quiz data
            for i, wrong_q in enumerate(st.session_state.quiz_wrong_questions):
                with st.expander(f"Question {i+1}: {wrong_q['question'][:50]}..."):
                    st.write(f"**Your Answer:** {wrong_q['user_answer']}")
                    st.write(f"**Correct Answer:** {wrong_q['correct_answer']}")
                    st.write(f"**Explanation:**")
                    explanation = wrong_q.get('explanation', 'No explanation available for this question.')
                    st.info(explanation)

def report_page():
    st.header("📈 Quiz Reports")
    
    history = load_quiz_history()
    current_results = load_quiz_results()
    
    # Merge current results into history for display
    display_history = history.copy()
    for result in current_results:
        email = result['Email']
        if email not in display_history:
            display_history[email] = []
        # Add current result if not already in history
        display_history[email].append(result)
    
    if st.session_state.user_email == ADMIN_EMAIL:
        # Admin sees all students
        students = [e for e in st.session_state.authorized_emails if e != ADMIN_EMAIL]
        if students:
            selected_student = st.selectbox("Select Student", students)
            email_to_show = selected_student
        else:
            st.warning("No students found. Add students in the 'Manage Students' tab.")
            return
    else:
        # Student sees only their own
        email_to_show = st.session_state.user_email
    
    if email_to_show in display_history and display_history[email_to_show]:
        user_history = display_history[email_to_show]
        
        st.subheader(f"Report for: {email_to_show}")
        st.metric("Total Quizzes Completed", len(user_history))
        
        # Create table data
        quiz_names = [f"Quiz {i+1}" for i in range(len(user_history))]
        dates = [r['Timestamp'].split()[0] for r in user_history]
        scores = [int(r.get('Scored', 0)) for r in user_history]
        totals = [15] * len(user_history)
        averages = [f"{(s/15*100):.1f}%" for s in scores]
        
        report_df = pd.DataFrame({
            'Quiz': quiz_names,
            'Date': dates,
            'Score': scores,
            'From': totals,
            'Average': averages,
            'Status': [r['Pass_Fail'] for r in user_history]
        })
        
        st.dataframe(report_df, width='stretch')
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Score", f"{sum(scores)/len(scores):.1f}/15")
        with col2:
            st.metric("Pass Rate", f"{len([r for r in user_history if r['Pass_Fail']=='Pass'])/len(user_history)*100:.0f}%")
        with col3:
            st.metric("Best Score", f"{max(scores)}/15")
    else:
        st.info(f"No quiz history found for {email_to_show}")

def attendance_page():
    """Attendance tracking page for students and admin"""
    st.header("📅 Attendance Report")
    
    # Load Zoom credentials from Streamlit secrets only (like admin credentials)
    zoom_account_id = None
    zoom_client_id = None
    zoom_client_secret = None
    
    try:
        zoom_account_id = st.secrets.get("ZOOM_ACCOUNT_ID")
        zoom_client_id = st.secrets.get("ZOOM_CLIENT_ID")
        zoom_client_secret = st.secrets.get("ZOOM_CLIENT_SECRET")
    except Exception as e:
        pass
    
    if not all([zoom_account_id, zoom_client_id, zoom_client_secret]):
        st.error("⚠️ Zoom API credentials not configured in Streamlit Cloud Secrets")
        st.info("""
**📝 To configure Zoom credentials:**

1. Go to your Streamlit Cloud dashboard
2. Click on your app → **Settings** → **Secrets**
3. Add these three credentials (same place where you added ADMIN_EMAIL and ADMIN_PASSWORD):

```toml
ZOOM_ACCOUNT_ID = "your_zoom_account_id"
ZOOM_CLIENT_ID = "your_zoom_client_id"
ZOOM_CLIENT_SECRET = "your_zoom_client_secret"
```

4. Save and reboot the app
        """)
        
        st.warning("🔒 **Security Note**: Never commit these credentials to Git. Keep them only in Streamlit Cloud Secrets.")
        return
    
    # Date range: Jan 24, 2026 to today
    start_date = datetime(2026, 1, 24)
    end_date = datetime.now()
    
    st.info(f"📊 Tracking attendance from **{start_date.strftime('%B %d, %Y')}** to **{end_date.strftime('%B %d, %Y')}**")
    
    # Check cache
    cache = load_attendance_cache()
    should_refresh = False
    
    if cache and 'last_updated' in cache:
        last_updated = cache['last_updated']
        hours_since_update = (datetime.now() - last_updated).total_seconds() / 3600
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"📍 Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S IST')} ({hours_since_update:.1f} hours ago)")
        with col2:
            if st.button("🔄 Refresh Data", type="secondary"):
                should_refresh = True
    else:
        should_refresh = True
        st.warning("No cached data found. Fetching attendance data...")
    
    # Fetch or use cached data
    if should_refresh or not cache:
        progress_placeholder = st.empty()
        
        def update_progress(message):
            progress_placeholder.info(f"⏳ {message}")
        
        with st.spinner("Fetching attendance data from Zoom..."):
            attendance_data, error = fetch_attendance_data(
                zoom_account_id, 
                zoom_client_id, 
                zoom_client_secret,
                start_date,
                end_date,
                update_progress
            )
        
        progress_placeholder.empty()
        
        if error:
            st.error(f"❌ {error}")
            return
        
        if attendance_data:
            # Convert defaultdict to regular dict for JSON serialization
            serializable_data = {}
            for date, emails in attendance_data.items():
                serializable_data[date] = {}
                for email, info in emails.items():
                    serializable_data[date][email] = {
                        'present': info['present'],
                        'duration': info['duration'],
                        'join_time': info['join_time'].isoformat() if info['join_time'] else None,
                        'leave_time': info['leave_time'].isoformat() if info['leave_time'] else None
                    }
            
            save_attendance_cache(serializable_data)
            st.success("✅ Attendance data fetched and cached successfully!")
            cache = {'data': serializable_data, 'last_updated': datetime.now()}
    
    if not cache or 'data' not in cache:
        st.warning("No attendance data available.")
        return
    
    attendance_data = cache['data']
    
    # Determine which email to show
    if st.session_state.user_email == ADMIN_EMAIL:
        # Admin sees dropdown to select student
        students = [e for e in st.session_state.authorized_emails if e != ADMIN_EMAIL]
        if students:
            email_to_show = st.selectbox("Select Student", students)
        else:
            st.warning("No students found. Add students in the 'Manage Students' tab.")
            return
    else:
        # Student sees only their own
        email_to_show = st.session_state.user_email
    
    st.subheader(f"📊 Attendance for: {email_to_show}")
    
    # Prepare attendance report
    attendance_records = []
    all_dates = sorted(attendance_data.keys())
    
    total_present = 0
    total_duration_seconds = 0
    
    for date in all_dates:
        date_data = attendance_data[date]
        
        if email_to_show.lower() in date_data:
            student_data = date_data[email_to_show.lower()]
            status = "Present" if student_data['present'] else "Absent"
            duration_seconds = student_data['duration']
            duration_minutes = duration_seconds // 60
            
            # Parse join/leave times
            join_time = None
            leave_time = None
            session_time_minutes = 0
            
            if student_data.get('join_time'):
                try:
                    join_time = datetime.fromisoformat(student_data['join_time'])
                except:
                    pass
            
            if student_data.get('leave_time'):
                try:
                    leave_time = datetime.fromisoformat(student_data['leave_time'])
                except:
                    pass
            
            if join_time and leave_time:
                session_time_minutes = int((leave_time - join_time).total_seconds() // 60)
            
            attendance_records.append({
                'Date': date,
                'Status': status,
                'Active Time (min)': duration_minutes,
                'Session Time (min)': session_time_minutes,
                'Join Time': join_time.strftime('%H:%M:%S') if join_time else 'N/A',
                'Leave Time': leave_time.strftime('%H:%M:%S') if leave_time else 'N/A'
            })
            
            if status == "Present":
                total_present += 1
                total_duration_seconds += duration_seconds
        else:
            # No record for this date = Absent
            attendance_records.append({
                'Date': date,
                'Status': 'Absent',
                'Active Time (min)': 0,
                'Session Time (min)': 0,
                'Join Time': 'N/A',
                'Leave Time': 'N/A'
            })
    
    if not attendance_records:
        st.info("No attendance records found for this student.")
        return
    
    # Display metrics
    total_days = len(all_dates)
    attendance_rate = (total_present / total_days * 100) if total_days > 0 else 0
    avg_duration = (total_duration_seconds // 60) // total_present if total_present > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Total Days", total_days)
    with col2:
        st.metric("✅ Days Present", total_present)
    with col3:
        st.metric("📊 Attendance Rate", f"{attendance_rate:.1f}%")
    with col4:
        st.metric("⏱️ Avg Active Time", f"{avg_duration} min")
    
    # Display table
    df = pd.DataFrame(attendance_records)
    
    # Style the dataframe
    def highlight_status(row):
        if row['Status'] == 'Present':
            return ['background-color: #d4edda'] * len(row)
        else:
            return ['background-color: #f8d7da'] * len(row)
    
    styled_df = df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_df, width='stretch', height=400)
    
    # Download CSV
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Download Attendance CSV",
        data=csv,
        file_name=f"attendance_{email_to_show.replace('@', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def admin_dashboard():
    tab1, tab2 = st.tabs(["📊 Student Status", "👥 Manage Students"])
    
    with tab1:
        st.header("👨💼 Admin Dashboard")
        st.subheader("📊 Student Status Grid")
        
        get_quiz_data.clear()
        results_df = get_quiz_data()
        
        all_students = [email for email in st.session_state.authorized_emails if email != ADMIN_EMAIL]
        
        grid_data = []
        for email in all_students:
            student_result = results_df[results_df['Email'] == email] if not results_df.empty else pd.DataFrame()
            
            if not student_result.empty:
                row = student_result.iloc[-1]
                # Handle both old and new column names
                score = row.get('Scored') if 'Scored' in row.index else row.get('Quiz_Score', 0)
                attempt_count = int(row.get('Attempt_Count', 1)) if 'Attempt_Count' in row.index else 1
                grid_data.append({
                    'Email': email,
                    'Status': '✅ Completed',
                    'Score': score,
                    'Attempt_Count': attempt_count,
                    'Pass_Fail': row['Pass_Fail'],
                    'Timestamp': row['Timestamp']
                })
            else:
                grid_data.append({
                    'Email': email,
                    'Status': '❌ Not Completed',
                    'Score': 0,
                    'Attempt_Count': 0,
                    'Pass_Fail': 'Not Completed',
                    'Timestamp': '-'
                })
        
        grid_df = pd.DataFrame(grid_data)
        
        # Ensure proper data types for Arrow compatibility
        grid_df['Score'] = grid_df['Score'].astype(int)
        grid_df['Attempt_Count'] = grid_df['Attempt_Count'].astype(int)
        
        def highlight_status(row):
            if row['Status'] == '✅ Completed':
                if row['Pass_Fail'] == 'Pass':
                    return ['background-color: #d4edda'] * len(row)
                else:
                    return ['background-color: #f8d7da'] * len(row)
            else:
                return ['background-color: #fff3cd'] * len(row)
        
        styled_grid = grid_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_grid, width='stretch')
        
        completed = len([s for s in grid_data if s['Status'] == '✅ Completed'])
        pending = len(all_students) - completed
        pass_count = len([s for s in grid_data if s['Pass_Fail'] == 'Pass'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Students", len(all_students))
        with col2:
            st.metric("Completed", completed)
        with col3:
            st.metric("Pending", pending)
        with col4:
            st.metric("Pass Rate", f"{(pass_count/completed*100):.1f}%" if completed > 0 else "0%")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", key="refresh_status"):
                st.rerun()
        
        with col2:
            # Create Excel export with proper data types
            export_data = []
            for email in all_students:
                student_result = results_df[results_df['Email'] == email] if not results_df.empty else pd.DataFrame()
                if not student_result.empty:
                    row = student_result.iloc[-1]
                    # Handle both old and new column names
                    if 'Scored' in row.index:
                        score = int(row['Scored']) if pd.notna(row['Scored']) else 0
                    else:
                        score_val = row.get('Quiz_Score', 0)
                        if isinstance(score_val, str) and '/' in score_val:
                            score = int(score_val.split('/')[0])
                        else:
                            score = int(score_val) if score_val else 0
                    
                    attempt_count = int(row.get('Attempt_Count', 1)) if 'Attempt_Count' in row.index else 1
                    
                    # Timestamp is already stored in IST
                    timestamp_str = str(row['Timestamp'])
                    timestamp_ist = f"{timestamp_str} IST"
                    
                    export_data.append({
                        'Email': email,
                        'Score(15)': score,
                        'Attempt_Count': attempt_count,
                        'Pass_Fail': str(row['Pass_Fail']),
                        'Timestamp': timestamp_ist
                    })
                else:
                    export_data.append({
                        'Email': email,
                        'Score(15)': 0,
                        'Attempt_Count': 0,
                        'Pass_Fail': 'Not Completed',
                        'Timestamp': 'Not Completed'
                    })
            
            export_df = pd.DataFrame(export_data)
            
            # Create Excel file in memory with proper formatting
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.utils import get_column_letter
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Quiz Results')
                workbook = writer.book
                worksheet = writer.sheets['Quiz Results']
                
                # Format Score column as integer
                for row_num, row in enumerate(worksheet.iter_rows(min_row=2, max_row=len(export_df)+1, min_col=3, max_col=3), 2):
                    for cell in row:
                        cell.number_format = '0'  # Integer format
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = get_column_letter(column[0].column)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
            
            output.seek(0)
            
            st.download_button(
                label="📥 Download Report Excel",
                data=output,
                file_name=f"student_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_status"
            )
        
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    with tab2:
        st.header("👥 Manage Authorized Students")
        
        st.write(f"**Total Students: {len([e for e in st.session_state.authorized_emails if e != ADMIN_EMAIL])}**")
        
        # Upload text file with emails
        st.subheader("📤 Upload Student Emails")
        uploaded_file = st.file_uploader("Upload text file with student emails (one per line)", type=['txt'], key="upload_emails_file")
        
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode('utf-8')
                emails = [email.strip() for email in content.split('\n') if email.strip() and '@' in email]
                
                if emails:
                    # Add admin email if not present
                    if ADMIN_EMAIL not in emails:
                        emails.insert(0, ADMIN_EMAIL)
                    
                    st.session_state.authorized_emails = emails
                    if save_authorized_emails(st.session_state.authorized_emails):
                        st.success(f"Uploaded {len(emails)-1} student emails successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save emails")
                else:
                    st.error("No valid emails found in file")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        st.divider()
        
        with st.form("add_student_form"):
            new_email = st.text_input("Add New Student Email")
            add_button = st.form_submit_button("➕ Add Student")
            
            if add_button and new_email:
                if new_email in st.session_state.authorized_emails:
                    st.error("Email already exists!")
                elif '@' not in new_email:
                    st.error("Invalid email format!")
                else:
                    st.session_state.authorized_emails.append(new_email)
                    if save_authorized_emails(st.session_state.authorized_emails):
                        st.success(f"Added {new_email} successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save email")
        
        st.divider()
        st.subheader("Current Students")
        
        students = [email for email in st.session_state.authorized_emails if email != ADMIN_EMAIL]
        for idx, email in enumerate(students):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(email)
            with col2:
                if st.button("🗑️", key=f"del_{idx}_{email.replace('@', '_').replace('.', '_')}"):
                    st.session_state.authorized_emails.remove(email)
                    if save_authorized_emails(st.session_state.authorized_emails):
                        st.success(f"Removed {email}")
                        st.rerun()
                    else:
                        st.error("Failed to remove email")

def main():
    # Page config with logo
    st.set_page_config(
        page_title="Quiz Application",
        page_icon="📝",
        layout="wide"
    )
    
    # Initialize database if available
    if DATABASE_AVAILABLE and get_database_url():
        init_database()
    
    # Custom CSS for logo in top left
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {
            background-image: url('https://via.placeholder.com/150x50/4CAF50/FFFFFF?text=QUIZ+APP');
            background-repeat: no-repeat;
            background-position: 20px 20px;
            padding-top: 80px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'quiz_results' not in st.session_state or not st.session_state.quiz_results:
        st.session_state.quiz_results = load_quiz_results()
    
    # Load authorized emails from file if exists, otherwise use default list
    saved_emails = load_authorized_emails()
    if saved_emails:
        st.session_state.authorized_emails = saved_emails
    elif 'authorized_emails' in st.session_state:
        # Save current list to file for first time
        save_authorized_emails(st.session_state.authorized_emails)
    
    if st.session_state.logged_in:
        # Top bar with logo and user info
        col1, col2, col3 = st.columns([1, 5, 1])
        with col1:
            if os.path.exists("Logo Full.png"):
                st.image("Logo Full.png", width=150)
        with col3:
            st.markdown(f"**{st.session_state.user_email}**")
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user_email = None
                st.rerun()
        
        st.divider()
        
        if st.session_state.user_email == ADMIN_EMAIL:
            tab1, tab2, tab3, tab4 = st.tabs(["📝 Quiz Generation", "👨💼 Admin Dashboard", "📈 Reports", "📅 Attendance"])
            with tab1:
                quiz_page()
            with tab2:
                admin_dashboard()
            with tab3:
                report_page()
            with tab4:
                attendance_page()
        else:
            tab1, tab2, tab3 = st.tabs(["📝 Quiz", "📈 My Report", "📅 My Attendance"])
            with tab1:
                quiz_page()
            with tab2:
                report_page()
            with tab3:
                attendance_page()
    else:
        login_page()

if __name__ == "__main__":
    main()
