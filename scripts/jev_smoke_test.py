import json, os, sys
import httpx
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY")
if not key:
    sys.exit("OPENROUTER_API_KEY is missing. Put it in .env")

prompt = "Write a Python function that merges two sorted lists."
payload = {
    "model": os.getenv("JEV_MODEL", "typesafe/jev-1.13"),
    "state": {"prompt_preview": prompt, "prompt_chars": len(prompt),
              "has_code_block": False, "has_image": False, "turns_so_far": 1},
    "questions": {
        "task_type": {
            "type": "choice",
            "instructions": "What kind of task is the user asking for?",
            "criteria": {
                "simple_qa": "A short factual or conversational question.",
                "reasoning": "Multi-step reasoning, math, planning or analysis.",
                "coding": "Writing, fixing or explaining code.",
            },
        },
        "complexity": {
            "type": "score",
            "instructions": "How demanding is this request for a language model?",
            "criteria": ["Trivial", "Moderate", "Hard", "Expert-level"],
        },
        "needs_deep_reasoning": {
            "type": "noul",
            "instructions": "Does answering well require extended step-by-step reasoning?",
            "criteria": {"true": "Yes, multi-step reasoning is needed.",
                         "false": "No, a direct answer is enough."},
        },
    },
}
r = httpx.post("https://openrouter.ai/api/alpha/decisions",
               headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
               json=payload, timeout=15)
print(r.status_code)
print(json.dumps(r.json(), indent=2))