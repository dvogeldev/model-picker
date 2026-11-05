# >>> model-picker: NOUS_API_KEY from pass (no key stored in files) >>>
if [ -z "${NOUS_API_KEY:-}" ] && command -v pass >/dev/null 2>&1; then
	_mp_key="$(pass show nous/NOUS_API_KEY </dev/null 2>/dev/null | head -n1)"
	if [ "${#_mp_key}" -ge 20 ]; then
		export NOUS_API_KEY="$_mp_key"
	fi
	unset _mp_key
fi
# <<< model-picker <<<
