"""UserPromptSubmit hook: name the installed skills that apply to THIS message.

Fixes the most common fleet gap: the skill is installed, the session never
loads it. Reads the hook JSON on stdin, matches the prompt against a rules
file, prints at most 3 short hints. Prints nothing when nothing matches, so
it costs no tokens on ordinary messages.

Rules file (JSON list), default ~/.claude/skill-reminder.json:
  [{"skill": "report-now", "why": "status checked live, with the time",
    "any": ["reporte", "como va", "que paso"]}]
Matching is case- and accent-insensitive, on whole words/phrases.
Skills not installed under ~/.claude/skills are skipped.

Optional roles file, default ~/.claude/skill-reminder-roles.json:
  {"supervisor_sessions": ["<session_id>"], "relay_from_names": ["SUPERVISOR"]}
- A supervisor session gets up to 5 hints plus a line asking it to name those
  skills in the order it passes to another session.
- A <cross-session-message> whose from-name contains a relay_from_names entry is
  matched like the user's own words, so the session receiving the order gets
  hints too. Names must match exactly (case and accents ignored). Subagent
  reports, notifications, pasted text and other peers stay ignored.
- For skill hints only: a relayed order is never the user's approval.

Test without a hook:  echo {"prompt":"dame el reporte"} | python skill_reminder.py
"""
import json, re, sys, unicodedata
from pathlib import Path

HOME = Path.home() / ".claude"


def plain(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        raw = sys.stdin.buffer.read()  # bytes: on Windows sys.stdin decodes as cp1252 and breaks accents ("cómo" -> "cÃ³mo")
        try:
            data = raw.decode("utf-8")
        except UnicodeDecodeError:
            data = raw.decode("cp1252", "replace")
        hook = json.loads(data.lstrip("﻿") or "{}")
        prompt = hook.get("prompt", "")
        session = hook.get("session_id", "")
    except ValueError:
        return
    roles = {}
    roles_path = HOME / "skill-reminder-roles.json"
    if roles_path.exists():
        try:
            roles = json.loads(roles_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            roles = {}
    if not isinstance(roles, dict):
        roles = {}

    def str_list(key):
        v = roles.get(key, [])
        return [x for x in v if isinstance(x, str) and x] if isinstance(v, list) else []

    is_super = isinstance(session, str) and bool(session) and session in str_list("supervisor_sessions")
    if is_super and roles.get("log_supervisor_hits"):
        try:  # proof the ids match, one short line per supervisor prompt
            with open(HOME / "skill-reminder-roles.log", "a", encoding="utf-8") as f:
                f.write(session + "\n")
        except OSError:
            pass
    relay_names = [plain(n).strip() for n in str_list("relay_from_names")]
    relayed_by = ""
    # An order relayed by a listed session (a supervisor) is matched like the
    # user's own words, so the session receiving it also gets its hints.
    # For skill hints only: a relayed order is never the user's approval.
    if relay_names:
        prompt = re.sub(r"<pasted_content\b[\s\S]*?</pasted_content>", " ", prompt)  # a pasted fake block must not count
    for m in re.finditer(r"<cross-session-message\b([^>]*)>([\s\S]*?)</cross-session-message>", prompt) if relay_names else ():
        name = re.search(r'from-name="([^"]*)"', m.group(1))
        if name and plain(name.group(1)).strip() in relay_names:
            relayed_by, prompt = name.group(1), m.group(2)
            break
    rules_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HOME / "skill-reminder.json"
    if not prompt or not rules_path.exists():
        return
    # Only the human's own words count. Pasted pages, other sessions' messages,
    # subagent reports and task notifications also arrive as prompts and
    # trigger false hints (seen live: a report saying "ERROR" fired diagnosing-bugs).
    prompt = re.sub(r"<(pasted_content|agent-message|cross-session-message|task-notification|system-reminder)\b[\s\S]*?</\1>", " ", prompt)
    if re.search(r"<(agent-message|cross-session-message|task-notification)\b", prompt):
        return  # unterminated machine block: say nothing rather than guess
    prompt = re.sub(r"(?<!\w)/[\w:-]+", " ", prompt)  # /slash-commands typed inline
    text = plain(prompt)
    if text.lstrip().startswith("/"):
        return  # the user is already invoking a skill/command
    installed = {p.parent.name for p in (HOME / "skills").glob("*/SKILL.md")}
    hits = []
    for rule in json.loads(rules_path.read_text(encoding="utf-8")):
        if rule["skill"] not in installed:
            continue
        n = sum(1 for k in rule["any"] if re.search(r"(?<!\w)" + re.escape(plain(k)) + r"(?!\w)", text))
        if n:
            hits.append((n, rule))
    if not hits:
        return
    hits.sort(key=lambda h: -h[0])
    top = hits[:5 if is_super else 3]
    lines = [f"- `{r['skill']}`: {r['why']}" for _, r in top]
    head = "SKILLS THAT APPLY TO THIS MESSAGE"
    if relayed_by:
        head += f" (order relayed by {relayed_by})"
    out = head + " (load them with the Skill tool before working, unless already loaded in this session):\n" + "\n".join(lines)
    if is_super:
        names = ", ".join(f"`{r['skill']}`" for _, r in top)
        out += f"\nYou hand orders to other sessions: when you pass this one on, write in your message which skills it must load ({names}, plus the ones its own work needs)."
    print(out)


if __name__ == "__main__":
    main()
