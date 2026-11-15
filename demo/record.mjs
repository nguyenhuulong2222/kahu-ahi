// Records the page scenes of the demo video with Playwright, one scene per recording.
//
//   node demo/record.mjs            all scenes
//   node demo/record.mjs 3 6        only scenes 3 and 6
//
// The page is the real one, served from docs/ (DEMO_URL, default http://localhost:8765/), in a 1280x627 window at
// device scale 1.5, so the picture is 1920x940 with everything 1.5 times larger than at scale 1. The remaining 140 px
// of the 1920x1080 frame is the caption band, so a caption never covers the page.
//
// Playwright's own recordVideo records at scale 1 whatever the device scale, so the picture is taken as screenshots
// (JPEG at quality 96, as many a second as the browser gives: 15 to 25) with the time of each, and ffmpeg makes build/sceneN.mp4 from them. A screenshot can
// also be taken of part of the window at a larger scale: that is the "camera" the band scene uses to frame the three
// figures tightly while staying sharp.
// Waiting for data, tiles or NASA's image is cut out: no picture is taken while the script waits.
import {chromium} from "playwright";
import {execFileSync} from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD = path.join(HERE, "build");
const BASE = process.env.DEMO_URL || "http://localhost:8765/";
const W = 1920, H = 940, SCALE = 1.5, VW = W / SCALE, VH = Math.round(H / SCALE), TAIL = 0.4;
const timing = JSON.parse(fs.readFileSync(path.join(BUILD, "timing.json"), "utf8"));
const script = JSON.parse(fs.readFileSync(path.join(HERE, "script.json"), "utf8"));
const sleep = ms => new Promise(ok => setTimeout(ok, ms));
const ease = u => u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;

// A ring that follows the mouse and pulses on a press, so a viewer sees what is pressed. Not part of the page.
// The browser's own full screen is refused here, so "Expand map" uses the page's own full-window mode instead: a
// screenshot of a browser in full screen is the size of the screen, not of the window.
const POINTER = () => {
  if (window.top !== window) return;
  Element.prototype.requestFullscreen = () => Promise.reject(new Error("no browser full screen while recording"));
  const make = () => {
    if (!document.documentElement || document.getElementById("demo-pointer")) return;
    const r = document.createElement("div");
    r.id = "demo-pointer";
    r.style.cssText = "position:fixed;left:0;top:0;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;border:3px solid #ffb000;"
      + "box-shadow:0 0 0 1.5px rgba(20,33,61,.9),inset 0 0 0 1.5px rgba(20,33,61,.9);background:rgba(255,176,0,.2);z-index:2147483647;pointer-events:none;transform:translate(-200px,-200px)";
    document.documentElement.appendChild(r);
    addEventListener("mousemove", e => { r.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)"; }, true);
    addEventListener("mousedown", () => {
      r.animate([{background: "rgba(255,176,0,.95)", boxShadow: "0 0 0 1.5px rgba(20,33,61,.9),0 0 0 0 rgba(255,176,0,.9)"},
        {background: "rgba(255,176,0,.2)", boxShadow: "0 0 0 1.5px rgba(20,33,61,.9),0 0 0 20px rgba(255,176,0,0)"}], {duration: 500, easing: "ease-out"});
    }, true);
  };
  make();
  document.addEventListener("DOMContentLoaded", make);
};

function tracker(page) {
  let open = 0, last = Date.now();
  const done = () => { open = Math.max(0, open - 1); last = Date.now(); };
  page.on("request", () => { open++; last = Date.now(); });
  page.on("requestfinished", done);
  page.on("requestfailed", done);
  // Quiet network, every map tile drawn, and no image in the card still loading.
  return async (quiet = 600, max = 25000) => {
    const start = Date.now();
    while (Date.now() - start < max) {
      const drawn = await page.evaluate(() => [...document.querySelectorAll("#map img.leaflet-tile")].every(i => i.classList.contains("leaflet-tile-loaded"))
        && [...document.querySelectorAll("#cardsheet img")].every(i => i.complete && i.naturalWidth > 0)).catch(() => false);
      if (drawn && open === 0 && Date.now() - last >= quiet) return;
      await sleep(60);
    }
    throw new Error("the page did not settle in " + max + " ms");
  };
}

async function open(page, settle, hash) {
  await page.goto("about:blank");
  await page.goto(BASE + hash);
  await page.waitForFunction(() => typeof D !== "undefined" && D && typeof map !== "undefined" && map);
  await settle();
  await sleep(500);
}

// One scene: its own browser context. `body` gets helpers whose clock starts at h.start().
async function scene(browser, n, opts, body) {
  const context = await browser.newContext({viewport: {width: VW, height: VH}, deviceScaleFactor: SCALE, reducedMotion: "reduce"});
  await context.addInitScript(POINTER);
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const errors = [];
  page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", e => errors.push(String(e)));
  const settle = tracker(page);
  let at = [0, 0];
  const mouse = {
    async put(x, y) { at = [x, y]; await page.mouse.move(x, y); },
    // Takes `ms` of real time however long each step takes: the position follows the clock.
    async glide(x, y, ms) {
      const [x0, y0] = at, t0 = Date.now();
      for (;;) {
        const u = Math.min(1, (Date.now() - t0) / ms), e = ease(u);
        await page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e);
        if (u >= 1) break;
        await sleep(8);
      }
      at = [x, y];
    },
    async click() { await page.mouse.down(); await sleep(60); await page.mouse.up(); },
  };
  // The camera: the part of the window in the picture, in page pixels from the window's top left. w = VW is the whole window.
  const cam = {x: 0, y: 0, w: VW};
  const clock = {t0: 0, skip: 0, on: false, busy: null};
  const frames = [];   // [scene seconds, JPEG at quality 96]
  const now = () => (Date.now() - clock.t0) / 1000;
  const shoot = async () => {
    const t = now() - clock.skip, whole = cam.w === VW && !cam.x && !cam.y;
    // The whole window is taken as it is; only a closer framing needs a clip (in document pixels) and its own scale.
    const s = whole ? null : await page.evaluate(() => [scrollX, scrollY]);
    const r = await cdp.send("Page.captureScreenshot", {format: "jpeg", quality: 96, optimizeForSpeed: true,
      ...(whole ? {} : {clip: {x: s[0] + cam.x, y: s[1] + cam.y, width: cam.w, height: cam.w * H / W, scale: W / cam.w}})});
    frames.push([t, Buffer.from(r.data, "base64")]);
  };
  const run = async () => { while (clock.on) await shoot(); };
  const h = {
    page, mouse, settle, errors, cam,
    open: hash => open(page, settle, hash),
    centre: async sel => { const b = await page.locator(sel).first().boundingBox(); return [b.x + b.width / 2, b.y + b.height / 2]; },
    async start() { clock.t0 = Date.now(); clock.on = true; clock.busy = run(); },
    // Wait until scene time t (seconds), not counting what was cut.
    async until(t) { const wait = (t + clock.skip - now()) * 1000; if (wait > 0) await sleep(wait); },
    // Leave the time `wait` takes out of the scene: no picture is taken meanwhile.
    async cut(wait) { clock.on = false; await clock.busy; const a = now(); await wait(); clock.skip += now() - a; clock.on = true; clock.busy = run(); },
    // Move the camera to frame (x, y, w) over `ms`.
    async push(x, y, w, ms) {
      const from = {...cam}, t0 = Date.now();
      for (;;) {
        const u = Math.min(1, (Date.now() - t0) / ms), e = ease(u);
        cam.x = from.x + (x - from.x) * e; cam.y = from.y + (y - from.y) * e; cam.w = from.w + (w - from.w) * e;
        if (u >= 1) break;
        await sleep(12);
      }
    },
  };
  let failed = null;
  try {
    await body(h);
    await h.until(opts.seconds + TAIL);
  } catch (e) { failed = e; }
  clock.on = false;
  await clock.busy;
  await context.close();
  if (failed) throw failed;
  // The pictures and how long each is shown, then one constant-rate file for build.py.
  const dir = path.join(BUILD, "raw" + n);
  fs.rmSync(dir, {recursive: true, force: true});
  fs.mkdirSync(dir, {recursive: true});
  const end = opts.seconds + TAIL;
  let list = "ffconcat version 1.0\n";
  frames.forEach(([t, png], i) => {
    const name = String(i).padStart(5, "0") + ".jpg";
    fs.writeFileSync(path.join(dir, name), png);
    list += "file " + name + "\nduration " + Math.max(0.001, (i + 1 < frames.length ? frames[i + 1][0] : end) - t).toFixed(4) + "\n";
  });
  list += "file " + String(frames.length - 1).padStart(5, "0") + ".jpg\n";
  fs.writeFileSync(path.join(dir, "list.txt"), list);
  const file = path.join(BUILD, "scene" + n + ".mp4");
  execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-i", path.join(dir, "list.txt"), "-vf", "fps=30,scale=" + W + ":" + H + ",setsar=1,format=yuv444p", "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", file]);
  fs.rmSync(dir, {recursive: true, force: true});
  const gaps = frames.slice(1).map((f, i) => f[0] - frames[i][0]);
  const info = {scene: n, seconds: opts.seconds, pictures: frames.length, pictures_per_second: +(frames.length / end).toFixed(1), longest_gap_seconds: +Math.max(...gaps).toFixed(3), console_errors: errors};
  fs.writeFileSync(path.join(BUILD, "scene" + n + ".json"), JSON.stringify(info, null, 2) + "\n");
  console.log("scene " + n + ": " + opts.seconds.toFixed(2) + " s, " + info.pictures_per_second + " pictures a second, longest gap " + info.longest_gap_seconds + " s" + (errors.length ? ", console errors: " + errors.join(" | ") : ", console clean"));
}

const S = Object.fromEntries(timing.scenes.map(s => [s.n, s]));
const len = n => S[n].end - S[n].start;
const st = script.scene_state;
const toTop = (h, sel, gap) => h.page.evaluate(([sel, gap]) => scrollTo(0, document.querySelector(sel).getBoundingClientRect().top + scrollY - gap), [sel, gap]);
// Scroll the page at reading speed (the page's own links jump in one frame).
const scrollTo_ = (h, to, ms) => h.page.evaluate(([to, ms]) => new Promise(ok => {
  const from = scrollY, t0 = performance.now();
  const step = t => { const u = Math.min(1, (t - t0) / ms), e = u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; scrollTo(0, from + (to - from) * e); if (u < 1) requestAnimationFrame(step); else ok(); };
  requestAnimationFrame(step);
}), [to, ms]);
const fullScreen = async h => { await h.page.locator("#expand").click(); await sleep(900); await h.settle(); await sleep(900); };

const SCENES = {
  // The first screen for the lower 48 states, then the result band, framed on its three figures.
  3: b => scene(b, 3, {seconds: len(3)}, async h => {
    await h.open("#region=conus");
    await h.mouse.put(790, 420);
    const hb = await h.page.locator("#headline").boundingBox();
    await h.start();
    // Come to rest beside the one-line result ("about 6.6 times as many"), not on it.
    await h.until(0.4); await h.mouse.glide(hb.x + hb.width + 34, hb.y + 16, 650);
    await h.until(1.6);
    const to = await h.page.evaluate(() => Math.round(document.getElementById("harm").getBoundingClientRect().top + scrollY - 8));
    await scrollTo_(h, to, 600);
    // Closer: the card's heading and its three figures (as recorded, one ratio, month by month) fill the picture.
    const card = await h.page.locator("#harm").boundingBox(), figs = await h.page.locator("#harmbody .figs").boundingBox();
    const w = Math.max(card.width + 2 * card.x, (figs.y + figs.height + 10) * W / H);
    await h.until(2.35);
    await Promise.all([h.push(0, 0, Math.min(VW, w), 550), h.mouse.glide(card.x + card.width + 8, figs.y - 14, 500)]);
  }),
  // Months of a busy fire season in the western states, played, with the map full screen.
  4: b => scene(b, 4, {seconds: len(4)}, async h => {
    await h.open("#region=conus&month=" + st.play_from);
    await fullScreen(h);
    await h.page.evaluate(v => map.setView([v[0], v[1]], v[2], {animate: false}), st.play_view);
    await h.page.evaluate(y => gridYear(y), +st.play_from.slice(0, 4));
    await h.settle(900); await sleep(600);
    const [x, y] = await h.centre("#tl-play");
    await h.mouse.put(x + 250, y - 150);
    await h.start();
    await h.until(0.15); await h.mouse.glide(x, y, 550);
    await h.until(0.85); await h.mouse.click();
    await h.until(1.5); await h.mouse.glide(x + 150, y - 190, 600);   // on open ocean, clear of the scale bar and the fires
  }),
  // By state, then a state where the test fails and the page says so.
  5: b => scene(b, 5, {seconds: len(5)}, async h => {
    await h.open("#region=conus&state=" + st.not_harmonized);   // once, so its map is already in the browser's cache
    await h.open("#region=conus");
    await toTop(h, "#bystate", 8);
    await sleep(400);
    await h.mouse.put(840, 380);
    await h.start();
    // From the sentence "37 of 49 are harmonized" down to the map and the table.
    await h.until(0.9);
    await scrollTo_(h, await h.page.evaluate(() => Math.round(document.querySelector(".stategrid").getBoundingClientRect().top + scrollY - 14)), 500);
    const spot = await h.page.evaluate(name => {
      const p = [...document.querySelectorAll(".statemap path")].find(e => (e.querySelector("title") || {}).textContent.startsWith(name + ":"));
      const r = p.getBoundingClientRect();
      for (let fy = .5; fy < 1; fy += .1) for (let fx = .5; fx > 0; fx -= .1) { const x = r.x + r.width * fx, y = r.y + r.height * fy; if (document.elementFromPoint(x, y) === p) return [x, y]; }
      return null;
    }, await h.page.evaluate(id => ST.states[id].name, st.not_harmonized));
    if (!spot) throw new Error("the state was not found on the By state map");
    await h.until(1.5); await h.mouse.glide(spot[0], spot[1], 600);
    await h.until(2.25); await h.mouse.click();
    await h.until(2.36);   // the press is seen; the state's own page is cut to once it has loaded
    await h.cut(async () => {
      await h.page.waitForFunction(id => new URLSearchParams(location.hash.slice(1)).get("state") === id, st.not_harmonized);
      await h.page.evaluate(() => scrollTo(0, 0));
      const hb = await h.page.locator("#headline").boundingBox();
      await h.mouse.put(hb.x + hb.width + 34, hb.y + hb.height - 10);   // beside the refusal, not on it
      await h.settle(); await sleep(400);
    });
  }),
  // One detection on a busy day: the card, the zoom, NASA's image of the day. The map is full screen.
  6: b => scene(b, 6, {seconds: len(6)}, async h => {
    const hash = "#region=conus&state=" + st.day_state + "&day=" + st.day;
    const find = () => h.page.evaluate(() => {
      // The counted detection with the most neighbours on screen: the middle of the day's largest fire.
      const m = document.getElementById("map").getBoundingClientRect();
      const pts = drawnRows.map(r => { const q = map.latLngToContainerPoint([r[0], r[1]]); return {x: q.x + m.x, y: q.y + m.y, counted: det(r).counted}; });
      let best = null;
      for (const a of pts) { if (!a.counted) continue; const n = pts.filter(b => Math.hypot(a.x - b.x, a.y - b.y) < 17).length; if (!best || n > best.n) best = {n, x: a.x, y: a.y}; }
      return best;
    });
    const card = async () => { await h.page.waitForSelector("#cardsheet:not([hidden]) #card-go"); await h.settle(900); };
    // Once through without recording, so the image and the close-up map are in the cache.
    await h.open(hash);
    await fullScreen(h);
    let d = await find();
    await h.page.mouse.click(d.x, d.y); await card();
    await h.page.locator("#card-go").click(); await h.settle(1200); await sleep(1500);
    await h.open(hash);
    await fullScreen(h);
    d = await find();
    await h.mouse.put(d.x - 170, d.y + 130);
    await h.start();
    await h.until(0.15); await h.mouse.glide(d.x, d.y, 500);
    await h.until(0.8); await h.mouse.click();
    await h.until(1.0);
    await h.cut(card);
    const [gx, gy] = await h.centre("#card-go");
    await h.until(1.45); await h.mouse.glide(gx, gy, 400);
    await h.until(1.95); await h.mouse.click();
    await h.until(2.15);
    await h.cut(async () => { await h.settle(1200); await sleep(700); });
    await h.until(2.2); await h.mouse.glide(gx + 40, gy + 200, 250);
    // Roll the card down to NASA's image at reading speed. (The mouse wheel does not reach the card under automation
    // while the map is full screen, so its scroll position is moved directly, as the page's is in other scenes.)
    await h.until(2.4);
    await h.page.evaluate(ms => new Promise(ok => {
      const s = document.getElementById("cardsheet"), i = s.querySelector("img"), from = s.scrollTop, t0 = performance.now();
      const to = Math.min(s.scrollHeight - s.clientHeight, Math.round(i.getBoundingClientRect().top - s.getBoundingClientRect().top + s.scrollTop - 70));
      const step = t => { const u = Math.min(1, (t - t0) / ms), e = u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; s.scrollTop = from + (to - from) * e; if (u < 1) requestAnimationFrame(step); else ok(); };
      requestAnimationFrame(step);
    }), 450);
    const seen = await h.page.evaluate(() => { const s = document.getElementById("cardsheet").getBoundingClientRect(), i = document.querySelector("#cardsheet img").getBoundingClientRect(); return i.top >= s.top && i.bottom <= s.bottom; });
    if (!seen) throw new Error("NASA's image is not wholly inside the card after scrolling");
    // Off the card, so the ring does not sit on the image.
    const sheet = await h.page.locator("#cardsheet").boundingBox();
    await h.mouse.glide(sheet.x - 46, gy + 220, 350);
  }),
  // The record as if Aqua had ended.
  7: b => scene(b, 7, {seconds: timing.end_card_at - S[7].start + timing.fade}, async h => {
    await h.open("#region=conus&view=all");
    await toTop(h, "#h-drill", 20);
    await sleep(500);
    const [x, y] = await h.centre("#record1 input[value=viirs]");
    await h.mouse.put(x + 100, y + 74);
    await h.start();
    await h.until(0.05); await h.mouse.glide(x, y, 300);
    await h.until(0.42); await h.mouse.click();
  }),
};

const want = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(SCENES);
const browser = await chromium.launch();
try { for (const n of want) await SCENES[n](browser); } finally { await browser.close(); }
