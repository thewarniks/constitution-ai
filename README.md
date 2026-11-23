# Constitution Ai



A legal-help chatbot that explains legal problems and court cases in plain language. It can answer from your own reference datasets, such as laws, judgments, FAQs or case notes.

It gives general legal information, not legal advice. Users must accept a disclaimer before chatting, and the system prompt tells the model not to invent case citations and to recommend a lawyer for serious matters.

**Live preview:** https://thewarniks.github.io/constitution-ai/ (static pages on GitHub Pages; the AI chat needs the Python server, see below).

## Run it

You need Python 3.10 or newer.

1. Get the code and install the dependencies (once):

   ```bash
   git clone https://github.com/thewarniks/constitution-ai.git
   cd constitution-ai
   python -m venv .venv
   ```

   Then on Windows run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, or on macOS/Linux run `.venv/bin/python -m pip install -r requirements.txt`.

2. Copy `.env.example` to `.env` and fill in the key for each provider you'll use. A free Groq key is the quickest start. `.env` is ignored by git, so keys never get uploaded.

3. Start the web app. On Windows, double-click `start.bat` or run `.\.venv\Scripts\python.exe server.py`. On macOS/Linux, run `.venv/bin/python server.py`.

   Then open http://localhost:8000.

## GitHub Pages (static preview)

GitHub Pages can only host static files, so `docs/` holds an exported copy of the website pages. On that copy the chat and the contact form show a short notice, because they need the Python server.

After changing the website, rebuild the copy and commit it:

```bash
python export_static.py --base /constitution-ai/
```

To make the AI chat work online too, deploy `server.py` to a Python host such as Render, Railway or a VPS, and set your API keys there as environment variables.

| Address | What it is |
|---|---|
| http://localhost:8000/ | The website (built from the Aigocy template) |
| http://localhost:8000/chat | The website's chat page |
| http://localhost:8000/app | The chat dashboard |
| http://localhost:8000/classic | The old chat-ui page |

## The website

`website/` is a full site built from the **Aigocy** template in `aigocy/`. It uses the template's CSS, JavaScript, fonts, icons and page layouts, with legal content and new artwork. The template's own images were flat grey placeholders, so every image in `website/static/assets/images/legal/` is new.

| Page | Template page it is based on |
|---|---|
| Home `/` | `index.html`: hero, about, practice areas, use cases, how it works, benefits, features, AI engines, statistics, questions people ask, FAQ, contact |
| About `/about` | `about.html` |
| Practice Areas `/practice-areas` and one page per area | `service.html`, `service-single.html` |
| Use Cases `/use-cases` and one page per example | `work.html`, `work-single.html` |
| Guides `/guides` and one page per guide | `blog-three-columns.html`, `blog-single.html` |
| Contact `/contact` | `contact.html`. The form saves messages to `contact_messages.jsonl` |
| Ask the AI `/chat` | New page in the template's style, using the same chat backend |
| 404 | `404.html` |

**How it fits together:**
- **Routes:** `website/routes.py` holds the page routes and is registered in `server.py`.
- **Layout:** `website/templates/` holds the Jinja pages. `base.html` has the shared header, footer and mobile menu, and `_macros.html` has the repeated sections.
- **Text:** all page text lives in `website/site_content.py`: practice areas, use cases, guides, FAQs and stats. Edit that file to change what the site says. Set `contact_email` there to show an email on the Contact page.
- **Chat page:** `website/static/assets/js/site-chat.js` stores chats in the same browser storage as the dashboard, so both show the same chat history.

**What was changed or left out of the template:**
- **Fake material removed:** made-up team members, testimonials, awards, client logos and statistics.
- **Replacements:** a strip of the AI providers the app supports, example questions people ask, and facts about the product.
- **Demo-only controls removed:** the colour switcher.

The guides give general information on Indian law, reviewed November 2026. Re-check them when laws change.

## The dashboard

The dashboard (`static/index.html`, `static/app.js`) is at `/app`. Pick the provider and model under **Settings**.

- **Sidebar:** Dashboard, Chats, Datasets, Settings and About. Its card at the bottom points to free legal aid (NALSA helpline 15100 in India).
- **Dashboard:** the jurisdiction you're asking about, how many reference datasets are on, topic shortcuts (Tenancy, Consumer, Police, Family, Work) and a summary. The summary shows questions per day/week/month, how many were answered, and how many answers used your datasets.
- **Chat panel:**
  - streaming answers with markdown and an optional reasoning box
  - Stop, Regenerate and Copy
  - attach PDFs, Word or text files (their text is sent to the model) or photos (for vision models)
  - voice input with the mic button (Chrome/Edge)
  - download a chat as Markdown
- **Chats:** saved in your browser (localStorage), with search, open, download and delete.

Other versions:
- The old chat-ui page is still at http://localhost:8000/classic.
- The Streamlit version still works: `.\.venv\Scripts\python.exe -m streamlit run app.py` (http://localhost:8501).

## Free providers

| Provider | Get a free key | Put in `.env` | Notes |
|---|---|---|---|
| Groq | https://console.groq.com/keys | `GROQ_API_KEY=...` | Very fast; free plan has rate limits |
| Google Gemini | https://aistudio.google.com/apikey | `GEMINI_API_KEY=...` | Free tier with daily limits |
| OpenRouter | https://openrouter.ai/settings/keys | `OPENROUTER_API_KEY=...` | Only `:free` models are listed; `openrouter/free` picks one for you |
| Ollama | no key: install from https://ollama.com | nothing | Runs on your PC; run `ollama pull llama3.2` first |
| Hive (DeepSeek V4.1 Flash) | https://thehive.ai dashboard → Service API Keys → Create API Key | `HIVE_API_KEY=...` (the **Secret Key**) | OpenAI-style endpoint at `api-cdn.thehive.ai/api/v3` |

The model lists for these come live from each provider, so they stay current. After adding a key, restart the app. The first provider with a key is selected automatically, or you can set `DEFAULT_PROVIDER` in `.env`.

Free plans have usage limits, and free models may log your prompts. Avoid sending real private case details to free models.

## How it works

```
Streamlit app (app.py)
   |  legal system prompt + custom instructions + best dataset passages
   v
providers/*.json (your old chat-ui configs + free ones) Anthropic Claude
DeepSeek, OpenAI, DeepInfra, Qwen, NVIDIA NIM,           (llm.py)
Groq, Gemini, OpenRouter, Ollama
   (openai_compat.py: POST url + path,
    Bearer key, OpenAI-style streaming,
    the same way the old chat-ui did)
```

**Providers** come from your old chat-ui config files in `providers/`. Each one sets the URL, path, model list and max tokens; add another JSON file in the same format to add a provider.

**API keys:** `<NAME>_API_KEY` in `.env` (e.g. `DEEPSEEK_API_KEY`) is used first, otherwise the `apiKey` inside the provider's JSON file. Placeholder values like `your-...-here` count as no key.

**Reference datasets:** in the sidebar's *Reference datasets* section, upload `.txt`, `.md`, `.csv`, `.json`, `.jsonl` or `.docx` files and tick the ones to use. For each question, `dataset.py`:
- ranks each file's passages by keyword relevance (BM25), using your last two questions
- sends the top N to the model, which cites them like `[file #n]`

A line under each answer lists the passages used. Files are kept in `datasets/`.

**Also in the sidebar:**
- jurisdiction and answer language
- custom instructions with reference files
- for Claude: effort, reasoning and web search
- for other providers: temperature and max tokens
- saved chat history, with Markdown and JSON download

In the chat you can attach PDFs, Word or text files, and photos. For providers other than Claude, the text is pulled out of PDFs and Word files for them. You can also stop, retry and regenerate answers.

## Errors you may see

| Message | Meaning | Fix |
|---|---|---|
| `402 ... Insufficient Balance` | The provider account has no credit | Top up on the provider's site (DeepSeek: platform.deepseek.com), or pick another provider |
| `401 ... Authentication Fails` | The key is wrong or revoked | Put a valid key in `.env` and restart |
| `... has no API key` | No key set for that provider | Add `<NAME>_API_KEY` to `.env` |
| Error on an image question | The model is text-only (e.g. `deepseek-chat`) | Use a vision model such as `gpt-4o` or Claude |

## Files

- `server.py`: the web server and chat API (serves the website, the dashboard and the classic page)
- `website/`: the website built from the Aigocy template (`routes.py`, `site_content.py`, `templates/`, `static/assets/`)
- `aigocy/`: the original Aigocy template source, kept for reference
- `static/index.html`, `static/app.js`: the chat dashboard at `/app`
- `static/classic.html`: the old chat-ui page, served at `/classic`
- `app.py`: the alternative Streamlit app
- `openai_compat.py`, `providers.py`, `providers/`: OpenAI-compatible providers from your old chat-ui configs
- `llm.py`: the Claude streaming call
- `dataset.py`, `datasets/`: reference datasets and passage search
- `prompts.py`: the law-focused system prompt
- `attachments.py`, `history.py`: chat attachments and saved chats
- `start.bat`: double-click launcher for the web app

## Notes

- **Exposed keys:** the API keys inside the old config files are written in plain text. If they're yours, consider revoking them and keeping new ones only in `.env`.
- **Private data:** saved chats (`history/`) and datasets (`datasets/`) can contain private case details. Both folders, and `providers/`, are ignored by git.
