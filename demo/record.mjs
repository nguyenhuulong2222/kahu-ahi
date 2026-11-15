// Records the page scenes of the demo video with Playwright, one scene per recording.
//
//   node demo/record.mjs            all scenes
//   node demo/record.mjs 3 6        only scenes 3 and 6
//
// The page is the real one, served from docs/ (DEMO_URL, default http://localhost:8765/). The picture is 1920x940:
// the remaining 140 px of the 1920x1080 frame is the caption band, so a caption never covers the page.
// Each recording starts with a magenta square in the corner; build.py finds the frame where it goes away and counts
// the scene from 0.5 s after that. Waiting for data, tiles or NASA's image is cut out: the script notes the stretches
// of real time that make up the scene in build/sceneN.json and build.py keeps only those.
import {chromium} from "playwright";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD = path.join(HERE, "build");
const BASE = process.env.DEMO_URL || "http://localhost:8765/";
const W = 1920, H = 940, LEAD = 0.5, TAIL = 0.5;
const timing = JSON.parse(fs.readFileSync(path.join(BUILD, "timing.json"), "utf8"));
const script = JSON.parse(fs.readFileSync(path.join(HERE, "script.json"), "utf8"));
const sleep = ms => new Promise(ok => setTimeout(ok, ms));

// A ring that follows the mouse and pulses on a press, so a viewer sees what is pressed. Not part of the page.
const POINTER = () => {
  if (window.top !== window) return;
  const make = () => {
    if (!document.documentElement || document.getElementById("demo-pointer")) return;
    const r = document.createElement("div");
    r.id = "demo-pointer";
    r.style.cssText = "position:fixed;left:0;top:0;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:4px solid #ffb000;"
      + "box-shadow:0 0 0 2px rgba(20,33,61,.9),inset 0 0 0 2px rgba(20,33,61,.9);background:rgba(255,176,0,.2);z-index:2147483647;pointer-events:none;transform:translate(-200px,-200px)";
    document.documentElement.appendChild(r);
    addEventListener("mousemove", e => { r.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)"; }, true);
    addEventListener("mousedown", () => {
      r.animate([{background: "rgba(255,176,0,.95)", boxShadow: "0 0 0 2px rgba(20,33,61,.9),0 0 0 0 rgba(255,176,0,.9)"},
        {background: "rgba(255,176,0,.2)", boxShadow: "0 0 0 2px rgba(20,33,61,.9),0 0 0 30px rgba(255,176,0,0)"}], {duration: 500, easing: "ease-out"});
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

// One scene: its own browser context and video. `body` gets helpers whose clock starts when the marker goes away.
async function scene(browser, n, opts, body) {
  const dir = path.join(BUILD, "raw" + n);
  fs.rmSync(dir, {recursive: true, force: true});
  const context = await browser.newContext({viewport: {width: W, height: H}, deviceScaleFactor: 1, reducedMotion: opts.motion ? "no-preference" : "reduce",
    recordVideo: {dir, size: {width: W, height: H}}});
  await context.addInitScript(POINTER);
  const page = await context.newPage();
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
        const u = Math.min(1, (Date.now() - t0) / ms), e = u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
        await page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e);
        if (u >= 1) break;
        await sleep(8);
      }
      at = [x, y];
    },
    async click() { await page.mouse.down(); await sleep(60); await page.mouse.up(); },
  };
  const clock = {t0: 0, skip: 0, parts: [], from: 0};
  const now = () => (Date.now() - clock.t0) / 1000;
  const h = {
    page, mouse, settle, errors,
    open: hash => open(page, settle, hash),
    centre: async sel => { const b = await page.locator(sel).first().boundingBox(); return [b.x + b.width / 2, b.y + b.height / 2]; },
    // Start the clock: show the marker, take it away, and leave half a second of still picture before time 0.
    async start() {
      await page.evaluate(() => { const m = document.createElement("div"); m.id = "demo-sync"; m.style.cssText = "position:fixed;left:0;top:0;width:64px;height:64px;background:#ff00ff;z-index:2147483646"; document.documentElement.appendChild(m); });
      await sleep(700);
      await page.evaluate(() => new Promise(ok => { document.getElementById("demo-sync").remove(); requestAnimationFrame(() => requestAnimationFrame(ok)); }));
      clock.gone = Date.now();
      clock.t0 = clock.gone + LEAD * 1000;
      await sleep(LEAD * 1000);
    },
    // Wait until scene time t (seconds), not counting what was cut.
    async until(t) { const wait = (t + clock.skip - now()) * 1000; if (wait > 0) await sleep(wait); },
    // Leave the time `wait` takes out of the scene.
    async cut(wait) { const a = now(); clock.parts.push([clock.from, a]); await wait(); const b = now(); clock.skip += b - a; clock.from = b; },
  };
  let failed = null;
  try {
    await body(h);
    await h.until(opts.seconds + TAIL);
    clock.parts.push([clock.from, now()]);
  } catch (e) { failed = e; }
  const video = page.video();
  await context.close();
  if (failed) throw failed;
  const file = path.join(BUILD, "scene" + n + ".webm");
  fs.copyFileSync(await video.path(), file);
  fs.rmSync(dir, {recursive: true, force: true});
  // Times are seconds after the marker went away.
  fs.writeFileSync(path.join(BUILD, "scene" + n + ".json"), JSON.stringify({scene: n, seconds: opts.seconds, lead: LEAD,
    parts: clock.parts.map(([a, b]) => [+(a + LEAD).toFixed(3), +(b + LEAD).toFixed(3)]), console_errors: errors}, null, 2) + "\n");
  console.log("scene " + n + ": " + opts.seconds.toFixed(2) + " s in " + clock.parts.length + " part(s)" + (errors.length ? ", console errors: " + errors.join(" | ") : ", console clean"));
}

const S = Object.fromEntries(timing.scenes.map(s => [s.n, s]));
const len = n => S[n].end - S[n].start;
const st = script.scene_state;

const SCENES = {
  // The first screen for the lower 48 states, then the result band.
  3: b => scene(b, 3, {seconds: len(3)}, async h => {
    await h.open("#region=conus");
    await h.mouse.put(1180, 560);
    // Come to rest beside the one-line result ("about 6.6 times as many"), not on it.
    const hb = await h.page.locator("#headline").boundingBox();
    await h.start();
    await h.until(0.4); await h.mouse.glide(hb.x + hb.width + 50, hb.y + 22, 700);
    // Bring the result band to the top of the picture at reading speed (the page's own link jumps there in one frame).
    await h.until(1.7);
    const to = await h.page.evaluate(() => Math.round(document.getElementById("harm").getBoundingClientRect().top + scrollY - 14));
    await h.page.evaluate(to => new Promise(ok => {
      const from = scrollY, t0 = performance.now(), ms = 650;
      const step = t => { const u = Math.min(1, (t - t0) / ms), e = u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; scrollTo(0, from + (to - from) * e); if (u < 1) requestAnimationFrame(step); else ok(); };
      requestAnimationFrame(step);
    }), to);
    const big = await h.page.locator("#harmbody .fig:not(.base) .big").first().boundingBox();
    await h.until(2.6); await h.mouse.glide(big.x + big.width + 40, big.y + big.height / 2, 600);
  }),
  // Months of a busy fire season, played.
  4: b => scene(b, 4, {seconds: len(4)}, async h => {
    await h.open("#region=conus&month=" + st.play_from);
    await h.page.evaluate(y => gridYear(y), +st.play_from.slice(0, 4));
    await h.settle();
    await h.mouse.put(420, 700);
    const [x, y] = await h.centre("#tl-play");
    await h.start();
    await h.until(0.15); await h.mouse.glide(x, y, 550);
    await h.until(0.85); await h.mouse.click();
    await h.until(1.5); await h.mouse.glide(x + 330, y - 120, 600);
  }),
  // By state, then a state where the test fails and the page says so.
  5: b => scene(b, 5, {seconds: len(5)}, async h => {
    await h.open("#region=conus&state=" + st.not_harmonized);   // once, so its map is already in the browser's cache
    await h.open("#region=conus");
    await h.page.evaluate(() => scrollTo(0, document.getElementById("bystate").getBoundingClientRect().top + scrollY - 14));
    await sleep(400);
    const spot = await h.page.evaluate(id => {
      const p = [...document.querySelectorAll(".statemap path")].find(e => (e.querySelector("title") || {}).textContent.startsWith(id + ":"));
      const r = p.getBoundingClientRect();
      for (let fy = .5; fy < 1; fy += .1) for (let fx = .5; fx > 0; fx -= .1) { const x = r.x + r.width * fx, y = r.y + r.height * fy; if (document.elementFromPoint(x, y) === p) return [x, y]; }
      return null;
    }, await h.page.evaluate(id => ST.states[id].name, st.not_harmonized));
    if (!spot) throw new Error("the state was not found on the By state map");
    await h.mouse.put(1250, 560);
    await h.start();
    await h.until(0.5); await h.mouse.glide(spot[0], spot[1], 900);
    await h.until(1.75); await h.mouse.click();
    await h.until(2.05);
    await h.cut(async () => {
      await h.page.waitForFunction(id => new URLSearchParams(location.hash.slice(1)).get("state") === id, st.not_harmonized);
      await h.page.evaluate(() => scrollTo(0, 0));
      await h.mouse.put(1215, 262);   // beside the refusal, not on it
      await h.settle(); await sleep(400);
    });
  }),
  // One detection on a busy day: the card, the zoom, NASA's image of the day.
  6: b => scene(b, 6, {seconds: len(6)}, async h => {
    const hash = "#region=conus&state=" + st.day_state + "&day=" + st.day;
    const find = () => h.page.evaluate(() => {
      // The counted detection with the most neighbours on screen: the middle of the day's largest fire.
      const m = document.getElementById("map").getBoundingClientRect();
      const pts = drawnRows.map(r => { const q = map.latLngToContainerPoint([r[0], r[1]]); return {x: q.x + m.x, y: q.y + m.y, counted: det(r).counted}; });
      let best = null;
      for (const a of pts) { if (!a.counted) continue; const n = pts.filter(b => Math.hypot(a.x - b.x, a.y - b.y) < 25).length; if (!best || n > best.n) best = {n, x: a.x, y: a.y}; }
      return best;
    });
    const card = async () => { await h.page.waitForSelector("#cardsheet:not([hidden]) #card-go"); await h.settle(900); };
    // Once through without recording anything that matters, so the image and the close-up map are in the cache.
    await h.open(hash);
    let d = await find();
    await h.page.mouse.click(d.x, d.y); await card();
    await h.page.locator("#card-go").click(); await h.settle(1200); await sleep(1500);
    await h.open(hash);
    d = await find();
    await h.mouse.put(d.x - 260, d.y + 190);
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
    await h.until(2.2); await h.mouse.glide(gx + 60, gy + 300, 250);
    // Roll the card down to NASA's image with the wheel, as a reader would.
    const to = await h.page.evaluate(() => { const s = document.getElementById("cardsheet"), i = s.querySelector("img"); return Math.min(s.scrollHeight - s.clientHeight, Math.round(i.getBoundingClientRect().top - s.getBoundingClientRect().top + s.scrollTop - 150)); });
    await h.until(2.4);
    for (let i = 0; i < 40; i++) {
      const cur = await h.page.evaluate(() => document.getElementById("cardsheet").scrollTop);
      if (to - cur < 2) break;
      await h.page.mouse.wheel(0, Math.max(8, Math.ceil((to - cur) / Math.max(1, 9 - i))));
      await sleep(28);
    }
    if (await h.page.evaluate(() => document.getElementById("cardsheet").scrollTop) < to - 4) throw new Error("the card did not scroll to NASA's image");
    // Off the card, so the ring does not sit on the image.
    const sheet = await h.page.locator("#cardsheet").boundingBox();
    await h.mouse.glide(sheet.x - 70, gy + 330, 350);
  }),
  // The record as if Aqua had ended.
  7: b => scene(b, 7, {seconds: timing.end_card_at - S[7].start + timing.fade}, async h => {
    await h.open("#region=conus&view=all");
    await h.page.evaluate(() => scrollTo(0, document.getElementById("h-drill").getBoundingClientRect().top + scrollY - 30));
    await sleep(500);
    const [x, y] = await h.centre("#record1 input[value=viirs]");
    await h.mouse.put(x + 150, y + 110);
    await h.start();
    await h.until(0.05); await h.mouse.glide(x, y, 300);
    await h.until(0.42); await h.mouse.click();
  }),
};

const want = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(SCENES);
const browser = await chromium.launch();
try { for (const n of want) await SCENES[n](browser); } finally { await browser.close(); }
