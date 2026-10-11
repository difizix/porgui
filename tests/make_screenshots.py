"""README screenshots (docs/img/) of a running porgui, opened through its URL query parameters.

Run `runs/pnm_from_extrude.py` first (writes runs/pakextr/), start porgui (host or container), then:
    python tests/make_screenshots.py [http://localhost:8501] [--chrome /usr/bin/google-chrome]
Needs `pip install playwright` and either `playwright install chromium` or a local Chrome.
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

out_dir = Path(__file__).resolve().parent.parent / "docs" / "img"

SHOTS = {
    "image.png": "image?img=pakextr/extruded_240x200x28_5p0um.mhd&axis=Z&slice=14",
    "network.png": "network?net=pakextr/extruded_ms.xmf",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", nargs="?", default="http://localhost:8501")
    parser.add_argument("--chrome", help="Browser executable, instead of playwright's chromium")
    parser.add_argument("--wait", type=float, default=8, help="Seconds to let each page render")
    args = parser.parse_args()

    out_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        for name, route in SHOTS.items():
            page.goto(f"{args.url.rstrip('/')}/{route}", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(args.wait * 1000)
            page.screenshot(path=out_dir / name)
            print(out_dir / name)
        browser.close()


if __name__ == "__main__":
    main()
