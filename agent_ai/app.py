import os
import re
import json
import random
import pandas as pd
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import PyPDF2
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)

try:
    if USE_AI:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    USE_AI = False

app = Flask(__name__)
app.secret_key = "change-me"
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

rubric = """
- Clarity: Is the writing clear and easy to understand?
- Content Accuracy: Are the facts correct and complete?
- Grammar and Style: Is the language correct and well-written?
- Depth: Does the answer show real understanding of the topic?
"""

template_text = """
You are an AI grading assistant.
Given the QUESTION, a student's SUBMISSION, and the RUBRIC, provide:

1. Overall feedback (2–3 sentences).
2. Strengths (bullet points).
3. Areas to improve (bullet points).
4. Suggestions for revision (bullet points).
5. Final Grade (1-10, integer only).

Respond ONLY in JSON with keys: "grade" (int) and "feedback" (string).
Question: {question}
Submission: {submission}
Rubric: {rubric}
"""

def ai_grade_answer(question, answer):
    # If OPENAI key present, use it, else fallback to dummy grading
    if USE_AI:
        prompt = template_text.format(question=question, submission=answer, rubric=rubric)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=512
            )
            reply = resp.choices[0].message.content
            parsed = json.loads(reply)
            grade = int(parsed.get("grade", 5))
            feedback = parsed.get("feedback", "")
            return max(1, min(10, grade)), feedback
        except Exception as e:
            # fallback to dummy
            print("AI call failed:", e)
    # Dummy grader
    score = random.randint(1,10)
    feedback = f"Auto-graded (dummy): Score {score}/10. Suggest improving clarity and depth."
    return score, feedback

def extract_answers_from_pdf(pdf_path):
    answers = {}
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            try:
                p = page.extract_text() or ""
            except Exception:
                p = ""
            text += p + "\n"
    # Look for patterns like: RegNo:123 Section:A Answer:...
    matches = re.findall(r"RegNo\s*[:\-]\s*(\w+)\s+Section\s*[:\-]\s*([\w\-]+)\s+Answer\s*[:\-]\s*(.+?)(?=RegNo\s*[:\-]|$)", text, re.S|re.I)
    for regno, section, answer in matches:
        answers[regno.strip()] = {"section": section.strip(), "answer": answer.strip()}
    return answers

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/grade', methods=['POST'])
def grade():
    question = request.form.get('question','').strip()
    section = request.form.get('section','').strip()
    file = request.files.get('pdf')
    if not question:
        flash("Please enter the question.", "danger")
        return redirect(url_for('index'))
    if not section:
        flash("Please enter/select a section.", "danger")
        return redirect(url_for('index'))
    if not file or not file.filename.lower().endswith('.pdf'):
        flash("Please upload a PDF file.", "danger")
        return redirect(url_for('index'))
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    student_data = extract_answers_from_pdf(filepath)
    results = []
    for regno, details in student_data.items():
        if details["section"].lower() == section.lower():
            grade_val, feedback_text = ai_grade_answer(question, details["answer"])
            results.append({
                "RegNo": regno,
                "Section": details["section"],
                "Submission": details["answer"],
                "Feedback": feedback_text,
                "Grade": grade_val
            })
    if not results:
        flash("No answers found for the chosen section in the PDF.", "warning")
        return redirect(url_for('index'))
    df = pd.DataFrame(results)
    csv_path = "graded_feedback.csv"
    df.to_csv(csv_path, index=False)
    table_html = df.to_html(classes="table table-striped", index=False, justify='left')
    return render_template('index.html', tables=table_html, download=True)

@app.route('/download', methods=['GET'])
def download():
    path = "graded_feedback.csv"
    if not os.path.exists(path):
        flash("No graded_feedback.csv found. Grade first.", "danger")
        return redirect(url_for('index'))
    return send_file(path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)