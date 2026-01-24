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

@st.cache_data
def get_quiz_data():
    """Get quiz results data"""
    return pd.DataFrame(st.session_state.quiz_results)

def save_quiz_result(email, score, pass_fail):
    """Save quiz result"""
    try:
        result = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Email": email,
            "Quiz_Score": score,
            "Pass_Fail": pass_fail
        }
        st.session_state.quiz_results.append(result)
        return True
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
    
    # Real-time Quiz Monitoring
    st.subheader("📈 Live Quiz Results")
    
    df = get_quiz_data()
    
    if not df.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_students = len(st.session_state.authorized_emails) - 1  # Exclude admin
        attempted = len(df)
        pending = total_students - attempted
        pass_count = len(df[df['Pass_Fail'] == 'Pass']) if 'Pass_Fail' in df.columns else 0
        
        with col1:
            st.metric("👥 Total Students", total_students)
        with col2:
            st.metric("✅ Attempted", attempted, delta=f"{(attempted/total_students*100):.1f}%")
        with col3:
            st.metric("⏳ Pending", pending)
        with col4:
            st.metric("🎯 Pass Rate", f"{(pass_count/attempted*100):.1f}%" if attempted > 0 else "0%")
        
        # Live results table with color coding
        st.subheader("📋 Results Table")
        
        # Add status colors
        def highlight_results(row):
            if row['Pass_Fail'] == 'Pass':
                return ['background-color: #d4edda'] * len(row)
            else:
                return ['background-color: #f8d7da'] * len(row)
        
        styled_df = df.style.apply(highlight_results, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        # Pending students list
        if pending > 0:
            st.subheader("⚠️ Pending Students")
            attempted_emails = df['Email'].tolist() if 'Email' in df.columns else []
            pending_emails = [email for email in st.session_state.authorized_emails 
                            if email != ADMIN_EMAIL and email not in attempted_emails]
            
            for email in pending_emails:
                st.write(f"🔴 {email}")
        
        # Auto-refresh option
        if st.button("🔄 Refresh Results"):
            st.rerun()
        
        # Download options
        st.subheader("📥 Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📄 Download Complete Results",
                data=csv,
                file_name=f"quiz_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Summary report
            summary_data = {
                'Metric': ['Total Students', 'Attempted', 'Pending', 'Pass Count', 'Fail Count', 'Pass Rate'],
                'Value': [total_students, attempted, pending, pass_count, attempted-pass_count, f"{(pass_count/attempted*100):.1f}%" if attempted > 0 else "0%"]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_csv = summary_df.to_csv(index=False)
            st.download_button(
                label="📊 Download Summary Report",
                data=summary_csv,
                file_name=f"quiz_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        st.info("📋 No quiz attempts yet. Results will appear here as students complete the quiz.")
        st.write(f"👥 **{len(st.session_state.authorized_emails) - 1} students** are authorized to take the quiz.")
    
    st.divider()
    
    # Email Management Section
    st.subheader("📧 Email Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Authorized Emails:**")
        for i, email in enumerate(st.session_state.authorized_emails):
            if email != ADMIN_EMAIL:  # Don't allow removing admin
                if st.button(f"❌ {email}", key=f"remove_{i}"):
                    st.session_state.authorized_emails.remove(email)
                    st.rerun()
            else:
                st.write(f"🔒 {email} (Admin)")
    
    with col2:
        st.write("**Add New Email:**")
        new_email = st.text_input("Enter email address:")
        if st.button("➕ Add Email"):
            if new_email and new_email not in st.session_state.authorized_emails:
                st.session_state.authorized_emails.append(new_email)
                st.success(f"Added {new_email}")
                st.rerun()
            elif new_email in st.session_state.authorized_emails:
                st.warning("Email already exists")
        
        st.write("**Upload Email List:**")
        uploaded_file = st.file_uploader("Upload CSV/TXT file with emails", type=['csv', 'txt'])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_emails = pd.read_csv(uploaded_file)
                    emails = df_emails.iloc[:, 0].tolist()  # First column
                else:
                    emails = uploaded_file.read().decode('utf-8').strip().split('\n')
                
                new_emails = [email.strip() for email in emails if email.strip() and email.strip() not in st.session_state.authorized_emails]
                
                if new_emails:
                    st.session_state.authorized_emails.extend(new_emails)
                    st.success(f"Added {len(new_emails)} new emails")
                    st.rerun()
                else:
                    st.info("No new emails to add")
            except Exception as e:
                st.error(f"Error processing file: {e}")

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