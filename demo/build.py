#!/usr/bin/env python3
"""Builds the 30-second demo video of the Kahu Ahi page: demo/kahu-ahi-demo.mp4 and demo/kahu-ahi-demo.srt.

Steps, in order (each stops the build when it fails):
  1. tools      ffmpeg and ffprobe are installed, demo/narration.wav is there
  2. numbers    every number said or shown is checked against docs/data (check_numbers.py)
  3. voice      silence trimmed, sped up without a pitch change if it is up to 8% too long, loudness normalised;
                the sentences are found from the pauses and each scene is timed to its sentence
  4. cards      title, challenge and end cards and the caption strips, drawn by the browser (cards.mjs)
  5. record     the page scenes, recorded with Playwright from the local page (record.mjs)
  6. assemble   ffmpeg: 1920x1080, 30 fps, H.264 yuv420p, AAC, faststart; captions burned in below the picture
  7. check      duration, size and loudness measured; one frame a second to demo/frames/; demo/storyboard.png

Usage:
  python3 demo/build.py                 everything
  python3 demo/build.py --keep          do not record again; use the recordings already in demo/build/
  python3 demo/build.py --scenes 3 6    record only these scenes again

Standard library only, plus ffmpeg/ffprobe and Node with Playwright (see build_demo.md).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import check_numbers

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = HERE / "build"
OUT = HERE / "kahu-ahi-demo.mp4"
SRT = HERE / "kahu-ahi-demo.srt"
URL = "http://localhost:8765/"

FPS = 30
W, H, BAND = 1920, 940, 140          # picture, and the caption band below it: 940 + 140 = 1080
MAX_TOTAL = 29.0                     # hard limit for the finished video, seconds
MAX_VOICE = 28.5                     # the voice must fit in this
MAX_SPEEDUP = 1.08
LEAD, TAIL = 0.2, 0.25               # silence before and after the voice
FADE = 0.2                           # cross-fade into and out of the cards
END_CARD_AFTER = 1.1                 # seconds of the last page scene before the end card
SILENCE = "silencedetect=noise=-35dB:d=0.18"
MIN_SPEECH = 0.15                    # shorter sounds between pauses are breaths, not words
LOUDNESS = "I=-16:TP=-1.5:LRA=11"
BAND_COLOUR = "0x0e1730"
SCENES = [3, 4, 5, 6, 7]


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"Command failed: {' '.join(str(c) for c in cmd[:6])} ...\n{r.stderr[-3000:]}")
    return r


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout.strip())


def silences(path):
    err = run(["ffmpeg", "-hide_banner", "-i", path, "-af", SILENCE, "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([-\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([-\d.]+)", err)]
    return list(zip(starts, ends + [duration(path)] * (len(starts) - len(ends))))


def speech(path):
    """Stretches of sound between pauses, breaths left out."""
    total, out, at = duration(path), [], 0.0
    for a, b in silences(path) + [(total, total)]:
        if a - at >= MIN_SPEECH:
            out.append((max(0.0, at), a))
        at = b
    return out


def sentences(parts, texts):
    """Put the stretches of speech into as many groups as there are captions, in order, so that each group's share of
    the speaking time is as close as possible to its caption's share of the letters."""
    n, m = len(parts), len(texts)
    if n < m:
        sys.exit(f"Found {n} stretches of speech for {m} captions: the pauses between sentences could not be told apart.")
    spoken = sum(b - a for a, b in parts)
    want = [len(t) / sum(len(t) for t in texts) for t in texts]
    best = {(0, 0): (0.0, [])}
    for j in range(1, m + 1):
        for i in range(j, n - (m - j) + 1):
            for k in range(j - 1, i):
                if (k, j - 1) not in best:
                    continue
                cost = (sum(b - a for a, b in parts[k:i]) / spoken - want[j - 1]) ** 2 + best[(k, j - 1)][0]
                if (i, j) not in best or cost < best[(i, j)][0]:
                    best[(i, j)] = (cost, best[(k, j - 1)][1] + [(parts[k][0], parts[i - 1][1])])
    return best[(n, m)][1]


def frame(t):
    return round(t * FPS) / FPS


def voice(script):
    src = HERE / "narration.wav"
    quiet, total = silences(src), duration(src)
    start = quiet[0][1] if quiet and quiet[0][0] <= 0.01 else 0.0
    end = quiet[-1][0] if quiet and quiet[-1][1] >= total - 0.01 else total
    spoken = end - start
    tempo = max(1.0, spoken / (MAX_VOICE - 0.05))
    if tempo > MAX_SPEEDUP:
        sys.exit(f"The voice is {spoken:.2f} s after trimming: {100 * (spoken / MAX_VOICE - 1):.1f}% longer than {MAX_VOICE} s, more than the 8% that may be sped up. Nothing was built.")
    chain = f"atrim={start:.4f}:{end:.4f},asetpts=PTS-STARTPTS" + (f",atempo={tempo:.5f}" if tempo > 1 else "")
    # Loudness in two passes: measure, then normalise with the measured values.
    err = run(["ffmpeg", "-hide_banner", "-i", src, "-af", f"{chain},loudnorm={LOUDNESS}:print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    norm = (f"loudnorm={LOUDNESS}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
            f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    out = BUILD / "voice.wav"
    run(["ffmpeg", "-hide_banner", "-y", "-i", src, "-af", f"{chain},{norm},aresample=48000", "-ac", "1", out])
    length = duration(out)
    if length > MAX_VOICE:
        sys.exit(f"The voice is still {length:.2f} s after trimming and speeding up; it must fit in {MAX_VOICE} s.")
    said = [(LEAD + a, LEAD + b) for a, b in sentences(speech(out), script["captions"])]
    total_out = frame(LEAD + length + TAIL + 0.5 / FPS)
    if total_out > MAX_TOTAL:
        sys.exit(f"The video would be {total_out:.2f} s; the limit is {MAX_TOTAL} s.")
    # A scene changes halfway through the pause between two sentences.
    cuts = [0.0] + [frame((said[i][1] + said[i + 1][0]) / 2) for i in range(len(said) - 1)] + [total_out]
    scenes = [{"n": i + 1, "start": cuts[i], "end": cuts[i + 1], "said": [round(said[i][0], 3), round(said[i][1], 3)], "caption": script["captions"][i]} for i in range(len(said))]
    timing = {"fps": FPS, "total": total_out, "lead": LEAD, "fade": FADE, "end_card_at": frame(cuts[6] + END_CARD_AFTER),
              "voice": {"source_seconds": round(total, 3), "trimmed_from": round(start, 3), "trimmed_to": round(end, 3), "tempo": round(tempo, 5),
                        "seconds": round(length, 3), "input_loudness_lufs": float(m["input_i"])},
              "scenes": scenes}
    (BUILD / "timing.json").write_text(json.dumps(timing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return timing


def stamp(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(timing):
    SRT.write_text("".join(f"{s['n']}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['caption']}\n\n" for s in timing["scenes"]), encoding="utf-8")


def served():
    try:
        return b"Kahu Ahi" in urllib.request.urlopen(URL, timeout=3).read()
    except OSError:
        return False


def marker_gone(video):
    """Seconds into a recording at which the magenta square in the corner goes away."""
    rate = 50
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={rate},crop=32:32:16:16,scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    seen = False
    for i in range(len(raw) // 3):
        r, g, b = raw[3 * i:3 * i + 3]
        magenta = r > 180 and g < 90 and b > 180
        if seen and not magenta:
            return i / rate
        seen = seen or magenta
    sys.exit(f"No marker found in {video}; record that scene again.")


def assemble(timing, script):
    S = {s["n"]: s for s in timing["scenes"]}
    total, end_at = timing["total"], timing["end_card_at"]
    need = {n: S[n]["end"] - S[n]["start"] for n in SCENES}
    need[7] = end_at - S[7]["start"] + FADE
    inputs, chains = [], []

    def still(name, seconds):
        inputs.extend(["-loop", "1", "-framerate", FPS, "-t", f"{seconds:.4f}", "-i", BUILD / f"{name}.png"])
        return len(inputs) // 8 - 1

    # Inputs 0-2: the cards; 3-9: the captions; then the recordings; last, the voice.
    title = still("card_title", S[2]["start"] + FADE)
    challenge = still("card_challenge", S[3]["start"] - S[2]["start"] + FADE)
    end = still("card_end", total - end_at)
    caps = [still(f"cap_{i}", total) for i in range(1, 8)]
    n_in = len(inputs) // 8
    labels = []
    for n in SCENES:
        video, meta = BUILD / f"scene{n}.webm", json.loads((BUILD / f"scene{n}.json").read_text())
        if meta["console_errors"]:
            sys.exit(f"Scene {n} was recorded with console errors: {meta['console_errors']}")
        t0 = marker_gone(video)
        inputs.extend(["-i", video])
        frames, parts, left = round(need[n] * FPS), [], need[n]
        for a, b in meta["parts"]:
            if left <= 0:
                break
            b = min(b, a + left + 2 / FPS)
            left -= b - a
            parts.append((t0 + a, t0 + b))
        if left > 0.05:
            sys.exit(f"Scene {n} is {left:.2f} s short; record it again.")
        chains.append(f"[{n_in}:v]fps={FPS},split={len(parts)}" + "".join(f"[s{n}p{i}]" for i in range(len(parts))))
        for i, (a, b) in enumerate(parts):
            chains.append(f"[s{n}p{i}]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[s{n}q{i}]")
        chains.append("".join(f"[s{n}q{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=1,trim=end_frame={frames},setpts=PTS-STARTPTS,format=yuv420p[s{n}]")
        labels.append(f"[s{n}]")
        n_in += 1
    inputs.extend(["-i", BUILD / "voice.wav"])
    fmt = f"fps={FPS},format=yuv420p,setsar=1,settb=AVTB"
    chains += [f"[{title}:v]{fmt}[c1]", f"[{challenge}:v]{fmt}[c2]", f"[{end}:v]{fmt}[c3]",
               "".join(labels) + f"concat=n={len(labels)}:v=1:a=0,setsar=1,fps={FPS},settb=AVTB[page]",
               f"[c1][c2]xfade=transition=fade:duration={FADE}:offset={S[2]['start']:.4f}[a]",
               f"[a][page]xfade=transition=fade:duration={FADE}:offset={S[3]['start']:.4f}[b]",
               f"[b][c3]xfade=transition=fade:duration={FADE}:offset={end_at:.4f},pad={W}:{H + BAND}:0:0:color={BAND_COLOUR}[v0]"]
    last = "v0"
    for i, c in enumerate(caps):
        s = S[i + 1]
        chains.append(f"[{last}][{c}:v]overlay=0:{H}:enable='gte(t,{s['start']:.4f})*lt(t,{s['end']:.4f})'[v{i + 1}]")
        last = f"v{i + 1}"
    chains.append(f"[{last}]trim=end_frame={round(total * FPS)},format=yuv420p[v]")
    chains.append(f"[{n_in}:a]adelay={round(LEAD * 1000)},apad,atrim=end={total:.4f}[au]")
    run(["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[au]",
         "-r", FPS, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{total:.4f}", "-movflags", "+faststart",
         "-metadata", "title=Kahu Ahi: one fire record across MODIS and VIIRS", "-metadata", f"comment={script['comment']}",
         "-metadata", f"artist=Team Kahu Ahi ({script['team_members']})", OUT])


def check(timing, script):
    info = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", OUT]).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    length, size = float(info["format"]["duration"]), int(info["format"]["size"])
    err = run(["ffmpeg", "-hide_banner", "-i", OUT, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    tail = err[err.rindex("Summary:"):]
    loud = {"integrated_lufs": float(re.search(r"I:\s+([-\d.]+) LUFS", tail).group(1)), "range_lu": float(re.search(r"LRA:\s+([-\d.]+) LU", tail).group(1)),
            "true_peak_dbfs": float(re.search(r"Peak:\s+([-\d.]+) dBFS", tail).group(1))}
    head = OUT.read_bytes()[:4096]
    report = {"file": OUT.name, "duration_seconds": round(length, 3), "bytes": size, "megabytes": round(size / 1e6, 2),
              "video": {"codec": v["codec_name"], "width": v["width"], "height": v["height"], "pix_fmt": v["pix_fmt"], "frame_rate": v["r_frame_rate"], "frames": int(v["nb_frames"])},
              "audio": {"codec": a["codec_name"], "sample_rate": a["sample_rate"], "channels": a["channels"]},
              "faststart": b"moov" in head, "comment": info["format"]["tags"].get("comment"), "loudness": loud,
              "voice": timing["voice"], "captions": [{"n": s["n"], "from": s["start"], "to": s["end"], "said_from": s["said"][0], "said_to": s["said"][1], "text": s["caption"]} for s in timing["scenes"]],
              "numbers": json.loads((BUILD / "numbers.json").read_text(encoding="utf-8"))}
    problems = []
    if length > MAX_TOTAL: problems.append(f"duration {length:.2f} s is over {MAX_TOTAL} s")
    if (v["codec_name"], v["width"], v["height"], v["pix_fmt"], v["r_frame_rate"]) != ("h264", W, H + BAND, "yuv420p", f"{FPS}/1"): problems.append("video stream is not 1920x1080 30 fps H.264 yuv420p")
    if a["codec_name"] != "aac": problems.append("audio is not AAC")
    if not report["faststart"]: problems.append("moov atom is not at the start (faststart)")
    if size >= 50e6: problems.append("file is 50 MB or more")
    if report["comment"] != script["comment"]: problems.append("comment tag missing")
    if any(s["start"] > s["said"][0] or s["end"] < s["said"][1] for s in timing["scenes"]): problems.append("a caption does not cover its sentence")
    report["problems"] = problems
    (BUILD / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # One frame a second, and the very last one: 30 pictures for the contact sheet.
    frames = HERE / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    times = [float(t) for t in range(int(length) + 1) if t < length - 0.05] + [length - 1.5 / FPS]
    for t in times:
        run(["ffmpeg", "-hide_banner", "-y", "-ss", f"{t:.3f}", "-i", OUT, "-frames:v", "1", frames / f"t{round(t * 10):04d}.png"])
    run(["node", HERE / "cards.mjs", "storyboard"])
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--keep", action="store_true", help="use the recordings already in demo/build/")
    ap.add_argument("--scenes", nargs="*", type=int, help="record only these scenes again")
    args = ap.parse_args()
    for tool in ("ffmpeg", "ffprobe", "node"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is not installed. Nothing was built.")
    if not (HERE / "narration.wav").exists():
        sys.exit("demo/narration.wav is not there. The team supplies the voice track; none is generated here.")
    BUILD.mkdir(exist_ok=True)
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    if check_numbers.run():
        sys.exit("A number in the demo disagrees with the data. Nothing was built.")
    timing = voice(script)
    write_srt(timing)
    print(subprocess.run(["node", str(HERE / "cards.mjs")], capture_output=True, text=True, check=True).stdout, end="")
    todo = [] if args.keep else [str(n) for n in (args.scenes or SCENES)]
    if todo:
        server = None
        if not served():
            server = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--directory", str(ROOT / "docs")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
        try:
            r = subprocess.run(["node", str(HERE / "record.mjs"), *todo], text=True)
            if r.returncode:
                sys.exit("Recording failed. Nothing was assembled.")
        finally:
            if server:
                server.terminate()
    assemble(timing, script)
    report = check(timing, script)
    print(f"{OUT.name}: {report['duration_seconds']:.1f} s, {report['megabytes']} MB, {report['loudness']['integrated_lufs']} LUFS")
    for p in report["problems"]:
        print("PROBLEM:", p)
    if report["problems"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
