"""
app.py – ScholarMind Flask Application
AI-powered research platform with multi-language support,
user authentication, and interactive presentations.

Pipeline: search → scrape → analyze → report → PDF → PPT → speech
"""

import os
from flask import Flask, render_template, request, jsonify, send_file, session
from auth import auth_bp, init_db, login_required
from search import search_web
from scraper import scrape_and_merge
from summarizer import (
    generate_report, generate_slides_json, generate_speech,
    chat_with_context, SUPPORTED_LANGUAGES
)
from pdf_generator import generate_pdf
from ppt_generator import generate_ppt

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Register auth blueprint
app.register_blueprint(auth_bp)

# Initialize database
init_db()

# ── Output paths ────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
PDF_PATH = os.path.join(OUTPUT_DIR, "report.pdf")
PPT_PATH = os.path.join(OUTPUT_DIR, "presentation.pptx")
SPEECH_PATH = os.path.join(OUTPUT_DIR, "speech.txt")

# Store last generation data for speech generation
_last_generation = {}


# ── Routes ──────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    """Render the main research page."""
    return render_template(
        "index.html",
        languages=SUPPORTED_LANGUAGES,
        username=session.get("username", "Researcher"),
    )


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    """
    Main research pipeline endpoint.
    Accepts JSON: { "topic": "...", "language": "..." }
    Returns JSON with the research report text and source links.
    """
    global _last_generation

    data = request.get_json()
    topic = data.get("topic", "").strip() if data else ""
    language = data.get("language", "English") if data else "English"

    if not topic:
        return jsonify({"error": "Please enter a research topic."}), 400

    if language not in SUPPORTED_LANGUAGES:
        language = "English"

    try:
        # Step 1: Search the web
        print(f"\n{'='*60}")
        print(f"  ScholarMind Research Pipeline: {topic}")
        print(f"  Language: {language}")
        print(f"{'='*60}")

        print("\n[Pipeline] Step 1/5: Searching the web...")
        search_results = search_web(topic, max_results=10)

        if not search_results:
            return jsonify({
                "error": "No search results found. Please try a different topic."
            }), 404

        # Step 2: Scrape and extract content
        print("[Pipeline] Step 2/5: Extracting content from sources...")
        corpus = scrape_and_merge(search_results, max_pages=6)

        if not corpus or len(corpus) < 100:
            return jsonify({
                "error": "Could not extract sufficient content. Please try a different topic."
            }), 404

        # Step 3: Generate research report
        print(f"[Pipeline] Step 3/5: Generating research report in {language}...")
        report = generate_report(topic, corpus, language=language, sources=search_results)

        # Step 4: Generate PDF
        print("[Pipeline] Step 4/5: Generating PDF report...")
        generate_pdf(topic, report)

        # Step 5: Generate PowerPoint
        print("[Pipeline] Step 5/5: Generating PowerPoint presentation...")
        slides_data = generate_slides_json(topic, report, language=language)
        generate_ppt(topic, slides_data, language=language)

        # Store for speech generation
        _last_generation = {
            "topic": topic,
            "report": report,
            "slides_data": slides_data,
            "language": language,
        }

        # Extract source links
        source_links = []
        for r in search_results:
            source_links.append({
                "title": r.get("title", "Source"),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", ""),
            })

        print(f"\n{'='*60}")
        print(f"  Pipeline Complete!")
        print(f"{'='*60}\n")

        return jsonify({
            "success": True,
            "report": report,
            "topic": topic,
            "language": language,
            "sources": source_links,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[Pipeline] Error: {e}")
        return jsonify({
            "error": f"An error occurred during research generation: {str(e)}"
        }), 500


@app.route("/generate-speech", methods=["POST"])
@login_required
def generate_speech_route():
    """
    Generate a presentation speech script.
    Accepts JSON: { "duration": 10 }
    """
    global _last_generation

    if not _last_generation:
        return jsonify({"error": "Please generate a research report first."}), 400

    data = request.get_json()
    duration = data.get("duration", 10) if data else 10

    try:
        duration = int(duration)
        if duration not in [5, 10, 15, 20]:
            duration = 10
    except (ValueError, TypeError):
        duration = 10

    try:
        print(f"\n[Pipeline] Generating {duration}-min speech script...")
        speech = generate_speech(
            topic=_last_generation["topic"],
            slides_data=_last_generation["slides_data"],
            report=_last_generation["report"],
            duration=duration,
            language=_last_generation.get("language", "English"),
        )

        # Save speech to file
        with open(SPEECH_PATH, "w", encoding="utf-8") as f:
            f.write(f"ScholarMind Presentation Speech\n")
            f.write(f"Topic: {_last_generation['topic']}\n")
            f.write(f"Duration: {duration} minutes\n")
            f.write(f"Language: {_last_generation.get('language', 'English')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(speech)

        return jsonify({
            "success": True,
            "speech": speech,
            "duration": duration,
        })

    except Exception as e:
        print(f"[Pipeline] Speech error: {e}")
        return jsonify({
            "error": f"Failed to generate speech: {str(e)}"
        }), 500


@app.route("/download/pdf")
@login_required
def download_pdf():
    """Download the generated PDF report."""
    if not os.path.exists(PDF_PATH):
        return jsonify({"error": "PDF not yet generated. Please generate a report first."}), 404
    return send_file(
        PDF_PATH,
        as_attachment=True,
        download_name="ScholarMind_Report.pdf",
        mimetype="application/pdf",
    )


@app.route("/download/ppt")
@login_required
def download_ppt():
    """Download the generated PowerPoint presentation."""
    if not os.path.exists(PPT_PATH):
        return jsonify({"error": "PPT not yet generated. Please generate a report first."}), 404
    return send_file(
        PPT_PATH,
        as_attachment=True,
        download_name="ScholarMind_Presentation.pptx",
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.route("/download/speech")
@login_required
def download_speech():
    """Download the generated speech script."""
    if not os.path.exists(SPEECH_PATH):
        return jsonify({"error": "Speech not yet generated."}), 404
    return send_file(
        SPEECH_PATH,
        as_attachment=True,
        download_name="ScholarMind_Speech.txt",
        mimetype="text/plain",
    )


@app.route("/api/languages")
def get_languages():
    """Return supported languages."""
    return jsonify({"languages": SUPPORTED_LANGUAGES})

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    """
    Real-time AI chat about the current research topic.
    Accepts JSON: { "message": "..." }
    """
    global _last_generation

    data = request.get_json()
    user_message = data.get("message", "").strip() if data else ""

    if not user_message:
        return jsonify({"error": "Please enter a message."}), 400

    # Use last generation context if available
    context_report = _last_generation.get("report", "")
    context_topic = _last_generation.get("topic", "general research")
    context_language = _last_generation.get("language", "English")

    try:
        reply = chat_with_context(
            user_message=user_message,
            topic=context_topic,
            report_context=context_report,
            language=context_language,
        )
        return jsonify({
            "success": True,
            "reply": reply,
        })
    except Exception as e:
        print(f"[Chat] Error: {e}")
        return jsonify({
            "error": f"Chat error: {str(e)}"
        }), 500


# ── Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n╔══════════════════════════════════════════════╗")
    print("║     🔬 ScholarMind — Running                ║")
    print(f"║     http://0.0.0.0:{port}                      ║")
    print("╚══════════════════════════════════════════════╝\n")
    app.run(host="0.0.0.0", port=port)
