"""Mizan agent: a bounded tool-calling loop with code-enforced guardrails.

Guardrails:
  1. Constant tool menu; search budget enforced at execution time.
  2. Leaked tool-call syntax in the answer is rejected.
  3. Numeric grounding: every AED amount must come from the question or a tool result.

Usage: python agent.py "your question"
"""
import json
import re
import sys
import time

from clients import aoai
from packs import pack_tools, system_prompt
from retrieval import search_law, search_tool_schema
from settings import CHAT_DEPLOYMENT

MAX_STEPS = 6          # safety brake: total LLM calls per question
MAX_SEARCHES = 2       # tool budget, enforced by the executor
MAX_OUTPUT = 1500      # caps cost, latency, and rate-limit reservation

LEAK_RE = re.compile(r"to=functions\.|<\|[^|]*\|>")
AED_RE = re.compile(r"AED\s*\**\s*([\d][\d,]*(?:\.\d+)?)", re.IGNORECASE)
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
SAFE_FAILURE = ("I couldn't produce a verified answer this time. Please try again, "
                "or confirm the details with MOHRE.")


def numbers_in(text: str) -> set:
    out = set()
    for n in NUM_RE.findall(text or ""):
        try:
            out.add(round(float(n.replace(",", "")), 2))
        except ValueError:
            pass
    return out


def check_answer(answer: str, allowed_numbers: set) -> str | None:
    """Return a correction message if the answer breaks a guardrail, else None."""
    if LEAK_RE.search(answer or ""):
        return ("Your reply contained a tool call written as text. Use the tool-calling mechanism "
                "to call the tool properly, then answer.")
    for raw in AED_RE.findall(answer or ""):
        if round(float(raw.replace(",", "")), 2) not in allowed_numbers:
            return (f"Your reply states AED {raw}, which does not come from the user's message or any tool result. "
                    "Never compute amounts yourself: call calculate_gratuity and report its amount_aed exactly.")
    return None


def available_tools() -> dict:
    return {"search_law": (search_tool_schema(), search_law), **pack_tools()}


def run(question: str, history: list | None = None) -> dict:
    tools = available_tools()
    schemas = [schema for schema, _ in tools.values()]
    messages = [{"role": "system", "content": system_prompt()}, *(history or []), {"role": "user", "content": question}]
    allowed_numbers = numbers_in(question)
    trace, usage, searches, started = [], {"prompt_tokens": 0, "completion_tokens": 0}, 0, time.perf_counter()

    def done(answer):
        return {"answer": answer, "trace": trace, "usage": usage,
                "total_ms": int((time.perf_counter() - started) * 1000)}

    for step in range(1, MAX_STEPS + 1):
        t0 = time.perf_counter()
        resp = aoai().chat.completions.create(
            model=CHAT_DEPLOYMENT, messages=messages, tools=schemas,
            tool_choice="auto", max_completion_tokens=MAX_OUTPUT,
        )
        llm_ms = int((time.perf_counter() - t0) * 1000)
        usage["prompt_tokens"] += resp.usage.prompt_tokens
        usage["completion_tokens"] += resp.usage.completion_tokens
        msg = resp.choices[0].message

        if not msg.tool_calls:
            problem = check_answer(msg.content, allowed_numbers)
            if problem is None:
                trace.append({"step": step, "action": "answer", "llm_ms": llm_ms})
                return done(msg.content)
            trace.append({"step": step, "action": "guard:rejected", "llm_ms": llm_ms, "reason": problem[:80]})
            messages.append({"role": "assistant", "content": msg.content or ""})
            messages.append({"role": "user", "content": problem})
            continue

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in msg.tool_calls
            ],
        })
        for call in msg.tool_calls:
            name = call.function.name
            t1 = time.perf_counter()
            try:
                args = json.loads(call.function.arguments or "{}")
                if name == "search_law" and searches >= MAX_SEARCHES:
                    result = {"error": "Search budget exhausted. Do not search again. Call calculate_gratuity if an "
                                       "amount is needed; otherwise answer from the passages you already have."}
                elif name in tools:
                    result = tools[name][1](**args)
                    if name == "search_law":
                        searches += 1
                else:
                    result = {"error": f"unknown tool {name}"}
            except Exception as exc:
                args, result = {}, {"error": f"{type(exc).__name__}: {exc}"}
            result_text = json.dumps(result, ensure_ascii=False)
            if name != "search_law":
                allowed_numbers |= numbers_in(result_text)
            sources = ([f"{r['source']} (PDF page {r['pdf_page']})" for r in result]
                       if name == "search_law" and isinstance(result, list) else None)
            trace.append({"step": step, "action": f"tool:{name}", "args": args, "llm_ms": llm_ms,
                          "tool_ms": int((time.perf_counter() - t1) * 1000), "sources": sources})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result_text})

    trace.append({"step": MAX_STEPS, "action": "guard:step_limit"})
    return done(SAFE_FAILURE)


if __name__ == "__main__":
    out = run(sys.argv[1])
    print("\n--- TRACE ---")
    for t in out["trace"]:
        print(t)
    print(f"\n--- ANSWER ---\n{out['answer']}")
    print(f"\n--- COST/LATENCY --- tokens in={out['usage']['prompt_tokens']} out={out['usage']['completion_tokens']} | total {out['total_ms']} ms")
