// Draws the title, challenge and end cards, the caption strips and (with "storyboard") the contact sheet, as PNG files,
// with the page's own mark (docs/kahu-ahi-mark.svg), colours and font stack. Text only: no photograph, no logo.
//
//   node demo/cards.mjs               cards and captions -> demo/build/
//   node demo/cards.mjs storyboard    demo/frames/*.png -> demo/storyboard.png
import {chromium} from "playwright";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD = path.join(HERE, "build");
const script = JSON.parse(fs.readFileSync(path.join(HERE, "script.json"), "utf8"));
const mark = fs.readFileSync(path.join(HERE, "..", "docs", "kahu-ahi-mark.svg"), "utf8");
const W = 1920, H = 940, BAND = 140, CAPTION_PX = 46;
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
// The page's tokens (docs/index.html :root).
const CSS = `*{box-sizing:border-box}html,body{margin:0}body{font-family:"Avenir Next","Segoe UI","Helvetica Neue",Arial,sans-serif;color:#14213d;background:#eef1f4}
.card{width:${W}px;height:${H}px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 160px}
.card svg{height:230px;width:auto;margin-bottom:26px}
h1{font-size:112px;line-height:1;margin:0;font-weight:700;letter-spacing:-.01em}
.sub{font-size:44px;color:#55627a;margin:10px 0 44px;font-style:italic}
.line{font-size:42px;font-weight:600;margin:6px 0}.small{font-size:34px;color:#55627a;margin:6px 0}
.kicker{font-size:34px;font-weight:700;color:#0b6e6e;letter-spacing:.06em;text-transform:uppercase;margin:0 0 18px}
.big{font-size:68px;line-height:1.12;font-weight:700;margin:0 0 54px;white-space:nowrap}
.quote{font-size:46px;line-height:1.3;max-width:1450px;margin:0 0 22px;border-left:10px solid #8a4b00;background:#fff6e5;padding:26px 36px;text-align:left}
.addr{font-size:50px;font-weight:700;margin:8px 0}.addr.second{font-weight:600;font-size:42px}
.cap{width:${W}px;height:${BAND}px;background:#0e1730;color:#fff;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 70px}
.cap p{margin:0;font-size:${CAPTION_PX}px;line-height:1.22;font-weight:600;text-wrap:balance}`;
const page_ = body => `<!doctype html><meta charset="utf-8"><style>${CSS}</style>${body}`;

const browser = await chromium.launch();
const page = await browser.newPage({viewport: {width: W, height: H}, deviceScaleFactor: 1});
if (process.argv[2] === "storyboard") {
  const dir = path.join(HERE, "frames");
  const frames = fs.readdirSync(dir).filter(f => f.endsWith(".png")).sort();
  const cells = frames.map(f => `<figure><img src="data:image/png;base64,${fs.readFileSync(path.join(dir, f)).toString("base64")}"><figcaption>${(+f.slice(1, 5) / 10).toFixed(1)} s</figcaption></figure>`).join("");
  await page.setViewportSize({width: 2400, height: 800});
  await page.setContent(`<!doctype html><meta charset="utf-8"><style>body{margin:0;padding:16px;background:#14213d;font-family:"Avenir Next",Arial,sans-serif}
    .g{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}figure{margin:0}img{width:100%;display:block}figcaption{color:#fff;font-size:20px;font-weight:600;padding:4px 2px 0}</style><div class="g">${cells}</div>`);
  await page.waitForFunction(() => [...document.images].every(i => i.complete));
  await page.screenshot({path: path.join(HERE, "storyboard.png"), fullPage: true});
  console.log("storyboard: " + frames.length + " frames");
} else {
  fs.mkdirSync(BUILD, {recursive: true});
  const cards = {
    card_title: `<div class="card">${mark}<h1>Kahu Ahi</h1><p class="sub">keeper of the fire</p><p class="line">Team Kahu Ahi, Maui, Hawaiʻi</p><p class="small">${esc(script.team_members)}</p><p class="small">NASA Space Apps Challenge 2026, Honolulu Local Event</p></div>`,
    card_challenge: `<div class="card"><p class="kicker">The challenge</p><p class="big">Harmonization of MODIS and VIIRS Hot Spots</p><p class="quote">${esc(script.notice_sentence)}</p><p class="small">${esc(script.notice_source)}</p></div>`,
    card_end: `<div class="card">${mark}<h1>Kahu Ahi</h1><p class="sub">keeper of the fire</p><p class="addr">${esc(script.site)}</p><p class="addr second">${esc(script.repository)}</p><p class="small" style="margin-top:34px">Narration: AI-generated voice</p></div>`,
  };
  for (const [name, body] of Object.entries(cards)) {
    await page.setContent(page_(body));
    const over = await page.evaluate(() => { const c = document.querySelector(".card"); return c.scrollHeight > c.clientHeight || c.scrollWidth > c.clientWidth; });
    if (over) throw new Error(name + " does not fit the picture");
    await page.screenshot({path: path.join(BUILD, name + ".png"), clip: {x: 0, y: 0, width: W, height: H}});
  }
  for (const [i, text] of script.captions.entries()) {
    await page.setContent(page_(`<div class="cap"><p>${esc(text)}</p></div>`));
    const fit = await page.evaluate(() => { const p = document.querySelector(".cap p"), r = p.getBoundingClientRect(); return {h: r.height, lines: Math.round(r.height / parseFloat(getComputedStyle(p).lineHeight)), px: parseFloat(getComputedStyle(p).fontSize)}; });
    if (fit.h > BAND - 12 || fit.px < 44) throw new Error("caption " + (i + 1) + " does not fit the band: " + JSON.stringify(fit));
    await page.screenshot({path: path.join(BUILD, "cap_" + (i + 1) + ".png"), clip: {x: 0, y: 0, width: W, height: BAND}});
    console.log("caption " + (i + 1) + ": " + fit.lines + " line(s) at " + fit.px + " px");
  }
}
await browser.close();
