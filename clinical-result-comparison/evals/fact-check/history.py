"""Read only durable model-message envelopes and resolve their target turn offline.

Never descend into parts, tool payloads, UI output, or arbitrary JSON containers.
Legacy archives can omit model turn IDs; UI pydantic timestamps bridge that gap.
"""
import json
from pathlib import Path


def turn_id(message):
    meta = message.get('metadata') or {}
    ids = {str(v) for v in (message.get('turn_id'), meta.get('turn_id')) if v}
    if len(ids) > 1:
        raise ValueError('conflicting message turn IDs')
    return next(iter(ids), None)


def target_messages(run_dir):
    root = Path(run_dir)
    path = root/'debug-history.json'
    if not path.is_file():
        return [], 'durable model history missing'
    history = json.loads(path.read_text())
    if isinstance(history, dict):
        model = history.get('raw_model_messages', history.get('effective_model_messages'))
        ui = history.get('raw_ui_messages', [])
    else:
        model, ui = history, []
    if not isinstance(model, list) or not all(isinstance(m, dict) and
            m.get('kind') in ('request', 'response') and isinstance(m.get('parts'), list)
            for m in model):
        return [], 'unrecognized durable model-message shape'
    mp = root/'messages.json'
    if mp.is_file():
        current_ui = json.loads(mp.read_text())
        if isinstance(current_ui, list):
            ui = [*ui, *current_ui]
    ui = [m for m in ui if isinstance(m, dict)]
    run = json.loads((root/'run.json').read_text()) if (root/'run.json').is_file() else {}
    target = run.get('turn_id')
    known = {t for m in [*model, *ui] if (t := turn_id(m))}
    if not target:
        if len(known) > 1:
            return [], 'ambiguous target turn (multiple archived turns, no run.turn_id)'
        target = next(iter(known), None)
    timestamps = {}
    for m in ui:
        t = turn_id(m)
        stamp = ((m.get('metadata') or {}).get('pydantic_ai') or {}).get('timestamp')
        if stamp and t:
            timestamps.setdefault(stamp, set()).add(t)
    # A single prompt is the only safe fallback for old archives without timing/IDs.
    prompts = sum(p.get('part_kind') == 'user-prompt' for m in model
                  for p in m['parts'] if isinstance(p, dict))
    single = prompts == 1 and (not known or known == {target})
    selected = []
    for m in model:
        explicit = turn_id(m)
        timed = timestamps.get(m.get('timestamp'), set())
        if len(timed) > 1 or explicit and timed and timed != {explicit}:
            return [], 'ambiguous model-message turn mapping'
        resolved = explicit or next(iter(timed), None)
        if resolved is None:
            if not single:
                return [], 'unscoped model message; target turn cannot be proven'
            resolved = target
        if resolved == target:
            selected.append(m)
    return selected, f'target turn {target or "legacy single-prompt"}'
