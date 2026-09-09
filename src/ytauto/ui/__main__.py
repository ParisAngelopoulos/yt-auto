"""python -m ytauto.ui"""

import argparse

from .server import serve

parser = argparse.ArgumentParser(description="Bedieningspagina voor de videopipeline")
parser.add_argument("--port", type=int, default=8765)
parser.add_argument("--no-browser", action="store_true")
args = parser.parse_args()

serve(port=args.port, open_browser=not args.no_browser)
