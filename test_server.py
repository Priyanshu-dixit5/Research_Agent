"""Quick end-to-end test of ScholarMind server."""
import requests

BASE = "http://127.0.0.1:5000"
session = requests.Session()

# 1. Check redirect to login
r = session.get(f"{BASE}/", allow_redirects=False)
print(f"[1] GET /  → Status {r.status_code}, Location: {r.headers.get('Location', 'N/A')}")

# 2. Register
r = session.post(f"{BASE}/register", data={
    "username": "tester2",
    "email": "tester2@test.com",
    "password": "test123",
    "confirm_password": "test123",
}, allow_redirects=False)
print(f"[2] POST /register → Status {r.status_code}, Location: {r.headers.get('Location', 'N/A')}")

# 3. Login
r = session.post(f"{BASE}/login", data={
    "username": "tester2",
    "password": "test123",
}, allow_redirects=False)
print(f"[3] POST /login → Status {r.status_code}, Location: {r.headers.get('Location', 'N/A')}")

# 4. Follow redirect to main page
if r.status_code == 302:
    r = session.get(f"{BASE}/", allow_redirects=True)
    print(f"[4] GET / (after login) → Status {r.status_code}")
    has_scholarmind = "ScholarMind" in r.text
    has_topic_input = 'id="topic-input"' in r.text
    has_language = 'id="language-select"' in r.text
    has_chat_tab = 'tab-chat' in r.text
    has_tts = 'tts-controls' in r.text
    print(f"    ScholarMind branding: {has_scholarmind}")
    print(f"    Topic input: {has_topic_input}")
    print(f"    Language selector: {has_language}")
    print(f"    Chat tab: {has_chat_tab}")
    print(f"    TTS controls: {has_tts}")

# 5. Test /api/languages
r = session.get(f"{BASE}/api/languages")
print(f"[5] GET /api/languages → Status {r.status_code}")
if r.status_code == 200:
    langs = r.json().get("languages", {})
    print(f"    Languages: {list(langs.keys())}")

# 6. Test /chat endpoint (should work even without a report)
r = session.post(f"{BASE}/chat", json={"message": "Hello"})
print(f"[6] POST /chat → Status {r.status_code}")
if r.status_code == 200:
    reply = r.json().get("reply", "")
    print(f"    Reply length: {len(reply)} chars")
    print(f"    Reply preview: {reply[:120]}...")

print("\n✅ All endpoint tests completed!")
