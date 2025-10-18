
# agent_ai - Simple Grading Assistant

This is a minimal Flask project that:
- Accepts a question and a PDF containing student answers (RegNo, Section, Answer).
- Grades answers (uses OpenAI if OPENAI_API_KEY is provided in .env; otherwise uses a dummy grader).
- Saves results to graded_feedback.csv and allows download.

## Setup

1. (Optional) Create and activate a venv.
2. Install dependencies:
   pip install -r requirements.txt
3. Create a .env file with OPENAI_API_KEY if you want AI grading (optional).
4. Run:
   python app.py
5. Open http://127.0.0.1:5000 in your browser.

PDF format recommendation:
RegNo:123 Section:A Answer:The mitochondria is the powerhouse of the cell.
RegNo:124 Section:A Answer:It helps in energy production inside the cell.
