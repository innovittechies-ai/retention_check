import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

# Configuration
if 'authorized_emails' not in st.session_state:
    st.session_state.authorized_emails = [
        "user1@example.com",
        "user2@example.com", 
        "user3@example.com",
        "admin@example.com"
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

def generate_quiz_with_openai(transcript, api_key):
    """Generate quiz using OpenAI API"""
    url = "https://api.openai.com/v1/chat/completions"
    
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
        'model': 'gpt-3.5-turbo',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        content = response.json()['choices'][0]['message']['content']
        try:
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
    st.title("📝 Quiz Application")
    st.write(f"Welcome, {st.session_state.user_email}!")
    
    # Option to generate quiz from transcript
    st.header("Generate Custom Quiz")
    api_key = st.text_input("Enter OpenAI API Key (optional):", type="password")
    transcript = st.text_area("Paste transcript to generate custom quiz:", height=150)
    
    if st.button("Generate Custom Quiz") and api_key and transcript:
        with st.spinner("Generating quiz..."):
            custom_quiz = generate_quiz_with_openai(transcript, api_key)
            if custom_quiz:
                st.session_state.current_quiz = custom_quiz['questions']
                st.success("Custom quiz generated!")
                st.rerun()
    
    # Use default quiz if no custom quiz
    if 'current_quiz' not in st.session_state:
        st.session_state.current_quiz = QUIZ_QUESTIONS
    
    st.header("Take Quiz")
    
    with st.form("quiz_form"):
        user_answers = {}
        
        for i, q in enumerate(st.session_state.current_quiz):
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
            
            for i, q in enumerate(st.session_state.current_quiz):
                correct = q['correct']
                user_choice = user_answers[i][0]
                
                if user_choice == correct:
                    score += 1
                    results.append("✅")
                else:
                    results.append(f"❌ (Correct: {correct})")
            
            percentage = (score / len(st.session_state.current_quiz)) * 100
            pass_fail = "Pass" if percentage >= 70 else "Fail"
            
            st.header("🎯 Results")
            st.write(f"**Score: {score}/{len(st.session_state.current_quiz)} ({percentage:.1f}%)**")
            st.write(f"**Status: {pass_fail}**")
            
            for i, result in enumerate(results):
                st.write(f"Q{i+1}: {result}")
            
            # Save results
            if save_quiz_result(st.session_state.user_email, f"{score}/{len(st.session_state.current_quiz)}", pass_fail):
                st.success("Results saved successfully!")

def admin_dashboard():
    """Display admin dashboard"""
    st.header("👨💼 Admin Dashboard")
    
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
                    df = pd.read_csv(uploaded_file)
                    emails = df.iloc[:, 0].tolist()  # First column
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
    
    st.divider()
    
    # Quiz Results Section
    df = get_quiz_data()
    
    if not df.empty:
        st.subheader("📊 Quiz Results")
        st.dataframe(df)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name=f"quiz_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Statistics
        st.subheader("📈 Statistics")
        if 'Pass_Fail' in df.columns:
            pass_count = len(df[df['Pass_Fail'] == 'Pass'])
            total_count = len(df)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", len(st.session_state.authorized_emails))
            with col2:
                st.metric("Total Attempts", total_count)
            with col3:
                st.metric("Pass Rate", f"{(pass_count/total_count*100):.1f}%" if total_count > 0 else "0%")
    else:
        st.info("No quiz results found.")

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
            if 'current_quiz' in st.session_state:
                del st.session_state.current_quiz
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