# AI Research Assistant

A production-quality web application that generates comprehensive, structured, academic-level research reports using AI.

## Features

- **Web Search** – Automatically searches multiple sources via DuckDuckGo
- **Content Extraction** – Scrapes and cleans web content with BeautifulSoup
- **AI-Powered Reports** – Generates structured research using Google Gemini
- **PDF Export** – Produces professional, formatted PDF reports (reportlab Platypus)
- **PowerPoint Export** – Creates 10-slide research presentations (python-pptx)
- **Modern UI** – Dark-themed, responsive frontend with glassmorphism design

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, Flask |
| AI | Google Gemini API |
| Search | DuckDuckGo (no API key needed) |
| Scraping | requests, BeautifulSoup4 |
| PDF | reportlab (Platypus) |
| PPT | python-pptx |
| Frontend | HTML5, CSS3, JavaScript |

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit the `.env` file and add your Google Gemini API key:

```
GEMINI_API_KEY=your_actual_api_key_here
```

You can get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run the Application

```bash
python app.py
```

Open your browser and navigate to: **http://127.0.0.1:5000**

## Usage

1. Enter a research topic (e.g., "Quantum Computing", "CRISPR Gene Editing")
2. Click **Generate Report**
3. Wait for the AI to search, analyze, and generate your report
4. View the formatted report on the webpage
5. Download the **PDF** or **PowerPoint** using the buttons

## Project Structure

```
research_agent/
├── app.py              # Flask application & routes
├── search.py           # Web search module (DuckDuckGo)
├── scraper.py          # Content extraction & merging
├── summarizer.py       # Gemini API integration
├── pdf_generator.py    # PDF report generation
├── ppt_generator.py    # PowerPoint presentation generation
├── templates/
│   └── index.html      # Frontend template
├── static/
│   └── style.css       # Stylesheet
├── output/             # Generated PDF & PPT files
├── .env                # API key configuration
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Report Structure

The AI generates reports with these sections:

1. Executive Summary
2. Introduction
3. Historical Background
4. Core Concepts and Theory
5. Technical Architecture / Working Mechanism
6. Real-World Applications
7. Case Studies
8. Advantages and Strengths
9. Limitations and Challenges
10. Current Trends and Innovations
11. Future Scope
12. Conclusion
13. References

## License

MIT License
