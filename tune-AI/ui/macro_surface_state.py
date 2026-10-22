"""Small, presentation-independent helpers for DAW-owned macro snapshots."""


def macro_at(snapshot, index):
    """Return a slot by its protocol ID, never by an assumed list ordering."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("macros"), list):
        return None
    for macro in snapshot["macros"]:
        if isinstance(macro, dict) and macro.get("macroId") == index:
            return macro
    return None


def macro_is_assigned(macro):
    """Keep a broken or bypassed mapping from falling back to legacy MIDI."""
    return isinstance(macro, dict) and macro.get("state") in (1, 2, 3)


def macro_value_text(macro):
    """Use the plug-in's formatted text, not a fabricated percentage."""
    if not isinstance(macro, dict):
        return ""
    targets = macro.get("targets")
    if isinstance(targets, list) and len(targets) == 1 and isinstance(targets[0], dict):
        return str(targets[0].get("valueText") or "")
    return ""
