# Step-dir

A lightweight, zero-dependency terminal UI (TUI) directory navigator for Linux and macOS. Browse directories in a split-pane `curses` interface and drop back into your shell with `pwd` changed to the selected folder.

## How it works

A child process cannot change its parent shell's working directory directly. `sd` pairs two small files:

- `sd_tui.py` — A Python `curses` TUI that writes the chosen directory path to a temporary file.
- `sd.sh` — A Bash/Zsh shell function `sd()` that runs the TUI and `cd`s into the selected path on exit.

## Requirements

- **Python 3.8+** (`python3`, standard library only — no `pip` packages required)
- **Bash** or **Zsh**
- **curl** (for remote installation)

## Installation

### Quick install (Linux & macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/itachi-19/step-dir/master/install.sh | bash
```

Then reload your shell config:

```bash
# Bash
source ~/.bashrc

# Zsh (macOS default)
source ~/.zshrc
```

### Custom install location

```bash
SD_INSTALL_DIR="$HOME/.sd" curl -fsSL https://raw.githubusercontent.com/itachi-19/step-dir/master/install.sh | bash
```

### Manual install

1. Download `sd_tui.py` and `sd.sh` into the same directory (for example `~/.local/share/sd`).
2. Make `sd_tui.py` executable:

   ```bash
   chmod +x ~/.local/share/sd/sd_tui.py
   ```

3. Add this line to `~/.bashrc` or `~/.zshrc`:

   ```bash
   source "$HOME/.local/share/sd/sd.sh"
   ```

### Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/itachi-19/step-dir/master/install.sh | bash -s -- --uninstall
```

## Usage

```text
sd [options] [start_dir]
```

| Option | Description |
| :--- | :--- |
| `start_dir` | Initial directory to open (defaults to `.`) |
| `-a`, `--all` | Show hidden directories (starting with `.`) |
| `-f`, `--files` | Show files in the listing for context (dimmed, non-selectable) |
| `-L`, `--follow` | Follow symbolic links to directories |
| `-h`, `--help` | Show CLI help message |

## Keybindings

| Key | Action |
| :--- | :--- |
| `Up` / `k`, `Down` / `j` | Move selection up or down |
| `PageUp` / `PageDown`, `g` / `G` | Jump by page, or to top / bottom |
| `Enter` / `Right` / `l` | Open highlighted directory (or select if `.` is highlighted) |
| `Backspace` / `Left` / `h` | Go to parent directory |
| `s` | Select highlighted directory and `cd` into it |
| `c` | Select current directory (shown in header) and `cd` into it |
| `.` | Toggle hidden directories |
| `f` | Toggle file visibility |
| `/` | Live substring filter (`Enter` to apply, `Esc` to clear) |
| `~` | Jump to `$HOME` |
| `-` | Jump to `$OLDPWD` |
| `q` / `Esc` | Quit without changing directory |
