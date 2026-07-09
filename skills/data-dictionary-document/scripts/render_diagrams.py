#!/usr/bin/env python3
"""Render every Mermaid (.mmd) file in a directory to a .png image.

Usage:
    python render_diagrams.py <diagrams-dir> [--renderer auto|mmdc|kroki|npx] [--scale 2]

Renderers, tried in this order when --renderer is "auto" (the default):
  1. mmdc   local Mermaid CLI, used when it is already on PATH (fully offline)
  2. kroki  https://kroki.io web service — NOTE: this sends the diagram text
            (component names, entity names) to a third-party service. Do not
            use it for confidential codebases; install mermaid-cli instead
            (npm install -g @mermaid-js/mermaid-cli).
  3. npx    npx -y @mermaid-js/mermaid-cli — downloads the CLI plus a headless
            browser on first use; slow but works without a global install.

The .mmd source files stay next to the generated .png files so users can edit
a diagram and re-run this script. Exits non-zero when any diagram fails and
prints the renderer's error (usually a Mermaid syntax error) so the caller
can fix the .mmd file and re-run.
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

KROKI_URL = "https://kroki.io/mermaid/png"


def render_with_cli(cli_cmd, mmd_path, png_path, scale):
    cmd = cli_cmd + ["-i", mmd_path, "-o", png_path, "-s", str(scale),
                     "-b", "white", "--quiet"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not os.path.isfile(png_path):
        raise RuntimeError((result.stderr or result.stdout or "").strip()
                           or "mermaid CLI failed with no output")


def render_with_kroki(mmd_path, png_path):
    with open(mmd_path, encoding="utf-8") as f:
        source = f.read()
    request = urllib.request.Request(
        KROKI_URL, data=source.encode("utf-8"), method="POST",
        headers={"Content-Type": "text/plain",
                 # kroki.io sits behind Cloudflare, which rejects the default
                 # Python urllib user agent with HTTP 403 (error 1010)
                 "User-Agent": "Mozilla/5.0 (compatible; render-diagrams/1.0)"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"kroki.io returned HTTP {err.code}: {detail}") from err
    with open(png_path, "wb") as f:
        f.write(data)


def pick_renderers(choice):
    """Return an ordered list of (name, callable-factory) to try."""
    mmdc = shutil.which("mmdc")
    npx = shutil.which("npx")
    options = {}
    if mmdc:
        options["mmdc"] = [mmdc]
    if npx:
        options["npx"] = [npx, "-y", "@mermaid-js/mermaid-cli"]
    if choice == "auto":
        order = [name for name in ("mmdc", "kroki", "npx")
                 if name == "kroki" or name in options]
    elif choice == "kroki":
        order = ["kroki"]
    elif choice in options:
        order = [choice]
    else:
        sys.exit(f"Renderer '{choice}' is not available on this machine "
                 f"(command not found on PATH).")
    return order, options


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="folder containing .mmd files")
    parser.add_argument("--renderer", default="auto",
                        choices=["auto", "mmdc", "kroki", "npx"])
    parser.add_argument("--scale", type=int, default=2,
                        help="pixel scale for CLI renderers (default 2)")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        sys.exit(f"Not a directory: {args.directory}")
    mmd_files = sorted(f for f in os.listdir(args.directory)
                       if f.lower().endswith(".mmd"))
    if not mmd_files:
        sys.exit(f"No .mmd files found in {args.directory}")

    order, options = pick_renderers(args.renderer)
    failures = []
    kroki_used = False

    for name in mmd_files:
        mmd_path = os.path.join(args.directory, name)
        png_path = os.path.splitext(mmd_path)[0] + ".png"
        errors = []
        for renderer in order:
            try:
                if renderer == "kroki":
                    render_with_kroki(mmd_path, png_path)
                    kroki_used = True
                else:
                    render_with_cli(options[renderer], mmd_path, png_path,
                                    args.scale)
                print(f"OK   {name} -> {os.path.basename(png_path)} "
                      f"[{renderer}]")
                break
            except Exception as exc:  # try the next renderer
                errors.append(f"{renderer}: {exc}")
        else:
            failures.append((name, errors))
            print(f"FAIL {name}")

    if kroki_used:
        print("\nNote: kroki.io (a public web service) rendered some diagrams; "
              "the diagram text was sent over the network.")
    if failures:
        print("\nFAILED diagrams — fix the .mmd source and re-run:")
        for name, errors in failures:
            print(f"\n  {name}")
            for err in errors:
                print(f"    {err}")
        sys.exit(1)
    print(f"\nRendered {len(mmd_files)} diagram(s) successfully.")


if __name__ == "__main__":
    main()
