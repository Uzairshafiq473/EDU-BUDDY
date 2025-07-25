**𝐄𝐃𝐔 𝐁𝐔𝐃𝐃𝐘 - 𝐀𝐈-𝐏𝐨𝐰𝐞𝐫𝐞𝐝 𝐄𝐝𝐮𝐜𝐚𝐭𝐢𝐨𝐧𝐚𝐥 𝐏𝐥𝐚𝐭𝐟𝐨𝐫𝐦**

EDU BUDDY is an interactive, Flask-based educational platform that leverages a multi-agent AI system powered by CrewAI and Groq's LLM (llama-3.1-8b-instant) to deliver personalized learning experiences. With features like chat-based learning, dynamic quiz generation, file analysis, and progress tracking, EDU BUDDY makes education accessible and engaging for students, educators, and lifelong learners.

**𝐋𝐢𝐯𝐞 𝐏𝐫𝐨𝐣𝐞𝐜𝐭:** https://edu-buddy.onrender.com/

**𝐓𝐚𝐛𝐥𝐞 𝐨𝐟 𝐂𝐨𝐧𝐭𝐞𝐧𝐭𝐬**

**𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬**
**𝐌𝐮𝐥𝐭𝐢-𝐀𝐠𝐞𝐧𝐭 𝐒𝐲𝐬𝐭𝐞𝐦**
**𝐓𝐞𝐜𝐡 𝐒𝐭𝐚𝐜𝐤**
**𝐈𝐧𝐬𝐭𝐚𝐥𝐥𝐚𝐭𝐢𝐨𝐧**
**𝐔𝐬𝐚𝐠𝐞**
**𝐏𝐫𝐨𝐣𝐞𝐜𝐭 𝐒𝐭𝐫𝐮𝐜𝐭𝐮𝐫𝐞**
**𝐂𝐨𝐧𝐭𝐫𝐢𝐛𝐮𝐭𝐢𝐧𝐠**
**𝐋𝐢𝐜𝐞𝐧𝐬𝐞**

**𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬**

**𝐈𝐧𝐭𝐞𝐫𝐚𝐜𝐭𝐢𝐯𝐞 𝐂𝐡𝐚𝐭:** Ask questions and receive beginner-friendly, markdown-formatted answers tailored to your level.

**𝐃𝐲𝐧𝐚𝐦𝐢𝐜 𝐐𝐮𝐢𝐳𝐳𝐞𝐬:** Generate up to 10 MCQs based on user topics or recent chats, with progress tracking to identify weak areas.

**𝐅𝐢𝐥𝐞 𝐀𝐧𝐚𝐥𝐲𝐬𝐢𝐬:** Upload PDF, DOCX, or TXT files to get AI-generated summaries of educational content.

**𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 𝐓𝐫𝐚𝐜𝐤𝐢𝐧𝐠:** Monitor learning progress with metrics like quiz scores, topics covered, and weak areas, stored in SQLite.

**𝐑𝐨𝐛𝐮𝐬𝐭 𝐁𝐚𝐜𝐤𝐞𝐧𝐝:** Handles errors, rate limits, and logs activities for reliability and debugging.

**𝐌𝐮𝐥𝐭𝐢-𝐀𝐠𝐞𝐧𝐭 𝐒𝐲𝐬𝐭𝐞𝐦**

EDU BUDDY uses CrewAI to orchestrate three specialized AI agents, each with distinct roles, working sequentially to deliver cohesive learning experiences:

**𝐃𝐚𝐭𝐚 𝐑𝐞𝐬𝐞𝐚𝐫𝐜𝐡𝐞𝐫 🕵️‍♂️**
**𝐑𝐨𝐥𝐞:** Gathers and analyzes educational content.
**𝐓𝐚𝐬𝐤𝐬:**

* Scrapes websites using requests and BeautifulSoup for relevant material.
* Analyzes uploaded files (PDF, DOCX, TXT) to generate summaries.
* Creates detailed, markdown-formatted content for quizzes and explanations.
  **Example:** Fetches Python-related content for a quiz or chat response.

**𝐏𝐞𝐫𝐬𝐨𝐧𝐚𝐥𝐢𝐳𝐞𝐝 𝐄𝐝𝐮𝐜𝐚𝐭𝐨𝐫 👩‍🏫**

**𝐑𝐨𝐥𝐞:** Delivers clear, beginner-friendly explanations.

**𝐓𝐚𝐬𝐤𝐬:**

* Answers user queries in simple, markdown-formatted responses.
* Simplifies complex content from the Researcher for accessibility.
  **Example:** Explains "What is JavaScript?" with bullet points for beginners.

**𝐐𝐮𝐢𝐳 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐨𝐫 📝**

**𝐑𝐨𝐥𝐞:** Creates engaging MCQs to reinforce learning.

**𝐓𝐚𝐬𝐤𝐬:**

* Generates a JSON array of up to 10 MCQs based on Researcher-provided content.
* Extracts sub-topics to ensure relevant questions with four options (one correct).
* Provides fallback quizzes for generic topics if needed.
  **Example:** Creates questions like “What is Python?” with options like “A programming language” (correct).

The agents work together in a sequential process, ensuring accurate content retrieval, clear explanations, and meaningful assessments.

**𝐓𝐞𝐜𝐡 𝐒𝐭𝐚𝐜𝐤**

* **Backend:** Flask (Python web framework)
* **AI:** CrewAI, Groq LLM (llama-3.1-8b-instant) via litellm
* **Database:** SQLite for storing conversations, quiz results, and user topics
* **File Handling:** PyPDF2 (PDF), python-docx (DOCX), python-pptx (PPTX placeholder)
* **Web Scraping:** requests, BeautifulSoup
* **Frontend:** HTML, CSS, JavaScript (chat interface in chat.html)
* **Other:** python-dotenv for environment variables, flask-cors for cross-origin requests

**𝐈𝐧𝐬𝐭𝐚𝐥𝐥𝐚𝐭𝐢𝐨𝐧**

**𝐂𝐥𝐨𝐧𝐞 𝐭𝐡𝐞 𝐑𝐞𝐩𝐨𝐬𝐢𝐭𝐨𝐫𝐲:**
git clone [https://github.com/Uzairshafiq473/EDU-BUDDY.git](https://github.com/Uzairshafiq473/EDU-BUDDY.git)
cd EDU-BUDDY

**𝐒𝐞𝐭 𝐔𝐩 𝐚 𝐕𝐢𝐫𝐭𝐮𝐚𝐥 𝐄𝐧𝐯𝐢𝐫𝐨𝐧𝐦𝐞𝐧𝐭:**
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

**𝐈𝐧𝐬𝐭𝐚𝐥𝐥 𝐃𝐞𝐩𝐞𝐧𝐝𝐞𝐧𝐜𝐢𝐞𝐬:**
pip install -r requirements.txt

Ensure you have a requirements.txt file with dependencies like:

* flask
* crewai
* litellm
* python-dotenv
* sqlite3
* requests
* beautifulsoup4
* PyPDF2
* python-docx
* flask-cors
* markdown2
* werkzeug

**𝐒𝐞𝐭 𝐔𝐩 𝐄𝐧𝐯𝐢𝐫𝐨𝐧𝐦𝐞𝐧𝐭 𝐕𝐚𝐫𝐢𝐚𝐛𝐥𝐞𝐬:**
Create a .env file in the project root:

```
GROQ_API_KEY=your_groq_api_key
FLASK_SECRET_KEY=your_secure_key
DB_PATH=student_data.db
```

**𝐑𝐮𝐧 𝐭𝐡𝐞 𝐀𝐩𝐩𝐥𝐢𝐜𝐚𝐭𝐢𝐨𝐧:**
python app.py

The app runs on [http://localhost:8000](http://localhost:8000) by default (configurable via PORT environment variable).

**𝐔𝐬𝐚𝐠𝐞**

**𝐂𝐡𝐚𝐭 𝐈𝐧𝐭𝐞𝐫𝐟𝐚𝐜𝐞:**
Visit / to interact with EDU BUDDY.
Ask questions (e.g., "What is Python?") and receive tailored responses.
Use "exit" or "quit" to clear the session.

**𝐐𝐮𝐢𝐳 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐢𝐨𝐧:**
Send a POST request to /generate\_quiz with a topic or rely on the last chat message.
Receive a JSON response with MCQs and submit answers via /submit\_quiz.

**𝐅𝐢𝐥𝐞 𝐔𝐩𝐥𝐨𝐚𝐝:**
Upload PDF, DOCX, or TXT files via /upload to get AI-generated summaries.

**𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 𝐓𝐫𝐚𝐜𝐤𝐢𝐧𝐠:**
Access /progress to view quiz scores, weak areas, and recent topics.

**𝐂𝐨𝐧𝐭𝐫𝐢𝐛𝐮𝐭𝐢𝐧𝐠**

Contributions are welcome! To contribute:

* Fork the repository.
* Create a feature branch (git checkout -b feature-name).
* Commit changes (git commit -m "Add feature").
* Push to the branch (git push origin feature-name).
* Open a pull request.

Please ensure code follows PEP 8 standards and includes relevant tests.

**𝐋𝐢𝐜𝐞𝐧𝐬𝐞**

This project is licensed under the MIT License. See the LICENSE file for details.

EDU BUDDY is a step toward making education accessible and engaging through AI. Check out the live project on GitHub and share your feedback! 🌟
