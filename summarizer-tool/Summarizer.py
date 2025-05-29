import os
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
import google.generativeai as genai

# Setup Gemini API
genai.configure(api_key="API Key")  # Replace with your actual API key
model = genai.GenerativeModel("models/gemini-1.5-flash")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'} #Only .txt, .pdf, and .docx files will be allowed

# Setup Flask to designate where uploaded files are stored
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#Defining fuction to check and see if file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Defining function to extract text from uploaded file
def extract_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    elif ext == ".pdf":
        reader = PdfReader(filepath)
        extracted = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    extracted.append(text)
            except Exception as e:
                print(f"Failed to extract text from page {i + 1}: {e}")
        return "\n".join(extracted)

    elif ext == ".docx":
        doc = Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])

    else:
        raise ValueError("Unsupported file type")

#Defining function to summarize text using Gemini API
def summarize(text):
    try:
        response = model.generate_content(f"Summarize the following text while focusing on the main takeaways:\n\n{text}. The summary shouldn't be longer than two paragraphs.")
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {str(e)}")

@app.route("/", methods=["GET", "POST"])
def index():
    summary = ""
    error = ""

    if request.method == "POST":
        uploaded_file = request.files.get("file")

        #Calling function to check if file is allowed
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(filepath)

            #Extracts text
            try:
                text = extract_text(filepath)
                summary = summarize(text)
                os.remove(filepath)  # ✅ Delete file after use
            except Exception as e:
                error = f"Error processing file: {str(e)}"
                if os.path.exists(filepath):
                    os.remove(filepath)  # ✅ Ensure cleanup even on failure
        else:
            error = "Invalid file type. Only .txt, .pdf, and .docx are supported."

    return render_template("index.html", summary=summary, error=error)

if __name__ == "__main__":
    app.run(debug=True)

