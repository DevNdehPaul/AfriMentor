from flask import Flask, render_template, request, send_from_directory
from openai import OpenAI
from db import init_db, get_cached_answer, save_answer
from PIL import Image
# import fitz  # PyMuPDF
from pdf2image import convert_from_path
import tempfile
import pytesseract
import os
import json
import requests

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Use environment variable for API key (never hard-code secrets)
client = OpenAI(api_key="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")



app = Flask(__name__)

SYSTEM_PROMPT = """
You are an AI guide that helps African youth explore career opportunities.
Given a young person's country, education level, interests, skills, available startup capital,
and internet access, you will suggest:

1. Relevant job sectors and roles in their local economy
2. Short vocational training paths (TVET/apprenticeship/online)
3. Entrepreneurship ventures with realistic startup cost ranges (USD)
4. A simple 90-day action plan with offline/online options

Keep responses practical, encouraging, and easy to understand.
"""

SYSTEM_PROMPT_1 = """
You are a helpful translation assistant. 
Translate the provided text into the selected target language (Yoruba, Swahili, Fulfulde, etc.).
Keep translations simple, clear, and educational.
"""

CONTENT_DIR = "content"
MANIFEST_FILE = os.path.join(CONTENT_DIR, "manifest.json")
os.makedirs(CONTENT_DIR, exist_ok=True)

def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 0, "files": []}

def save_manifest(data):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def extract_text_from_pdf(pdf_path):
    text = ""
    # Option 1: Direct extraction
    # doc = fitz.open(pdf_path)
    # for page in doc:
    #     text += page.get_text("text") + "\n"
    # doc.close()

    if text.strip():
        return text

    # Option 2: OCR fallback (convert to images first)
    images = convert_from_path(pdf_path)
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    return text

def extract_text_from_image(image_path):
    img = Image.open(image_path)
    return pytesseract.image_to_string(img)

def translate_text(text, target_lang):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_1},
            {"role": "user", "content": f"Target language: {target_lang}\n\nText:\n{text}"}
        ],
        max_tokens=800
    )
    return completion.choices[0].message.content

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/ai-tutor', methods=['GET', 'POST'])
def ai_tutor():
    answer = None
    if request.method == 'POST':
        question = request.form['question'].strip()
        answer = get_cached_answer(question)
        if not answer:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are AfriMentor, an AI tutor helping African students with clear, culturally relevant answers."
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            )
            answer = response.choices[0].message.content
            save_answer(question, answer)
    return render_template('ai_tutor.html', answer=answer)

@app.route("/career", methods=["GET", "POST"])
def career():
    response_text = None
    if request.method == "POST":
        country = request.form.get("country", "")
        education = request.form.get("education", "")
        interests = request.form.get("interests", "")
        skills = request.form.get("skills", "")
        capital = request.form.get("capital", "")
        internet = request.form.get("internet", "yes")

        user_prompt = f"""
        Country: {country}
        Education: {education}
        Interests: {interests}
        Skills: {skills}
        Startup capital (USD): {capital}
        Internet access: {internet}
        """

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )

        response_text = completion.choices[0].message.content

    return render_template("career_navigator.html", response=response_text)

@app.route("/translate", methods=["GET", "POST"])
def translate():
    translation = None
    extracted_text = None

    if request.method == "POST":
        target_lang = request.form.get("language", "Yoruba")
        input_text = request.form.get("input_text", "")
        file = request.files.get("file")

        if input_text.strip():
            extracted_text = input_text
        elif file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                file.save(tmp.name)
                if file.filename.lower().endswith(".pdf"):
                    extracted_text = extract_text_from_pdf(tmp.name)
                else:
                    extracted_text = extract_text_from_image(tmp.name)

        if extracted_text:
            translation = translate_text(extracted_text, target_lang)

    return render_template("translate.html",
                           translation=translation,
                           extracted_text=extracted_text
                           )

@app.route("/community")
def community():
    manifest = load_manifest()
    return render_template("community.html", manifest=manifest)

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    if file:
        filepath = os.path.join(CONTENT_DIR, file.filename)
        file.save(filepath)

        # update manifest
        manifest = load_manifest()
        if file.filename not in manifest["files"]:
            manifest["version"] += 1
            manifest["files"].append(file.filename)
            save_manifest(manifest)

        return {"status": "success", "message": "File uploaded"}
    return {"status": "error", "message": "No file provided"}

@app.route("/files/<path:filename>")
def get_file(filename):
    return send_from_directory(CONTENT_DIR, filename, as_attachment=True)

@app.route("/manifest")
def manifest():
    return load_manifest()


@app.route("/fetch_cloud", methods=["POST"])
def fetch_cloud():
    """
    Fetch updates from a central cloud source (e.g. a public repo).
    Replace the sample URL with your own cloud storage or API.
    """
    try:
        CLOUD_URL = "https://raw.githubusercontent.com/someuser/somerepo/main/manifest.json"
        res = requests.get(CLOUD_URL, timeout=10)
        if res.status_code == 200:
            cloud_manifest = res.json()
            local_manifest = load_manifest()

            new_files = []
            for f in cloud_manifest["files"]:
                if f not in local_manifest["files"]:
                    file_url = f"https://raw.githubusercontent.com/someuser/somerepo/main/content/{f}"
                    file_res = requests.get(file_url, timeout=10)
                    if file_res.status_code == 200:
                        with open(os.path.join(CONTENT_DIR, f), "wb") as out:
                            out.write(file_res.content)
                        new_files.append(f)

            if new_files:
                local_manifest["version"] = cloud_manifest["version"]
                local_manifest["files"].extend(new_files)
                save_manifest(local_manifest)
                return {"status": "success", "message": f"Fetched {len(new_files)} new files"}
            else:
                return {"status": "success", "message": "Already up to date"}
        else:
            return {"status": "error", "message": "Cloud manifest not reachable"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
if __name__ == '__main__':
    init_db()

    app.run(debug=True)
