"""
summarizer.py – AI Integration Module for ScholarMind
Sends extracted web content to AI and generates:
  1. A structured academic research report (multi-language)
  2. A slide-ready summary (JSON) for PowerPoint generation
  3. A timed presentation speech script

Includes automatic retry with backoff for rate-limit (429) errors,
and model fallback if the primary model quota is exhausted.
"""

import os
import json
import re
import time
from dotenv import load_dotenv
from google import genai

# Load API key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Initialize the client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# Models to try in order (each has separate quota)
MODEL_PRIORITY = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

# Supported languages
SUPPORTED_LANGUAGES = {
    "English": "English",
    "Hindi": "हिन्दी (Hindi)",
    "Marathi": "मराठी (Marathi)",
    "Sanskrit": "संस्कृतम् (Sanskrit)",
    "Tamil": "தமிழ் (Tamil)",
    "Telugu": "తెలుగు (Telugu)",
    "Bengali": "বাংলা (Bengali)",
    "Gujarati": "ગુજરાતી (Gujarati)",
    "Kannada": "ಕನ್ನಡ (Kannada)",
    "Urdu": "اردو (Urdu)",
    "Malayalam": "മലയാളം (Malayalam)",
    "Punjabi": "ਪੰਜਾਬੀ (Punjabi)",
}


# ── Research Report Prompt ──────────────────────────────────────────
RESEARCH_PROMPT = """
Generate a comprehensive, in-depth academic-level research report on "{topic}".

**IMPORTANT: Write the ENTIRE report in {language}.**

Use the following reference material gathered from the web to inform your report.
Do NOT simply summarize it — deeply analyze, synthesize, restructure, and expand
with your own knowledge to produce a thorough, well-organized research document.

--- REFERENCE MATERIAL ---
{content}
--- END REFERENCE MATERIAL ---

--- SOURCE URLS ---
{sources}
--- END SOURCE URLS ---

Follow this exact structure:

1. Executive Summary
2. Introduction
3. Historical Background & Evolution
4. Core Concepts and Theoretical Framework
5. Technical Architecture / Working Mechanism (if applicable)
6. Methodology & Research Approaches
7. Real-World Applications & Use Cases
8. Case Studies & Industry Examples
9. Comparative Analysis
10. Advantages and Strengths
11. Limitations, Challenges & Ethical Considerations
12. Current Trends and Innovations
13. Future Scope & Emerging Directions
14. Conclusion
15. References & Sources (numbered list — include URLs from the source list above)

FORMATTING RULES:
- Use clear headings and subheadings (e.g., "## 1. Executive Summary").
- Use bullet points where appropriate.
- Maintain professional academic tone throughout.
- Avoid repetition — each section must add unique value.
- Ensure logical flow between sections.
- Provide deep analysis, not surface-level explanation.
- Content must be detailed, analytical, and evidence-based — no filler text.
- Each section should have at least 3-4 substantive paragraphs or structured points.
- In the References section, include the actual URLs from the source material.
- Write everything in {language}.
"""


# ── Slide Summary Prompt ───────────────────────────────────────────
SLIDES_PROMPT = """
Based on the following research report, generate a JSON array of slides
for a professional PowerPoint presentation.

**IMPORTANT: Write ALL slide content in {language}.**

--- RESEARCH REPORT ---
{report}
--- END RESEARCH REPORT ---

Generate EXACTLY 14 slides with this structure:

Slide 1: Title Slide — title = the topic name, bullets = ["Research Presentation", "Powered by ScholarMind"]
Slide 2: Executive Summary — 5-6 key bullet points
Slide 3: Introduction & Background — 5-6 bullet points
Slide 4: Historical Evolution — 5-6 bullet points
Slide 5: Core Concepts & Theory — 5-6 bullet points
Slide 6: Technical Architecture / How It Works — 5-6 bullet points
Slide 7: Research Methodology — 4-5 bullet points
Slide 8: Real-World Applications — 5-6 bullet points
Slide 9: Case Studies & Examples — 4-5 bullet points
Slide 10: Advantages & Strengths — 5-6 bullet points
Slide 11: Challenges & Limitations — 5-6 bullet points
Slide 12: Current Trends & Innovations — 5-6 bullet points
Slide 13: Future Scope & Conclusion — 5-6 bullet points
Slide 14: References — list 5-6 key references with URLs

CRITICAL RULES:
- Each bullet must be ONE concise sentence (max 15 words).
- Do NOT write paragraphs — only short, punchy bullet points.
- Return ONLY valid JSON — no markdown, no explanation.
- Write all content in {language}.

JSON format:
[
  {{"title": "Slide Title", "bullets": ["Point 1", "Point 2", "Point 3"]}},
  ...
]
"""


# ── Presentation Speech Prompt ────────────────────────────────────
SPEECH_PROMPT = """
Generate a professional presentation speech script for the following research topic.

**IMPORTANT: Write the ENTIRE speech in {language}.**

The presentation has {num_slides} slides and the speech should be designed
for approximately {duration} minutes of speaking time.

--- SLIDE DATA ---
{slides_json}
--- END SLIDE DATA ---

--- RESEARCH SUMMARY ---
{report_summary}
--- END RESEARCH SUMMARY ---

Generate a speech script with the following format:

For each slide, write:
- [SLIDE X: Title] (time: MM:SS - MM:SS)
- The spoken text for that slide (2-4 paragraphs per slide)
- Speaker notes/tips in brackets [Tip: ...]

RULES:
- Use a professional, engaging speaking tone.
- Include transitions between slides ("Moving on to...", "Let's now look at...").
- Add audience engagement cues ("As you can see...", "This is particularly important because...").
- Pace the speech naturally across the {duration}-minute duration.
- Include an opening greeting and closing thank you.
- Write everything in {language}.
"""


def _call_gemini(prompt: str, max_tokens: int = 8192, temperature: float = 0.7) -> str:
    """
    Call AI with automatic retry and model fallback.
    Tries each model in MODEL_PRIORITY until one succeeds.
    Retries up to 3 times per model on rate-limit errors.
    """
    if not client:
        raise ValueError("API key not set. Please configure GEMINI_API_KEY in your .env file.")

    last_error = None

    for model_name in MODEL_PRIORITY:
        for attempt in range(3):  # Up to 3 retries per model
            try:
                print(f"[ScholarMind] Trying {model_name} (attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                )
                print(f"[ScholarMind] Success with {model_name}")
                return response.text

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Rate limit (429) — wait and retry
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    delay_match = re.search(r"retry\s*in\s*([\d.]+)s", error_str, re.I)
                    wait_time = float(delay_match.group(1)) if delay_match else (10 * (attempt + 1))
                    print(f"[ScholarMind] Rate limited on {model_name}. Waiting {wait_time:.0f}s...")

                    if attempt < 2:
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[ScholarMind] {model_name} exhausted, trying next model...")
                        break

                # Other API errors — try next model
                else:
                    print(f"[ScholarMind] Error with {model_name}: {e}")
                    break

    # All models failed
    raise RuntimeError(
        f"All AI models failed. Last error: {last_error}\n"
        "Your API quota may be exhausted. Please wait a few minutes and try again."
    )


def generate_report(topic: str, content: str, language: str = "English", sources: list = None) -> str:
    """
    Generate a structured research report.

    Args:
        topic: The research topic.
        content: Merged web content corpus.
        language: Output language (default: English).
        sources: List of source URLs.

    Returns:
        The full research report as a string.
    """
    sources_text = ""
    if sources:
        sources_text = "\n".join([f"- {s.get('title', 'Source')}: {s.get('url', '')}" for s in sources])
    else:
        sources_text = "No source URLs available."

    prompt = RESEARCH_PROMPT.format(
        topic=topic,
        language=language,
        content=content,
        sources=sources_text
    )
    report = _call_gemini(prompt, max_tokens=8192, temperature=0.7)
    print(f"[ScholarMind] Generated report: {len(report)} chars in {language}")
    return report


def generate_slides_json(topic: str, report: str, language: str = "English") -> list[dict]:
    """
    Generate a slide-ready JSON summary from the research report.

    Args:
        topic: The research topic.
        report: The full research report text.
        language: Output language.

    Returns:
        A list of dicts, each with 'title' and 'bullets' keys.
    """
    prompt = SLIDES_PROMPT.format(report=report, language=language)
    raw = _call_gemini(prompt, max_tokens=4096, temperature=0.5)
    raw = raw.strip()

    # Clean up: remove ```json ... ``` wrapper if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        slides = json.loads(raw)
    except json.JSONDecodeError:
        print("[ScholarMind] Failed to parse slides JSON, using fallback.")
        slides = _fallback_slides(topic, report)

    # Ensure the title slide has the topic name
    if slides and slides[0]:
        slides[0]["title"] = topic

    print(f"[ScholarMind] Generated {len(slides)} slides")
    return slides


def generate_speech(topic: str, slides_data: list, report: str,
                    duration: int = 10, language: str = "English") -> str:
    """
    Generate a timed presentation speech script.

    Args:
        topic: The research topic.
        slides_data: List of slide dicts with 'title' and 'bullets'.
        report: The full research report (used for context).
        duration: Speech duration in minutes.
        language: Output language.

    Returns:
        The speech script as a string.
    """
    # Use first 3000 chars of report as summary context
    report_summary = report[:3000] + "..." if len(report) > 3000 else report

    slides_json = json.dumps(slides_data, ensure_ascii=False, indent=2)

    prompt = SPEECH_PROMPT.format(
        topic=topic,
        language=language,
        num_slides=len(slides_data),
        duration=duration,
        slides_json=slides_json,
        report_summary=report_summary,
    )
    speech = _call_gemini(prompt, max_tokens=8192, temperature=0.7)
    print(f"[ScholarMind] Generated speech: {len(speech)} chars ({duration} min, {language})")
    return speech


def _fallback_slides(topic: str, report: str) -> list[dict]:
    """Generate basic fallback slides if JSON parsing fails."""
    sections = [
        "Executive Summary", "Introduction & Background",
        "Historical Evolution", "Core Concepts & Theory",
        "Technical Architecture", "Research Methodology",
        "Real-World Applications", "Case Studies",
        "Advantages & Strengths", "Challenges & Limitations",
        "Current Trends", "Future Scope & Conclusion",
        "References",
    ]

    slides = [{"title": topic, "bullets": ["Research Presentation", "Powered by ScholarMind"]}]

    for section in sections:
        slides.append({
            "title": section,
            "bullets": [
                f"Key insight about {section.lower()} in {topic}",
                f"Important aspect of {section.lower()}",
                f"Notable finding related to {section.lower()}",
                f"Significant development in this area",
            ],
        })

    return slides[:14]


# ── Chat Prompt ──────────────────────────────────────────────────
CHAT_PROMPT = """
You are ScholarMind, an expert AI research assistant. The user has generated
a research report on "{topic}" and now wants to ask follow-up questions.

**Respond in {language}.**

--- RESEARCH REPORT CONTEXT ---
{report_context}
--- END CONTEXT ---

User Question: {user_message}

INSTRUCTIONS:
- Answer the question based on the research context above.
- If the question is about something not covered in the report, use your
  general knowledge but note that it's beyond the report's scope.
- Be detailed, helpful, and precise.
- Use bullet points and clear structure when appropriate.
- Respond in {language}.
"""


def chat_with_context(
    user_message: str,
    topic: str = "general",
    report_context: str = "",
    language: str = "English",
) -> str:
    """
    Answer a follow-up question using the research report as context.

    Args:
        user_message: The user's question.
        topic: The research topic.
        report_context: The full report for context (first 4000 chars used).
        language: Response language.

    Returns:
        The AI's answer as a string.
    """
    # Use at most 4000 chars of context to stay within token limits
    context = report_context[:4000] + "..." if len(report_context) > 4000 else report_context

    if not context:
        context = "No research report has been generated yet. Answer using general knowledge."

    prompt = CHAT_PROMPT.format(
        topic=topic,
        language=language,
        report_context=context,
        user_message=user_message,
    )
    reply = _call_gemini(prompt, max_tokens=4096, temperature=0.7)
    print(f"[ScholarMind Chat] Reply: {len(reply)} chars")
    return reply


if __name__ == "__main__":
    print("ScholarMind Summarizer module loaded.")
    print(f"Models to try: {MODEL_PRIORITY}")
    print(f"Supported languages: {list(SUPPORTED_LANGUAGES.keys())}")
    print("Requires GEMINI_API_KEY in .env to function.")
