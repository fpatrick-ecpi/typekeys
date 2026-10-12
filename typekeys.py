#!/usr/bin/env python3
"""
typekeys.py: type text into the frontmost app using low-level macOS
keyboard events (CGEvent), holding Shift/Option as real modifier keys.

This is one level below AppleScript's System Events and is what remote
desktop canvases (NETLAB, Guacamole, noVNC) actually respond to.

Usage:
  python3 typekeys.py                          # prompt for the text (hidden, like a password)
  python3 typekeys.py --show                   # prompt, but echo what you type
  python3 typekeys.py -f ~/openai.key          # type a file's contents
  python3 typekeys.py -c                       # type the clipboard (long paste blocks)
  python3 typekeys.py -t "Hello_World"         # type literal text
  python3 typekeys.py --enter                  # ...then press Enter
  options: --delay 0.03 (seconds between keys), --wait 3 (seconds before
           starting so you can click into the target window),
           --breather 200 (extra pause every N chars on long scripts; 0 = off)

Handles:
  * newlines: \\n, \\r\\n and bare \\r all normalize to Shift+Return by default,
    so multi-line text goes into chat boxes WITHOUT submitting on every line
    (--newline enter switches to plain Return presses for documents)
  * dashes: the hyphen is the plain hyphen key; the en dash is Option+hyphen;
    the em dash is Option+Shift+hyphen. All are sent as real key presses
    with real modifiers
  * long scripts: clipboard/file input, a breather pause every N characters
    so the canvas doesn't drop keys, and progress on stderr

Setup (once):
  pip3 install pyobjc-framework-Quartz
  System Settings > Privacy & Security > Accessibility: enable your terminal app
"""
import argparse, getpass, subprocess, sys, time
try:
    import Quartz
except ImportError:
    sys.exit("Missing dependency: run  pip3 install pyobjc-framework-Quartz")

# US layout virtual key codes
KEYS = {
    'a':0,'s':1,'d':2,'f':3,'h':4,'g':5,'z':6,'x':7,'c':8,'v':9,'b':11,'q':12,
    'w':13,'e':14,'r':15,'y':16,'t':17,'1':18,'2':19,'3':20,'4':21,'6':22,'5':23,
    '=':24,'9':25,'7':26,'-':27,'8':28,'0':29,']':30,'o':31,'u':32,'[':33,'i':34,
    'p':35,'l':37,'j':38,"'":39,'k':40,';':41,'\\':42,',':43,'/':44,'n':45,'m':46,
    '.':47,'`':50,' ':49,'\n':36,'\t':48,
}
SHIFTED = {'!':'1','@':'2','#':'3','$':'4','%':'5','^':'6','&':'7','*':'8','(':'9',
           ')':'0','_':'-','+':'=','{':'[','}':']','|':'\\',':':';','"':"'",'<':',',
           '>':'.','?':'/','~':'`'}
# char -> (base key, needs shift too); typed with Option held
OPTIONED = {'–': ('-', False),   # en dash  = Option+hyphen
            '—': ('-', True)}    # em dash  = Option+Shift+hyphen
SHIFT_KEY = 56
OPT_KEY = 58
# Word/rendered-markdown lookalikes -> typeable equivalents
SANITIZE = {'“': '"', '”': '"', '‘': "'", '’': "'",
            '…': '...', ' ': ' ', '−': '-', '•': '-'}

def post(keycode, down, flags=0):
    ev = Quartz.CGEventCreateKeyboardEvent(None, keycode, down)
    Quartz.CGEventSetFlags(ev, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

def press(keycode, shift, delay, alt=False):
    flags = 0
    if shift: flags |= Quartz.kCGEventFlagMaskShift
    if alt:   flags |= Quartz.kCGEventFlagMaskAlternate
    if alt:
        post(OPT_KEY, True, flags); time.sleep(delay/4)
    if shift:
        post(SHIFT_KEY, True, flags); time.sleep(delay/4)
    post(keycode, True, flags);  time.sleep(delay/4)
    post(keycode, False, flags); time.sleep(delay/4)
    if shift:
        post(SHIFT_KEY, False, Quartz.kCGEventFlagMaskAlternate if alt else 0); time.sleep(delay/4)
    if alt:
        post(OPT_KEY, False, 0); time.sleep(delay/4)

def type_text(text, delay, breather=200, newline='shift'):
    # Normalize every newline style to \n (typed as a real Return press).
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Swap curly quotes and friends (Word / rendered markdown) for typeable twins.
    for bad, good in SANITIZE.items():
        text = text.replace(bad, good)
    total = len(text)
    for i, ch in enumerate(text, 1):
        if ch == '\n':
            # Shift+Return = newline WITHOUT submitting (chat boxes send on
            # plain Return). Use --newline enter for plain Returns (documents).
            press(KEYS['\n'], newline == 'shift', delay)
        elif ch in OPTIONED:
            base, also_shift = OPTIONED[ch]
            press(KEYS[base], also_shift, delay, alt=True)
        elif ch in SHIFTED:
            press(KEYS[SHIFTED[ch]], True, delay)
        elif ch.isupper():
            press(KEYS[ch.lower()], True, delay)
        elif ch in KEYS:
            press(KEYS[ch], False, delay)
        else:
            print(f"skipping unsupported character: {ch!r}", file=sys.stderr)
        time.sleep(delay)
        if breather and i % breather == 0:
            time.sleep(0.4)
            print(f"  ...{i}/{total}", file=sys.stderr)

ap = argparse.ArgumentParser()
g = ap.add_mutually_exclusive_group()
g.add_argument('-f', '--file', help='type the contents of this file')
g.add_argument('-t', '--text', help='type this literal text')
g.add_argument('-c', '--clipboard', action='store_true', help='type the current clipboard')
ap.add_argument('--delay', type=float, default=0.03)
ap.add_argument('--wait', type=float, default=3.0, help='seconds to wait before typing')
ap.add_argument('--breather', type=int, default=200,
                help='pause briefly every N characters on long scripts (0 = off)')
ap.add_argument('--newline', choices=['shift', 'enter'], default='shift',
                help="how to type newlines: 'shift' = Shift+Return, no submit "
                     "(chat boxes; default); 'enter' = plain Return (documents)")
ap.add_argument('--show', action='store_true', help='echo the prompted text instead of hiding it')
ap.add_argument('--enter', action='store_true', help='press Enter at the end')
a = ap.parse_args()

if a.text is not None:
    text = a.text
elif a.file:
    text = open(a.file).read().rstrip('\n')
elif a.clipboard:
    text = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout
    if not text:
        sys.exit("Clipboard is empty.")
else:
    # Prompt. getpass hides the input so the secret doesn't stay on screen
    # (and it never touches shell history either way).
    text = input("Text to type: ") if a.show else getpass.getpass("Text to type (hidden): ")
    if not text:
        sys.exit("Nothing to type.")
print(f"Typing {len(text)} chars in {a.wait:g}s. Click into the target window now...", file=sys.stderr)
time.sleep(a.wait)
type_text(text, a.delay, a.breather, a.newline)
if a.enter:
    press(KEYS['\n'], False, a.delay)
print("Done.", file=sys.stderr)
