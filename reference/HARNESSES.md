# Setting the model per harness

How each harness on this machine sets the conversation model. The context
map applies in each harness. Context types: deep-research, coding,
reasoning, image-generation, routing, fast, general.

## pi (this harness)

**`/set-model <context>`** — registered by `~/.pi/agent/extensions/set-model.ts`.
Switches the conversation model and thinking level in one step, recorded in
the session (restored on resume). Reads the context map from
`~/.pi/agent/set-model.json` — data, not code. With no argument it opens a
context picker. Aliases: research, code, thinking, image, route, quick.

**`/set-model update`** — runs the assignment refresh now (same job as the
daily timer) and reports the diff. The timer:
`systemctl --user list-timers model-picker-refresh.timer` — daily 06:30,
`Persistent=true`, unit files in `~/.config/systemd/user/`.

Other paths:

- `/model` — interactive model picker; `Ctrl+S` on a model saves it as the
  default for new sessions. Models come from the `nous-portal` extension
  (full Nous catalog, OpenRouter-style ids under provider `nous-portal`).
- `Ctrl+P` cycles scoped models; `/scoped-models` and settings
  `enabledModels` + `modelThinkingLevels` control the cycle and startup
  levels. Current scoped set lives in `~/.pi/agent/settings.json`.
- Startup: `--provider nous-portal --model z-ai/glm-5.3` or settings
  `defaultProvider`/`defaultModel`.
- Per-request routing without switching: virtual models
  (`pi.registerVirtualModel` in an extension) pick a physical model per
  request. Use a virtual model if a context must route every turn
  automatically, with no command.

**Image generation is not a conversation model.** pi generates images
through codemode: `models.generateImages()` with image-type models (e.g.
`openrouter/google/gemini-2.5-flash-image`), which never appear in `/model`.
`/set-model image-generation` sets a vision flagship (e.g.
`qwen3.8-max-0902`) so the conversation can read images. The codemode image
model creates images.

## hermes (`~/.hermes`)

- `/model <model>` — gateway slash command; sets a per-session model
  override (`gateway/slash_commands_model.py` → `set_model_override`).
  Model ids are OpenRouter-style: `z-ai/glm-5.3`, `moonshotai/kimi-k3`.
- `/fast`, `/reasoning` — service tier and reasoning display toggles.
- Standing config in `~/.hermes/config.yaml`: `model.default`
  (`google/gemini-3.8-flash` via provider `nous`). The file also holds
  per-role `reference_models` with `reasoning_effort`. That file is the
  hermes equivalent of the context map.
- Hermes plugins live in `~/.hermes/plugins/` (`plugin.yaml` +
  `__init__.py`). The manifest key is `provides_hooks`. Enable a plugin
  through `plugins.enabled` in config.yaml. A hermes-side `/set-model`
  plugin is a possible follow-up. No such plugin is installed yet.

## opencode (`~/.config/opencode`)

- `/models` — built-in model picker for the session.
- `opencode.json` — per-agent models and custom providers. The file is
  empty on this machine. An agent entry like `{ "model": ... }` pins a
  model per agent type. That entry is the opencode analogue of the context
  map.
