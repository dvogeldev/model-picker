# model-picker

Picks the right model for the job, from the Nous Portal and OpenRouter
catalogs. It refreshes once a day. You can switch with one command.

You run several AI harnesses (pi, hermes, opencode) against the Nous
Portal, and new models show up constantly. This repo keeps those decisions
out of your head. Every model gets classified once a day. Each kind of
work gets a standing model. So you switch with `/set-model <context>`
instead of researching model cards at midnight.

## What you get

- **A picker skill** for any agent that reads skills. Ask "which model
  should I use for X?" and get a ranked answer, with current prices and
  promotions.
- **A `/set-model` command in pi** — `/set-model coding` switches the
  conversation to the standing coding model in one step.
- **A daily refresh** (a systemd timer at 06:30) that re-ingests both
  catalogs. It keeps the standing assignments current. You get the newest Kimi
  for deep research, the newest MiniMax flash for routing, and so on.

## Install

```bash
git clone git@github.com:dvogeldev/model-picker.git ~/projects/model-picker
~/projects/model-picker/install.sh
```

The installer links the repo into `~/.agents/skills/`, installs the pi
extension, and enables the daily timer. It's safe to run again.

## The standing map

| Context | What it's for |
|---|---|
| `deep-research` | Long-context work — Kimi lineage |
| `coding` | Top coding flagship people actually use |
| `reasoning` | Hard math and logic — DeepSeek lineage |
| `image-generation` | Conversations about images (vision model) |
| `routing` | Cheap agent dispatch — MiniMax flash |
| `fast` | High-volume, low-cost work |
| `general` | The everyday default |

Which exact model each context points at changes as new models ship. Run
`/set-model update` in pi (or
`python3 scripts/refresh_assignments.py`) to see today's assignments and
what changed.

## Changing the defaults

You have two levers:

- **Change the rule** (e.g. "coding should prefer Qwen"): the rules live
  in `scripts/refresh_assignments.py`. Change one, run the script, and
  every future refresh follows it.
- **Freeze one context**: add `"lock": true` to an entry in
  `~/.pi/agent/set-model.json`. The daily refresh then leaves it alone.

## Where things live

Everything else in this repo is documented for the agents that maintain
it.

- `AGENTS.md` — the map for agents: which file governs which decision,
  and how to change things safely.
- `SKILL.md` + `reference/` — the skill itself, written for machine
  readers (Simplified Technical English).
- `extensions/set-model.ts` — the pi `/set-model` command.
- `systemd/` — the daily refresh units.

If you're a person: you're in the right place. If you're an agent: start
at `AGENTS.md`.
