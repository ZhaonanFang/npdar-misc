"""Record the npdar demo GIFs from the HTML made by render_plotly.R.

Setup: pip install playwright pillow  (uses the installed Microsoft Edge)
Run:   Rscript render_plotly.R && python record_plotly.py

GIFs are saved to gifs/ here, then copied to ../npdar/man/figures if that folder exists.
"""
import io
import pathlib
import shutil

from PIL import Image
from playwright.sync_api import sync_playwright

W, H = 800, 520
HERE = pathlib.Path(__file__).parent
BUILD_DIR = HERE / "build"
GIF_DIR = HERE / "gifs"
NPDAR_FIGURES = HERE.parent / "npdar" / "man" / "figures"

CURSOR_JS = """
(() => {
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;left:-50px;top:-50px;width:24px;height:24px;pointer-events:none;z-index:99999;';
  c.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M3 2 L3 19 L8 14.5 L11.5 22 L14.5 20.7 L11 13.3 L18 13 Z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  const r = document.createElement('div');
  r.style.cssText = 'position:fixed;left:-50px;top:-50px;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;border:3px solid rgba(224,0,135,.8);pointer-events:none;z-index:99998;display:none;';
  document.body.append(r, c);
  addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', e => { r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; r.style.display = 'block'; }, true);
  addEventListener('mouseup', () => { r.style.display = 'none'; }, true);
})();
"""

# Data coordinates -> viewport pixels, via plotly's own axis objects
PX_JS = """
([xv, yv]) => {
  const gd = document.querySelector('.js-plotly-plot');
  const b = gd.getBoundingClientRect();
  const xa = gd._fullLayout.xaxis, ya = gd._fullLayout.yaxis;
  const px = (a, v) => a._offset + a.c2p(a.d2c(v));
  return [b.left + px(xa, xv), b.top + px(ya, yv)];
}
"""


class Recorder:
    def __init__(self, page):
        self.page, self.frames = page, []
        self.x, self.y = 30, 30
        page.mouse.move(self.x, self.y)

    def snap(self, ms=60):
        self.page.wait_for_timeout(25)
        img = Image.open(io.BytesIO(self.page.screenshot())).convert("RGB")
        self.frames.append((img, ms))

    def hold(self, n=1, ms=120):
        for _ in range(n):
            self.snap(ms)

    def move(self, x, y, steps=8, ms=40):
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)  # ease in/out
            self.page.mouse.move(x0 + (x - x0) * t, y0 + (y - y0) * t)
            self.snap(ms)
        self.x, self.y = x, y

    def click(self, hold_ms=500):
        self.page.mouse.down()
        self.snap(110)
        self.page.mouse.up()
        self.page.wait_for_timeout(250)
        self.snap(hold_ms)

    def save(self, name):
        imgs = [f[0] for f in self.frames]
        durs = [f[1] for f in self.frames]
        pal = [im.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
               for im in imgs]
        pal[0].save(GIF_DIR / name, save_all=True, append_images=pal[1:],
                    duration=durs, loop=0, optimize=True, disposal=1)


def open_plot(page, html, ready_selector):
    page.goto((BUILD_DIR / html).as_uri())
    page.wait_for_selector(ready_selector)
    page.wait_for_timeout(800)
    page.evaluate(CURSOR_JS)
    r = Recorder(page)
    r.hold(2, 300)
    return r


def run_raincloud(page):
    r = open_plot(page, "raincloud.html", ".js-plotly-plot .updatemenu-button")

    def pix(xv, yv):
        return page.evaluate(PX_JS, [xv, yv])

    def scatter_point(k, idx):
        # Skip the legend-only traces, which hold a single NA
        return page.evaluate("""([k, idx]) => {
          const gd = document.querySelector('.js-plotly-plot');
          const t = gd.data.filter(d => d.type === 'scatter' && d.mode === 'markers' && d.x.length > 1)[k];
          return [t.x[idx], t.y[idx]];
        }""", [k, idx])

    # Raw values: one point per group
    for k, idx in [(0, 20), (1, 25), (2, 30)]:
        r.move(*pix(*scatter_point(k, idx)), steps=9)
        r.hold(5, 120)

    # Box stats: a few pixels above the median line, inside the box, where the dots
    # do not take over the hover
    med = page.evaluate("""() => {
      const gd = document.querySelector('.js-plotly-plot');
      return gd.calcdata.filter(cd => cd[0].trace.type === 'box')[1][0].med;
    }""")
    mx, my = pix(med, 2)
    r.move(mx, my - 6, steps=12)
    r.hold(18, 120)

    buttons = page.evaluate("""() => [...document.querySelectorAll('.updatemenu-button')].map(e => {
      const b = e.getBoundingClientRect();
      return [b.left + b.width / 2, b.top + b.height / 2, e.textContent]; })""")
    pos = {label: (x, y) for x, y, label in buttons}

    r.move(*pos["Scatter"], steps=12)
    r.hold(2, 200)
    r.click(1100)  # hide
    r.click(1100)  # show
    r.move(*pos["Box"], steps=8)
    r.click(1100)  # hide
    r.click(1100)  # show
    r.save("plot_raincloud_ly.gif")


def run_corrmat(page):
    r = open_plot(page, "corrmat.html", ".js-plotly-plot .heatmaplayer")

    # Tiles are named "<row> vs <column>": qsec vs hp, then gear vs qsec
    for col, row in [("hp", "qsec"), ("qsec", "gear")]:
        r.move(*page.evaluate(PX_JS, [col, row]), steps=12)
        r.hold(16, 120)
    r.save("plot_corrmat_ly.gif")


def main():
    GIF_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": W, "height": H})
        run_raincloud(page)
        run_corrmat(page)
        browser.close()

    try:
        NPDAR_FIGURES.mkdir(exist_ok=True)
        for gif in GIF_DIR.glob("*.gif"):
            shutil.copy2(gif, NPDAR_FIGURES / gif.name)
        print(f"Copied GIFs to {NPDAR_FIGURES}")
    except OSError as e:
        print(f"Saved to {GIF_DIR}, but could not copy to {NPDAR_FIGURES}: {e}")


if __name__ == "__main__":
    main()
