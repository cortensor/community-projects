import json
import time
import requests
import logging
import math
import re
from typing import Any, Dict, List, Optional

from config import (
    CORTENSOR_API_URL,
    CORTENSOR_API_KEY,
    CORTENSOR_SESSION_ID,
    LATEST_DEVLOG_FILE,
    INSIGHTS_QUEUE_FILE,
    PROCESSED_MESSAGES_FILE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cortensor_processor")

def safe_load_json(path: str, default: Any):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        logger.error("❌ JSON decode error reading %s", path)
        return default
    except Exception as e:
        logger.exception("❌ Error reading %s: %s", path, e)
        return default

def safe_write_json(path: str, data: Any):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        import os
        os.replace(tmp, path)
    except Exception as e:
        logger.exception("❌ Failed to write JSON to %s: %s", path, e)

class CortensorProcessor:
    def __init__(self):
        self.processed_messages = set()
        self.load_processed_messages()
        self._max_attempts = 4
        self._initial_backoff = 0.8

    def load_processed_messages(self):
        try:
            data = safe_load_json(PROCESSED_MESSAGES_FILE, {"processed_ids": []})
            ids = data.get("processed_ids", [])
            self.processed_messages = set(ids if isinstance(ids, list) else [])
            logger.info("📥 Loaded %d processed message ids", len(self.processed_messages))
        except Exception as e:
            logger.exception("❌ Failed to load processed messages: %s", e)
            self.processed_messages = set()

    def save_processed_message(self, message_id: str):
        try:
            self.processed_messages.add(message_id)
            safe_write_json(PROCESSED_MESSAGES_FILE, {"processed_ids": list(self.processed_messages)})
            logger.info("💾 Saved processed message id: %s (total=%d)", message_id, len(self.processed_messages))
        except Exception as e:
            logger.exception("❌ Failed to save processed message id %s: %s", message_id, e)

    # ---------------- prompt + request -------------------------------------
    def build_prompt(self, content: str) -> str:
        prompt = f"""
You are an assistant that summarizes developer updates.

OUTPUT FORMAT (must follow exactly, return valid JSON only):
- tldr: a single-line TL;DR (one short sentence)
- summary: a high-level summary of 2-3 sentences
- key_insights: an array of 3-5 short bullet strings

Return exactly a JSON object, for example:
{{"tldr":"One-line TL;DR.","summary":"Two to three sentence high-level summary.","key_insights":["insight1","insight2","insight3"]}}

DO NOT include any extra commentary or text outside the JSON object.

Now summarize the following developer update (be concise and factual):

---
{content}
---
"""
        return prompt.strip()

    def _request_with_backoff(self, payload: dict, headers: dict, timeout: int = 90) -> Optional[requests.Response]:
        attempt = 0
        while attempt < self._max_attempts:
            try:
                attempt += 1
                resp = requests.post(CORTENSOR_API_URL, json=payload, headers=headers, timeout=timeout)
                if resp.status_code < 500:
                    return resp
                logger.warning("⚠️ Cortensor API returned %d, attempt %d/%d", resp.status_code, attempt, self._max_attempts)
            except requests.exceptions.RequestException as e:
                logger.warning("⚠️ RequestException on attempt %d: %s", attempt, e)
            backoff = self._initial_backoff * (2 ** (attempt - 1))
            jitter = backoff * 0.1 * (0.5 - (time.time() % 1))
            wait = max(0.2, backoff + jitter)
            time.sleep(wait)
        logger.error("❌ All attempts to call Cortensor API failed")
        return None

    def call_cortensor_api(self, content: str) -> Optional[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {CORTENSOR_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = self.build_prompt(content)
        payload = {
            "session_id": CORTENSOR_SESSION_ID,
            "prompt": prompt,
            "model": "DeepSeek R1 Distill Qwen 14B Q4_K_M",
            "max_tokens": 512,
            "temperature": 0.0,
            "top_p": 0.9,
            "top_k": 40,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "stream": False
        }
        logger.info("🤖 Calling Cortensor API (model=%s, prompt_len=%d)", payload["model"], len(prompt))
        resp = self._request_with_backoff(payload, headers, timeout=90)
        if resp is None:
            return None

        logger.info("📥 Cortensor API status: %s", resp.status_code)

        # Extract textual content from response envelope
        raw_text = ""
        try:
            ct = resp.headers.get("Content-Type", "")
            if "application/json" in ct:
                parsed = resp.json()
                raw_text = self._extract_text_from_response_object(parsed)
            else:
                try:
                    parsed = resp.json()
                    raw_text = self._extract_text_from_response_object(parsed)
                except Exception:
                    raw_text = resp.text or ""
        except Exception as e:
            logger.exception("❌ Error parsing response: %s", e)
            try:
                raw_text = resp.text or ""
            except Exception:
                raw_text = ""

        raw_text = (raw_text or "").strip()

        # Try parse JSON inside raw_text
        try:
            candidate = json.loads(raw_text)
            if isinstance(candidate, dict):
                tldr = self._get_first_string(candidate, ["tldr", "tl;dr", "TLDR"])
                summary = self._get_first_string(candidate, ["summary", "high_level_summary"])
                key_insights = self._normalize_key_insights(candidate.get("key_insights") or candidate.get("insights") or [])
                return {"tldr": tldr, "summary": summary, "key_insights": key_insights, "raw": raw_text}
        except Exception:
            pass

        # Try envelope choices -> message -> content
        try:
            parsed_envelope = None
            try:
                parsed_envelope = resp.json()
            except Exception:
                parsed_envelope = None
            if isinstance(parsed_envelope, dict):
                if "choices" in parsed_envelope and isinstance(parsed_envelope["choices"], list) and parsed_envelope["choices"]:
                    first = parsed_envelope["choices"][0]
                    message_content = None
                    if isinstance(first, dict):
                        if "message" in first and isinstance(first["message"], dict):
                            message_content = first["message"].get("content")
                        if not message_content:
                            message_content = first.get("text")
                    if message_content:
                        raw_candidate = message_content.strip()
                        try:
                            parsed_inner = json.loads(raw_candidate)
                            if isinstance(parsed_inner, dict):
                                tldr = self._get_first_string(parsed_inner, ["tldr", "tl;dr", "TLDR"])
                                summary = self._get_first_string(parsed_inner, ["summary", "high_level_summary"])
                                key_insights = self._normalize_key_insights(parsed_inner.get("key_insights") or parsed_inner.get("insights") or [])
                                return {"tldr": tldr, "summary": summary, "key_insights": key_insights, "raw": raw_candidate}
                        except Exception:
                            raw_text = raw_candidate
        except Exception:
            pass

        # Heuristic parse plain text
        parsed = self._heuristic_parse_plain_text(raw_text)
        return {"tldr": parsed.get("tldr"), "summary": parsed.get("summary"), "key_insights": parsed.get("key_insights", []), "raw": raw_text}

    # ---------------- parsing helpers -------------------------------------
    @staticmethod
    def _get_first_string(d: dict, keys: List[str]) -> Optional[str]:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    @staticmethod
    def _normalize_key_insights(raw) -> List[str]:
        if raw is None:
            return []
        if isinstance(raw, list):
            out = []
            for item in raw:
                if isinstance(item, str) and item.strip():
                    out.append(re.sub(r"\s+", " ", item).strip())
                elif isinstance(item, dict):
                    txt = item.get("text") or item.get("content") or ""
                    if isinstance(txt, str) and txt.strip():
                        out.append(re.sub(r"\s+", " ", txt).strip())
            return out[:5]
        if isinstance(raw, str):
            lines = [ln.strip() for ln in re.split(r'[\r\n]+', raw) if ln.strip()]
            lines = [re.sub(r'^\d+\.\s*', '', ln) for ln in lines]
            return lines[:5]
        return []

    @staticmethod
    def _extract_text_from_response_object(obj: dict) -> str:
        for key in ("text", "response", "content", "result"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        choices = obj.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                msg = first.get("message") or first.get("delta")
                if isinstance(msg, dict):
                    cont = msg.get("content") or msg.get("text")
                    if isinstance(cont, str):
                        return cont
                if "text" in first and isinstance(first["text"], str):
                    return first["text"]
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return str(obj)

    def _heuristic_parse_plain_text(self, text: str) -> Dict[str, Any]:
        out = {"tldr": None, "summary": None, "key_insights": []}
        if not text:
            return out
        t = text.strip()
        t = re.sub(r"^\s*```(?:json|text)?\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t)
        t = re.sub(r"\r\n?", "\n", t)
        t = re.sub(r"[ \t]+", " ", t)
        # TL;DR label
        m = re.search(r'^(?:TL;DR|TLDR|T\/L;DR)[:\-\s]*([^\n]+)', t, flags=re.IGNORECASE)
        if m:
            out["tldr"] = m.group(1).strip()
            t_after = t[m.end():].strip()
        else:
            first_sentence = re.split(r'(?<=[.!?])\s+', t, maxsplit=1)[0].strip()
            out["tldr"] = first_sentence
            t_after = t[len(first_sentence):].strip()
        source = t_after if t_after else t
        sentences = re.split(r'(?<=[.!?])\s+', source)
        out["summary"] = " ".join(s.strip() for s in sentences[:3] if s.strip())
        bullets = re.findall(r'^[\-\*•]\s*(.+)', t, flags=re.MULTILINE)
        if not bullets:
            bullets = re.findall(r'^\d+\.\s*(.+)', t, flags=re.MULTILINE)
        if not bullets:
            m2 = re.search(r'Key Insights[:\s]*\n(.*)', t, flags=re.IGNORECASE | re.DOTALL)
            if m2:
                block = m2.group(1).strip()
                lines = [ln.strip() for ln in re.split(r'[\r\n]+', block) if ln.strip()]
                for ln in lines:
                    if len(ln) < 6:
                        continue
                    bullets.append(re.sub(r'^\d+\.\s*', '', ln))
                    if len(bullets) >= 6:
                        break
        if not bullets:
            lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
            candidate = []
            for ln in lines:
                if len(ln) < 12 or len(ln) > 400:
                    continue
                if ln.lower().startswith(("note:", "info:", "summary")):
                    continue
                candidate.append(ln)
                if len(candidate) >= 6:
                    break
            bullets = candidate
        cleaned = []
        for b in bullets:
            s = re.sub(r'\s+', ' ', b).strip()
            s = re.sub(r'^[\-\*\u2022\s]+', '', s)
            if s:
                cleaned.append(s)
            if len(cleaned) >= 5:
                break
        out["key_insights"] = cleaned
        return out

    # ---------------- VALIDATION & fallback --------------------------------
    META_PATTERN = re.compile(r"\b(I am an assistant|I need to|I will|I'll|Now I|First I|the output should|return JSON)\b", flags=re.I)

    def _is_meta_text(self, s: Optional[str]) -> bool:
        if not s:
            return True
        if self.META_PATTERN.search(s):
            return True
        return False

    def validate_insight(self, insight: Dict[str, Any]) -> bool:
        """
        Validate insight dict has meaningful tldr/summary/key_insights.
        Return True if OK, False otherwise.
        """
        if not insight or not isinstance(insight, dict):
            return False
        tldr = (insight.get("tldr") or "").strip()
        summary = (insight.get("summary") or "").strip()
        keys = insight.get("key_insights") or []
        if not tldr or len(tldr) > 400:
            return False
        if self._is_meta_text(tldr):
            return False
        if not summary or self._is_meta_text(summary):
            return False
        if not isinstance(keys, list) or len([k for k in keys if isinstance(k, str) and len(k.strip()) >= 8]) < 1:
            return False
        return True

    # ---------------- queue handling --------------------------------------
    def add_insight_to_queue(self, message_id: str, original_content: str, insight_data: Dict[str, Any]):
        try:
            queue = safe_load_json(INSIGHTS_QUEUE_FILE, {"messages": []})
            messages = queue.get("messages", [])
        except Exception:
            logger.exception("❌ Error loading insights queue file")
            queue = {"messages": []}
            messages = queue["messages"]

        for item in messages:
            if item.get("message_id") == message_id:
                logger.info("⏭️ Insight for message %s already in queue -> skipping", message_id)
                return

        insight_norm = {
            "tldr": insight_data.get("tldr"),
            "summary": insight_data.get("summary"),
            "key_insights": insight_data.get("key_insights") or insight_data.get("insights") or [],
            "raw": insight_data.get("raw") or None
        }

        entry = {
            "message_id": message_id,
            "original_content": original_content,
            "insight": insight_norm,
            "sent": False,
            "timestamp": time.time()
        }
        messages.append(entry)
        queue["messages"] = messages
        safe_write_json(INSIGHTS_QUEUE_FILE, queue)
        logger.info("💾 Insight for message %s added to queue (queued_total=%d)", message_id, len(messages))

    # ---------------- processing incoming devlog file -----------------------
    def process_new_messages(self):
        try:
            data = safe_load_json(LATEST_DEVLOG_FILE, {})
            message_data = data.get("message")
            if not message_data:
                logger.debug("📭 No message object found in latest devlog file")
                return

            message_id = message_data.get("id")
            content = message_data.get("content", "")
            processed_flag = bool(message_data.get("processed", False))

            if not message_id:
                logger.warning("⚠️ message object found but no id -> skipping")
                return

            if message_id in self.processed_messages or processed_flag:
                logger.info("⏭️ Message %s already processed -> skipping", message_id)
                return

            logger.info("🔄 Processing message id=%s (len=%d chars)", message_id, len(content or ""))
            insight = self.call_cortensor_api(content)
            if insight:
                # Validate insight; if not valid, attempt fallback heuristics
                if not self.validate_insight(insight):
                    logger.warning("⚠️ Insight validation failed; attempting fallback parsing for message %s", message_id)
                    # try to heuristically parse raw
                    raw = insight.get("raw") or ""
                    parsed = {}
                    if raw:
                        parsed = self._heuristic_parse_plain_text(raw)
                    # if still invalid, try heuristic on original content
                    if not parsed.get("tldr"):
                        parsed = self._heuristic_parse_plain_text(content)
                    # normalize parsed into insight shape
                    fallback_insight = {
                        "tldr": parsed.get("tldr"),
                        "summary": parsed.get("summary"),
                        "key_insights": parsed.get("key_insights") or [],
                        "raw": raw or content
                    }
                    if self.validate_insight(fallback_insight):
                        logger.info("✅ Fallback insight validated for message %s", message_id)
                        self.add_insight_to_queue(message_id, content, fallback_insight)
                        self.save_processed_message(message_id)
                        message_data["processed"] = True
                        data["message"] = message_data
                        safe_write_json(LATEST_DEVLOG_FILE, data)
                        logger.info("✅ Successfully processed (fallback) message %s", message_id)
                    else:
                        # last resort: create minimal insight from original content
                        logger.error("❌ Fallback also failed. Creating minimal insight for message %s", message_id)
                        minimal = self._heuristic_parse_plain_text(content)
                        minimal_insight = {
                            "tldr": minimal.get("tldr") or "Update: see original devlog.",
                            "summary": minimal.get("summary") or "",
                            "key_insights": minimal.get("key_insights") or [],
                            "raw": raw or content
                        }
                        self.add_insight_to_queue(message_id, content, minimal_insight)
                        self.save_processed_message(message_id)
                        message_data["processed"] = True
                        data["message"] = message_data
                        safe_write_json(LATEST_DEVLOG_FILE, data)
                        logger.info("✅ Processed message %s with minimal fallback", message_id)
                else:
                    logger.info("✅ Insight passed validation for message %s", message_id)
                    self.add_insight_to_queue(message_id, content, insight)
                    self.save_processed_message(message_id)
                    message_data["processed"] = True
                    data["message"] = message_data
                    safe_write_json(LATEST_DEVLOG_FILE, data)
                    logger.info("✅ Successfully processed and queued message %s", message_id)
            else:
                logger.error("❌ Cortensor API call returned no insight for message %s", message_id)

        except Exception as e:
            logger.exception("❌ Unexpected error while processing new messages: %s", e)

    # ---------------- main loop ------------------------------------------------
    def run(self, poll_interval_seconds: int = 60):
        logger.info("🚀 Starting Cortensor Processor (poll_interval=%ds)", poll_interval_seconds)
        while True:
            try:
                self.process_new_messages()
            except KeyboardInterrupt:
                logger.info("🛑 Stopping Cortensor Processor (KeyboardInterrupt)")
                break
            except Exception as e:
                logger.exception("❌ Loop error: %s", e)
            time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    processor = CortensorProcessor()
    processor.run(poll_interval_seconds=60)
