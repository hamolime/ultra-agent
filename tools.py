import requests
import json
import os
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

MEM_FILE = "memory.json"

def web_search(query: str):
    try:
        r = requests.get(
            f"https://text.pollinations.ai/search?q={query}",
            timeout=8
        )

        return f"""
🔎 SEARCH RESULT
Query: {query}

{r.text[:500]}
"""
    except:
        return "search failed"

def manage_long_term_memory(chat_id, action, key=None, value=None):
    if not os.path.exists(MEM_FILE):
        json.dump({}, open(MEM_FILE, "w"))

    data = json.load(open(MEM_FILE, "r"))

    cid = str(chat_id)
    if cid not in data:
        data[cid] = {}

    if action == "save":
        data[cid][key] = value
        json.dump(data, open(MEM_FILE, "w"))
        return "saved"

    if action == "get":
        return json.dumps(data.get(cid, {}))
