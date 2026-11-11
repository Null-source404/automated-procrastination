# Lazy Assessment Assistant

## What this project does

This folder contains a small browser-based assessment sandbox and two Python
helpers that read the question shown in a browser, generate a draft answer, and
put that draft into the page's answer box. You can review or edit the draft
before submitting it.

The two helpers use different AI providers:

- `offline.py` sends the question to a local Ollama server. The model runs on
your computer; the script itself does not send the prompt to Gemini.
- `school.py` sends the question to Google's Gemini API. It requires internet
access and a valid Gemini API key.

Use the local sandbox to practice and check the browser/terminal interaction.
Only use the live-site mode where you are authorized to do so and AI assistance
is permitted.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Self-contained practice portal. It displays 8 software-engineering questions for each of 5 simulated tasks, has a four-minute per-question timer, and provides a Submit & Next button. It does not need a web server. |
| `offline.py` | Playwright browser helper using Ollama's local `/api/generate` endpoint. It prints the question and progress in the terminal, fills a draft, and waits for you to press Enter in the terminal or click Submit in the browser. Press `S` in the terminal to skip. |
| `school.py` | Playwright browser helper using the Gemini API. It fills a generated draft and waits for Enter in the terminal to submit, or `skip` to continue. Its test mode limits the run to two questions per task and two tasks. |
| `README.md` | Setup and usage instructions for this folder. |
| `env/` | Local Python virtual environment currently present in this folder. It is not source code and normally should not be committed. |

## Requirements

- Windows (the current `offline.py` uses the Windows-only standard-library
module `msvcrt` to read terminal keys without blocking).
- Python 3.12 or another compatible Python version.
- Playwright's Python package and its Chromium browser.
- For `offline.py`: Ollama running locally, with the configured model available.
- For `school.py`: the `google-genai` package, internet access, and a valid
Gemini API key.

The `env` environment was checked while preparing this guide: it has Playwright
and Requests installed, but `google-genai` was not found. There is no dependency
manifest in this folder, so install packages into the environment before first
use.

## One-time setup

Open PowerShell and change to this folder:

```powershell
Set-Location "C:\Users\HP\Downloads\Desktop\DevFest 2025\Python\Lazy"
.\env\Scripts\Activate.ps1
```

If PowerShell reports that script execution is disabled, use the environment's
Python executable directly instead of activating it:

```powershell
.\env\Scripts\python.exe -m pip install playwright requests google-genai
.\env\Scripts\python.exe -m playwright install chromium
```

If the environment is not present, create it first:

```powershell
py -3 -m venv env
.\env\Scripts\python.exe -m pip install playwright requests google-genai
.\env\Scripts\python.exe -m playwright install chromium
```

Installing `google-genai` is only necessary for `school.py`; installing
`requests` is only necessary for `offline.py`. Playwright and Chromium are
needed by both.

### Ollama setup for `offline.py`

Install Ollama, then download the model configured in `offline.py` (currently
`llama3.2`) and make sure the Ollama service is running:

```powershell
ollama pull llama3.2
ollama serve
```

If Ollama is already running as a background service, do not start a second
`ollama serve` process. The script calls
`http://localhost:11434/api/generate` and allows up to 120 seconds for a
response. Change `LOCAL_MODEL` in `offline.py` if you want to use another
model that is installed in Ollama.

### Gemini setup for `school.py`

`school.py` currently sets `API_KEY` to the placeholder string
`GEMINI_API_KEY`. Replace it with a valid key before using the script, or update
the program to read the key from an environment variable. Do not commit or
share a real API key. The Gemini model name is set in the source; it must be
available to the key/account being used.

## Running `offline.py`

1. Complete the one-time setup and start Ollama.
2. Open `offline.py` and set `TEST_MODE = True` to use the local
`index.html` sandbox. The checked-in default is `False`, which opens the live
portal URL configured in the script.
3. From PowerShell in this folder, run:

   ```powershell
   .\env\Scripts\python.exe .\offline.py
   ```

4. In test mode, the Chromium window opens the local portal. In live mode,
sign in in the browser and navigate to the authorized task, then press Enter
in the terminal when prompted.
5. Check the question printed in the terminal against the one shown in the
browser. The script generates a draft and fills the browser answer box.
6. Review or edit the draft in the browser. Press Enter in the terminal to
submit the text currently in the browser, click the page's Submit/Next
button to submit there, or press `S` in the terminal to skip.
7. The script continues until there is no answer box (the sandbox displays its
completion screen after all 40 questions). Press Enter at the final prompt
to close Chromium.

If Ollama is unavailable, the model is missing, or Ollama returns an empty
answer, the script reports an error instead of silently generating a generic
fallback answer.

## Running `school.py`

1. Install the dependencies, configure a valid Gemini API key as described
above, and ensure the Gemini model in the source is available to your
account.
2. `school.py` currently has `TEST_MODE = True`, so it opens the local
`index.html` sandbox. Set it to `False` in the source only when you intend
to use the live portal and are authorized to do so.
3. Run it from PowerShell in this folder:

   ```powershell
   .\env\Scripts\python.exe .\school.py
   ```

4. Review the browser draft, edit it if needed, and press Enter in the terminal
to submit. Type `skip` to skip according to the script's current behavior.
5. Press Enter at the final prompt to close the browser.

In test mode, the script intentionally stops after two questions in each of
the first two tasks; it does not complete the sandbox's full set of 40
questions. Also, the current `skip` branch increments the script's question
counter without clicking the page's Submit/Next button, so the browser may
remain on the same question. Prefer not to use `skip` until that behavior is
fixed.

## Important mode and workflow notes

- `TEST_MODE` is a source-code setting in each script; it is not currently a
command-line option.
- The sandbox is defined by `index.html` and contains 5 tasks with 8 questions
 each. It is separate from the live portal.
- `offline.py` uses Ollama locally for generation, but live mode still opens a
remote portal in a browser. “Offline” describes the AI inference provider,
not the entire live-site workflow.
- `school.py` uses a Gemini API and can incur account usage or charges.
- Browser automation depends on the page having recognizable question,
textarea, and submit-button elements. If the live site changes its page
structure, the selectors or navigation behavior may need updating.
- Treat generated answers as drafts: verify correctness and follow the rules
that apply to the assessment before submitting them.
