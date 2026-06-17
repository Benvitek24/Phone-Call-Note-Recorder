"""llama-cpp-python CRM-note generation (CPU only, streaming).

Corrections folded in:
  (H) The literal "<|begin_of_text|>" is NOT included in the prompt. llama-cpp
      adds the BOS token itself when tokenizing, so emitting it as text too would
      produce a double-BOS and degrade output. The header special tokens are
      still recognized because create_completion tokenizes with special=True.
  (D) n_ctx is 8192 (was 4096 in the spec) so a real ~50-minute call plus
      few-shot examples fits. The transcript is also pre-trimmed by
      transcription.transcript_for_llm() before it reaches build_prompt().
"""

from llama_cpp import Llama

from PyQt6.QtCore import QThread, pyqtSignal

from utils.paths import MODEL_FILE
from utils.logger import get_logger
from core.transcription import transcript_for_llm

log = get_logger("llm")

N_CTX = 8192        # fits long transcript + examples (review item D)
MAX_TOKENS = 350
TEMPERATURE = 0.3
STOP = ["<|eot_id|>", "<|end_of_text|>"]

SYSTEM_PROMPT = """You are a CRM note writer for a Keyence inside sales representative.

Rules:
- Write in lowercase
- Write conversationally, not like formal business writing
- Write in third person about the customer
- Keep notes short — if the call was short, the note is short
- Capture only what was explicitly discussed: why they called, the customer's application, products mentioned, what happens next
- Never add information not stated in the transcript
- Never pad with filler phrases or pleasantries
- Always end with the action taken or next step
- Preserve product names and model numbers exactly as spoken
- Do not use bullet points
- The transcript is auto-merged from two separate audio channels ("You" = the rep, "Customer" = the other party) by timestamp, so turns may be interleaved, split mid-sentence, or contain filler/back-channel words ("yeah", "okay"). Reconstruct what was actually discussed; do not be thrown off by fragmentation."""


def load_llm() -> Llama:
    """Load the GGUF model. CPU only (n_gpu_layers=0) — intentional per spec."""
    return Llama(
        model_path=MODEL_FILE,
        n_gpu_layers=0,
        n_ctx=N_CTX,
        verbose=False,
    )


def build_prompt(transcript: str, examples: list[dict]) -> str:
    """Build the Llama-3 instruction prompt. No literal BOS (see correction H).

    examples: list of {"transcript": str, "rep_note": str}
    """
    examples_block = ""
    if examples:
        examples_block = "\n\nHere are examples of good CRM notes in the correct style:\n"
        for i, ex in enumerate(examples, 1):
            examples_block += (
                f"\n--- Example {i} ---\n"
                f"Transcript:\n{ex['transcript']}\n\n"
                f"Note:\n{ex['rep_note']}\n"
            )

    return (
        f"<|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}"
        f"{examples_block}"
        f"<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"Write a CRM note for this call transcript:\n\n{transcript}"
        f"<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


class SummarizationThread(QThread):
    token_ready            = pyqtSignal(str)
    summarization_complete = pyqtSignal(str)
    summarization_error    = pyqtSignal(str)

    def __init__(self, llm, transcript, training_store):
        super().__init__()
        self.llm            = llm
        self.transcript     = transcript
        self.training_store = training_store
        self._cancelled     = False

    def run(self):
        try:
            examples = self.training_store.get_examples_for_prompt()
            prompt = build_prompt(transcript_for_llm(self.transcript), examples)

            full_text = ""
            for token in self.llm.create_completion(
                prompt,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True,
                stop=STOP,
            ):
                if self._cancelled:
                    break
                chunk = token['choices'][0]['text']
                if chunk:
                    full_text += chunk
                    self.token_ready.emit(chunk)

            self.summarization_complete.emit(full_text.strip())
        except Exception as e:  # noqa: BLE001
            log.exception("Summarization failed")
            self.summarization_error.emit(str(e))

    def cancel(self):
        self._cancelled = True
