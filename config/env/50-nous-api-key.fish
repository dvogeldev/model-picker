# [model-picker] NOUS_API_KEY from pass. No key is stored in a file.
# pass entry: nous/NOUS_API_KEY
if not set -q NOUS_API_KEY; and type -q pass
	set -l _mp_key (pass show nous/NOUS_API_KEY </dev/null 2>/dev/null | head -n1 | string collect)
	if test (string length -- "$_mp_key") -ge 20
		set -gx NOUS_API_KEY "$_mp_key"
	end
	set -e _mp_key
end
