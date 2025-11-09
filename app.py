# app.py
# Chainlit-based front-end for the simple SD/DS chatbot KB
# Run with: chainlit run app.py

import json
import os
import difflib
import textwrap
import chainlit as cl

KB_FILE = "kb.json"
MATCH_THRESHOLD = 0.45  # fuzzy match threshold

DEFAULT_KB = [
    {
        "question": "What is Python used for?",
        "answer": "Python is a versatile programming language used for web development, data science, scripting, automation, and more. Popular libraries: requests, Flask/FastAPI, pandas, numpy, scikit-learn, PyTorch.",
        "tags": ["python", "language", "general"]
    },
    {
        "question": "How do I start learning machine learning?",
        "answer": "Start with Python basics, statistics, and linear algebra. Learn pandas/numpy for data handling, then study supervised learning (linear/logistic regression, decision trees). Use scikit-learn for experiments and follow with deep learning frameworks like PyTorch or TensorFlow.",
        "tags": ["ml", "machine learning", "learning path", "data science"]
    },
    {
        "question": "What is version control / Git?",
        "answer": "Git is a distributed version control system for tracking changes in source code. Typical workflow: clone, create branches, commit, push, open pull requests, and merge. Platforms: GitHub, GitLab, Bitbucket.",
        "tags": ["git", "version control", "vcs"]
    },
    {
        "question": "What is Docker and why use it?",
        "answer": "Docker packages applications into lightweight containers for consistent environments across development and production. Use it to isolate dependencies and simplify deployment.",
        "tags": ["docker", "containers", "devops"]
    },
    {
        "question": "How do I evaluate a model?",
        "answer": "Choose metrics suitable for the problem: accuracy/precision/recall/F1 for classification, RMSE/MAE for regression. Use cross-validation to estimate generalization and inspect learning curves and confusion matrices.",
        "tags": ["model evaluation", "metrics", "ml"]
    },
    {
        "question": "When should I use SQL vs NoSQL?",
        "answer": "Use SQL (relational DBs) for structured data with strong consistency and ACID requirements. Use NoSQL for flexible schemas, high throughput, or hierarchical/document data (e.g., MongoDB). Consider use-case and scaling needs.",
        "tags": ["sql", "database", "nosql"]
    },
    {
        "question": "What are REST APIs?",
        "answer": "REST (Representational State Transfer) is an architectural style for networked applications using HTTP verbs (GET/POST/PUT/DELETE). Design resources with clear URLs, use status codes, and consider authentication and pagination.",
        "tags": ["rest", "api", "web"]
    },
    {
        "question": "How to test my code?",
        "answer": "Write unit tests for functions, integration tests for components, and use test automation. In Python, use pytest or unittest. Run tests in CI and aim for clear, deterministic tests.",
        "tags": ["testing", "ci", "pytest"]
    }
]


def load_kb(path=KB_FILE):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                kb = json.load(f)
                if isinstance(kb, list):
                    return kb
        except Exception:
            pass
    return DEFAULT_KB.copy()


def save_kb(kb, path=KB_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)


def normalize(text):
    return " ".join(text.lower().strip().split())


def score_match(query, text):
    return difflib.SequenceMatcher(None, normalize(query), normalize(text)).ratio()


def find_best_answer(kb, query):
    query_n = normalize(query)
    best = None
    best_score = 0.0

    for item in kb:
        s_q = score_match(query_n, item["question"])
        s_a = score_match(query_n, item["answer"])
        s_t = 0.0
        if item.get("tags"):
            s_t = max((score_match(query_n, t) for t in item["tags"]), default=0.0)
        combined = max(s_q * 1.2, s_a * 0.9, s_t * 1.0)
        if combined > best_score:
            best_score = combined
            best = item

    if best_score >= MATCH_THRESHOLD:
        return best, best_score

    # fallback: keyword containment in question
    for item in kb:
        qn = normalize(item["question"])
        if any(word for word in query_n.split() if word and word in qn):
            return item, 0.0

    return None, best_score


def format_wrapped(text, indent=0, width=80):
    wrapper = textwrap.TextWrapper(width=width - indent)
    prefix = " " * indent
    lines = []
    for line in wrapper.wrap(text):
        lines.append(prefix + line)
    return "\n".join(lines)


# Maintain KB in module-level variable so handlers can access and modify it
KB = load_kb()


@cl.on_message
async def handle_message(message: str):
    global KB

    user_text = message.strip()
    if not user_text:
        await cl.Message(content="(empty message)").send()
        return

    # Commands
    if user_text.startswith("/"):
        cmd, *rest = user_text.split(" ", 1)
        arg = rest[0].strip() if rest else ""
        cmd = cmd.lower()

        if cmd == "/help":
            help_text = (
                "Commands:\n"
                "  /help                       Show this help\n"
                "  /add Q|A|tag1,tag2          Add new Q/A (use '|' to separate question, answer, tags)\n"
                "  /list                       List stored Q/A entries\n"
                "  /save                       Save knowledge base to disk (kb.json)\n"
                "  /load                       Load knowledge base from disk (overwrites current)\n"
                "\nExample for /add:\n"
                "/add What is pytest?|A testing framework for Python.|testing,pytest\n"
            )
            await cl.Message(content=help_text).send()
            return

        if cmd == "/list":
            if not KB:
                await cl.Message(content="Knowledge base is empty.").send()
                return
            lines = []
            for i, item in enumerate(KB, 1):
                tags = ", ".join(item.get("tags", []))
                lines.append(f"{i}. {item['question']} (tags: {tags})")
            await cl.Message(content="\n".join(lines)).send()
            return

        if cmd == "/add":
            if not arg:
                await cl.Message(content="Usage: /add Question|Answer|tag1,tag2").send()
                return
            parts = [p.strip() for p in arg.split("|")]
            if len(parts) < 2:
                await cl.Message(content="Please provide at least Question and Answer separated by '|'.").send()
                return
            q = parts[0]
            a = parts[1]
            tags = []
            if len(parts) >= 3 and parts[2]:
                tags = [t.strip() for t in parts[2].split(",") if t.strip()]
            KB.append({"question": q, "answer": a, "tags": tags})
            await cl.Message(content="Added to knowledge base.").send()
            return

        if cmd == "/save":
            try:
                save_kb(KB)
                await cl.Message(content=f"Saved KB to {KB_FILE}.").send()
            except Exception as e:
                await cl.Message(content=f"Failed to save KB: {e}").send()
            return

        if cmd == "/load":
            KB = load_kb()
            await cl.Message(content="Knowledge base loaded.").send()
            return

        # unknown command
        await cl.Message(content="Unknown command. Type /help for available commands.").send()
        return

    # Normal query: perform fuzzy retrieval
    item, score = find_best_answer(KB, user_text)
    if item:
        answer = format_wrapped(item["answer"], indent=2)
        if score and score < 0.6:
            meta = f"\n\n(matched: \"{item['question']}\" score={score:.2f})"
        else:
            meta = ""
        await cl.Message(content=f"Bot:\n{answer}{meta}").send()
    else:
        await cl.Message(content="Bot: I don't have a good answer for that. You can add it with /add.").send()