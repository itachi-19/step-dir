#!/usr/bin/env python3
"""
sd - A terminal UI directory navigator.

Prints the selected directory path to --output-file (or stdout if omitted)
so a parent shell wrapper function can `cd` into it.
"""

from __future__ import annotations

import argparse
import curses
import os
import stat
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sd",
        description="Interactive TUI directory navigator that changes the shell's pwd.",
    )
    parser.add_argument(
        "start_dir",
        nargs="?",
        default=".",
        help="Initial directory to open (default: current directory)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show hidden directories (starting with '.')",
    )
    parser.add_argument(
        "-f",
        "--files",
        action="store_true",
        help="Show files in the listing for context (dimmed, non-selectable)",
    )
    parser.add_argument(
        "-L",
        "--follow",
        action="store_true",
        help="Follow symbolic links to directories",
    )
    parser.add_argument(
        "--output-file",
        help="Write the selected directory path to this file instead of stdout",
    )
    return parser.parse_args()


def list_entries(
    directory: Path,
    show_hidden: bool,
    show_files: bool,
    follow_symlinks: bool,
) -> tuple[list[tuple[str, bool, bool]], str | None]:
    """
    Return (entries, error_msg).
    Each entry is (name, is_dir, is_symlink).
    """
    entries: list[tuple[str, bool, bool]] = []
    try:
        with os.scandir(directory) as it:
            dirs: list[tuple[str, bool, bool]] = []
            files: list[tuple[str, bool, bool]] = []
            for entry in it:
                name = entry.name
                if not show_hidden and name.startswith("."):
                    continue
                try:
                    is_link = entry.is_symlink()
                    is_dir = entry.is_dir(follow_symlinks=follow_symlinks)
                except OSError:
                    is_link = False
                    is_dir = False

                if is_dir:
                    dirs.append((name, True, is_link))
                elif show_files:
                    files.append((name, False, is_link))

            dirs.sort(key=lambda x: x[0].lower())
            files.sort(key=lambda x: x[0].lower())
            entries = dirs + files
        return entries, None
    except PermissionError:
        return [], "Permission denied"
    except OSError as exc:
        return [], str(exc)


def format_perms(path: Path) -> str:
    try:
        st = path.lstat()
        return stat.filemode(st.st_mode)
    except OSError:
        return "??????????"


def init_colors() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # Header / path
    curses.init_pair(2, curses.COLOR_BLUE, -1)     # Directories
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Selected row
    curses.init_pair(4, curses.COLOR_GREEN, -1)    # Action / status highlight
    curses.init_pair(5, curses.COLOR_YELLOW, -1)   # Filter / symlink
    curses.init_pair(6, curses.COLOR_RED, -1)      # Error


def run_tui(stdscr: curses.window, args: argparse.Namespace) -> Path | None:
    curses.curs_set(0)
    stdscr.keypad(True)
    init_colors()

    current_dir = Path(args.start_dir).expanduser().resolve()
    if not current_dir.is_dir():
        current_dir = Path.cwd().resolve()

    show_hidden = args.all
    show_files = args.files
    follow_symlinks = args.follow

    filter_text = ""
    filtering = False
    cursor_idx = 0
    scroll_offset = 0
    status_msg = ""

    def load_current() -> tuple[list[tuple[str, bool, bool]], str | None]:
        raw, err = list_entries(current_dir, show_hidden, show_files, follow_symlinks)
        if filter_text:
            needle = filter_text.lower()
            raw = [e for e in raw if needle in e[0].lower()]
        # Always include a "." entry at index 0 to select current_dir
        items = [(".", True, False)] + raw
        return items, err

    while True:
        items, err = load_current()
        if err:
            status_msg = f"Error: {err}"

        if cursor_idx >= len(items):
            cursor_idx = max(0, len(items) - 1)

        height, width = stdscr.getmaxyx()
        stdscr.erase()

        # Layout dimensions
        header_rows = 2
        footer_rows = 2
        list_height = max(1, height - header_rows - footer_rows)

        if cursor_idx < scroll_offset:
            scroll_offset = cursor_idx
        elif cursor_idx >= scroll_offset + list_height:
            scroll_offset = cursor_idx - list_height + 1

        split_pane = width >= 72
        left_width = (width // 2) - 1 if split_pane else width - 1

        # Header
        flags = []
        if show_hidden:
            flags.append("hidden")
        if show_files:
            flags.append("files")
        if follow_symlinks:
            flags.append("follow")
        flag_str = f" [{', '.join(flags)}]" if flags else ""

        header_text = f" {current_dir}{flag_str}"
        stdscr.addnstr(
            0,
            0,
            header_text.ljust(width - 1),
            width - 1,
            curses.color_pair(1) | curses.A_BOLD,
        )
        stdscr.hline(1, 0, curses.ACS_HLINE, width - 1)

        # Left pane: directory listing
        for row in range(list_height):
            idx = scroll_offset + row
            if idx >= len(items):
                break
            name, is_dir, is_link = items[idx]
            y = header_rows + row

            if name == ".":
                label = " .  [select current directory]"
            elif is_dir:
                suffix = "@/" if is_link else "/"
                label = f" {name}{suffix}"
            else:
                suffix = "@" if is_link else ""
                label = f" {name}{suffix}"

            if idx == cursor_idx:
                attr = curses.color_pair(3) | curses.A_BOLD
                stdscr.addnstr(y, 0, label.ljust(left_width), left_width, attr)
            else:
                if name == ".":
                    attr = curses.color_pair(4) | curses.A_BOLD
                elif is_dir:
                    attr = (
                        curses.color_pair(5) if is_link else curses.color_pair(2)
                    ) | curses.A_BOLD
                else:
                    attr = curses.A_DIM
                stdscr.addnstr(y, 0, label, left_width, attr)

        # Right pane: preview
        if split_pane:
            div_x = left_width + 1
            stdscr.vline(header_rows, div_x, curses.ACS_VLINE, list_height)
            preview_x = div_x + 2
            preview_w = max(1, width - preview_x - 1)

            sel_name, sel_is_dir, _ = items[cursor_idx]
            target_path = current_dir if sel_name == "." else current_dir / sel_name

            if sel_is_dir:
                perms = format_perms(target_path)
                title = f"Preview: {target_path.name or '/'} ({perms})"
                stdscr.addnstr(
                    header_rows,
                    preview_x,
                    title,
                    preview_w,
                    curses.color_pair(1) | curses.A_BOLD,
                )
                sub_items, sub_err = list_entries(
                    target_path, show_hidden, True, follow_symlinks
                )
                if sub_err:
                    stdscr.addnstr(
                        header_rows + 2,
                        preview_x,
                        f"[{sub_err}]",
                        preview_w,
                        curses.color_pair(6),
                    )
                elif not sub_items:
                    stdscr.addnstr(
                        header_rows + 2,
                        preview_x,
                        "(empty)",
                        preview_w,
                        curses.A_DIM,
                    )
                else:
                    for prow, (sname, sis_dir, slink) in enumerate(
                        sub_items[: max(0, list_height - 2)]
                    ):
                        py = header_rows + 2 + prow
                        ssuf = "/" if sis_dir else ("@" if slink else "")
                        sattr = (
                            curses.color_pair(2) if sis_dir else curses.A_DIM
                        )
                        stdscr.addnstr(py, preview_x, f"{sname}{ssuf}", preview_w, sattr)
            else:
                perms = format_perms(target_path)
                stdscr.addnstr(
                    header_rows,
                    preview_x,
                    f"File: {sel_name} ({perms})",
                    preview_w,
                    curses.A_DIM,
                )

        # Footer
        stdscr.hline(height - 2, 0, curses.ACS_HLINE, width - 1)
        if filtering:
            footer = f" /{filter_text}_   (Enter: apply, Esc: clear)"
            fattr = curses.color_pair(5) | curses.A_BOLD
        elif status_msg:
            footer = f" {status_msg}"
            fattr = curses.color_pair(6) | curses.A_BOLD
            status_msg = ""
        else:
            filt_hint = f" [filter: {filter_text}]" if filter_text else ""
            footer = (
                f" [Enter/l] open  [h/Bksp] up  [s] select  [.] hidden  "
                f"[/] filter  [~] home  [q] quit{filt_hint}"
            )
            fattr = curses.A_NORMAL
        stdscr.addnstr(height - 1, 0, footer, width - 1, fattr)

        stdscr.refresh()

        # Input handling
        key = stdscr.getch()

        if filtering:
            if key in (10, 13, curses.KEY_ENTER):
                filtering = False
            elif key == 27:  # Esc
                filter_text = ""
                filtering = False
                cursor_idx = 0
                scroll_offset = 0
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                filter_text = filter_text[:-1]
                cursor_idx = 0
                scroll_offset = 0
            elif 32 <= key <= 126:
                filter_text += chr(key)
                cursor_idx = 0
                scroll_offset = 0
            continue

        sel_name, sel_is_dir, _ = items[cursor_idx]

        if key in (ord("q"), 27):
            if filter_text and key == 27:
                filter_text = ""
                cursor_idx = 0
                scroll_offset = 0
            else:
                return None
        elif key in (curses.KEY_UP, ord("k")):
            cursor_idx = max(0, cursor_idx - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor_idx = min(len(items) - 1, cursor_idx + 1)
        elif key == curses.KEY_PPAGE:
            cursor_idx = max(0, cursor_idx - list_height)
        elif key == curses.KEY_NPAGE:
            cursor_idx = min(len(items) - 1, cursor_idx + list_height)
        elif key in (ord("g"), curses.KEY_HOME):
            cursor_idx = 0
        elif key in (ord("G"), curses.KEY_END):
            cursor_idx = len(items) - 1
        elif key in (10, 13, curses.KEY_ENTER, curses.KEY_RIGHT, ord("l")):
            if sel_name == ".":
                return current_dir
            if sel_is_dir:
                candidate = (current_dir / sel_name).resolve()
                if os.access(candidate, os.R_OK | os.X_OK):
                    current_dir = candidate
                    filter_text = ""
                    cursor_idx = 0
                    scroll_offset = 0
                else:
                    status_msg = f"Cannot enter '{sel_name}': Permission denied"
        elif key in (curses.KEY_LEFT, ord("h"), curses.KEY_BACKSPACE, 127, 8):
            parent = current_dir.parent
            if parent != current_dir:
                prev_name = current_dir.name
                current_dir = parent
                filter_text = ""
                new_items, _ = load_current()
                cursor_idx = 0
                for i, (n, is_d, _) in enumerate(new_items):
                    if is_d and n == prev_name:
                        cursor_idx = i
                        break
                scroll_offset = 0
        elif key == ord("s"):
            if sel_name == ".":
                return current_dir
            if sel_is_dir:
                return (current_dir / sel_name).resolve()
            return current_dir
        elif key == ord("c"):
            return current_dir
        elif key == ord("."):
            show_hidden = not show_hidden
            cursor_idx = 0
            scroll_offset = 0
        elif key == ord("f"):
            show_files = not show_files
            cursor_idx = 0
            scroll_offset = 0
        elif key == ord("/"):
            filtering = True
        elif key == ord("~"):
            current_dir = Path.home().resolve()
            filter_text = ""
            cursor_idx = 0
            scroll_offset = 0
        elif key == ord("-"):
            oldpwd = os.environ.get("OLDPWD")
            if oldpwd and Path(oldpwd).is_dir():
                current_dir = Path(oldpwd).resolve()
                filter_text = ""
                cursor_idx = 0
                scroll_offset = 0
            else:
                status_msg = "OLDPWD is not set"


def main() -> int:
    args = parse_args()

    # If --help/-h wasn't triggered, run curses UI
    selected = curses.wrapper(run_tui, args)
    if selected is None:
        return 1

    if args.output_file:
        Path(args.output_file).write_text(str(selected), encoding="utf-8")
    else:
        print(selected)
    return 0


if __name__ == "__main__":
    sys.exit(main())