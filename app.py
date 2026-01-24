import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

# Configuration
if 'authorized_emails' not in st.session_state:
    st.session_state.authorized_emails = [
        "admin@example.com",
        "anuradharandive04@gmail.com",
        "shafeekansari2002@gmail.com",
        "kotireddynarendrareddy@gmail.com",
        "cheeravinaykumar94@gmail.com",
        "abinash.kar.november18@gmail.com",
        "ashfakhshaikh7@gmail.com",
        "vattesandeep28@gmail.com",
        "akhima.shaik2003@gmail.com",
        "shivakumar0752@gmail.com",
        "praveenbhatlu7@gmail.com",
        "apurvachavan306@gmail.com",
        "rakeshpandeeti@gmail.com",
        "itsmrmanu@gmail.com",
        "bhanusri1177@gmail.com",
        "mkrout997@gmail.com",
        "sowmyavreddy12@gmail.com",
        "chidrawarsanjana9@gmail.com",
        "mayuri.shah715@gmail.com",
        "prasanthchowdary789@gmail.com",
        "sanjaikumar1202@gmail.com",
        "shreyas.phansalkar2017@gmail.com",
        "hksamreen0@gmail.com",
        "sahilmutha230901@gmail.com",
        "ankitamarathe25@gmail.com",
        "tsananse0298@gmail.com",
        "umakondaru@gmail.com",
        "hemigipson@gmail.com"
    ]

ADMIN_EMAIL = "admin@example.com"

# In-memory storage (replace with Google Sheets in production)
if 'quiz_results' not in st.session_state:
    st.session_state.quiz_results = []

# Sample quiz questions
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

# Global quiz storage - shared across all users using file system
import os
QUIZ_FILE = "current_quiz.json"
RESULTS_FILE = "quiz_results.json"

def load_current_quiz():
    """Load current quiz from file or return default"""
    if os.path.exists(QUIZ_FILE):
        try:
            with open(QUIZ_FILE, 'r') as f:
                return json.load(f)
        except:
            return QUIZ_QUESTIONS
    return QUIZ_QUESTIONS

def save_current_quiz(quiz_questions):
    """Save current quiz to file"""
    try:
        with open(QUIZ_FILE, 'w') as f:
            json.dump(quiz_questions, f)
        return True
    except:
        return False

def load_quiz_results():
    """Load quiz results from file"""
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_quiz_results(results):
    """Save quiz results to file"""
    try:
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f)
        return True
    except:
        return False

@st.cache_data
def get_quiz_data():
    """Get quiz results data from file"""
    results = load_quiz_results()
    return pd.DataFrame(results)

def save_quiz_result(email, score, pass_fail):
    """Save quiz result to file"""
    try:
        # Load existing results
        results = load_quiz_results()
        
        # Check if user already submitted
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
            # Update existing result
            results[existing_index] = new_result
        else:
            # Add new result
            results.append(new_result)
        
        # Save to file
        if save_quiz_results(results):
            # Also update session state for immediate UI update
            st.session_state.quiz_results = results
            return True
        return False
    except Exception as e:
        st.error(f"Error saving result: {e}")
        return False

def generate_quiz_with_gemini(transcript, api_key):
    """Generate quiz using Google Gemini API"""
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

    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        try:
            content = response.json()['candidates'][0]['content']['parts'][0]['text']
            # Clean JSON if it has markdown formatting
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
    """Display login page"""
    st.title("🔐 Quiz Login")
    
    with st.form("login_form"):
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
    """Display quiz page"""
    # Check if user is admin
    if st.session_state.user_email == ADMIN_EMAIL:
        st.title("📝 Quiz Application - Admin")
        st.write(f"Welcome, {st.session_state.user_email}!")
        
        # Option to generate quiz from transcript (Admin only)
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
    
    # Load current quiz (shared across all users)
    current_quiz = load_current_quiz()
    
    st.header("Take Quiz")
    
    with st.form("quiz_form"):
        user_answers = {}
        
        for i, q in enumerate(current_quiz):
            st.subheader(f"Q{i+1} ({q['difficulty'].title()})")
            st.write(q['question'])
            
            user_answers[i] = st.radio(
                f"Select answer for Q{i+1}:",
                q['options'],
                key=f"q_{i}"
            )
        
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
            
            # Save results
            if save_quiz_result(st.session_state.user_email, f"{score}/{len(current_quiz)}", pass_fail):
                st.success("Results saved successfully!")

def admin_dashboard():
    """Display admin dashboard"""
    st.header("👨💼 Admin Dashboard")
    
    # Auto-refresh every 5 seconds
    import time
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Student Status Grid
    st.subheader("📊 Student Status Grid (Auto-refreshing)")
    
    # Get quiz results (clear cache to get fresh data)
    get_quiz_data.clear()
    results_df = get_quiz_data()
    
    # Create complete student grid
    all_students = [email for email in st.session_state.authorized_emails if email != ADMIN_EMAIL]
    
    grid_data = []
    for email in all_students:
        # Check if student has completed quiz
        student_result = results_df[results_df['Email'] == email] if not results_df.empty else pd.DataFrame()
        
        if not student_result.empty:
            # Student completed quiz
            row = student_result.iloc[-1]  # Get latest attempt
            grid_data.append({
                'Email': email,
                'Status': '✅ Completed',
                'Score': row['Quiz_Score'],
                'Pass_Fail': row['Pass_Fail'],
                'Timestamp': row['Timestamp']
            })
        else:
            # Student hasn't completed quiz
            grid_data.append({
                'Email': email,
                'Status': '❌ Not Completed',
                'Score': '-',
                'Pass_Fail': '-',
                'Timestamp': '-'
            })
    
    # Create and display grid
    grid_df = pd.DataFrame(grid_data)
    
    # Color coding function
    def highlight_status(row):
        if row['Status'] == '✅ Completed':
            if row['Pass_Fail'] == 'Pass':
                return ['background-color: #d4edda'] * len(row)  # Light green
            else:
                return ['background-color: #f8d7da'] * len(row)  # Light red
        else:
            return ['background-color: #fff3cd'] * len(row)  # Light yellow
    
    styled_grid = grid_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_grid, width='stretch')
    
    # Summary stats
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
    
    # Auto-refresh and Download
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    
    with col2:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
        if auto_refresh:
            time.sleep(5)
            st.rerun()
    
    with col3:
        csv = grid_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Report CSV",
            data=csv,
            file_name=f"student_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Show last update time
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

def main():
    """Main application"""
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Load existing quiz results on startup
    if 'quiz_results' not in st.session_state or not st.session_state.quiz_results:
        st.session_state.quiz_results = load_quiz_results()
    
    # Sidebar
    if st.session_state.logged_in:
        st.sidebar.title("Navigation")
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = None
            st.rerun()
        
        # Admin mode
        if st.session_state.user_email == ADMIN_EMAIL:
            if st.sidebar.checkbox("Admin Mode"):
                admin_dashboard()
                return
    
    # Main content
    if not st.session_state.logged_in:
        login_page()
    else:
        quiz_page()

if __name__ == "__main__":
    main()Admin only)
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
    
    # Load current quiz (shared across all users)
    current_quiz = load_current_quiz()
    
    st.header("Take Quiz")
    
    with st.form("quiz_form"):
        user_answers = {}
        
        for i, q in enumerate(current_quiz):
            st.subheader(f"Q{i+1} ({q['difficulty'].title()})")
            st.write(q['question'])
            
            user_answers[i] = st.radio(
                f"Select answer for Q{i+1}:",
                q['options'],
                key=f"q_{i}"
            )
        
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
            
            # Save results
            if save_quiz_result(st.session_state.user_email, f"{score}/{len(current_quiz)}", pass_fail):
                st.success("Results saved successfully!")

def admin_dashboard():
    """Display admin dashboard"""
    st.header("👨💼 Admin Dashboard")
    
    # Auto-refresh every 5 seconds
    import time
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Student Status Grid
    st.subheader("📊 Student Status Grid (Auto-refreshing)")
    
    # Get quiz results (clear cache to get fresh data)
    get_quiz_data.clear()
    results_df = get_quiz_data()
    
    # Create complete student grid
    all_students = [email for email in st.session_state.authorized_emails if email != ADMIN_EMAIL]
    
    grid_data = []
    for email in all_students:
        # Check if student has completed quiz
        student_result = results_df[results_df['Email'] == email] if not results_df.empty else pd.DataFrame()
        
        if not student_result.empty:
            # Student completed quiz
            row = student_result.iloc[-1]  # Get latest attempt
            grid_data.append({
                'Email': email,
                'Status': '✅ Completed',
                'Score': row['Quiz_Score'],
                'Pass_Fail': row['Pass_Fail'],
                'Timestamp': row['Timestamp']
            })
        else:
            # Student hasn't completed quiz
            grid_data.append({
                'Email': email,
                'Status': '❌ Not Completed',
                'Score': '-',
                'Pass_Fail': '-',
                'Timestamp': '-'
            })
    
    # Create and display grid
    grid_df = pd.DataFrame(grid_data)
    
    # Color coding function
    def highlight_status(row):
        if row['Status'] == '✅ Completed':
            if row['Pass_Fail'] == 'Pass':
                return ['background-color: #d4edda'] * len(row)  # Light green
            else:
                return ['background-color: #f8d7da'] * len(row)  # Light red
        else:
            return ['background-color: #fff3cd'] * len(row)  # Light yellow
    
    styled_grid = grid_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_grid, use_container_width=True)
    
    # Summary stats
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
    
    # Auto-refresh and Download
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    
    with col2:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
        if auto_refresh:
            time.sleep(5)
            st.rerun()
    
    with col3:
        csv = grid_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Report CSV",
            data=csv,
            file_name=f"student_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Show last update time
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

def main():
    """Main application"""
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Sidebar
    if st.session_state.logged_in:
        st.sidebar.title("Navigation")
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = None
            st.rerun()
        
        # Admin mode
        if st.session_state.user_email == ADMIN_EMAIL:
            if st.sidebar.checkbox("Admin Mode"):
                admin_dashboard()
                return
    
    # Main content
    if not st.session_state.logged_in:
        login_page()
    else:
        quiz_page()

if __name__ == "__main__":
    main()r(f"Q{i+1} ({q['difficulty'].title()})")
            st.write(q['question'])
            
            user_answers[i] = st.radio(
                f"Select answer for Q{i+1}:",
                q['options'],
                key=f"q_{i}"
            )
        
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
            
            # Save results
            if save_quiz_result(st.session_state.user_email, f"{score}/{len(current_quiz)}", pass_fail):
                st.success("Results saved successfully!")

def admin_dashboard():
    """Display admin dashboard"""
    st.header("👨💼 Admin Dashboard")
    
    # Auto-refresh every 5 seconds
    import time
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Student Status Grid
    st.subheader("📊 Student Status Grid (Auto-refreshing)")
    
    # Get quiz results (clear cache to get fresh data)
    get_quiz_data.clear()
    results_df = get_quiz_data()
    
    # Create complete student grid
    all_students = [email for email in st.session_state.authorized_emails if email != ADMIN_EMAIL]
    
    grid_data = []
    for email in all_students:
        # Check if student has completed quiz
        student_result = results_df[results_df['Email'] == email] if not results_df.empty else pd.DataFrame()
        
        if not student_result.empty:
            # Student completed quiz
            row = student_result.iloc[-1]  # Get latest attempt
            grid_data.append({
                'Email': email,
                'Status': '✅ Completed',
                'Score': row['Quiz_Score'],
                'Pass_Fail': row['Pass_Fail'],
                'Timestamp': row['Timestamp']
            })
        else:
            # Student hasn't completed quiz
            grid_data.append({
                'Email': email,
                'Status': '❌ Not Completed',
                'Score': '-',
                'Pass_Fail': '-',
                'Timestamp': '-'
            })
    
    # Create and display grid
    grid_df = pd.DataFrame(grid_data)
    
    # Color coding function
    def highlight_status(row):
        if row['Status'] == '✅ Completed':
            if row['Pass_Fail'] == 'Pass':
                return ['background-color: #d4edda'] * len(row)  # Light green
            else:
                return ['background-color: #f8d7da'] * len(row)  # Light red
        else:
            return ['background-color: #fff3cd'] * len(row)  # Light yellow
    
    styled_grid = grid_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_grid, use_container_width=True)
    
    # Summary stats
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
    
    # Auto-refresh and Download
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    
    with col2:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
        if auto_refresh:
            time.sleep(5)
            st.rerun()
    
    with col3:
        csv = grid_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Report CSV",
            data=csv,
            file_name=f"student_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Show last update time
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

def main():
    """Main application"""
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Sidebar
    if st.session_state.logged_in:
        st.sidebar.title("Navigation")
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = None
            st.rerun()
        
        # Admin mode
        if st.session_state.user_email == ADMIN_EMAIL:
            if st.sidebar.checkbox("Admin Mode"):
                admin_dashboard()
                return
    
    # Main content
    if not st.session_state.logged_in:
        login_page()
    else:
        quiz_page()

if __name__ == "__main__":
    main()