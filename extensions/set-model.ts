import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import { readFileSync } from "node:fs";

/**
 * /set-model — set the conversation model for a work context.
 *
 * Contexts (deep-research, coding, reasoning, image-generation, routing,
 * fast, general) map to a model + thinking level. The map lives in
 * ~/.pi/agent/set-model.json (editable data; maintained by the
 * model-picker skill); built-in defaults follow the model-picker taxonomy.
 */

type ContextEntry = { model: string; thinking?: string; note?: string };

const DEFAULT_CONTEXTS: Record<string, ContextEntry> = {
	"deep-research": {
		model: "nous-portal/moonshotai/kimi-k3",
		thinking: "high",
		note: "long-context specialist — deep research, whole books/codebases",
	},
	coding: {
		model: "nous-portal/z-ai/glm-5.3",
		thinking: "high",
		note: "coding workhorse",
	},
	reasoning: {
		model: "nous-portal/deepseek/deepseek-v4-pro",
		thinking: "medium",
		note: "hard reasoning — math, proof-style logic",
	},
	"image-generation": {
		model: "nous-portal/qwen/qwen3.8-max-0902",
		thinking: "high",
		note: "vision flagship for the conversation; image generation runs via codemode models.generateImages()",
	},
	routing: {
		model: "nous-portal/minimax/minimax-m3",
		thinking: "medium",
		note: "cheap agentic routing / dispatch",
	},
	fast: {
		model: "nous-portal/z-ai/glm-5.3-flash",
		thinking: "low",
		note: "cheap quick work, high volume",
	},
	general: {
		model: "nous-portal/z-ai/glm-5.3",
		thinking: "high",
		note: "default general assistant",
	},
};

const CONTEXT_ALIASES: Record<string, string> = {
	research: "deep-research",
	deep: "deep-research",
	code: "coding",
	programming: "coding",
	prog: "coding",
	thinking: "reasoning",
	logic: "reasoning",
	image: "image-generation",
	images: "image-generation",
	"image-gen": "image-generation",
	imagegen: "image-generation",
	route: "routing",
	agent: "routing",
	dispatch: "routing",
	quick: "fast",
	cheap: "fast",
	value: "fast",
	default: "general",
	chat: "general",
};

function agentDir(): string {
	const override = process.env.PI_CODING_AGENT_DIR?.trim();
	return override && override.length > 0 ? override : join(homedir(), ".pi/agent");
}

function loadContexts(): Record<string, ContextEntry> {
	try {
		const raw = JSON.parse(readFileSync(join(agentDir(), "set-model.json"), "utf8")) as Record<
			string,
			unknown
		>;
		const merged: Record<string, ContextEntry> = { ...DEFAULT_CONTEXTS };
		for (const [key, value] of Object.entries(raw)) {
			if (typeof value !== "object" || value === null) continue;
			const entry = value as Record<string, unknown>;
			if (typeof entry.model !== "string" || !entry.model.trim()) continue;
			merged[key] = {
				model: entry.model.trim(),
				thinking: typeof entry.thinking === "string" ? entry.thinking : undefined,
				note: typeof entry.note === "string" ? entry.note : undefined,
			};
		}
		return merged;
	} catch {
		return { ...DEFAULT_CONTEXTS };
	}
}

function splitModelId(spec: string): { provider: string; id: string } {
	const slash = spec.indexOf("/");
	if (slash === -1) return { provider: "nous-portal", id: spec };
	return { provider: spec.slice(0, slash), id: spec.slice(slash + 1) };
}

export default function setModel(pi: ExtensionAPI) {
	const usage = (contexts: Record<string, ContextEntry>) =>
		`/set-model <context> — contexts: ${Object.keys(contexts).join(", ")}`;

	pi.registerCommand("set-model", {
		description: "Set the conversation model for a work context (deep-research, coding, reasoning, image-generation, routing, fast, general), or `update` to refresh catalog + assignments now",
		getArgumentCompletions: (prefix: string) => {
			const contexts = loadContexts();
			const items = Object.keys(contexts).map((k) => ({ value: k, label: `${k} — ${contexts[k].model}` }));
			items.push({ value: "update", label: "update — refresh catalog + assignments now" });
			const filtered = items.filter((i) => i.value.startsWith(prefix));
			return filtered.length > 0 ? filtered : null;
		},
		handler: async (args: string, ctx) => {
			const contexts = loadContexts();
			const arg = args.trim().toLowerCase();
			let key: string | undefined;

			if (arg === "update") {
				const script = join(
					homedir(),
					".agents/skills/model-picker/scripts/refresh_assignments.py",
				);
				const exit = await new Promise<number>((resolve) => {
						execFile("python3", [script], { timeout: 120_000 }, (error) => resolve(error ? 1 : 0));
				});
				if (exit !== 0) {
					ctx.ui.notify("Assignment refresh failed — see ~/.cache/model-picker/assignments-report.md", "error");
					return;
				}
				try {
					const report = readFileSync(
						join(homedir(), ".cache/model-picker/assignments-report.md"),
						"utf8",
					);
					const changed = report.trim().split("\n").filter((l) => l.includes("→"));
					const unchanged = report.trim().split("\n").filter((l) => l.includes("(unchanged)")).length;
					const summary = changed.length > 0 ? changed.join("\n") : `no changes (${unchanged} contexts verified)`;
					ctx.ui.notify(`Assignments refreshed\n${summary}`, "info");
				} catch {
					ctx.ui.notify("Assignments refreshed", "info");
				}
				return;
			}

			if (!arg) {
				const items = Object.entries(contexts).map(
					([k, v]) => `${k} — ${v.model}${v.thinking ? ` @ ${v.thinking}` : ""}${v.note ? `  (${v.note})` : ""}`,
				);
				const choice = await ctx.ui.select("Set model for context:", items);
				if (!choice) return;
				key = choice.split(" — ")[0];
			} else {
				key = arg in contexts ? arg : CONTEXT_ALIASES[arg];
				if (!key) {
					ctx.ui.notify(usage(contexts), "error");
					return;
				}
			}

			const entry = contexts[key];
			const { provider, id } = splitModelId(entry.model);
			const model = ctx.modelRegistry.find(provider, id);
			if (!model) {
				ctx.ui.notify(`Model not found in registry: ${entry.model}`, "error");
				return;
			}
			const ok = await pi.setModel(model);
			if (!ok) {
				ctx.ui.notify(`No credentials configured for provider ${provider}`, "error");
				return;
			}
			if (entry.thinking) await pi.setThinkingLevel(entry.thinking);
			const level = pi.getThinkingLevel();
			const note = entry.note ? `\n${entry.note}` : "";
			ctx.ui.notify(`${key} → ${provider}/${id} @ ${level}${note}`, "info");
		},
	});
}
