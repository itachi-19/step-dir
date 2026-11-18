#!/usr/bin/env bash
set -euo pipefail

# Installer for sd (TUI directory navigator) on Linux and macOS.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/itachi-19/step-dir/master/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/itachi-19/step-dir/master/install.sh | bash -s -- --uninstall

REPO_RAW_URL="${SD_REPO_URL:-https://raw.githubusercontent.com/itachi-19/step-dir/master}"
INSTALL_DIR="${SD_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/sd}"
MARKER_START="# >>> sd >>>"
MARKER_END="# <<< sd <<<"

UNINSTALL=0
for arg in "$@"; do
    case "$arg" in
        --uninstall)
            UNINSTALL=1
            ;;
        -h|--help)
            cat <<'EOF'
Install or uninstall sd (TUI directory navigator).

Options:
  --uninstall    Remove sd files and shell rc block
  -h, --help     Show this help message

Environment variables:
  SD_INSTALL_DIR  Target directory (default: ~/.local/share/sd)
  SD_REPO_URL     Base raw URL to download sd_tui.py and sd.sh
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

detect_rc_files() {
    local -a files=()
    local shell_name
    shell_name="$(basename "${SHELL:-}")"

    case "$shell_name" in
        zsh)
            files+=("$HOME/.zshrc")
            ;;
        bash)
            if [[ "$(uname -s)" == "Darwin" && -f "$HOME/.bash_profile" ]]; then
                files+=("$HOME/.bash_profile")
            else
                files+=("$HOME/.bashrc")
            fi
            ;;
        *)
            [[ -f "$HOME/.zshrc" ]] && files+=("$HOME/.zshrc")
            [[ -f "$HOME/.bashrc" ]] && files+=("$HOME/.bashrc")
            if [[ ${#files[@]} -eq 0 ]]; then
                files+=("$HOME/.bashrc")
            fi
            ;;
    esac
    printf '%s\n' "${files[@]}"
}

remove_rc_block() {
    local rc_file="$1"
    [[ -f "$rc_file" ]] || return 0
    if grep -qF "$MARKER_START" "$rc_file"; then
        local tmp
        tmp="$(mktemp)"
        awk -v start="$MARKER_START" -v end="$MARKER_END" '
            $0 == start { skip=1; next }
            $0 == end   { skip=0; next }
            !skip       { print }
        ' "$rc_file" > "$tmp"
        mv "$tmp" "$rc_file"
        echo "Removed sd block from $rc_file"
    fi
}

if [[ "$UNINSTALL" -eq 1 ]]; then
    while IFS= read -r rc; do
        remove_rc_block "$rc"
    done < <(detect_rc_files)

    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf -- "$INSTALL_DIR"
        echo "Removed $INSTALL_DIR"
    fi
    echo "sd uninstalled."
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found on PATH." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR"

# Use local files if running from a cloned repo; otherwise fetch via curl
SCRIPT_DIR=""
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fi

fetch_file() {
    local name="$1"
    local dest="$INSTALL_DIR/$name"
    if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/$name" ]]; then
        cp "$SCRIPT_DIR/$name" "$dest"
    else
        if ! command -v curl >/dev/null 2>&1; then
            echo "Error: curl is required to download $name." >&2
            exit 1
        fi
        curl -fsSL "$REPO_RAW_URL/$name" -o "$dest"
    fi
}

fetch_file "sd_tui.py"
fetch_file "sd.sh"
chmod +x "$INSTALL_DIR/sd_tui.py"

while IFS= read -r rc; do
    mkdir -p "$(dirname "$rc")"
    touch "$rc"
    if ! grep -qF "$MARKER_START" "$rc"; then
        {
            echo ""
            echo "$MARKER_START"
            echo "source \"$INSTALL_DIR/sd.sh\""
            echo "$MARKER_END"
        } >> "$rc"
        echo "Added sd to $rc"
    else
        echo "sd already configured in $rc"
    fi
done < <(detect_rc_files)

echo ""
echo "Installed sd to $INSTALL_DIR"
echo "Restart your shell or run:"
while IFS= read -r rc; do
    echo "  source \"$rc\""
done < <(detect_rc_files)
