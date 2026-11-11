# Multi-Client Assessment Automation Tool
import os
import sys
import time
import random
import requests
import msvcrt
import re
from playwright.sync_api import sync_playwright

# ===============================================================================
# 🔑 CONFIGURATION & ENGINE SETUP
# ===============================================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "dolphin-phi"  # Ensure `ollama serve` is running

TARGET_URL = "https://uoem.ribara.co/dashboard/student/task-assessment"
# ===============================================================================

def get_client_identifier() -> str:
    """Extracts client name from terminal argument or defaults to 'default_client'."""
    if len(sys.argv) > 1:
        return sys.argv[1].strip().lower()
    return "default_client"

def generate_local_ai_response(question_text: str) -> str:
    """Queries local Ollama model with prompt framing and extended timeout."""
    payload = {
        "model": LOCAL_MODEL,
        "prompt": (
            f"You are a sharp, authentic software engineering student taking a timed university assessment. "
            f"Write a concise, direct 2-sentence response in the first person ('I would...', 'My approach...'). "
            f"Focus strictly on practical engineering execution, real-world tooling, and clean system design principles. "
            f"Avoid generic fluff, textbook definitions, or sounding robotic. Keep it grounded and technically precise.\n\nQuestion: {question_text}"
        ),
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 120
        }
    }
    
    try:
        # 60s timeout prevents dropping connections during heavy model evaluation
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not get a response from Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running."
        ) from exc

    answer = response.json().get("response", "").strip()
    if not answer:
        raise RuntimeError(f"Ollama returned an empty response for model {LOCAL_MODEL}.")
    return answer

def run_portal_slayer():
    client_id = get_client_identifier()
    # Dynamic profile directory per client to isolate cookies and sessions
    user_data_dir = os.path.abspath(f"profiles/{client_id}")
    
    print("\n" + "="*70)
    print(f"[+] INITIALIZING SESSION FOR CLIENT: {client_id.upper()}")
    print(f"[+] Profile Directory: {user_data_dir}")
    print("="*70 + "\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            no_viewport=True,
            args=["--start-maximized", "--disable-dev-shm-usage"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_navigation_timeout(30000)

        try:
            print(f"[*] Navigating to assessment portal for [{client_id}]...")
            page.goto(TARGET_URL, wait_until="commit", timeout=25000)
            time.sleep(2)
            
            # Manual login hand-off for new sessions or Google Sign-In
            if "auth.ribara.co" in page.url or "login" in page.url:
                print(f"\n[!] Authentication required for {client_id}!")
                print("[!] Complete the login manually in the browser window.")
                page.wait_for_url("**/dashboard/student/task-assessment", timeout=180000)
                print(f"[+] Authentication successful! Session saved for {client_id}.")

            print("\n" + "="*70)
            print(f"[!] AUTOMATION ACTIVE FOR: {client_id.upper()}")
            print("="*70 + "\n")

            last_answered_question = ""

            while True:
                try:
                    box_locator = page.locator("textarea, input[type='text'], [contenteditable='true']").filter(has_not=page.locator("[disabled]")).first
                    
                    if not box_locator.is_visible(timeout=2000):
                        print(f"[{client_id}] Waiting for active input box...", end="\r")
                        time.sleep(1)
                        continue

                    # Refined container scope with strict UI button & boilerplate filtering
                    question_text = page.evaluate("""() => {
                        const box = document.querySelector('textarea:not([disabled]), input[type="text"]:not([disabled]), [contenteditable="true"]');
                        if (!box) return null;
                        
                        let container = box.closest('div[class*="card"], div[class*="question"], div[class*="assessment"], form') || box.parentElement;
                        let rawText = container ? container.innerText : box.parentElement.innerText;
                        
                        let lines = rawText.split('\\n').map(l => l.trim()).filter(l => {
                            const lower = l.toLowerCase();
                            if (!l || l.length < 2) return false;
                            
                            // Blacklist UI button labels, navigation, and metadata headers
                            const uiBlacklist = [
                                'back', 'next', 'continue', 'submit', 'save', 'save and score', 
                                'final submit', 'overall progress', 'complete', 'difficulty:', 
                                'importance:', 'your answer', 'self assessment', 'objective assessment'
                            ];
                            
                            if (uiBlacklist.some(term => lower === term || lower.startsWith(term))) return false;
                            if (/^\\d{1,2}:\\d{2}$/.test(l) || /^\\d+%$/.test(l)) return false;
                            return true;
                        });
                        return lines.join('\\n').trim() || rawText;
                    }""")

                    if not question_text or question_text == last_answered_question:
                        time.sleep(1)
                        continue

                    last_answered_question = question_text

                    print(f"\n" + "-"*65)
                    print(f"[?] QUESTION ({client_id.upper()}):\n{question_text}")
                    print(f"-"*65)
                    print(f"[*] Querying Ollama for natural student response...")
                    
                    try:
                        ai_answer = generate_local_ai_response(question_text)
                    except Exception as e:
                        print(f"[!] Ollama error: {e}. Retrying...")
                        time.sleep(1)
                        continue

                    print(f"\n[!] GENERATED ANSWER:\n{ai_answer}")
                    print(f"-"*65)

                    # Inject response into portal input field
                    box_locator.fill(ai_answer)
                    
                    # CRITICAL FIX: Trigger input/change events so portal JavaScript enables the Next button instantly
                    box_locator.evaluate("node => { node.dispatchEvent(new Event('input', { bubbles: true })); node.dispatchEvent(new Event('change', { bubbles: true })); }")
                    print(f"[+] Answer injected and events dispatched for {client_id}!")

                    # Check for final submit button to trigger manual override
                    final_btn = page.locator("button").filter(
                        has_text=re.compile("save and score|submit assessment|final submit", re.IGNORECASE)
                    ).first

                    if final_btn.is_visible(timeout=1000) and final_btn.is_enabled():
                        print("\n" + "="*65)
                        print(f"[!] FINAL QUESTION REACHED FOR [{client_id.upper()}]!")
                        print("[!] MANUAL OVERRIDE: Review the answer and click 'Save & Score' in the browser.")
                        print("="*65 + "\n")
                        input("Press ENTER in this terminal after completing final submission...")
                        break

                    # Optimized, lightning-fast pacing delay (10-15 seconds)
                    delay_seconds = random.randint(10, 15)
                    print(f"[*] Quick pacing delay ({delay_seconds}s)... Press ENTER to skip instantly.")

                    for remaining in range(delay_seconds, 0, -1):
                        print(f"[~] Auto-advancing in {remaining:02d}s...", end="\r")
                        
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if key in [b'\r', b'\n', b' ']:
                                print(f"\n[!] Manual override triggered! Skipping remaining time...")
                                break
                                
                        time.sleep(1)

                    print("\n")
                    
                    # Locate, verify enabled state, and click 'Next' button safely
                    # --- RECOMMENDED SOLUTION ---
                    next_btn = page.locator("button:has-text('Next'), button:has-text('Continue'), button[type='submit']").first
                    
                    if next_btn.is_visible(timeout=2000):
                        try:
                            # Force-enable the button via JS if the portal validation lags
                            next_btn.evaluate("node => { node.removeAttribute('disabled'); node.classList.remove('disabled'); }")
                            
                            # Now click it instantly without waiting around
                            next_btn.click(force=True)
                            print(f"[OK] Force-advanced to next question for {client_id}.\n")
                            time.sleep(1.5)
                        except Exception as e:
                            print(f"[!] Could not auto-click Next: {e}. Please advance manually.")
                    else:
                        print(f"[!] Couldn't locate 'Next' button. Advance manually in browser.")
                except Exception as loop_err:
                    print(f"\n[!] Loop exception: {loop_err}")
                    time.sleep(2)

        finally:
            context.close()
            print(f"\n[*] Session closed for: {client_id}. Profile saved under profiles/{client_id}.")

if __name__ == "__main__":
    run_portal_slayer()
