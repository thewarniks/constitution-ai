"""Legal-help chatbot: a Streamlit chat UI.

Run with:  streamlit run app.py

The backend works like the earlier chat-ui project: chats go to the provider
picked in the sidebar (DeepSeek, OpenAI, DeepInfra, Qwen, NVIDIA NIM from
./providers, or Anthropic Claude). Reference datasets in ./datasets are
searched for each question and the best passages are sent along.

UI features ported from the chat-ui: streaming with a stop button, file and
image attachments, regenerate, saved chat history with JSON download, custom
instructions with reference files, and an optional view of the reasoning.
"""

import base64
import json
import os

import anthropic
import streamlit as st
from dotenv import load_dotenv

import dataset
import history
import llm
import openai_compat
import providers
from attachments import ACCEPTED_TYPES, extract_text, to_content_block
from prompts import DISCLAIMER, build_system_prompt

# override=True: Streamlit reruns this script on every interaction, so key edits in .env apply without a restart.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

EFFORTS = ["low", "medium", "high", "max"]
JURISDICTIONS = [
    "India",
    "United States",
    "United Kingdom",
    "Canada",
    "Australia",
    "Other / General",
]
LANGUAGES = ["Same as my question", "English", "Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Spanish", "French"]
EXAMPLE_QUESTIONS = [
    "My landlord won't return my security deposit. What can I do?",
    "I received a court summons. What happens next and what should I prepare?",
    "How do I file a consumer complaint against a company for a defective product?",
]

st.set_page_config(page_title="Constitution Ai", page_icon="⚖️")


@st.cache_resource
def get_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def error_message(exc: Exception) -> str:
    if isinstance(exc, openai_compat.ProviderError):
        return exc.message
    if isinstance(exc, anthropic.AuthenticationError):
        return "The API key was rejected. Check `ANTHROPIC_API_KEY` in your `.env` file."
    if isinstance(exc, anthropic.RateLimitError):
        return "Too many requests right now. Wait a minute and try again."
    if isinstance(exc, anthropic.APIStatusError):
        if "credit balance" in str(exc.message).lower():
            return ("Your Anthropic account has no credit left. Add credits at console.anthropic.com → "
                    "Plans & Billing, or pick a free provider (Groq, Gemini, OpenRouter) in the sidebar.")
        return f"The API returned an error ({exc.status_code}): {exc.message}"
    if isinstance(exc, anthropic.APIConnectionError):
        return "Couldn't reach the API. Check your internet connection."
    return f"Unexpected error: {exc}"


# ---- Session state and chat actions --------------------------------------

state = st.session_state
state.setdefault("chat_id", history.new_id())
state.setdefault("messages", [])


def save_chat() -> None:
    if state.messages:
        history.save(
            state.chat_id,
            state.messages,
            {"jurisdiction": state.get("jurisdiction"), "language": state.get("language")},
        )


def new_chat() -> None:
    state.chat_id = history.new_id()
    state.messages = []


def load_chat(chat_id: str) -> None:
    record = history.load(chat_id)
    state.chat_id = record["id"]
    state.messages = record["messages"]
    settings = record.get("settings") or {}
    if settings.get("jurisdiction") in JURISDICTIONS:
        state.jurisdiction = settings["jurisdiction"]
    if settings.get("language") in LANGUAGES:
        state.language = settings["language"]


def delete_chat(chat_id: str) -> None:
    history.delete(chat_id)
    if chat_id == state.chat_id:
        new_chat()


def delete_all_chats() -> None:
    history.delete_all()
    new_chat()


def request_regenerate() -> None:
    state.regenerate = True


def delete_dataset(name: str) -> None:
    dataset.delete_dataset(name)
    state.selected_datasets = [n for n in state.get("selected_datasets", []) if n != name]


def provider_label(name: str) -> str:
    p = all_providers[name]
    return p["title"] + ("" if providers.is_ready(p) else "  (no API key)")


def trim_to_last_user() -> None:
    """Drop everything after the last user message (the old resendMessage())."""
    while state.messages and state.messages[-1]["role"] != "user":
        state.messages.pop()


def finish_interrupted_reply() -> None:
    """A Stop click (or any rerun) interrupts streaming; keep what arrived."""
    changed = False
    for m in list(state.messages):
        if m.get("status") == "streaming":
            changed = True
            if m["content"].strip():
                m["content"] += "\n\n_(Stopped.)_"
                m["status"] = "done"
            else:
                state.messages.remove(m)
    if changed:
        save_chat()


finish_interrupted_reply()

# ---- Sidebar -------------------------------------------------------------

all_providers = providers.load()

with st.sidebar:
    st.header("⚖️ Settings")
    names = list(all_providers)
    if state.get("provider") not in names:
        state.provider = providers.default_name(all_providers)
    provider_name = st.selectbox("Provider", names, format_func=provider_label, key="provider")
    provider = all_providers[provider_name]
    is_claude = provider["kind"] == "anthropic"
    models = provider["models"]
    if state.get(f"model-{provider_name}") not in models:
        state.pop(f"model-{provider_name}", None)  # the live model list changed
    model = st.selectbox(
        "Model", models,
        index=models.index(provider["default_model"]) if provider["default_model"] in models else 0,
        key=f"model-{provider_name}",
    )
    jurisdiction = st.selectbox("Jurisdiction", JURISDICTIONS, key="jurisdiction")
    language = st.selectbox("Answer language", LANGUAGES, key="language")

    temperature = max_tokens = None
    if is_claude:
        effort = st.select_slider(
            "Effort", EFFORTS, value="high", help="Higher effort reasons more carefully but is slower and costs more."
        )
        show_thinking = st.toggle("Show reasoning", help="Show a summary of how the assistant reasoned.")
        web_search = st.toggle(
            "Search the web for current law",
            help="Lets the assistant check current statutes and court rules online. "
            "Web search must be enabled for your organization in the Anthropic Console.",
        )
    else:
        effort, show_thinking, web_search = "high", True, False  # reasoning shows if the model sends it
        with st.expander("Advanced"):
            if st.checkbox("Set temperature"):
                temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
            max_tokens = st.number_input("Max tokens (0 = provider default)", 0, 1_000_000, 0, 256) or None

    with st.expander("Reference datasets"):
        st.caption("Upload laws, judgments, FAQs or case notes. For each question, the most relevant "
                   "passages from the ticked datasets are sent to the model as reference.")
        state.setdefault("ds_round", 0)
        uploads = st.file_uploader(
            "Add dataset files", type=sorted(e.lstrip(".") for e in dataset.ALLOWED_EXTENSIONS),
            accept_multiple_files=True, key=f"ds-upload-{state.ds_round}",
        )
        if uploads:
            for f in uploads:
                try:
                    name = dataset.save_dataset(f.name, f.getvalue())
                    state.selected_datasets = sorted({*state.get("selected_datasets", []), name})
                except Exception as exc:
                    st.warning(f"Couldn't add {f.name}: {exc}")
            state.ds_round += 1  # a fresh uploader, so the same files aren't saved again
            st.rerun()
        available = dataset.list_datasets()
        names_available = [d["name"] for d in available]
        state.selected_datasets = [n for n in state.get("selected_datasets", []) if n in names_available]
        selected_datasets = st.multiselect("Use for answers", names_available, key="selected_datasets")
        top_k = st.number_input("Passages per question", 1, 20, 5)
        for d in available:
            col_name, col_del = st.columns([5, 1])
            col_name.caption(f"📄 {d['name']} · {d['chunks']} passages")
            col_del.button("🗑", key=f"ds-del-{d['name']}", on_click=delete_dataset, args=(d["name"],),
                           help="Delete this dataset")

    with st.expander("Custom instructions"):
        custom_instructions = st.text_area(
            "Instructions",
            key="custom_instructions",
            placeholder="e.g. I am a law student, cite sections and leading cases.",
        )
        ref_files = st.file_uploader(
            "Reference files", type=["docx", "md", "txt"], accept_multiple_files=True, key="ref_files"
        )
        reference_docs = []
        for f in ref_files or []:
            try:
                reference_docs.append((f.name, extract_text(f.name, f.getvalue())))
            except Exception as exc:  # a corrupt .docx shouldn't break the page
                st.warning(f"Couldn't read {f.name}: {exc}")

    st.divider()
    st.subheader("Chats")
    st.button("➕ New conversation", on_click=new_chat, use_container_width=True)
    if state.messages:
        col_md, col_json = st.columns(2)
        col_md.download_button(
            "⬇ Transcript",
            history.to_markdown(state.messages),
            file_name=f"legal-chat-{state.chat_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        col_json.download_button(
            "⬇ JSON",
            json.dumps(state.messages, indent=2),
            file_name=f"legal-chat-{state.chat_id}.json",
            mime="application/json",
            use_container_width=True,
        )

    saved = history.list_chats()
    with st.expander(f"History ({len(saved)})"):
        for chat in saved[:30]:
            col_open, col_del = st.columns([5, 1])
            label = ("▶ " if chat["id"] == state.chat_id else "") + chat["title"]
            col_open.button(label, key=f"open-{chat['id']}", on_click=load_chat, args=(chat["id"],),
                            use_container_width=True)
            col_del.button("🗑", key=f"del-{chat['id']}", on_click=delete_chat, args=(chat["id"],),
                           help="Delete this chat")
        if saved:
            st.button("Delete all history", on_click=delete_all_chats, type="secondary")
        else:
            st.caption("No saved chats yet.")

    st.divider()
    st.caption(DISCLAIMER)

# ---- Main page -----------------------------------------------------------

st.title("⚖️ Constitution Ai")
st.caption("Understand your legal problem, your options, and the court process, in plain language.")

if not providers.is_ready(provider):
    st.warning(
        f"{provider['title']} has no API key. Put it in `.env` as `{openai_compat.env_key_name(provider)}` "
        "and restart the app, or pick another provider in the sidebar."
    )
    if is_claude:
        st.stop()  # Claude always needs a key; some OpenAI-style gateways don't
elif not provider.get("needs_key", True) and provider.get("reachable") is False:
    st.info(f"{provider['title']} isn't responding. For Ollama: install it from ollama.com, run "
            "`ollama pull llama3.2` in a terminal, and keep the Ollama app open.")

if not state.get("accepted_disclaimer"):
    st.warning(DISCLAIMER)
    if st.button("I understand, continue", type="primary"):
        state.accepted_disclaimer = True
        st.rerun()
    st.stop()


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("thinking"):
            with st.expander("Reasoning"):
                st.markdown(message["thinking"])
        content = message["content"]
        if isinstance(content, str):
            st.markdown(content)
            return
        for block in content:
            if block["type"] == "text":
                st.markdown(block["text"])
            elif block["type"] == "image":
                st.image(base64.b64decode(block["source"]["data"]), width=240)
            elif block["type"] == "document":
                st.caption(f"📎 {block.get('title', 'document')}")


def message_text(content) -> str:
    if isinstance(content, str):
        return content
    return " ".join(b["text"] for b in content if b.get("type") == "text")


def answer_events(api_messages: list[dict], system: str):
    """Stream from the selected provider; both paths yield the same (kind, value) events."""
    if is_claude:
        return llm.stream_answer(
            get_client(provider["api_key"]), api_messages, system,
            model=model, effort=effort, show_thinking=show_thinking, web_search=web_search,
        )
    return openai_compat.stream_chat(
        provider, openai_compat.to_openai_messages(api_messages), system,
        model=model, max_tokens=max_tokens, temperature=temperature,
    )


def generate_reply() -> None:
    """Stream the provider's answer to the conversation into a new assistant message."""
    api_messages = [{"role": m["role"], "content": m["content"]} for m in state.messages]
    passages = []
    if selected_datasets:
        recent_questions = [message_text(m["content"]) for m in api_messages if m["role"] == "user"][-2:]
        passages = dataset.search(" ".join(recent_questions), selected_datasets, int(top_k))
    system = build_system_prompt(
        jurisdiction,
        language=None if language == LANGUAGES[0] else language,
        custom_instructions=custom_instructions,
        reference_docs=reference_docs,
        web_search=web_search,
        passages=passages,
    )
    reply = {"role": "assistant", "content": "", "thinking": "", "status": "streaming"}
    state.messages.append(reply)

    with st.chat_message("assistant"):
        stop_slot = st.empty()
        stop_slot.button("⏹ Stop", key="stop")  # clicking it reruns the script, which interrupts the stream
        thinking_slot = st.expander("Reasoning").empty() if show_thinking else None
        status_slot = st.empty()
        text_slot = st.empty()
        status_slot.caption("Thinking…")
        info = {}
        try:
            for kind, value in answer_events(api_messages, system):
                if kind == "thinking" and thinking_slot:
                    reply["thinking"] += value
                    thinking_slot.markdown(reply["thinking"])
                elif kind == "text":
                    status_slot.empty()
                    reply["content"] += value
                    text_slot.markdown(reply["content"] + "▌")
                elif kind == "status":
                    status_slot.caption(value)
                elif kind == "done":
                    info = value
        except (anthropic.APIError, openai_compat.ProviderError) as exc:
            state.messages.remove(reply)
            state.last_error = error_message(exc)
            st.rerun()

    if passages:
        used = ", ".join(f"{p['dataset']} #{p['chunk']}" for p in passages)
        reply["content"] += f"\n\n_Reference passages used: {used}_"
    if info.get("sources"):
        reply["content"] += "\n\n**Sources**\n" + "\n".join(
            f"- [{title}]({url})" for url, title in info["sources"].items()
        )
    if info.get("stop_reason") == "refusal":
        reply["content"] += "\n\n_I can't help with that request. Please rephrase it or ask a lawyer directly._"
    elif info.get("stop_reason") == "max_tokens":
        reply["content"] += "\n\n_(The answer was cut off because it was too long. Ask me to continue.)_"
    reply["status"] = "done"
    save_chat()
    st.rerun()


chat_value = st.chat_input(
    "Describe your legal question or situation, or attach a document…",
    accept_file="multiple",
    file_type=ACCEPTED_TYPES,
)
pending_prompt = state.pop("pending_prompt", None)
run_generation = False

if state.pop("regenerate", False):
    trim_to_last_user()
    run_generation = bool(state.messages)

if chat_value or pending_prompt:
    text = chat_value.text if chat_value else pending_prompt
    blocks = []
    for f in (chat_value.files if chat_value else []):
        try:
            blocks.append(to_content_block(f.name, f.getvalue()))
        except Exception as exc:
            st.warning(f"Skipped {f.name}: {exc}")
    if text or blocks:
        if blocks:
            blocks.append({"type": "text", "text": text or "Please review the attached document(s) and explain what they mean for me."})
            content = blocks
        else:
            content = text
        state.messages.append({"role": "user", "content": content})
        run_generation = True

if not state.messages and not run_generation:
    st.info("Describe your situation, including where it happened and any important dates. "
            "You can also attach a notice, contract, FIR, or court order (PDF, Word, text, or a photo). For example:")
    for question in EXAMPLE_QUESTIONS:
        if st.button(question, use_container_width=True):
            state.pending_prompt = question
            st.rerun()

for message in state.messages:
    render_message(message)

if error := state.pop("last_error", None):
    st.error(error)

if run_generation:
    generate_reply()
elif state.messages:
    last_is_user = state.messages[-1]["role"] == "user"
    st.button("🔄 Retry" if last_is_user else "🔄 Regenerate answer", on_click=request_regenerate)
