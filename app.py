from flask import Flask, render_template, request
from smart_india_recommender import recommend_jobs
import PyPDF2
import re

app = Flask(__name__)

# -----------------------------
# MASTER SKILL LIST
# -----------------------------
skill_list = [
    "python","java","c++","sql","mysql","postgresql",
    "machine learning","deep learning","nlp",
    "tensorflow","pytorch","pandas","numpy",
    "flask","django","fastapi","api",
    "javascript","react","html","css",
    "aws","azure","docker","kubernetes",
    "excel","powerbi","tableau"
]

# -----------------------------
# PDF TEXT EXTRACTION
# -----------------------------
def extract_text_from_pdf(pdf_file):
    text = ""
    reader = PyPDF2.PdfReader(pdf_file)

    for page in reader.pages:
        text += page.extract_text() + " "

    return text.lower()

# -----------------------------
# SKILL EXTRACTION
# -----------------------------
def extract_skills(text):
    found = []

    for skill in skill_list:
        if re.search(r"\b" + re.escape(skill) + r"\b", text):
            found.append(skill)

    return found


@app.route("/", methods=["GET","POST"])
def home():

    results = []
    detected_skills = []

    if request.method == "POST":

        skills = request.form.get("skills")
        resume = request.files.get("resume")

        # Resume upload flow
        if resume and resume.filename != "":
            text = extract_text_from_pdf(resume)
            detected_skills = extract_skills(text)

            skill_string = ", ".join(detected_skills)
            results = recommend_jobs(skill_string)

        # Manual input flow
        elif skills:
            detected_skills = [s.strip() for s in skills.split(",")]
            results = recommend_jobs(skills)

    return render_template(
        "index.html",
        results=results,
        detected_skills=detected_skills
    )


if __name__ == "__main__":
    app.run(debug=True)