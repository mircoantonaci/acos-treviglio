#!/usr/bin/env python3
"""
A.S.D. A.C.O.S. Treviglio Calcio 1971 — CLI Project Manager (acos-cli.py)
Fondata il 18 Agosto 1971 — Treviglio (BG)

Comandi disponibili:
  python3 acos-cli.py build      Rigenera il sito WordPress locale, i file HTML e aggiorna GitHub Pages
  python3 acos-cli.py deploy     Sincronizza e pubblica su GitHub Pages (https://mircoantonaci.github.io/acos-treviglio/)
  python3 acos-cli.py status     Verifica lo stato di file locali, server Local.app e repository GitHub Pages
  python3 acos-cli.py export     Crea il pacchetto ZIP completo pronto per il deploy (acos-studio/dist/)
"""

import argparse
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path("/Users/antonacim/Local Sites/calcio")
STUDIO_DIR = PROJECT_ROOT / "acos-studio"
DIST_DIR = STUDIO_DIR / "dist"
GH_PAGES_DIR = STUDIO_DIR / "gh-pages"

GENERATOR_SCRIPT = STUDIO_DIR / "build_acos_cinematic.py"
INDEX_HTML = STUDIO_DIR / "index.html"
STANDALONE_HTML = STUDIO_DIR / "simulazione_acos.html"
LIVE_TPL_FILE = PROJECT_ROOT / "app" / "public" / "wp-content" / "mu-plugins" / "acos-cinematic-template.html"

GH_PAGES_URL = "https://mircoantonaci.github.io/acos-treviglio/"


def cmd_build(args):
    print("==================================================================")
    print(" 🔨 BUILD — A.S.D. A.C.O.S. Treviglio Calcio 1971 (v5.0)")
    print("==================================================================")
    if not GENERATOR_SCRIPT.exists():
        print(f"[ERRORE] Generatore non trovato in {GENERATOR_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    res = subprocess.run(
        [sys.executable, str(GENERATOR_SCRIPT)],
        cwd=str(STUDIO_DIR),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print("[ERRORE] Fallita esecuzione di build_acos_cinematic.py:", file=sys.stderr)
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

    print(res.stdout.strip())


def cmd_deploy(args):
    print("==================================================================")
    print(" 🚀 DEPLOY — Pubblicazione GitHub Pages (mircoantonaci/acos-treviglio)")
    print("==================================================================")
    if not (GH_PAGES_DIR / ".git").exists():
        print(f"[ERRORE] Repository Git non trovato in {GH_PAGES_DIR}", file=sys.stderr)
        sys.exit(1)

    if STANDALONE_HTML.exists():
        shutil.copy2(STANDALONE_HTML, GH_PAGES_DIR / "index.html")

    status = subprocess.run(
        ["git", "-C", str(GH_PAGES_DIR), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        subprocess.run(["git", "-C", str(GH_PAGES_DIR), "add", "index.html"], check=True)
        subprocess.run(
            ["git", "-C", str(GH_PAGES_DIR), "commit", "-m", "Aggiornamento portale A.C.O.S. Treviglio Calcio 1971"],
            check=True,
        )

    push = subprocess.run(["git", "-C", str(GH_PAGES_DIR), "push", "origin", "main"])
    if push.returncode == 0:
        print(f"[✓] Online 24/7 su: {GH_PAGES_URL}")
    else:
        sys.exit(push.returncode)


def cmd_status(args):
    print("==================================================================")
    print(" 📊 STATUS — A.S.D. A.C.O.S. Treviglio Calcio 1971")
    print("==================================================================")
    for label, path in [
        ("Generatore Master", GENERATOR_SCRIPT),
        ("Sito Statico (index.html)", INDEX_HTML),
        ("Simulazione Standalone", STANDALONE_HTML),
        ("Template WordPress Local.app", LIVE_TPL_FILE),
        ("Repository GitHub Pages", GH_PAGES_DIR / "index.html"),
    ]:
        if path.exists():
            print(f"[✓] {label:30s}: {path} ({path.stat().st_size:,} bytes)")
        else:
            print(f"[✗] {label:30s}: NON TROVATO ({path})")

    for label, url in [
        ("Local.app (127.0.0.1:10013)", "http://127.0.0.1:10013/"),
        ("GitHub Pages H24", GH_PAGES_URL),
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ACOS-CLI/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[✓] {label:30s}: HTTP {resp.status} ({url})")
        except Exception as exc:
            print(f"[!] {label:30s}: Non raggiungibile ({exc})")


def cmd_export(args):
    print("==================================================================")
    print(" 📦 EXPORT — Creazione Pacchetto ZIP Deploy")
    print("==================================================================")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_out = DIST_DIR / "acos-treviglio-deploy.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        if INDEX_HTML.exists():
            zf.write(INDEX_HTML, "acos-treviglio/index.html")
        assets_dir = STUDIO_DIR / "assets"
        if assets_dir.exists():
            for f in sorted(assets_dir.glob("*.*")):
                zf.write(f, f"acos-treviglio/assets/{f.name}")
    print(f"[✓] Creato pacchetto deploy: {zip_out} ({zip_out.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(description="CLI Manager A.S.D. A.C.O.S. Treviglio Calcio 1971")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("deploy")
    sub.add_parser("status")
    sub.add_parser("export")
    args = parser.parse_args()

    if args.cmd == "build":
        cmd_build(args)
    elif args.cmd == "deploy":
        cmd_deploy(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "export":
        cmd_export(args)


if __name__ == "__main__":
    main()
