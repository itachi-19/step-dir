# Source this file from ~/.bashrc or ~/.zshrc:
#   source /path/to/sd.sh
#
# Optional: set SD_TUI_BIN=/path/to/sd_tui.py if sd_tui.py is stored elsewhere.

if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    _SD_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
    _SD_DIR="$(cd -- "$(dirname -- "${(%):-%x}")" && pwd)"
else
    _SD_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
fi

sd() {
    local tui_bin="${SD_TUI_BIN:-}"
    if [[ -z "$tui_bin" ]]; then
        if [[ -f "$_SD_DIR/sd_tui.py" ]]; then
            tui_bin="$_SD_DIR/sd_tui.py"
        elif command -v sd_tui.py >/dev/null 2>&1; then
            tui_bin="$(command -v sd_tui.py)"
        else
            echo "sd: cannot find sd_tui.py (place it next to sd.sh or set SD_TUI_BIN)" >&2
            return 1
        fi
    fi

    local -a runner
    if [[ -x "$tui_bin" ]]; then
        runner=("$tui_bin")
    else
        runner=(python3 "$tui_bin")
    fi

    # Pass help flags straight through without creating a temp file
    local arg
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                "${runner[@]}" "$@"
                return $?
                ;;
        esac
    done

    local tmpfile
    tmpfile="$(mktemp "${TMPDIR:-/tmp}/sd.XXXXXX")" || return 1

    "${runner[@]}" --output-file "$tmpfile" "$@"
    local rc=$?

    local target=""
    if [[ $rc -eq 0 && -s "$tmpfile" ]]; then
        target="$(<"$tmpfile")"
    fi
    rm -f -- "$tmpfile"

    if [[ $rc -eq 0 && -n "$target" && -d "$target" ]]; then
        cd -- "$target" || return 1
    fi
    return 0
}
