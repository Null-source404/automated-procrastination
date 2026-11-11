# Relies on gemini api key for the bot to work
import os
import time
from playwright.sync_api import sync_playwright
from google import genai

#==============================================================================
# ⚠️ SECURITY WARNING: HARDCODED API KEY ⚠️
# TODO: MIGRATION REMINDER! 
# You have a hardcoded API key below for rapid testing. Before pushing this 
# code to GitHub or sharing it, remove the hardcoded string and use: 
# client = genai.Client() (which automatically picks up GOOGLE_API_KEY from environment)
# ==============================================================================
API_KEY = "GEMINI_API_KEY"
# Initialize Gemini client using the modern google-genai SDK
client = genai.Client(api_key=API_KEY)

# Toggle: True  -> Runs locally against sandbox simulation
# Toggle: False -> Runs live against the real Ribara portal (uoem.ribara.co)
TEST_MODE = True 

TOTAL_TASKS = 27
MAX_QUESTIONS_PER_TASK = 8
# ===============================================================================

def run_portal_slayer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        if TEST_MODE:
            print("[*] Running in TEST MODE: Loading local clone sandbox...")
            local_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
            if not os.path.exists(local_file):
                raise FileNotFoundError(f"Local test page not found: {local_file}")
            page.goto(f"file:///{local_file.replace('\\', '/')}" )
        else:
            print("[*] Running in LIVE MODE: Connecting to Ribara portal...")
            page.goto("https://uoem.ribara.co/login")
            input(">>> Log into your account manually in the browser, navigate to your task, then hit ENTER here...")

        # Main Task Loop (Up to 27 Tasks)
        for task_num in range(1, TOTAL_TASKS + 1):
            print(f"\n==================== TASK {task_num} of {TOTAL_TASKS} ====================")
            
            question_count = 0
            
            # Question Loop (Up to 8 Questions per Task)
            while question_count < MAX_QUESTIONS_PER_TASK:
                try:
                    start_time = time.time()
                    
                    # 1. Check for textareas (ensures active question view)
                    textareas = page.locator("textarea.answer-box, textarea")
                    if textareas.count() == 0:
                        print("[*] No active answer boxes found. Moving forward.")
                        break

                    target_box = textareas.first

                    # 2. Extract clean question text from DOM first (fixes NameError)
                    try:
                        question_text = page.locator(".question-title, h3, .card-body").inner_text()
                    except:
                        page_text = page.inner_text("body")
                        question_text = page_text[:800] # Fallback slice

                    # Optional: Print timer if visible in DOM
                    try:
                        timer_val = page.inner_text("#timer")
                        print(f"[*] Active Timer: {timer_val}")
                    except:
                        pass

                    # 3. Query Gemini AI with Circuit Breaker & Fallback
                    print(f"[*] Processing Question {question_count + 1} with student tone...")
                    
                    prompt = f"""You are a university student completing a practical coursework task. 
                    Write a natural, slightly conversational, and practical answer (2-3 sentences max). 
                    CRITICAL: Do NOT sound like a robotic AI or an encyclopedia. Avoid overly stiff academic boilerplate or rigid formatting. 
                    Write it in a natural first-person student voice (e.g., using phrases like 'I would start by...', 'First, we need to...'). 
                    Keep it realistic so it looks like a human typed it out quickly.

                    Current question:
                    {question_text}
                    """
                    
                    ai_answer = None
                    max_api_retries = 3
                    
                    for attempt in range(1, max_api_retries + 1):
                        try:
                            print(f"[*] API Attempt {attempt} of {max_api_retries}...")
                            response = client.models.generate_content(
                                model='gemini-3.8-flash',
                                contents=prompt,
                                config={"http_options": {"timeout": 10000}} # 10s strict timeout
                            )
                            ai_answer = response.text.strip()
                            break # Success! Break out of retry loop
                        except Exception as api_err:
                            print(f"[!] Attempt {attempt} failed: {api_err}")
                            if attempt == max_api_retries:
                                print("[!] API exhausted retries. Using intelligent fallback answer to keep mission alive...")
                                ai_answer = "I would approach this by reviewing the core requirements, implementing the solution step-by-step, and verifying the output against standard test cases."
                            else:
                                time.sleep(3) # Short pause before next try

                    # 4. Inject answer into DOM and trigger HITL Review Checkpoint
                    target_box.click()
                    target_box.fill(ai_answer)
                    print(f"\n[+] Answer injected into browser!")
                    print(f"--------------------------------------------------")
                    print(f"👉 Check your browser window right now!")
                    print(f"   - Edit it directly if you want to tweak it.")
                    print(f"   - Or just press ENTER here to approve and submit.")
                    print(f"--------------------------------------------------")
                    
                    user_action = input(">>> Press ENTER to submit (or type 'skip' to pass this question): ").strip().lower()
                    
                    if user_action == 'skip':
                        print("[*] Skipping question manually...")
                        question_count += 1
                        continue

                    # 5. Handle Submission / Next Button
                    submit_btn = page.locator("button#submit-btn, button:has-text('Submit'), button:has-text('Next'), button:has-text('Save')").first
                    if submit_btn.is_visible():
                        submit_btn.click()
                        print(f"[✓] Answer submitted successfully!")
                        if not TEST_MODE:
                            page.wait_for_load_state("networkidle", timeout=10000)

                    question_count += 1
                    elapsed = round(time.time() - start_time, 2)
                    print(f"[✓] Question cleared and submitted in {elapsed}s!")
                    
                    time.sleep(2) # Human-pace breather

                    if TEST_MODE and question_count >= 2:
                        print("[TEST MODE] Reached sample limit for this task. Simulating task shift...")
                        break

                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "UNAVAILABLE" in error_msg or "rate limit" in error_msg.lower():
                        print(f"[!] Gemini API is jammed (Traffic spike/503). Backing off for 12 seconds...")
                        time.sleep(12)
                    elif "Target page, context or browser has been closed" in error_msg or "Timeout" in error_msg:
                        print(f"[!] Browser or webpage lag caught: {error_msg}. Retrying connection...")
                        time.sleep(5)
                    else:
                        print(f"[!] Unexpected glitch caught: {e}. Retrying in 5 seconds...")
                        time.sleep(5)

            if TEST_MODE and task_num >= 2:
                print("\n[✓] Test simulation loop finished successfully.")
                break

        print("\n[🎉] Automation sequence completed!")
        input(">>> Press ENTER to close the browser session...")
        browser.close()

if __name__ == "__main__":
    run_portal_slayer()
