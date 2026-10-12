# typekeys

I use this to get text into VCASTLE. The VCASTLE remote canvas in the browser
won't take a paste, and the clipboard doesn't cross into the lab. typekeys
gets around that by typing the text for you, one real key press at a time.

It runs on my Mac and sends low-level macOS keyboard events (CGEvent) to
whatever window is in front. Shift and Option are held down as real modifier
keys, which is what remote canvases like NETLAB, Guacamole and noVNC respond
to. AppleScript keystrokes don't work there. This does.

## Setup (once)

1. Install the one dependency:

   ```bash
   pip3 install pyobjc-framework-Quartz
   ```

2. Give your terminal app permission to send key presses. Open System
   Settings > Privacy & Security > Accessibility and turn on the app you run
   the script from (Terminal, iTerm, VS Code). Quit and reopen that app.

3. Make the script runnable:

   ```bash
   chmod +x typekeys.py
   ```

## How to use it with VCASTLE

1. Open the VCASTLE lab in the browser and get to the place you want to type:
   a chat box, a terminal, a text editor, a form field.
2. In a terminal on your Mac, run one of the commands below.
3. You have 3 seconds. Click inside the VCASTLE window, right where the
   cursor should go.
4. Hands off the mouse and keyboard until it says `Done.` Typing goes to
   whatever window is in front, so a stray click sends the rest somewhere
   else. Press Ctrl+C in the terminal to stop it.

### Pick where the text comes from

Type a file. This is what I use most, with prepared prompt files:

```bash
./typekeys.py -f ~/path/to/prompt.txt
```

Type whatever is on your Mac clipboard. Good for long blocks:

```bash
./typekeys.py -c
```

Type a short bit of text:

```bash
./typekeys.py -t "Hello_World"
```

Type something secret, like an API key. With no source given, it asks you for
the text and hides it as you type, so it never shows on screen or lands in
your shell history:

```bash
./typekeys.py
```

Add `--show` if you want to see what you're typing at the prompt.

### Submit or keep going

By default it does not press Enter at the end. That keeps a chat message open
so the next file adds to the same message. Add `--enter` on the last one to
send it:

```bash
./typekeys.py -f part1.txt
```

```bash
./typekeys.py -f part2.txt --enter
```

### New lines

By default every new line is typed as Shift+Return. Chat boxes send the
message on a plain Return, so Shift+Return lets a multi-line prompt go in as
one message.

In a terminal, a code editor or a document, you want plain Returns instead:

```bash
./typekeys.py -f notes.txt --newline enter
```

## Options

| Option | What it does | Default |
|---|---|---|
| `-f FILE` | Type the contents of a file | |
| `-c` | Type the Mac clipboard | |
| `-t "TEXT"` | Type this text | |
| (none of those) | Ask for the text, hidden | |
| `--show` | Show the text as you type it at the prompt | off |
| `--enter` | Press Enter at the end | off |
| `--newline shift` or `enter` | Shift+Return for chat boxes, plain Return for everything else | `shift` |
| `--wait N` | Seconds before typing starts | `3` |
| `--delay N` | Seconds between keys | `0.03` |
| `--breather N` | Short pause every N characters on long text (0 turns it off) | `200` |

## What it handles for you

- **Curly quotes from Word.** Smart quotes, the ellipsis character, bullets,
  non-breaking spaces and the minus sign get swapped for plain characters
  you can type. Word's curly quotes can change how a prompt behaves, so this
  matters.
- **Dashes.** The hyphen, en dash and em dash are each typed with the real key
  combo a Mac uses.
- **Long text.** It pauses briefly every 200 characters so the canvas keeps
  up, and prints progress in the terminal.
- **Windows line endings.** All line ending styles are treated the same.

## If something goes wrong

- **Nothing types at all.** The terminal app doesn't have Accessibility
  permission. See Setup step 2, and restart the terminal after.
- **"Missing dependency".** Run the `pip3 install` line in Setup step 1.
- **Letters drop or come out of order.** The canvas is lagging. Slow it down
  with `--delay 0.06`, or `--delay 0.1` on a slow connection.
- **Wrong symbols show up.** The script assumes a US keyboard layout on both
  the Mac and the VCASTLE box. Check the keyboard layout in the VM.
- **"skipping unsupported character".** Letters like é or emoji have no key
  on a US keyboard, so they get skipped. The terminal names each one it skips.
  Edit them out of the text first.
- **A chat message sent too early.** That was a plain Return. Leave
  `--newline` at its default for chat boxes.
