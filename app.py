import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
import os
import time

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

def load_authorized_emails():
    if os.path.exists(AUTHORIZED_EMAILS_FILE):
        try:
            with open(AUTHORIZED_EMAILS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_authorized_emails(emails):
    try:
        with open(AUTHORIZED_EMAILS_FILE, 'w') as f:
            json.dump(emails, f)
        return True
    except:
        return False

def load_current_quiz():
    if os.path.exists(QUIZ_FILE):
        try:
            with open(QUIZ_FILE, 'r') as f:
                return json.load(f)
        except:
            return QUIZ_QUESTIONS
    return QUIZ_QUESTIONS

def save_current_quiz(quiz_questions):
    try:
        with open(QUIZ_FILE, 'w') as f:
            json.dump(quiz_questions, f)
        return True
    except:
        return False

def load_quiz_results():
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_quiz_results(results):
    try:
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f)
        return True
    except:
        return False

@st.cache_data
def get_quiz_data():
    results = load_quiz_results()
    return pd.DataFrame(results)

def save_quiz_result(email, score, pass_fail):
    try:
        results = load_quiz_results()
        existing_index = None
        for i, result in enumerate(results):
            if result.get("Email") == email:
                existing_index = i
                break
        
        new_result = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Email": email,
            "Quiz_Score": score,
            "Pass_Fail": pass_fail
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

    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        try:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].strip()
            return json.loads(content)
        except Exception as e:
            st.error(f"Failed to parse quiz JSON: {e}")
            return None
    else:
        st.error(f"Quiz generation failed: {response.text}")
        return None

def login_page():
    st.title("🔐 Quiz Login")
    
    # Admin login
    st.subheader("Admin Login")
    with st.form("admin_login_form"):
        admin_email = st.text_input("Admin Email")
        admin_pass = st.text_input("Admin Password", type="password")
        admin_submit = st.form_submit_button("🔑 Admin Login")
        
        if admin_submit:
            if admin_email == ADMIN_EMAIL and admin_pass == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.user_email = ADMIN_EMAIL
                st.success("Admin login successful!")
                st.rerun()
            else:
                st.error("Invalid admin credentials")
    
    st.divider()
    
    # Student login
    st.subheader("Student Login")
    with st.form("student_login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
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
        api_key = st.text_input("Enter Google AI Studio API Key (optional):", type="password")
        transcript = st.text_area("Paste transcript to generate custom quiz:", height=150)
        
        if st.button("Generate Custom Quiz") and api_key and transcript:
            with st.spinner("Generating quiz..."):
                custom_quiz = generate_quiz_with_gemini(transcript, api_key)
                if custom_quiz:
                    if save_current_quiz(custom_quiz['questions']):
                        st.success("Custom quiz generated! All students will now see this quiz.")
                        st.rerun()
                    else:
                        st.error("Failed to save quiz")
        
        st.divider()
        st.info("💡 After generating a custom quiz, students will see the new questions when they take the quiz.")
    else:
        st.title("📝 Quiz")
        st.write(f"Welcome, {st.session_state.user_email}!")
    
    current_quiz = load_current_quiz()
    st.header("Take Quiz")
    
    with st.form("quiz_form"):
        user_answers = {}
        
        for i, q in enumerate(current_quiz):
            st.subheader(f"Q{i+1} ({q['difficulty'].title()})")
            st.write(q['question'])
            user_answers[i] = st.radio(f"Select answer for Q{i+1}:", q['options'], key=f"q_{i}")
        
        submit_quiz = st.form_submit_button("Submit Quiz")
        
        if submit_quiz:
            score = 0
            results = []
            
            for i, q in enumerate(current_quiz):
                correct = q['correct']
                user_choice = user_answers[i][0]
                
                if user_choice == correct:
                    score += 1
                    results.append("✅")
                else:
                    results.append(f"❌ (Correct: {correct})")
            
            percentage = (score / len(current_quiz)) * 100
            pass_fail = "Pass" if percentage >= 70 else "Fail"
            
            st.header("🎯 Results")
            st.write(f"**Score: {score}/{len(current_quiz)} ({percentage:.1f}%)**")
            st.write(f"**Status: {pass_fail}**")
            
            for i, result in enumerate(results):
                st.write(f"Q{i+1}: {result}")
            
            if save_quiz_result(st.session_state.user_email, f"{score}/{len(current_quiz)}", pass_fail):
                st.success("Results saved successfully!")

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
                grid_data.append({
                    'Email': email,
                    'Status': '✅ Completed',
                    'Score': row['Quiz_Score'],
                    'Pass_Fail': row['Pass_Fail'],
                    'Timestamp': row['Timestamp']
                })
            else:
                grid_data.append({
                    'Email': email,
                    'Status': '❌ Not Completed',
                    'Score': '-',
                    'Pass_Fail': '-',
                    'Timestamp': '-'
                })
        
        grid_df = pd.DataFrame(grid_data)
        
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
            # Create CSV - extract numeric score from Quiz_Score field
            csv_lines = ['Email,Score,Pass_Fail,Timestamp']
            
            for email in all_students:
                student_result = results_df[results_df['Email'] == email] if not results_df.empty else pd.DataFrame()
                if not student_result.empty:
                    row = student_result.iloc[-1]
                    quiz_score_raw = str(row['Quiz_Score'])
                    # Extract just the number before the slash (e.g., "7" from "7/10")
                    if '/' in quiz_score_raw:
                        score = quiz_score_raw.split('/')[0]
                    else:
                        score = quiz_score_raw
                    pass_fail = str(row['Pass_Fail'])
                    timestamp = str(row['Timestamp'])
                    csv_lines.append(f'{email},{score},{pass_fail},{timestamp}')
                else:
                    csv_lines.append(f'{email},0,Not Completed,Not Completed')
            
            csv = '\n'.join(csv_lines)
            st.download_button(
                label="📥 Download Report CSV",
                data=csv,
                file_name=f"student_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv_status"
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
        with col2:
            st.markdown(f"### 📝 Quiz Application")
        with col3:
            st.markdown(f"**{st.session_state.user_email}**")
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user_email = None
                st.rerun()
        
        st.divider()
        
        if st.session_state.user_email == ADMIN_EMAIL:
            tab1, tab2 = st.tabs(["📝 Quiz Generation", "👨💼 Admin Dashboard"])
            with tab1:
                quiz_page()
            with tab2:
                admin_dashboard()
        else:
            quiz_page()
    else:
        # Show logo on login page
        if os.path.exists("Logo Full.png"):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image("Logo Full.png", width=300)
        login_page()

if __name__ == "__main__":
    main()
