# Model taxonomy

The classification framework for the picker: three axes per model, plus the
vendor groups that define the tiers. Encoding of the user's standing
definitions — change the definitions here, not in the script.

## Capability tiers

Vendor groups come first; every model inherits its tier from its vendor and
name class.

**Frontier labs** — the four vendors whose flagships define the frontier.

| Vendor prefix | Examples |
|---|---|
| `anthropic` | Claude opus / sonnet class |
| `openai` | GPT pro / standard class |
| `x-ai` | Grok flagship class |
| `google` | Gemini pro class |

- **frontier** — flagship model of a frontier lab (top of its family:
  opus/pro/ultra-class names). The capability ceiling for any task.
- **frontier-value** — the flash/mini/haiku/lite class *of a frontier lab*
  (e.g. Claude haiku, Gemini flash, GPT mini class). Near-frontier
  intelligence at a fraction of the cost — the default for bulk work.

**Non-frontier vendors** — everyone else: `moonshotai`, `deepseek`,
`minimax`, `qwen`, `meta`/`meta-llama`, `mistralai`, `tencent`,
`bytedance-seed`, `stepfun`, `xiaomi`, `amazon`, `cohere`, `nvidia`, `ibm-granite`, etc.

- **flagship** — the top tier of a non-frontier lab: Kimi K3, DeepSeek
  V4-pro, MiniMax M3, Qwen max. Near-frontier capability, usually far
  cheaper, often open weights. "Flagship" never applies to a frontier-lab
  model. The user's rule: frontier means Anthropic, OpenAI, X.ai, or
  Google. Flagship means the top tier of everyone else.
- **value** — the cheap tier of any lab: names containing flash, mini,
  lite, air, small, haiku, nano, instant. Challenger class: near-flagship
  intelligence at a fraction of cost. When the vendor is a frontier lab
  this is `frontier-value` instead.
- **small** — open models ≤32B params (e.g. Qwen 14B/27B/32B class).
  Self-hostable on a single GPU; fine for simple tasks, never for hard ones.

Unknown vendors default to flagship if large, small if ≤32B, value if the
name says so. The script tags heuristically. The agent checks each tag.

## Deployment size

Two signals, both in the catalog.

- **Openness** — `hugging_face_id` present = open weights (downloadable,
  self-hostable, fine-tunable); absent = proprietary (API only). Openness is
  a preference in the selection policy and a hard requirement when the user
  needs local deployment.
- **Scale** — parameter count (in the description or name, e.g.
  `-27b`), context window (`context_length`), and max completion tokens.
  Large params = heavy local footprint; long context = long-context
  deployment.

## Primary use cases

Specialty tags, from strongest signal to weakest:

- **long-context** — context ≥ 256K tokens, or Kimi/Gemini lineage. The deep
  research / whole-book / whole-codebase class. Kimi (Moonshot) is the
  standing preference for deep research: long-context specialist lineage at
  flagship price.
- **reasoning** — `reasoning.default_enabled` true, or r1/thinking names.
  Chain-of-thought class: math, proofs, planning. DeepSeek reasoning and
  frontier reasoning models.
- **agentic** — `tools` in supported parameters. Tool calling, function
  dispatch, agent routing. MiniMax flash class is the standing cheap-routing
  preference.
- **vision** — image in input modalities.
- **embed** — embedding models (Embed, BGE, sentence-transformers).
  Infrastructure, never a generation pick.
- **general** — everything else; quality tracks the capability tier.

## Selection policy (standing order)

1. **Capability** — highest tier that satisfies the task's difficulty.
2. **Task fit** — must serve the category and specialty needs.
3. **Value** — $/M tokens and active promotions break ties.
4. **Openness** — open weights preferred at parity; required for local.

Standing routing preferences — defaults, not fixed laws. A live table can
override a default:

- Deep research → Kimi.
- Cheap routing and dispatch → MiniMax flash class.
- Hard reasoning → DeepSeek reasoning or frontier reasoning tier.
- Coding → OpenRouter `programming` leaders.
- Bulk general work → frontier-value or `:free` variants.