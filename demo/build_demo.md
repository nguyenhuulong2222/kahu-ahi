# The 30-second demo video

`kahu-ahi-demo.mp4` is the project demo for the NASA Space Apps Challenge 2026 submission: 28.9 s, 1920x1080, 30 fps, H.264 (yuv420p), AAC, faststart, with English captions burned in.

**Narration: AI-generated voice (Google Gemini). Picture: screen recording of the live page.** The same sentence is in the file's `comment` tag, and the end card says "Narration: AI-generated voice". No music, no NASA logo, no AI-generated images or video; the title and end cards are text and the project's own mark (`docs/kahu-ahi-mark.svg`).

## Files

| File | What it is |
|---|---|
| `narration.wav` | The voice track supplied by the team (AI-generated, Google Gemini). Nothing here generates a voice. |
| `script.json` | The captions (the narration's words), the team line, the addresses and which state and day the scenes use. |
| `check_numbers.py` | Checks every number said or shown against `docs/data/*.json`; the build stops if one disagrees. |
| `build.py` | The whole build: voice, timing, cards, recording, assembly, checks. |
| `record.mjs` | Records the five page scenes with Playwright from the page served locally. |
| `cards.mjs` | Draws the title, challenge and end cards, the caption strips and the contact sheet. |
| `kahu-ahi-demo.srt` | The captions with their times. |
| `storyboard.png` | Thirty frames with their times: one a second and the last one. |

`build/` (recordings and intermediate files) and `frames/` (one frame a second) are made by the build and not committed.

## Rebuild

Needs `ffmpeg` and `ffprobe`, Python 3, and Node with Playwright:

```
cd demo && npm install && npx playwright install chromium && cd ..
python3 demo/build.py
```

`build.py` serves `docs/` on http://localhost:8765/ itself if nothing is serving it. The page loads its map tiles, the detection's place name and NASA's image of the day from the network, so the recording needs a connection. `python3 demo/build.py --keep` assembles again from the recordings already in `demo/build/`; `--scenes 3 6` records only those scenes again.

## How it is put together

- **Voice.** The silence at the start and end of `narration.wav` is cut. If the voice is then longer than 28.5 s it is sped up without a pitch change (ffmpeg `atempo`), by at most 8%; more than that stops the build. Loudness is normalised in two passes to -16 LUFS.
- **Timing.** The pauses in the voice are found with ffmpeg `silencedetect` and grouped into the seven sentences. A scene changes halfway through the pause before its sentence, and a caption is on screen for the whole of its scene, so for the whole of its sentence.
- **Picture.** The page is recorded in a 1280x627 window at device scale 1.5, so the picture is 1920x940 and everything is 1.5 times larger than at scale 1; the page keeps its wide, two-column layout at 1280. The remaining 140 px of the 1080 is a dark band that holds the caption (46 px, white) and, in small type at its right end, the site address, for the whole video. A caption never covers the page.
- **How the picture is taken.** Playwright's `recordVideo` records at scale 1 whatever the device scale, which would blur a 1.5x page, so `record.mjs` takes screenshots through Playwright instead (JPEG quality 96, 23 to 29 a second) with the time of each, and ffmpeg turns them into `build/sceneN.mp4`. In scene 3 the screenshot frames only the result card and its three figures, at a larger scale, so the figures are readable in a frame 640 px wide.
- **Full-window map.** Scenes 4 and 6 press the page's "Expand map". The browser's own full screen is refused while recording, so the page uses its built-in full-window mode (a screenshot of a browser in full screen would be the size of the screen, not of the window).
- **Pointer.** An amber ring follows the mouse and pulses on a press. It is added by the recording script and is not part of the page.
- **Waiting is cut out.** Where the page waits for the network (a state opening, the detection card with its place name and image, the close-up map), no picture is taken, so no frame shows a half-drawn map. Nothing else is cut or sped up; Play runs at the page's own Normal speed.
- **Scrolling.** The page and the detection card are scrolled by the script at reading speed (the page's own links jump in one frame, and the mouse wheel does not reach the card under automation).
- **Cuts.** Hard cuts between page scenes; 0.2 s cross-fades into and out of the cards.
- **ffmpeg here has no text filters**, so captions and cards are drawn by the browser as PNG files and overlaid.

## Scenes

1. Title card.
2. The challenge and the sentence from NASA's notice as the page words it.
3. First screen for the United States (lower 48 states), then the Harmonization result band.
4. Months, 2021, map expanded and set on the western states (`play_view` in `script.json`): Play from May runs June to November, with the date label and the timeline in the picture.
5. By state; New York (not harmonized) is selected and the page says why.
6. California, 18 Aug 2021, map expanded: one detection's card, "Zoom in here", then NASA's image of that day in the card.
7. "VIIRS-only record (as if Aqua had ended)", then the end card.
