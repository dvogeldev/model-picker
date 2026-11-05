#!/usr/bin/env bash
# Install model-picker: symlink the skill, install the pi extension,
# seed the context map, enable the daily timer. Safe to run again.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Skill on every skill-consuming harness path.
# pi and opencode read ~/.agents/skills. Hermes reads ~/.hermes/skills.
# Grok reads ~/.grok/skills. Hermes and Grok entries are relative links to
# the canonical install, so they follow wherever the repo lives.
mkdir -p ~/.agents/skills
if [ -e ~/.agents/skills/model-picker ] && [ ! -L ~/.agents/skills/model-picker ]; then
	echo "ERROR: ~/.agents/skills/model-picker exists and is not a symlink." >&2
	echo "Move it out of the way, then run this script again." >&2
	exit 1
fi
ln -sfn "$repo" ~/.agents/skills/model-picker
for d in ~/.hermes/skills ~/.grok/skills; do
	mkdir -p "$d"
	ln -sfn "../../.agents/skills/model-picker" "$d/model-picker"
done

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
