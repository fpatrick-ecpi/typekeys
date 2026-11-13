#!/usr/bin/env python3
"""
typekeys.py (Windows): type text into the frontmost app using low-level
Windows keyboard input (SendInput with hardware scan codes), holding Shift
and Alt down as real modifier keys.

This is the Windows port of fpatrick-ecpi/typekeys (macOS, CGEvent). Remote
desktop canvases (VCASTLE, NETLAB, Guacamole, noVNC) in a browser ignore
pasted text but respond to real key presses, so this sends real key presses.
No third-party packages are needed: only Python 3 and the standard library.

Usage:
  python typekeys.py                         # paste anything (multi-line ok), press Enter
  python typekeys.py --secret                # prompt hides what you paste (API keys)
  python typekeys.py -f C:\\path\\prompt.txt   # type a file's contents
  python typekeys.py -c                      # type the Windows clipboard
  python typekeys.py -t "Hello_World"        # type literal text
  python typekeys.py --enter                 # ...then press Enter
  python typekeys.py --dry-run               # show what would be typed, type nothing
  options: --delay 0.03 (seconds between keys), --wait 3 (seconds before
           starting so you can click into the target window),
           --breather 200 (extra pause every N chars on long text; 0 = off)

Handles:
  * newlines: \\n, \\r\\n and bare \\r all become Shift+Enter by default, so
    multi-line text goes into chat boxes WITHOUT submitting on every line
    (--newline enter switches to plain Enter presses for documents)
  * dashes: en dash is Alt+hyphen, em dash is Alt+Shift+hyphen (the same
    combos the Mac version sends with Option). --dashes ascii types a plain
    hyphen ("-") or two ("--") instead, for targets that ignore Alt combos
  * long text: a breather pause every N characters so the canvas keeps up,
    and progress on stderr

Assumes a US keyboard layout on the Windows PC and in the remote machine.
"""
import argparse
import ctypes
import getpass
import sys
import time
from ctypes import wintypes

if sys.platform != "win32":
    sys.exit("This is the Windows version. On a Mac, use the original typekeys.py.")

import msvcrt  # noqa: E402  (Windows only)

# Console output may not be UTF-8 (cp1252); never crash on a stray character.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------- key tables
# US layout, hardware scan codes (set 1). Scan codes are physical keys, the
# same thing a real keyboard sends, which is what a browser-based canvas reads.
KEYS = {
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07,
    "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B, "-": 0x0C, "=": 0x0D,
    "\t": 0x0F,
    "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15,
    "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19, "[": 0x1A, "]": 0x1B,
    "\n": 0x1C,
    "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22, "h": 0x23,
    "j": 0x24, "k": 0x25, "l": 0x26, ";": 0x27, "'": 0x28, "`": 0x29,
    "\\": 0x2B,
    "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31,
    "m": 0x32, ",": 0x33, ".": 0x34, "/": 0x35,
    " ": 0x39,
}
SHIFTED = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7",
    "*": "8", "(": "9", ")": "0", "_": "-", "+": "=", "{": "[", "}": "]",
    "|": "\\", ":": ";", '"': "'", "<": ",", ">": ".", "?": "/", "~": "`",
}
# char -> (base key, also shift); typed with Alt held (same as Option on a Mac)
ALTED = {"\u2013": ("-", False),   # en dash = Alt+hyphen
         "\u2014": ("-", True)}    # em dash = Alt+Shift+hyphen
SC_SHIFT = 0x2A
SC_ALT = 0x38
# Word / rendered-markdown lookalikes -> typeable equivalents
SANITIZE = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
            "\u2026": "...", "\u00a0": " ", "\u2212": "-", "\u2022": "-"}

# ------------------------------------------------------------------ SendInput
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.GetKeyState.argtypes = (ctypes.c_int,)
user32.GetKeyState.restype = ctypes.c_short


def post(scancode, down):
    flags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
    inp = INPUT(type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(0, scancode, flags, 0, 0))
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise OSError(f"SendInput failed (error {ctypes.get_last_error()}). "
                      "If the target window is running as administrator, "
                      "run this from an administrator terminal too.")


def press(scancode, shift, delay, alt=False):
    q = delay / 4
    if alt:
        post(SC_ALT, True); time.sleep(q)
    if shift:
        post(SC_SHIFT, True); time.sleep(q)
    post(scancode, True); time.sleep(q)
    post(scancode, False); time.sleep(q)
    if shift:
        post(SC_SHIFT, False); time.sleep(q)
    if alt:
        post(SC_ALT, False); time.sleep(q)


def release_modifiers():
    """Never leave Shift or Alt stuck down (for example after Ctrl+C)."""
    for sc in (SC_SHIFT, SC_ALT):
        try:
            post(sc, False)
        except OSError:
            pass


def type_text(text, delay, breather=200, newline="shift", dashes="alt"):
    # Normalize every newline style to \n (typed as a real Enter press).
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Swap curly quotes and friends (Word / rendered markdown) for typeable twins.
    for bad, good in SANITIZE.items():
        text = text.replace(bad, good)
    if dashes == "ascii":
        text = text.replace("\u2013", "-").replace("\u2014", "--")
    total = len(text)
    try:
        for i, ch in enumerate(text, 1):
            if ch == "\n":
                # Shift+Enter = newline WITHOUT submitting (chat boxes send on
                # plain Enter). Use --newline enter for plain Enters (documents).
                press(KEYS["\n"], newline == "shift", delay)
            elif ch in ALTED:
                base, also_shift = ALTED[ch]
                press(KEYS[base], also_shift, delay, alt=True)
            elif ch in SHIFTED:
                press(KEYS[SHIFTED[ch]], True, delay)
            elif ch.isupper() and ch.lower() in KEYS:
                press(KEYS[ch.lower()], True, delay)
            elif ch in KEYS:
                press(KEYS[ch], False, delay)
            else:
                print(f"skipping unsupported character: {ch!r}", file=sys.stderr)
            time.sleep(delay)
            if breather and i % breather == 0:
                time.sleep(0.4)
                print(f"  ...{i}/{total}", file=sys.stderr)
    finally:
        release_modifiers()


# ---------------------------------------------------------------- text input
def read_clipboard():
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = (wintypes.UINT,)
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
    CF_UNICODETEXT = 13
    for _ in range(20):  # another app may hold the clipboard for a moment
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _read_burst():
    """Read one key press, then everything that arrives right behind it.

    A multi-line paste arrives as one fast burst of characters, blank lines
    and all. Arrow and function keys come as a two-character sequence; they
    are skipped.
    """
    chars = []
    first = True
    while True:
        if not first:
            deadline = time.time() + 0.15
            while not msvcrt.kbhit() and time.time() < deadline:
                time.sleep(0.005)
            if not msvcrt.kbhit():
                break
        ch = msvcrt.getwch()
        first = False
        if ch in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        chars.append(ch)
    return "".join(chars)


def read_paste():
    """Read a paste of any length, then the Enter that ends it.

    The paste ends when you press Enter on its own after it. Backspace works
    for hand-typed fixes. Ctrl+C aborts.
    """
    print("Paste your text, then press Enter:", file=sys.stderr)
    if not sys.stdin.isatty():
        return sys.stdin.read().rstrip("\r\n")
    buf = []
    try:
        while True:
            burst = _read_burst().replace("\r\n", "\n").replace("\r", "\n")
            if burst == "\n":                       # Enter on its own: done
                sys.stderr.write("\n")
                break
            if burst == "\x1a" and not buf:         # Ctrl+Z on an empty prompt
                break
            for ch in burst:
                if ch in ("\x7f", "\b"):
                    if buf and buf[-1] != "\n":
                        buf.pop()
                        sys.stderr.write("\b \b")
                elif ch == "\x03":
                    raise KeyboardInterrupt
                else:
                    buf.append(ch)
                    sys.stderr.write(ch)
            sys.stderr.flush()
    except KeyboardInterrupt:
        sys.exit("\nAborted.")
    return "".join(buf).rstrip("\n")


def read_file(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")        # also strips Notepad's BOM
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    return text.rstrip("\r\n")


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description="Type text into the frontmost window with real key presses.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("-f", "--file", help="type the contents of this file")
    g.add_argument("-t", "--text", help="type this literal text")
    g.add_argument("-c", "--clipboard", action="store_true",
                   help="type the current clipboard")
    ap.add_argument("--delay", type=float, default=0.03)
    ap.add_argument("--wait", type=float, default=3.0,
                    help="seconds to wait before typing")
    ap.add_argument("--breather", type=int, default=200,
                    help="pause briefly every N characters on long text (0 = off)")
    ap.add_argument("--newline", choices=["shift", "enter"], default="shift",
                    help="how to type newlines: 'shift' = Shift+Enter, no submit "
                         "(chat boxes; default); 'enter' = plain Enter (documents)")
    ap.add_argument("--dashes", choices=["alt", "ascii"], default="alt",
                    help="en/em dashes: 'alt' = Alt+hyphen combos (default); "
                         "'ascii' = plain hyphens")
    ap.add_argument("--secret", action="store_true",
                    help="hide what you paste at the prompt (one line, for keys and passwords)")
    ap.add_argument("-n", "--dry-run", action="store_true",
                    help="print what would be typed and type nothing")
    ap.add_argument("--enter", action="store_true", help="press Enter at the end")
    a = ap.parse_args()

    if a.text is not None:
        text = a.text
    elif a.file:
        text = read_file(a.file)
    elif a.clipboard:
        text = read_clipboard()
        if not text:
            sys.exit("Clipboard is empty.")
    elif a.secret:
        # getpass hides the input so the secret doesn't stay on screen.
        text = getpass.getpass("Paste the secret, then press Enter (hidden): ")
        if not text:
            sys.exit("Nothing to type.")
    else:
        text = read_paste()
        if not text:
            sys.exit("Nothing to type.")

    if a.dry_run:
        print(f"[dry run] would type {len(text)} chars:", file=sys.stderr)
        print(text)
        return

    if user32.GetKeyState(0x14) & 1:  # VK_CAPITAL
        print("Warning: Caps Lock is on. Letters may come out inverted.",
              file=sys.stderr)
    print(f"Typing {len(text)} chars in {a.wait:g}s. "
          "Click into the target window now...", file=sys.stderr)
    try:
        time.sleep(a.wait)
        type_text(text, a.delay, a.breather, a.newline, a.dashes)
        if a.enter:
            press(KEYS["\n"], False, a.delay)
    except KeyboardInterrupt:
        release_modifiers()
        sys.exit("\nStopped.")
    except OSError as e:
        sys.exit(str(e))
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
