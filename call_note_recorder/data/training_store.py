"""Per-user few-shot training store.

One JSON file per Windows user under training_data/[USERNAME].json. Saved
examples are fed back into the LLM prompt as style references.

Correction folded in (review item E): example transcripts can be very long.
We store them in full (useful later), but `get_examples_for_prompt()` returns
*excerpts* capped by a character budget so the LLM context (n_ctx=8192) never
overflows even with the maximum 10 examples.

Corrupt-file rule (spec): back up the bad file as .bak and start fresh.
"""

import json
import os
import shutil
import uuid
from datetime import datetime

from utils.paths import TRAINING_FILE, TRAINING_DIR, USERNAME
from utils.logger import get_logger

log = get_logger("training")

# Per-example transcript excerpt cap (characters) when building the prompt.
EXAMPLE_TRANSCRIPT_CHARS = 1200
# Total budget for the whole examples block (characters), keeps us within n_ctx.
EXAMPLES_BLOCK_BUDGET = 6000


class TrainingStore:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if not os.path.exists(TRAINING_FILE):
            return {"version": "1.0", "username": USERNAME, "examples": []}
        try:
            with open(TRAINING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "examples" not in data or not isinstance(data["examples"], list):
                raise ValueError("missing examples list")
            return data
        except (json.JSONDecodeError, OSError, ValueError) as e:
            log.warning("training file corrupt (%s) — backing up as .bak and starting fresh", e)
            try:
                shutil.copy2(TRAINING_FILE, TRAINING_FILE + ".bak")
            except OSError:
                pass
            return {"version": "1.0", "username": USERNAME, "examples": []}

    def save_example(self, transcript: str, ai_note: str, rep_note: str):
        example = {
            "id":                str(uuid.uuid4()),
            "timestamp":         datetime.now().isoformat(timespec="seconds"),
            "transcript":        transcript,
            "ai_note":           ai_note,
            "rep_note":          rep_note,
            "used_for_training": True,
        }
        self.data['examples'].append(example)
        self._write()
        log.info("Saved training example %s (now %d total)",
                 example["id"][:8], len(self.data['examples']))

    def count(self) -> int:
        return len(self.data.get('examples', []))

    def get_examples_for_prompt(self) -> list[dict]:
        """Return style examples, ramped by how many are saved, each transcript
        truncated to an excerpt and the whole block capped by a budget."""
        examples = self.data.get('examples', [])
        n = len(examples)
        if n == 0:
            return []
        elif n <= 5:
            selected = examples
        elif n <= 15:
            selected = examples[-7:]
        else:
            selected = examples[-10:]

        out = []
        used = 0
        # Newest first so the most recent style wins if we hit the budget.
        for e in reversed(selected):
            excerpt = self._excerpt(e.get("transcript", ""))
            note = (e.get("rep_note") or "").strip()
            cost = len(excerpt) + len(note)
            if used + cost > EXAMPLES_BLOCK_BUDGET and out:
                break
            out.append({"transcript": excerpt, "rep_note": note})
            used += cost
        out.reverse()  # restore chronological order for the prompt
        return out

    @staticmethod
    def _excerpt(transcript: str) -> str:
        t = (transcript or "").strip()
        if len(t) <= EXAMPLE_TRANSCRIPT_CHARS:
            return t
        return t[:EXAMPLE_TRANSCRIPT_CHARS].rstrip() + " …"

    def _write(self):
        os.makedirs(TRAINING_DIR, exist_ok=True)
        with open(TRAINING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
