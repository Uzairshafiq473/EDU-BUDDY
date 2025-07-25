from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from crewai import Agent, Task, Crew, Process, CrewOutput
import sqlite3
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import litellm
import markdown2
from werkzeug.utils import secure_filename
import sys
import time
import logging
from litellm import RateLimitError
from docx import Document
import PyPDF2
from flask_cors import CORS

sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    logging.error("GROQ_API_KEY is not set. Please add it to your .env file.")
    print("Error: GROQ_API_KEY is not set. Please add it to your .env file.")
    exit(1)

flask_secret_key = os.getenv("FLASK_SECRET_KEY", "your_secure_key_here")
if not flask_secret_key or flask_secret_key == "your_secure_key_here":
    logging.warning("FLASK_SECRET_KEY is not set or using default. Set a secure key in .env for better security.")
    print("Warning: FLASK_SECRET_KEY is not set or using default. Set a secure key in .env for better security.")
app = Flask(__name__)
app.secret_key = flask_secret_key
CORS(app, resources={r"/*": {"origins": ["https://uzairshafiq473.github.io", "http://localhost:5000"]}})

# Configure upload folder
UPLOAD_FOLDER = '/tmp/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database setup
def get_db_connection():
    try:
        db_path = os.getenv("DB_PATH", "/tmp/student_data.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        print(f"Database connection error: {e}")
        return None
def clean_database():
    conn = get_db_connection()
    if conn:
        # Fetch all entries from performance table
        entries = conn.execute("SELECT id, topic, weak_area FROM performance").fetchall()
        for entry in entries:
            entry_id = entry["id"]
            topic = entry["topic"]
            weak_area = entry["weak_area"]
            
            # Clean topic
            if topic.lower().startswith("this comprehensive") or "welcome to" in topic.lower():
                new_topic = topic.lower().split("welcome to")[-1].strip() if "welcome to" in topic.lower() else "JavaScript"
                new_topic = new_topic.split()[:2]  # First 1-2 words
                new_topic = " ".join(new_topic).strip()
            elif topic.lower() in ["i now", "unknown"]:
                new_topic = "General Knowledge"
            else:
                new_topic = topic.split()[:2]  # First 1-2 words
                new_topic = " ".join(new_topic).strip()
            
            # Clean weak_area
            if weak_area and (weak_area.lower().startswith("this comprehensive") or "welcome to" in weak_area.lower()):
                new_weak_area = weak_area.lower().split("welcome to")[-1].strip() if "welcome to" in weak_area.lower() else "JavaScript"
                new_weak_area = new_weak_area.split()[:2]  # First 1-2 words
                new_weak_area = " ".join(new_weak_area).strip()
            elif weak_area and weak_area.lower() in ["i now", "unknown"]:
                new_weak_area = "General Knowledge"
            else:
                new_weak_area = weak_area if weak_area != "None" else None
            
            # Update the database
            conn.execute(
                "UPDATE performance SET topic = ?, weak_area = ? WHERE id = ?",
                (new_topic, new_weak_area, entry_id)
            )
        
        # Clean user_topics table
        topics = conn.execute("SELECT id, topic FROM user_topics").fetchall()
        for t in topics:
            topic_id = t["id"]
            topic = t["topic"]
            
            if topic.lower().startswith("this comprehensive") or "welcome to" in topic.lower():
                new_topic = topic.lower().split("welcome to")[-1].strip() if "welcome to" in topic.lower() else "JavaScript"
                new_topic = new_topic.split()[:2]  # First 1-2 words
                new_topic = " ".join(new_topic).strip()
            elif topic.lower() in ["i now", "unknown"]:
                new_topic = "General Knowledge"
            else:
                new_topic = topic.split()[:2]  # First 1-2 words
                new_topic = " ".join(new_topic).strip()
            
            conn.execute(
                "UPDATE user_topics SET topic = ? WHERE id = ?",
                (new_topic, topic_id)
            )
        
        conn.commit()
        conn.close()
        logging.info("Database cleaned successfully")

def crew_output_to_dict(crew_output):
    if isinstance(crew_output, CrewOutput):
        return {
            'raw_output': str(crew_output),
            'processed': True
        }
    return crew_output

def init_db():
    conn = get_db_connection()
    if conn:
        c = conn.cursor()
        try:
            c.execute("""
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT,
                    score INT,
                    weak_area TEXT,
                    topic TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT,
                    user_message TEXT,
                    bot_response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Naya table user_topics ke liye
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    topic TEXT,
                    start_date TEXT
                )
            """)
            conn.commit()
            logging.info("Database initialized successfully")
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            print(f"Database initialization error: {e}")
        finally:
            conn.close()

init_db()

# Custom scraping function
def scrape_website(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        logging.info(f"Successfully scraped website: {url}")
        return text
    except Exception as e:
        logging.error(f"Error scraping website {url}: {str(e)}")
        return f"Error scraping website: {str(e)}"

# LLM setup using litellm
litellm_model = "groq/llama-3.1-8b-instant"

researcher = Agent(
    role="Data Researcher",
    goal="Retrieve relevant educational content from the internet",
    backstory="The researcher is an AI agent designed to find and analyze educational content from various sources.",
    verbose=True,
    llm=litellm_model
)

teacher = Agent(
    role="Personalized Educator",
    goal="Provide clear, plagiarism-free explanations tailored to student's level",
    backstory="The teacher is an AI agent focused on delivering personalized and engaging educational content.",
    verbose=True,
    llm=litellm_model
)

quiz_master = Agent(
    role="Quiz Generator",
    goal="Create engaging quizzes based on learning topics",
    backstory="The quiz master is an AI agent that generates quizzes to test and reinforce learning.",
    verbose=True,
    llm=litellm_model
)

# Configure litellm with Groq API key
litellm.api_key = groq_api_key
litellm.groq_api_key = groq_api_key

# Character profile
character = {
    "name": "EDU BUDDY",
    "personality": "Friendly and helpful AI tutor",
    "greeting": "Assalam-o-Alaikum! Main EDU BUDDY hoon. Aaj hum kya seekhein ge?",
    "avatar": "/static/images/avatar.jpeg"
}

# Retry mechanism for rate limit errors
def execute_with_retry(crew, max_retries=3, initial_delay=3):
    for attempt in range(max_retries):
        try:
            result = crew.kickoff()
            logging.info(f"Successfully executed Crew task on attempt {attempt + 1}")
            return result
        except RateLimitError as e:
            wait_time = getattr(e, 'retry_after', initial_delay)
            logging.warning(f"Rate limit error on attempt {attempt + 1}. Waiting {wait_time} seconds. Error: {str(e)}")
            time.sleep(wait_time)
            if attempt == max_retries - 1:
                logging.error(f"Max retries ({max_retries}) reached. Failed to execute Crew task.")
                raise Exception(f"Rate limit exceeded after {max_retries} retries: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
            raise e

@app.route("/", methods=["GET", "POST"])
def chat():
    if "student_id" not in session:
        session["student_id"] = f"user_{datetime.now().timestamp()}"
        session["level"] = "beginner"
        session["interests"] = "general knowledge"
        session["conversation_history"] = []
        session["learning_progress"] = {"topics_covered": [], "quizzes_taken": 0}
    
    if request.method == "POST":
        user_input = request.form.get("user_input", "").strip()
        if not user_input:
            logging.warning("Empty input received in chat route")
            return jsonify({"error": "Empty input"}), 400
        
        if user_input.lower() in ["exit", "quit"]:
            session["conversation_history"] = []
            logging.info(f"Session cleared for student_id: {session['student_id']}")
            return jsonify({"status": "session cleared"})
        
        try:
            retrieve_task = Task(
                description=f"Find comprehensive information about: {user_input}. If needed, scrape relevant educational websites.",
                agent=researcher,
                expected_output="Detailed educational content with examples",
                max_tokens=300
            )
            
            teacher_task = Task(
                description=f"""You are an expert teacher. Answer the following question in simple language for beginners. 
Question: {user_input}
Give your answer in markdown format with headings and bullet points if needed. Do NOT include any thoughts, reasoning steps, or instructions—just the answer.""",
                agent=teacher,
                expected_output="Markdown answer only",
                max_tokens=400
            )
            
            crew = Crew(
                agents=[researcher, teacher],
                tasks=[retrieve_task, teacher_task],
                process=Process.sequential
            )
            
            response = execute_with_retry(crew)
            
            if isinstance(response, CrewOutput):
                response_text = markdown2.markdown(str(response))
            else:
                response_text = markdown2.markdown(response)
            
            conn = get_db_connection()
            if conn:
                conn.execute(
                    "INSERT INTO conversations (student_id, user_message, bot_response) VALUES (?, ?, ?)",
                    (session["student_id"], user_input, response_text)
                )
                conn.commit()
                conn.close()
                logging.info(f"Conversation stored for student_id: {session['student_id']}")
            
            session["conversation_history"].append({
                "user": user_input,
                "bot": response_text,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            
            logging.info(f"Chat response generated for user_input: {user_input}")
            return jsonify({
                "response": response_text,
                "timestamp": datetime.now().strftime("%H:%M"),
                "suggestions": get_learning_suggestions(user_input),
                "status": "success"
            })
            
        except Exception as e:
            logging.error(f"Error in chat route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return render_template("chat.html", character=character)

def get_learning_suggestions(topic):
    suggestions = [
        f"Tell me more about {topic}",
        f"What are the practical applications of {topic}?",
        f"Explain {topic} like I'm 10 years old",
        f"Compare {topic} with similar concepts",
        f"Generate a quiz about {topic}"
    ]
    return suggestions[:3]

@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    try:  
        data = request.get_json()  
        topic = data.get("topic", "")
        
        if not topic and session.get("conversation_history"):
            last_message = session["conversation_history"][-1]["user"].lower()
            logging.info(f"Last message from user: {last_message}")
            keywords = ["about", "learn", "explain", "on", "quiz", "welcome to"]
            for keyword in keywords:
                if keyword in last_message:
                    topic = last_message.split(keyword)[-1].strip()
                    logging.info(f"Initial topic extracted after keyword '{keyword}': {topic}")
                    break
            else:
                topic = last_message.strip()
                logging.info(f"Initial topic set to last message: {topic}")
            
            topic = topic.replace("i now can give a great answer", "").replace("for beginners", "").replace("welcome to the world of", "").strip()
            topic_words = topic.split()
            if len(topic_words) > 2:
                topic = " ".join(topic_words[-2:]).strip()
                logging.info(f"Initial topic after taking last 1-2 words: {topic}")
            elif topic_words:
                topic = topic_words[-1].strip()
                logging.info(f"Initial topic after taking last word: {topic}")
            else:
                topic = "General Knowledge"
                logging.info(f"Initial topic fallback to General Knowledge: {topic}")
        
        topic = topic.replace("#", "").replace("Thought:", "").strip()
        if not topic or topic in ["i", "what", "welcome", "assalam-o-alaikum", "i now"]:
            topic = "General Knowledge"
            logging.info(f"Initial topic set to default: {topic}")
            
        logging.info(f"Generating content for initial topic: {topic}")

        # Step 1: Generate content FIRST
        content_task = Task(
            description=f"Create detailed educational content about: {topic}. Use markdown headings for sub-topics.",
            agent=researcher,
            expected_output="Comprehensive notes in markdown format",
            max_tokens=300
        )
        
        crew = Crew(
            agents=[researcher],
            tasks=[content_task],
            process=Process.sequential
        )
        content_output = execute_with_retry(crew)
        
        content_output_str = str(content_output).strip()
        logging.info(f"Generated content: {content_output_str}")
        
        # Step 2: Topic ko content se nikaal kar confirm karo
        content_lines = content_output_str.lower().split('\n')
        extracted_topic = topic  # Fallback to initial topic
        for line in content_lines:
            if line.startswith('# '):  # Main heading se topic lo
                extracted_topic = line.replace('# ', '').strip()
                logging.info(f"Topic extracted from main heading: {extracted_topic}")
                break
            elif "welcome to" in line:
                extracted_topic = line.split("welcome to")[-1].strip()
                logging.info(f"Topic extracted from 'welcome to': {extracted_topic}")
                break
            elif "welcome to the world of" in line:
                extracted_topic = line.split("welcome to the world of")[-1].strip()
                logging.info(f"Topic extracted from 'welcome to the world of ': {extracted_topic}")
                break
            elif "what is " in line:
                extracted_topic = line.split("what is ")[-1].strip()
                logging.info(f"Topic extracted from 'what is ': {extracted_topic}")
                break
        # Clean extracted topic
        extracted_topic = extracted_topic.split()[:2]  # First 1-2 words as topic
        extracted_topic = " ".join(extracted_topic).strip()
        if not extracted_topic or extracted_topic in ["i", "what", "welcome", "i now", "this"]:
            extracted_topic = topic
        logging.info(f"Final extracted topic from content: {extracted_topic}")
        
        # Step 3: Extract sub-topics from content
        sub_topics = []
        for line in content_output_str.split('\n'):
            if line.startswith('## '):
                sub_topic = line.replace('## ', '').strip()
                sub_topics.append(sub_topic.lower())
        logging.info(f"Extracted sub-topics: {sub_topics}")

        # Step 4: Generate quiz FROM THAT CONTENT
        quiz_task = Task(
            description=f"""Given the following content, generate 10 MCQs. 
CONTENT:
{content_output_str}

RULES:
1. Each question MUST be answerable ONLY from the content above.
2. Each question must be 1 sentence (max 12 words).
3. Format output as a JSON array, like this:
[
  {{
    "question": "What is Python?",
    "options": [
      {{"text": "A programming language", "correct": true}},
      {{"text": "A fruit", "correct": false}},
      {{"text": "A car", "correct": false}},
      {{"text": "A city", "correct": false}}
    ]
  }},
  ...
]
4. Do NOT add any explanation or extra text.
5. If you cannot generate 10 questions from the content, generate as many as possible.

Quiz title: "{extracted_topic} Quiz"
""",
            agent=quiz_master,
            expected_output="JSON array of MCQ objects",
            max_tokens=300
        )

        crew = Crew(
            agents=[quiz_master],
            tasks=[quiz_task],
            process=Process.sequential
        )
        
        quiz_output = execute_with_retry(crew)
        logging.info(f"Raw quiz output: {quiz_output}")
        
        quiz_output_str = str(quiz_output).strip()
        json_start = quiz_output_str.find('[')
        json_end = quiz_output_str.rfind(']') + 1
        
        if json_start == -1 or json_end == 0:
            logging.error("No valid JSON found in quiz output")
            raise Exception("Failed to parse quiz data: No valid JSON found")

        quiz_json_str = quiz_output_str[json_start:json_end]
        
        try:
            quiz_data = json.loads(quiz_json_str)
            if not isinstance(quiz_data, list):
                raise ValueError("Quiz data is not a list")
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Invalid JSON from quiz output: {str(e)} - Raw output: {quiz_json_str}")
            raise Exception(f"Failed to parse quiz data: {str(e)}")

        clean_quiz = []
        for q in quiz_data[:10]:  # Pehle 10 MCQs process karo
            if not isinstance(q, dict):
                continue
            if not all(key in q for key in ["question", "options"]):
                continue
            if not isinstance(q["options"], list) or len(q["options"]) < 4:
                continue
            processed_options = []
            for opt in q["options"][:4]:
                if not isinstance(opt, dict):
                    continue
                processed_options.append({
                    "text": str(opt.get("text", "")[:50]),
                    "correct": bool(opt.get("correct", False))
                })
            if len(processed_options) == 4:
                clean_quiz.append({
                    "question": str(q["question"])[:100],
                    "options": processed_options
                })

        if len(clean_quiz) < 3:
            logging.warning(f"Not enough valid questions ({len(clean_quiz)}), using fallback quiz")
            raise Exception("Not enough valid questions generated")

        session["current_quiz"] = {
            "topic": f"{extracted_topic} Quiz",
            "questions": clean_quiz[:10],  # Pehle 10 MCQs save karo
            "sub_topics": sub_topics,
            "raw_topic": extracted_topic  # Sirf topic naam save
        }

        logging.info(f"Quiz generated successfully for topic: {extracted_topic}")
        return jsonify(session["current_quiz"])
       
    except Exception as e:
        logging.error(f"Quiz error: {str(e)}")
        fallback_quiz = create_fallback_quiz(topic)
        session["current_quiz"] = fallback_quiz
        return jsonify(fallback_quiz)


def create_fallback_quiz(topic):
    clean_topic = topic.replace("Thought:", "").replace("#", "").strip()  
    base_topic = clean_topic.split()[0] if clean_topic.split() else "General"  
    return {  
        "topic": f"{base_topic} Quiz",
        "questions": [
            {"question": f"What is {base_topic}'s main purpose?", "options": [
                {"text": "A programming concept", "correct": True},
                {"text": "A type of food", "correct": False},
                {"text": "A musical instrument", "correct": False},
                {"text": "A sports term", "correct": False}
            ]},
            {"question": f"How is {base_topic} primarily used?", "options": [
                {"text": "For solving problems", "correct": True},
                {"text": "For cooking food", "correct": False},
                {"text": "For playing games", "correct": False},
                {"text": "For building furniture", "correct": False}
            ]},
            {"question": f"What technology is {base_topic}?", "options": [
                {"text": "Computer-related", "correct": True},
                {"text": "Agricultural", "correct": False},
                {"text": "Mechanical", "correct": False},
                {"text": "Medical", "correct": False}
            ]},
            {"question": f"When was {base_topic} developed?", "options": [
                {"text": "In the digital age", "correct": True},
                {"text": "In ancient times", "correct": False},
                {"text": "In medieval period", "correct": False},
                {"text": "In prehistoric era", "correct": False}
            ]},
            {"question": f"Who uses {base_topic}?", "options": [
                {"text": "Developers and engineers", "correct": True},
                {"text": "Chefs and cooks", "correct": False},
                {"text": "Musicians", "correct": False},
                {"text": "Athletes", "correct": False}
            ]},
            {"question": f"What is {base_topic}'s main purpose?", "options": [
                {"text": "A programming concept", "correct": True},
                {"text": "A type of food", "correct": False},
                {"text": "A musical instrument", "correct": False},
                {"text": "A sports term", "correct": False}
            ]},
            {"question": f"How is {base_topic} primarily used?", "options": [
                {"text": "For solving problems", "correct": True},
                {"text": "For cooking food", "correct": False},
                {"text": "For playing games", "correct": False},
                {"text": "For building furniture", "correct": False}
            ]},
            {"question": f"What technology is {base_topic}?", "options": [
                {"text": "Computer-related", "correct": True},
                {"text": "Agricultural", "correct": False},
                {"text": "Mechanical", "correct": False},
                {"text": "Medical", "correct": False}
            ]},
            {"question": f"When was {base_topic} developed?", "options": [
                {"text": "In the digital age", "correct": True},
                {"text": "In ancient times", "correct": False},
                {"text": "In medieval period", "correct": False},
                {"text": "In prehistoric era", "correct": False}
            ]},
            {"question": f"Who uses {base_topic}?", "options": [
                {"text": "Developers and engineers", "correct": True},
                {"text": "Chefs and cooks", "correct": False},
                {"text": "Musicians", "correct": False},
                {"text": "Athletes", "correct": False}
            ]}
        ]
    }


@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if "student_id" not in session or "current_quiz" not in session:
        logging.error("No active quiz session in submit_quiz")
        return jsonify({"error": "No active quiz session"}), 400

    data = request.get_json()
    answers = data.get("answers", [])

    quiz = session["current_quiz"]
    questions = quiz["questions"]
    topic = quiz.get("raw_topic", "Unknown")
    logging.info(f"Topic in submit_quiz: {topic}")

    results = []
    correct_count = 0

    for i, question in enumerate(questions):
        user_answer = answers[i] if i < len(answers) and answers[i] is not None else None
        correct_index = next((j for j, opt in enumerate(question["options"]) if opt["correct"]), None)
        correct_text = next((opt["text"] for opt in question["options"] if opt["correct"]), None)

        if user_answer is not None and 0 <= user_answer < len(question["options"]):
            user_answer_text = question["options"][user_answer]["text"]
            is_correct = question["options"][user_answer]["correct"]
            if is_correct:
                correct_count += 1
        else:
            user_answer_text = "No answer"
            is_correct = False

        results.append({
            "question": question["question"],
            "user_answer": user_answer,
            "user_answer_text": user_answer_text,
            "correct_answer": correct_index,
            "correct_answer_text": correct_text,
            "is_correct": is_correct
        })

    total_questions = len(questions)
    score = int((correct_count / total_questions) * 100) if total_questions > 0 else 0
    weak_area = topic if score < 60 else "None"
    logging.info(f"Score: {score}, Weak Area: {weak_area}, Topic: {topic}")

    conn = get_db_connection()
    if conn:
        conn.execute(
            "INSERT INTO performance (student_id, score, weak_area, topic) VALUES (?, ?, ?, ?)",
            (session["student_id"], score, weak_area, topic)
        )
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing_topic = conn.execute(
            "SELECT topic FROM user_topics WHERE user_id = ? AND topic = ?",
            (session["student_id"], topic)
        ).fetchone()
        if not existing_topic:
            conn.execute(
                "INSERT INTO user_topics (user_id, topic, start_date) VALUES (?, ?, ?)",
                (session["student_id"], topic, current_date)
            )
            logging.info(f"Topic '{topic}' saved to user_topics for user_id: {session['student_id']}")
        conn.commit()
        conn.close()

    return jsonify({
        "score": score,
        "correct_answers": correct_count,
        "total_questions": total_questions,
        "results": results,
        "quiz_questions": questions
    })


@app.route("/progress")
def get_progress():
    if "student_id" not in session:
        logging.warning("No student_id found in session for progress retrieval")
        return jsonify({
            "total_quizzes": 0,
            "average_score": 0,
            "weak_areas": [],
            "recent_topics": [],
            "quiz_history": [],
            "new_topics": []
        })

    conn = get_db_connection()
    if conn is None:
        logging.error(f"Failed to connect to database for progress retrieval for student_id: {session['student_id']}")
        return jsonify({
            "error": "Database connection failed",
            "total_quizzes": 0,
            "average_score": 0,
            "weak_areas": [],
            "recent_topics": [],
            "quiz_history": [],
            "new_topics": []
        })
    
    try:
        quizzes = conn.execute(
            "SELECT topic, score, weak_area, timestamp FROM performance WHERE student_id = ? ORDER BY timestamp DESC",
            (session["student_id"],)
        ).fetchall()
        
        new_topics = conn.execute(
            "SELECT topic, start_date FROM user_topics WHERE user_id = ? ORDER BY start_date DESC",
            (session["student_id"],)
        ).fetchall()
        
        cleaned_quizzes = []
        for q in quizzes:
            q_dict = dict(q)
            # Clean topic and weak_area
            if len(q_dict["topic"].split()) > 2:
                q_dict["topic"] = " ".join(q_dict["topic"].split()[:2]).strip()
            if q_dict["weak_area"] and len(q_dict["weak_area"].split()) > 2:
                q_dict["weak_area"] = " ".join(q_dict["weak_area"].split()[:2]).strip()
            cleaned_quizzes.append(q_dict)
            
        cleaned_new_topics = []
        for t in new_topics:
            t_dict = dict(t)
            if len(t_dict["topic"].split()) > 2:
                t_dict["topic"] = " ".join(t_dict["topic"].split()[:2]).strip()
            cleaned_new_topics.append(t_dict)
            
        logging.info(f"Cleaned quizzes: {cleaned_quizzes}")
        logging.info(f"Cleaned new topics: {cleaned_new_topics}")
    except sqlite3.Error as e:
        logging.error(f"Database query error in progress route: {str(e)}")
        return jsonify({
            "error": f"Database query error: {str(e)}",
            "total_quizzes": 0,
            "average_score": 0,
            "weak_areas": [],
            "recent_topics": [],
            "quiz_history": [],
            "new_topics": []
        })
    finally:
        conn.close()
        logging.info("Database connection closed")
    
    progress_data = {
        "total_quizzes": len(cleaned_quizzes),
        "average_score": sum(q["score"] for q in cleaned_quizzes) / len(cleaned_quizzes) if cleaned_quizzes else 0,
        "weak_areas": list(set(q["weak_area"] for q in cleaned_quizzes if q["weak_area"] != "None")),
        "recent_topics": [q["topic"] for q in cleaned_quizzes[:5]],
        "quiz_history": [dict(q) for q in cleaned_quizzes],
        "new_topics": [t["topic"] for t in cleaned_new_topics[:5]]
    }
    
    logging.info(f"Progress data returned: {progress_data}")
    return jsonify(progress_data)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        logging.warning("No file part in upload request")
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        logging.warning("No selected file in upload request")
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        content = ""
        try:
            file_extension = filename.rsplit('.', 1)[1].lower()
            if file_extension == 'txt':
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif file_extension == 'pdf':
                with open(filepath, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    for page in pdf.pages:
                        content += page.extract_text() + "\n"
            elif file_extension == 'docx':
                doc = Document(filepath)
                for para in doc.paragraphs:
                    content += para.text + "\n"
            elif file_extension == 'pptx':
                content = "PPTX file handling not implemented yet."
            
            logging.info(f"File uploaded and content extracted: {filename}")
            
            file_task = Task(
                description=f"Analyze this uploaded file content: {content[:1000]}...",
                agent=researcher,
                expected_output="Summary and key points from the file",
                max_tokens=300
            )
            
            crew = Crew(
                agents=[researcher],
                tasks=[file_task],
                process=Process.sequential
            )
            response = execute_with_retry(crew)
            
            response_text = markdown2.markdown(str(response)) if isinstance(response, CrewOutput) else markdown2.markdown(response)
            
            logging.info(f"File analysis completed for: {filename}")
            return jsonify({
                "status": "success",
                "filename": filename,
                "content": response_text[:500] + "..." if len(response_text) > 500 else response_text
            })
            
        except Exception as e:
            logging.error(f"Error processing file {filename}: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Processed file but failed to analyze: {str(e)}"
            }), 500
    
    logging.warning(f"File type not allowed: {file.filename}")
    return jsonify({"error": "File type not allowed"}), 400

@app.route("/clear", methods=["POST"])
def clear_session():
    session.clear()
    logging.info(f"Session cleared for student_id: {session.get('student_id', 'unknown')}")
    return jsonify({"status": "success"})



import os

if __name__ == '__main__':
    logging.info("Starting Flask application")
    clean_database()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
