import os
from flask import Flask, render_template
from routes.documents_routes import document_bp
from database.db import init_db
from routes.chat_routes  import chat_bp
from dotenv import load_dotenv


app = Flask(__name__)

load_dotenv()

app.config["MAX_CONTENT_LENGTH"] = 21 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path, "uploads"
)


# Sql File allocation
app.config["DATABASE"] = os.path.join(app.root_path,"database","documind.db")

# Register the PDF upload API
app.register_blueprint(document_bp)
app.register_blueprint(chat_bp)

# Database Creation
with app.app_context():
    init_db()


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
