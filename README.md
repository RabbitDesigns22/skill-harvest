# skill-harvest

**Your best skills are already in your chat history. This finds them.**

`skill-harvest` is an agent skill for Claude Code. It reads **every** session on your machine, not just the current one, and does four things:

1. **Finds the methods worth a skill.** These are the asks you repeat, the third attempt that finally worked, and the correction you had to make twice. Evidence is counted across sessions; a message pasted into six chats counts once.
2. **Checks the market before building.** It runs `npx skills find` with 3+ queries and reads the SKILL.md of the top results. Each candidate then gets a verdict: EXISTS-GOOD (install that one), EXISTS-WEAK (build only the named missing part) or GAP.
3. **Finds the skills you installed that your sessions never load.** In our fleet of 42 sessions this was the biggest gap, bigger than any missing skill. It includes a `UserPromptSubmit` hook. The hook names the installed skill that fits each message and stays silent otherwise. Replayed on 300 real messages, it gave a hint on 44, at about 0.8 s each.
4. **Publishes only what passes a gate.** The skill must show evidence in 2+ sessions, be a method rather than a one-off, pass the market check, and win a with/without test on 3 real prompts. It must also contain no private data, and nothing goes public without your ok.

## What is in it

| File | What it does |
|---|---|
| `scripts/read_sessions.py` | Turns all `~/.claude/projects/**/*.jsonl` into one short Markdown digest per session: real human turns only, plus the skills loaded and the tools used. Measured: 5.2 GB raw became 977 KB of digests. |
| `scripts/forgotten_skills.py` | A prefilter that lists installed skills whose trigger phrases match what you asked in sessions that never loaded them. |
| `scripts/skill_reminder.py` | The hook. Your rules go in `~/.claude/skill-reminder.json`; there is an example in `references/`. |
| `references/` | The reader brief for parallel subagents, the market-check method, the quality gate, and the hand-off message template. |

## Install

```bash
npx skills add RabbitDesigns22/skill-harvest
```

Or copy `skills/skill-harvest/` into `~/.claude/skills/`.

Then ask: *"harvest skills from my sessions"*.

To turn on the reminder hook, add this to `~/.claude/settings.json` under `hooks.UserPromptSubmit`:

```json
{ "hooks": [ { "type": "command", "command": "python ~/.claude/skills/skill-harvest/scripts/skill_reminder.py", "timeout": 5 } ] }
```

## Honest limits

- Raw transcripts are private. Everything stays on your machine, and the scripts never modify `.jsonl` files.
- The forgotten-skill finder and the hook match words, not meaning. Read the hits before acting on them.
- How it differs from [task-observer](https://github.com/rebelytics/one-skill-to-rule-them-all), which logs friction *while* a session runs: `skill-harvest` works backwards over everything you already did, and adds the market check, the forgotten-skill audit and the publish gate. The two work well together.

## Works well with

- [`never-twice`](https://github.com/RabbitDesigns22/never-twice): a shared error log so the same mistake never happens twice.
- [`in-the-loop`](https://github.com/RabbitDesigns22/in-the-loop): many agents, one shared live board.
- [`one-pass`](https://github.com/RabbitDesigns22/one-pass): get it right the first time.

## Español

**Tus mejores skills ya están en tus chats.** `skill-harvest` lee todos los chats de tu compu y saca los métodos que se repiten o que siempre fallan. Antes de crear nada revisa el mercado (skills.sh). Encuentra las skills que tienes instaladas y que tus chats nunca cargan, y trae un aviso automático que te dice cuál aplica en cada mensaje. Solo publica lo que pasa un filtro estricto: pruebas reales, hueco en el mercado, prueba con y sin la skill y nada privado.

Instalar: `npx skills add RabbitDesigns22/skill-harvest`

## License

MIT. Made by [Rabbit Designs](https://github.com/RabbitDesigns22).
