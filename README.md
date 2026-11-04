# DocuMind AI

**Turn dense documents into clear, actionable knowledge.**

DocuMind AI is a web application designed to help users understand PDF
documents through document-grounded question answering and AI-assisted
summaries. It combines PDF text extraction, semantic retrieval, and a
language model to make information easier to find and review.

> **Project status:** Active development. Features and deployment
> configuration may evolve.

## Deployment
DocuMind AI is live at - https://documind-ai-nd32.onrender.com/

## Highlights

-   **PDF upload** --- upload supported PDF documents through the web
    interface.
-   **Text extraction** --- extract document text and page information
    with PyMuPDF.
-   **Semantic retrieval** --- split extracted text into chunks,
    generate embeddings, and retrieve relevant passages using Sentence
    Transformers and FAISS.
-   **Document chat** --- ask questions about a selected document and
    receive answers grounded in retrieved passages.
-   **AI responses** --- use the Groq API for language-model responses.
-   **Source context** --- responses can include page/chunk references
    when provided by the retrieval pipeline.
-   **Account authentication** --- Flask routes support signup, login,
    and email OTP verification.
-   **Responsive interface** --- HTML, CSS, and JavaScript frontend with
    dashboard and AI Workspace views.

## Technology Stack

  Layer                Technology
  -------------------- -----------------------
  Frontend             HTML, CSS, JavaScript
  Backend              Python, Flask
  PDF processing       PyMuPDF
  Embeddings           Sentence Transformers
  Vector search        FAISS (CPU)
  LLM integration      Groq API
  Database             SQLite
  Email verification   Gmail SMTP
  Configuration        `python-dotenv`

## How It Works

1.  A user uploads a PDF.
2.  The backend extracts text and page-level information.
3.  Extracted text is divided into chunks.
4.  Sentence Transformers creates embeddings for the chunks.
5.  FAISS indexes the vectors and retrieves passages relevant to a
    question.
6.  The retrieved context is sent to the configured Groq model to
    generate an answer.
7.  The application returns the answer and available source references
    to the UI.

The quality of answers depends on the PDF's text quality, chunking and
retrieval configuration, and the configured language model. Scanned PDFs
may require OCR; OCR support should not be assumed unless it has been
implemented and enabled.

## Project Structure

The exact structure may differ as development continues. A typical
layout is:

``` text
DocuMind-AI/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── routes/
│   ├── auth_routes.py
│   ├── documents_routes.py
│   └── chat_routes.py
│   └── auth_helpers.py
├── services/
│   ├── pdf_service.py
│   ├── chunking_service.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   └── rag_service.py
├── database/
│   ├── db.py
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   ├── login.html
│   ├── SignUp.html
│   └── otp_verification.html
├── static/
│   └── favicon.ico
├── uploads/                 # Locally uploaded(not for user)
```


## Prerequisites

-   Python 3.10 or a compatible version supported by your installed
    dependencies
-   `pip`
-   A Groq API key
-   Resend Gmail APi Key for Otp Verification Testing

FAISS and PyTorch-related dependencies can be large. Use a virtual
environment and allow installation to complete.

## Local Setup

### 1. Clone the repository

``` bash
git clone https://github.com/Aryan-018008/DocuMind-AI.git
cd DocuMind-AI
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt:

``` bat
.venv\Scripts\activate.bat
```

**macOS / Linux:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root. Never commit this file.

``` dotenv
FLASK_SECRET_KEY=replace_with_a_long_random_secret
GROQ_API_KEY=replace_with_your_groq_api_key

RESEND_API_KEY =replace_with_your_resend_key ( You can use other api key as well)
```

Only include variables required by the code you are running. If the
application uses a configurable Groq model name or other settings, add
those variables according to your configuration module.

For Gmail SMTP, use a Google App Password where applicable, not your
normal account password. Keep all credentials private.

### 5. Start the application

``` bash
python app.py
```

Open the local URL printed by Flask in your terminal (commonly
`http://127.0.0.1:5000`).

The development server is for local testing, not for production.

## Configuration Notes

-   `FLASK_SECRET_KEY` is required by the application for session
    security.
-   `GROQ_API_KEY` is required for Groq-backed AI responses.
-   `RESEND_API_KEY is required for Otp_Verification` 
-   Confirm that upload limits, allowed file types, database
    initialization, and model settings match your current
    implementation.

## Deployment Notes

For a Linux-based host such as Render, configure a production WSGI
server (for example, Gunicorn) and set secrets through the host's
environment-variable settings rather than committing `.env`.

Before deploying, verify:

-   the correct production start command for your Flask entry point;
-   all required environment variables are configured;
-   SQLite database files and uploaded documents are stored on
    persistent storage if they must survive restarts or redeploys;
-   FAISS indexes and embedding models are generated or restored as
    expected;
-   the application does not rely on files that exist only on your
    development machine.

`gunicorn` is not natively supported as a Windows development server; it
is typically used on Linux deployment environments.

## Security and Data Handling

-   Do not commit `.env`, API keys, SMTP credentials, private PDFs,
    local database files, or generated indexes.
-   Keep dependencies updated and review upload validation before
    exposing the application publicly.
-   Treat AI output as assistance, not authoritative advice. Verify
    important claims against the original PDF.
-   Review your hosting provider and AI provider's data-handling terms
    before uploading confidential documents.
-   Configure authentication, authorization, and file access controls
    carefully before production use.

## Troubleshooting

**`FLASK_SECRET_KEY is missing from .env`** - Confirm `.env` exists in
the project root and contains `FLASK_SECRET_KEY=...`. - Restart the
Flask process after changing environment variables.

**Groq client reports a missing API key** - Check that `GROQ_API_KEY` is
set correctly and loaded by the application. - Never paste the key into
source code or public issue reports.

**Gmail OTP delivery fails** - Check `RESEND_API_KEY`. - Verify that RESEND_API_KEY  configuration is enabled for the account.

**FAISS or Sentence Transformers installation fails** - Confirm your
Python version and platform compatibility. - Try installing dependencies
inside a fresh virtual environment and review the full pip error output.

**Uploaded documents disappear after deployment** - The host's
filesystem may be ephemeral. Configure persistent storage and ensure
upload/database paths point to it.

## Development

Contributions and issue reports are welcome. Before opening a pull
request:

1.  Reproduce the issue locally.
2.  Keep secrets and private documents out of commits.
3.  Test authentication, upload, document selection, chat, and error
    handling.
4.  Document any new environment variables or setup steps.

## Limitations

-   AI-generated answers may be incomplete or incorrect.
-   Retrieval quality depends on extracted text, chunking, and
    embeddings.
-   Scanned PDFs may not produce useful text without OCR.
-   Persistent storage and production security depend on deployment
    configuration.

## Author
Aryan Bharadwaj
