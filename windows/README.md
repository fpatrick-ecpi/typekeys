# typekeys for Windows

Types text into VCASTLE and other remote canvases with real Windows key
presses. This is the Windows port of
[fpatrick-ecpi/typekeys](https://github.com/fpatrick-ecpi/typekeys), which
runs on macOS.

The VCASTLE remote canvas in the browser won't take a paste, and the clipboard
doesn't cross into the lab. typekeys types the text for you, one real key press
at a time. Shift and Alt are held down as real modifier keys, which is what
remote canvases like NETLAB, Guacamole and noVNC respond to.

## Setup (once)

1. Install Python 3 from python.org or the Microsoft Store. Tick "Add python
   to PATH" if the installer asks.
2. Put `typekeys.py` (and `typekeys.cmd`, if you want the short command) in a
   folder you can find.

There is nothing to `pip install` and no permission to grant. The script uses
only Python and Windows itself.

## How to use it: run, paste, Enter

1. Open the VCASTLE lab in the browser and get to the place you want to type:
   a chat box, a terminal, a text editor, a form field.
2. In a PowerShell or Command Prompt window, in the folder with the script, run:

   ```powershell
   python typekeys.py
   ```

3. Paste your text at the prompt. Any length, more than one line is fine.
4. Press Enter.
5. You have 3 seconds. Click inside the VCASTLE window, right where the cursor
   should go.
6. Hands off the mouse and keyboard until it says `Done.` Typing goes to
   whatever window is in front, so a stray click sends the rest somewhere else.
   Press Ctrl+C in the terminal to stop it.

If you type at the prompt by hand instead of pasting, Enter ends it, so
hand-typed text is one line. Paste anything longer.

If you added `typekeys.cmd`, you can type `typekeys` instead of
`python typekeys.py` in every example below.

### Secrets

For an API key or password, add `--secret`. The prompt hides what you paste, so
it never shows on screen. The secret is one line.

```powershell
python typekeys.py --secret
```

### Other places the text can come from

Type a file, like a prepared prompt:

```powershell
python typekeys.py -f C:\Users\you\prompt.txt
```

Type whatever is already on your Windows clipboard, with no prompt:

```powershell
python typekeys.py -c
```

Type a short bit of text:

```powershell
python typekeys.py -t "Hello_World"
```

Check what would be typed without typing anything:

```powershell
python typekeys.py -f prompt.txt --dry-run
```

### Submit or keep going

By default it does not press Enter at the end. That keeps a chat message open
so the next run adds to the same message. Add `--enter` on the last one to send
it:

```powershell
python typekeys.py --enter
```

### New lines

By default every new line is typed as Shift+Enter. Chat boxes send the message
on a plain Enter, so Shift+Enter lets a multi-line prompt go in as one message.

In a terminal, a code editor or a document, you want plain Enters instead:

```powershell
python typekeys.py -f notes.txt --newline enter
```

## Options

| Option | What it does | Default |
|---|---|---|
| `-f FILE` | Type the contents of a file | |
| `-c` | Type the Windows clipboard | |
| `-t "TEXT"` | Type this text | |
| (none of those) | Prompt: paste, then press Enter | |
| `--secret` | Hide what you paste at the prompt (one line) | off |
| `-n`, `--dry-run` | Print what would be typed, type nothing | off |
| `--enter` | Press Enter at the end | off |
| `--newline shift` or `enter` | Shift+Enter for chat boxes, plain Enter for everything else | `shift` |
| `--dashes alt` or `ascii` | En and em dashes as Alt+hyphen combos, or as plain hyphens | `alt` |
| `--wait N` | Seconds before typing starts | `3` |
| `--delay N` | Seconds between keys | `0.03` |
| `--breather N` | Short pause every N characters on long text (0 turns it off) | `200` |

## What it handles for you

- **Curly quotes from Word.** Smart quotes, the ellipsis character, bullets,
  non-breaking spaces and the minus sign are swapped for plain characters you
  can type. Word's curly quotes can change how a prompt behaves.
- **Dashes.** The hyphen is the plain hyphen key. The en dash is Alt+hyphen and
  the em dash is Alt+Shift+hyphen, the same combos the Mac version sends with
  Option. If the lab ignores them, use `--dashes ascii`.
- **Long text.** It pauses briefly every 200 characters so the canvas keeps up,
  and prints progress in the terminal.
- **Line endings.** All line ending styles are treated the same.
- **Stuck keys.** If you press Ctrl+C or something fails, Shift and Alt are
  released so they don't stay held down.
- **File encodings.** Files saved by Notepad (with or without a byte order
  mark) are read correctly.

## If something goes wrong

- **Nothing types at all.** If the window you clicked is running as
  administrator, Windows blocks key presses from a normal terminal. Run the
  terminal as administrator too.
- **`python` is not recognized.** Python isn't installed or isn't on PATH. Try
  `py typekeys.py` instead.
- **Letters drop or come out of order.** The canvas is lagging. Slow it down
  with `--delay 0.06`, or `--delay 0.1` on a slow connection.
- **Letters come out in the wrong case.** Caps Lock is on. The script warns
  you. Turn it off and run again.
- **Wrong symbols show up.** The script assumes a US keyboard layout on the
  Windows PC and in the VCASTLE box. Check both layouts.
- **"skipping unsupported character".** Letters like é or emoji have no key on a
  US keyboard, so they get skipped. The terminal names each one it skips. Edit
  them out of the text first.
- **A chat message sent too early.** That was a plain Enter. Leave `--newline`
  at its default for chat boxes.

## Differences from the Mac version

| Mac | Windows |
|---|---|
| `pip3 install pyobjc-framework-Quartz` | No install; Python standard library only |
| Accessibility permission for the terminal | No permission step |
| Sends CGEvent key codes | Sends `SendInput` hardware scan codes |
| Option for en and em dashes | Alt for en and em dashes (`--dashes ascii` to avoid) |
| `-c` reads with `pbpaste` | `-c` reads the clipboard through the Windows API |
| `chmod +x`, run as `./typekeys.py` | Run as `python typekeys.py` or `typekeys.cmd` |
