"""Running totals of OpenAI usage with an estimated cost, so drivers can see what the assistant spends."""
import json
import os
import threading
from datetime import datetime

from src.config_manager import CONFIG_PATH

USAGE_PATH = os.path.join(os.path.dirname(CONFIG_PATH), "usage.json")

# OpenAI list prices in US dollars per million tokens, for the models Settings offers.
# Any other model set in config.json is counted but not priced.
PRICES = {
    "gpt-4o-mini-transcribe": {"text": 1.25, "audio": 3.00, "output": 5.00},
    "gpt-4o-transcribe": {"text": 2.50, "audio": 6.00, "output": 10.00},
    "gpt-4o-mini": {"text": 0.15, "output": 0.60},
    "gpt-4.1-mini": {"text": 0.40, "output": 1.60},
}
WHISPER_PER_MINUTE = {"whisper-1": 0.006}  # whisper-1 bills audio length, not tokens

_lock = threading.Lock()
_data = None


def _field(obj, name):
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return value if isinstance(value, (int, float)) else 0


def cost_of(model, usage):
    """(tokens, estimated dollars or None if the model has no price) for one API reply's usage."""
    details = usage.get("input_token_details") if isinstance(usage, dict) else getattr(usage, "input_token_details", None)
    audio = _field(details, "audio_tokens") if details else 0
    inputs = _field(usage, "input_tokens") or _field(usage, "prompt_tokens")
    output = _field(usage, "output_tokens") or _field(usage, "completion_tokens")
    tokens = inputs + output

    if model in WHISPER_PER_MINUTE:
        return tokens, _field(usage, "seconds") / 60 * WHISPER_PER_MINUTE[model]
    price = PRICES.get(model)
    if price is None:
        return tokens, None
    text = inputs - audio  # the input count includes the audio tokens
    dollars = (text * price["text"] + audio * price.get("audio", price["text"]) + output * price["output"]) / 1e6
    return tokens, dollars


def _month():
    return datetime.now().strftime("%Y-%m")


def _load():
    global _data
    if _data is None:
        try:
            with open(USAGE_PATH, "r", encoding="utf-8") as f:
                _data = json.load(f)
            if not isinstance(_data.get("months"), dict):
                raise ValueError("no months")
        except (OSError, ValueError, AttributeError):
            _data = {"months": {}}
    return _data


def _save():
    try:
        os.makedirs(os.path.dirname(USAGE_PATH), exist_ok=True)
        tmp_path = USAGE_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2)
        os.replace(tmp_path, USAGE_PATH)
    except OSError as e:
        print(f"Couldn't save usage totals: {e}")


def record(model, usage, command=False):
    """Add one API reply to this month's totals. command=True for the transcription, sent once per voice command.

    Never raises: counting must not break a command.
    """
    try:
        tokens, dollars = cost_of(model, usage) if usage is not None else (0, 0.0)
    except (TypeError, ValueError, KeyError):
        tokens, dollars = 0, 0.0
    with _lock:
        month = _load()["months"].setdefault(_month(), {"commands": 0, "tokens": 0, "cost": 0.0, "unpriced": 0})
        month["commands"] += 1 if command else 0
        month["tokens"] += tokens
        if dollars is None:
            month["unpriced"] += tokens
        else:
            month["cost"] += dollars
        _save()


def summary():
    """{"month": totals for this month, "total": totals for all time}. Totals: commands, tokens, cost, unpriced."""
    with _lock:
        months = _load()["months"]
        empty = {"commands": 0, "tokens": 0, "cost": 0.0, "unpriced": 0}
        total = dict(empty)
        for values in months.values():
            for key in total:
                total[key] += values.get(key, 0)
        return {"month": dict(months.get(_month(), empty)), "total": total}


def history():
    """[(month "YYYY-MM", totals)], newest first."""
    with _lock:
        return sorted(((month, dict(values)) for month, values in _load()["months"].items()), reverse=True)


def reset():
    with _lock:
        global _data
        _data = {"months": {}}
        _save()
