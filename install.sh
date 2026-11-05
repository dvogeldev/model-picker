#!/usr/bin/env bash
# Install model-picker: symlink the skill, install the pi extension,
# seed the context map, enable the daily timer. Safe to run again.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Skill on every skill-consuming harness path.
# pi reads ~/.agents/skills. Hermes reads ~/.hermes/skills.
# Grok reads ~/.grok/skills. OpenCode reads ~/.config/opencode/skills.
# The entries are relative links to the canonical install, so they follow
# wherever the repo lives.
mkdir -p ~/.agents/skills
if [ -e ~/.agents/skills/model-picker ] && [ ! -L ~/.agents/skills/model-picker ]; then
	echo "ERROR: ~/.agents/skills/model-picker exists and is not a symlink." >&2
	echo "Move it out of the way, then run this script again." >&2
	exit 1
fi
ln -sfn "$repo" ~/.agents/skills/model-picker
for d in ~/.hermes/skills ~/.grok/skills ~/.config/opencode/skills; do
	mkdir -p "$d"
	ln -sfn "../../.agents/skills/model-picker" "$d/model-picker"
done

# 1b. NOUS_API_KEY from pass — never a key in a file.
mkdir -p ~/.config/fish/conf.d
cp "$repo/config/env/50-nous-api-key.fish" ~/.config/fish/conf.d/50-nous-api-key.fish
if [ -f ~/.bashrc ] && ! grep -q "model-picker: NOUS_API_KEY" ~/.bashrc; then
	cat "$repo/config/env/nous-api-key.sh" >> ~/.bashrc
fi

# 1c. OpenCode config: add the nous-portal provider and the context
# agents. The merge adds or replaces only these keys. Everything else
# in opencode.json stays as it is. A backup is kept next to the file.
mkdir -p ~/.config/opencode
python3 - "$repo/config/opencode.json" <<'PYEOF'
import json, os, shutil, sys
repo_cfg = json.load(open(sys.argv[1]))
path = os.path.expanduser("~/.config/opencode/opencode.json")
try:
	with open(path) as f:
		current = json.load(f)
	if not isinstance(current, dict):
		raise ValueError("not an object")
except (OSError, ValueError):
	current = {}
if os.path.exists(path):
	shutil.copy2(path, path + ".model-picker.bak")
current.setdefault("provider", {})["nous-portal"] = repo_cfg["provider"]["nous-portal"]
agents = current.setdefault("agent", {})
for name, spec in repo_cfg["agent"].items():
	agents[name] = spec
with open(path, "w") as f:
	json.dump(current, f, indent=2)
	f.write("\n")
print("opencode.json: provider nous-portal + %d context agents installed" % len(repo_cfg["agent"]))
PYEOF

# 2. pi extension.
mkdir -p ~/.pi/agent/extensions
cp "$repo/extensions/set-model.ts" ~/.pi/agent/extensions/set-model.ts

# 3. Context map (live data — never overwrite an edited map).
if [ ! -f ~/.pi/agent/set-model.json ]; then
	cp "$repo/config/set-model.json" ~/.pi/agent/set-model.json
fi

# 4. Daily refresh timer.
mkdir -p ~/.config/systemd/user
cp "$repo/systemd/model-picker-refresh.service" "$repo/systemd/model-picker-refresh.timer" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now model-picker-refresh.timer

echo "Installed."
echo "Run /reload in pi to activate /set-model."
systemctl --user list-timers model-picker-refresh.timer --no-pager | head -3
