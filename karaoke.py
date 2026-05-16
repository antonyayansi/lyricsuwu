#!/usr/bin/env python3
"""
🎤 Karaoke Console Player v4
Reproduce un MP3 y muestra las letras sincronizadas.
Cada palabra aparece en ASCII art y se van acumulando.

Uso: python karaoke.py [archivo.lrc] [archivo.mp3]
"""

import sys
import os
import re
import time
import threading
import shutil

# Habilitar colores ANSI en Windows
if os.name == 'nt':
    os.system('')  # Activa ANSI en cmd/powershell
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

try:
    import pyfiglet
except ImportError:
    print("Instalando pyfiglet...")
    os.system(f"{sys.executable} -m pip install pyfiglet -q")
    import pyfiglet

# ─── Colores ANSI ───────────────────────────────────────────────
RESET      = "\033[0m"
BOLD       = "\033[1m"
DIM        = "\033[2m"
ITALIC     = "\033[3m"
UNDERLINE  = "\033[4m"
PURPLE     = "\033[38;5;141m"
CYAN       = "\033[38;5;81m"
WHITE      = "\033[38;5;255m"
GRAY       = "\033[38;5;245m"
DARK_GRAY  = "\033[38;5;238m"
GREEN      = "\033[38;5;114m"
MAGENTA    = "\033[38;5;207m"
YELLOW     = "\033[38;5;222m"
ORANGE     = "\033[38;5;208m"
PINK       = "\033[38;5;212m"
BLUE       = "\033[38;5;75m"
HIDE_CUR   = "\033[?25l"
SHOW_CUR   = "\033[?25h"

LINE_COLORS = [CYAN, MAGENTA, GREEN, YELLOW, PINK, ORANGE, BLUE, PURPLE]


def strip_accents(text):
    """Remueve acentos/especiales para pyfiglet."""
    reps = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
        '¿': '?', '¡': '!',
    }
    return "".join(reps.get(ch, ch) for ch in text)


def best_ascii(text, cols):
    """Renderiza texto en ASCII art eligiendo la mejor fuente que quepa."""
    clean = strip_accents(text)
    usable = cols - 4

    # Probar fuentes de mayor a menor tamaño
    fonts = ["standard", "small", "mini"]
    for font in fonts:
        try:
            fig = pyfiglet.Figlet(font=font, width=usable)
            art = fig.renderText(clean)
            lines = [l for l in art.rstrip('\n').split('\n') if l.strip()]
            max_w = max((len(l) for l in lines), default=0)
            if max_w <= usable:
                return lines
        except Exception:
            continue

    # Fallback: texto plano
    return [f"  {text}"]


def parse_lrc(filepath):
    lyrics = []
    pattern = re.compile(r'\[(\d{2}):(\d{2}\.\d{2})\]\s*(.*)')
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                ts = int(m.group(1)) * 60 + float(m.group(2))
                lyrics.append((ts, m.group(3)))
    return lyrics


def fmt_time(s):
    return f"{int(s)//60:02d}:{int(s)%60:02d}"


def prog_bar(cur, tot, w=40):
    if tot == 0: return ""
    p = min(cur / tot, 1.0)
    f = int(w * p)
    return f"{GREEN}{'━'*f}{WHITE}●{DARK_GRAY}{'─'*max(0,w-f-1)}{RESET}"


def clear():
    print("\033[2J\033[H", end='', flush=True)


def ctr(text, cols):
    vis = len(re.sub(r'\033\[[0-9;]*m', '', text))
    return " " * max(0, (cols - vis) // 2) + text


def get_duration(fp):
    try:
        from mutagen.mp3 import MP3
        return MP3(fp).info.length
    except: pass
    try:
        import subprocess
        r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
            '-of','default=noprint_wrappers=1:nokey=1',fp],
            capture_output=True,text=True,timeout=5)
        return float(r.stdout.strip())
    except: pass
    return os.path.getsize(fp) / (128*1000/8)


def play_audio(fp, stop):
    import subprocess

    # 1) Intentar pygame primero (cross-platform: macOS, Windows, Linux)
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not stop.is_set():
            time.sleep(0.1)
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        return
    except (ImportError, Exception):
        pass

    # 2) Fallback a comandos nativos del OS
    if sys.platform == 'darwin':
        cmd = ['afplay', fp]
    elif sys.platform == 'win32':
        # Windows: usar powershell con Media.SoundPlayer o ffplay/mpg123
        if shutil.which('ffplay'):
            cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', fp]
        elif shutil.which('mpg123'):
            cmd = ['mpg123', '-q', fp]
        else:
            # Último recurso: abrir con el reproductor predeterminado de Windows
            os.startfile(fp)
            # Esperar hasta que se detenga
            while not stop.is_set():
                time.sleep(0.1)
            return
    elif shutil.which('mpg123'):
        cmd = ['mpg123', '-q', fp]
    elif shutil.which('ffplay'):
        cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', fp]
    else:
        print(f"\n{BOLD}⚠  Sin reproductor. Instala pygame: pip install pygame{RESET}")
        stop.set()
        return

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while proc.poll() is None and not stop.is_set():
        time.sleep(0.1)
    if stop.is_set():
        proc.terminate()
        proc.wait()


def render(lyrics, idx, words_rev, total_w, elapsed, total_dur, song):
    """Renderiza frame: palabras acumuladas SIEMPRE en ASCII art."""
    cols = shutil.get_terminal_size().columns
    clear()

    color = LINE_COLORS[idx % len(LINE_COLORS)] if idx >= 0 else CYAN
    div = f"{DARK_GRAY}{'─' * min(56, cols-4)}{RESET}"

    # ─── Header ─────────────────────────────────────────
    print()
    print(ctr(f"{PURPLE}{BOLD}♫  K A R A O K E  ♫{RESET}", cols))
    print(f"  {div}")

    text = lyrics[idx][1] if 0 <= idx < len(lyrics) else ""

    # ─── Líneas anteriores ──────────────────────────────
    for i in range(max(0, idx-2), max(0, idx)):
        t = lyrics[i][1]
        if t:
            print(ctr(f"{DARK_GRAY}{t}{RESET}", cols))

    print()

    # ─── ZONA PRINCIPAL: ASCII ART ──────────────────────
    if text and words_rev > 0:
        all_w = text.split()
        revealed = all_w[:words_rev]
        pending = all_w[words_rev:]

        # Texto acumulado hasta ahora → renderizar en ASCII art
        accumulated = " ".join(revealed)
        art_lines = best_ascii(accumulated, cols)

        # Mostrar el ASCII art centrado con color
        print()
        for aline in art_lines:
            pad = max(0, (cols - len(aline)) // 2)
            print(f"{' '*pad}{color}{BOLD}{aline}{RESET}")
        print()

        # Texto original debajo para legibilidad (con palabras reveladas)
        # Palabras reveladas en blanco, la última en color
        if len(revealed) > 1:
            prev = " ".join(revealed[:-1])
            last = revealed[-1]
            line_txt = f"{WHITE}{prev} {color}{BOLD}{UNDERLINE}{last}{RESET}"
        else:
            line_txt = f"{color}{BOLD}{UNDERLINE}{revealed[0]}{RESET}"

        # Agregar pendientes como puntos
        if pending:
            dots = " ".join(["·"*len(w) for w in pending])
            line_txt += f"  {DARK_GRAY}{dots}{RESET}"

        print(ctr(line_txt, cols))
        print()

    elif text == "" and 0 <= idx < len(lyrics):
        # Interludio
        print()
        print(ctr(f"{PURPLE}{BOLD}♪ · · · ♪ · · · ♪{RESET}", cols))
        print()
    else:
        print()
        print(ctr(f"{DARK_GRAY}♪  Esperando...  ♪{RESET}", cols))
        print()

    # ─── Próximas líneas ────────────────────────────────
    print(f"  {div}")
    for i in range(1, 4):
        ni = idx + i
        if 0 <= ni < len(lyrics) and lyrics[ni][1]:
            op = GRAY if i == 1 else DARK_GRAY
            print(ctr(f"{op}{ITALIC if i==1 else ''}{lyrics[ni][1]}{RESET}", cols))
    print()

    # ─── Progreso ───────────────────────────────────────
    print(f"  {div}")
    bw = min(40, cols-20)
    print(f"  {GRAY}{fmt_time(elapsed)}{RESET}  {prog_bar(elapsed,total_dur,bw)}  {GRAY}{fmt_time(total_dur)}{RESET}")
    print()
    print(ctr(f"{DARK_GRAY}🎵 {song}  ·  Ctrl+C para salir{RESET}", cols))


def run_display(lyrics, t0, total_dur, stop, song):
    """Loop principal: revela palabra por palabra, siempre en ASCII art."""
    cur_idx = -1
    w_rev = 0
    total_w = 0
    w_times = []
    last_key = None

    print(HIDE_CUR, end='', flush=True)

    try:
        while not stop.is_set():
            elapsed = time.time() - t0
            if elapsed >= total_dur: break

            # Línea actual
            new_idx = -1
            for i, (ts, _) in enumerate(lyrics):
                if elapsed >= ts: new_idx = i
                else: break

            # Nueva línea → calcular tiempos de palabras
            if new_idx != cur_idx:
                cur_idx = new_idx
                w_rev = 0
                if 0 <= cur_idx < len(lyrics):
                    _, txt = lyrics[cur_idx]
                    words = txt.split() if txt else []
                    total_w = len(words)
                    cur_ts = lyrics[cur_idx][0]
                    nxt_ts = lyrics[cur_idx+1][0] if cur_idx+1 < len(lyrics) else total_dur
                    dur = nxt_ts - cur_ts

                    if words:
                        # 60% del tiempo para revelar, 40% para mantener completa
                        rt = dur * 0.60
                        iv = rt / len(words)
                        iv = max(0.15, min(0.7, iv))
                        w_times = [cur_ts + j*iv for j in range(len(words))]
                    else:
                        w_times = []
                        total_w = 0

            # Palabras reveladas
            nr = sum(1 for wt in w_times if elapsed >= wt)
            if w_times and nr < 1: nr = 1

            key = (cur_idx, nr)
            if key != last_key:
                w_rev = nr
                last_key = key
                render(lyrics, cur_idx, w_rev, total_w, elapsed, total_dur, song)

            time.sleep(0.05)
    finally:
        print(SHOW_CUR, end='', flush=True)


def main():
    if len(sys.argv) == 3:
        lrc, mp3 = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 1:
        d = os.path.dirname(os.path.abspath(__file__))
        ls = [f for f in os.listdir(d) if f.endswith('.lrc')]
        ms = [f for f in os.listdir(d) if f.endswith('.mp3')]
        if not ls or not ms:
            print(f"{BOLD}Uso:{RESET} python karaoke.py [archivo.lrc] [archivo.mp3]"); sys.exit(1)
        lrc, mp3 = os.path.join(d,ls[0]), os.path.join(d,ms[0])
        print(f"{GREEN}▸{RESET} {os.path.basename(lrc)} + {os.path.basename(mp3)}")
        time.sleep(1)
    else:
        print(f"{BOLD}Uso:{RESET} python karaoke.py <archivo.lrc> <archivo.mp3>"); sys.exit(1)

    for f in [lrc, mp3]:
        if not os.path.exists(f): print(f"Error: {f}"); sys.exit(1)

    lyrics = parse_lrc(lrc)
    if not lyrics: print("Error: LRC vacío."); sys.exit(1)

    total_dur = get_duration(mp3)
    song = os.path.splitext(os.path.basename(mp3))[0]
    cols = shutil.get_terminal_size().columns

    # ─── Splash ─────────────────────────────────────────
    clear()
    print()
    print(ctr(f"{PURPLE}{BOLD}♫  K A R A O K E  ♫{RESET}", cols))
    print()
    try:
        fig = pyfiglet.Figlet(font="standard", width=min(cols-4, 100))
        art = fig.renderText(strip_accents(song))
        for l in art.strip().split('\n'):
            pad = max(0,(cols-len(l))//2)
            print(f"{' '*pad}{CYAN}{l}{RESET}")
    except: print(ctr(f"{CYAN}{BOLD}{song}{RESET}", cols))

    print()
    print(f"    {WHITE}Duración:{RESET} {GREEN}{fmt_time(total_dur)}{RESET}   {WHITE}Líneas:{RESET} {GREEN}{len(lyrics)}{RESET}")
    print()
    for n in [3,2,1]:
        print(f"\r    {YELLOW}▸ {n}...{RESET}  ", end='', flush=True)
        time.sleep(1)

    # ─── Play ───────────────────────────────────────────
    stop = threading.Event()
    t0 = time.time()
    t = threading.Thread(target=play_audio, args=(mp3, stop)); t.daemon = True; t.start()

    try:
        run_display(lyrics, t0, total_dur, stop, song)
    except KeyboardInterrupt: pass
    finally:
        stop.set(); clear()
        print(SHOW_CUR, end='', flush=True)
        print()
        try:
            fig = pyfiglet.Figlet(font="standard", width=min(cols-4,100))
            art = fig.renderText("Gracias!")
            for l in art.strip().split('\n'):
                pad = max(0,(cols-len(l))//2)
                print(f"{' '*pad}{PURPLE}{l}{RESET}")
        except: pass
        print()
        print(ctr(f"{GREEN}¡Gracias por escuchar!{RESET}", cols))
        print()
        t.join(timeout=2)


if __name__ == "__main__":
    main()
