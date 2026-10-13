"""Print a chapter of the lecture notes (a built Decker page) to an A4 PDF.

All collapsible answers (<details>) are expanded. Run after `decker html`:

    python3 tools/notes_pdf.py notes/01-introduction-page.html notes/01-introduction-notes.pdf

The first argument is the page's path below public/, the second the output file.
Needs: Python with Playwright and its Chromium (`pip install playwright`, `playwright install chromium`).
"""
import functools
import http.server
import sys
import threading

from playwright.sync_api import sync_playwright

page_path, out = sys.argv[1], sys.argv[2]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


handler = functools.partial(QuietHandler, directory="public")
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}/{page_path}"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")
    page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    page.wait_for_timeout(1500)  # let math and fonts settle
    page.pdf(path=out, format="A4", print_background=True,
             margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
    browser.close()
server.shutdown()
print("written", out)
