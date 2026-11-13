#!/usr/bin/env python3
"""Build the encrypted One Body GitHub Pages site.

Reads the team password from ONEBODY_SITE_PASSWORD, or from
/home/box/agent-data/flo/onebody-2026-11-26-password.txt.
Never prints the password. Writes only public/encrypted files to site/ and docs/.
Raw PDFs in charts/ are not copied in the clear.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from base64 import b64encode
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERS = 600_000
KEYLEN = 32
SALT_LEN = 16

ROOT = Path(__file__).resolve().parent
CHARTS = ROOT / "charts"
SRC = ROOT / "src"
VENDOR_SRC = ROOT / "vendor"
ICONS_SRC = ROOT / "icons"
OUT = ROOT / "site"
DOCS = ROOT / "docs"
SALT_PATH = ROOT / "salt.bin"
PASSWORD_FILE = Path("/home/box/agent-data/flo/onebody-2026-11-26-password.txt")
KEYNAME = "ob-k"


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def get_password() -> bytes:
    if "ONEBODY_SITE_PASSWORD" in os.environ and os.environ["ONEBODY_SITE_PASSWORD"].strip():
        pw = os.environ["ONEBODY_SITE_PASSWORD"].strip()
    elif PASSWORD_FILE.is_file():
        pw = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    else:
        die("ONEBODY_SITE_PASSWORD is not set and password file is missing")
    if not pw:
        die("password is empty")
    return pw.encode("utf-8")


def get_salt() -> bytes:
    if SALT_PATH.exists():
        salt = SALT_PATH.read_bytes()
        if len(salt) != SALT_LEN:
            die(f"salt.bin must be {SALT_LEN} bytes")
        return salt
    salt = os.urandom(SALT_LEN)
    SALT_PATH.write_bytes(salt)
    os.chmod(SALT_PATH, 0o600)
    return salt


def derive_key(password: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, ITERS, dklen=KEYLEN)


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    iv = os.urandom(12)
    return iv + AESGCM(key).encrypt(iv, plaintext, None)


def load_songs() -> dict:
    path = ROOT / "songs.json"
    if not path.is_file():
        die("songs.json is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def iter_chart_entries(songs: dict):
    for s in songs["songs"]:
        if s.get("chart"):
            yield s["chart"]
        for ch in s.get("charts") or []:
            yield ch
        for sub in s.get("songs") or []:
            if sub.get("chart"):
                yield sub["chart"]
            for ch in sub.get("charts") or []:
                yield ch


def is_pdf(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        return path.read_bytes()[:4] == b"%PDF"
    except OSError:
        return False


def mark_present(songs: dict) -> None:
    """Flag which referenced files exist as real PDFs, without inventing charts."""
    for ch in iter_chart_entries(songs):
        fn = ch.get("file")
        ch["present"] = bool(fn and is_pdf(CHARTS / fn))


def client_payload(songs: dict) -> dict:
    """Strip internal match notes before encrypting into the app."""

    def clean_chart(ch: dict | None) -> dict | None:
        if not ch:
            return None
        out = {
            "file": ch.get("file"),
            "kind": ch.get("kind", "chord"),
            "label": ch.get("label"),
            "present": bool(ch.get("present")),
        }
        return out

    def clean_yt(yt):
        if not yt:
            return None
        if isinstance(yt, dict):
            return yt.get("id")
        return yt

    def clean_song(s: dict, keep_subs: bool = True) -> dict:
        out = {
            "n": s.get("n"),
            "set": s.get("set"),
            "setLabel": s.get("setLabel"),
            "title": s.get("title"),
            "key": s.get("key"),
            "artist": s.get("artist"),
            "songwriter": s.get("songwriter"),
            "note": s.get("note"),
            "medley": bool(s.get("medley")),
            "original": bool(s.get("original")),
            "youtube": clean_yt(s.get("youtube")),
        }
        if s.get("chart"):
            out["chart"] = clean_chart(s["chart"])
        if s.get("charts"):
            out["charts"] = [clean_chart(c) for c in s["charts"]]
        if keep_subs and s.get("songs"):
            out["songs"] = [clean_song(sub, keep_subs=False) for sub in s["songs"]]
        # drop Nones
        return {k: v for k, v in out.items() if v is not None and v is not False}

    ev = songs["event"]
    return {
        "version": songs["version"],
        "event": ev,
        "songs": [clean_song(s) for s in songs["songs"]],
    }


def build_songs_js(songs: dict) -> str:
    payload = client_payload(songs)
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return "(typeof window !== \"undefined\" ? window : self).OB_SET = " + body + ";\n"


def build_inner_html(songs_js: str) -> bytes:
    tpl = (SRC / "inner.html.tpl").read_text(encoding="utf-8")
    css = (SRC / "app.css").read_text(encoding="utf-8")
    appjs = (SRC / "app.js").read_text(encoding="utf-8")
    html = (
        tpl.replace("__CSS__", css)
        .replace("__SONGS__", songs_js)
        .replace("__APPJS__", appjs)
    )
    return html.encode("utf-8")


def gate_html(salt_b64: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>One Body</title>
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#1e3a32">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="One Body">
<link rel="apple-touch-icon" href="icons/icon-180.png">
<link rel="icon" type="image/png" href="icons/icon-192.png">
<style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3f1ea;color:#1d2330;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
form{{background:#fff;border:1px solid #e2ddd2;border-radius:18px;padding:24px;width:min(92vw,360px);box-shadow:0 6px 24px rgba(30,58,50,.08)}}
h1{{margin:0 0 4px;font:650 22px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#1e3a32}}
p{{margin:0 0 14px;color:#5e6675;font-size:14px}}
input[type=password]{{width:100%;box-sizing:border-box;font-size:17px;padding:11px 12px;border:1px solid #e2ddd2;border-radius:10px;background:#f3f1ea}}
button{{margin-top:12px;width:100%;font-size:16px;padding:11px;border:0;border-radius:999px;background:#1e3a32;color:#fff}}
label{{display:flex;gap:8px;align-items:center;font-size:13.5px;color:#5e6675;margin-top:10px}}
.err{{color:#b2463b;font-size:13.5px;min-height:18px;margin-top:8px}}
@media (prefers-color-scheme:dark){{
body{{background:#0f1412;color:#eef1f5}}
form{{background:#18211e;border-color:#28342f;box-shadow:none}}
h1{{color:#eef1f5}}p,label{{color:#a3acba}}
input[type=password]{{background:#0f1412;border-color:#28342f;color:#eef1f5}}
button{{background:#b7d4c6;color:#18211e}}
}}
</style></head>
<body>
<form id="f" autocomplete="on">
<h1>One Body</h1>
<p>Private. Enter the password to open.</p>
<input type="text" name="username" value="onebody" autocomplete="username" hidden>
<input id="pw" type="password" autocomplete="current-password" placeholder="Password" required autofocus>
<label><input id="rem" type="checkbox" checked> Remember on this device</label>
<button id="go">Open</button>
<div class="err" id="err"></div>
</form>
<script>
const SALT="{salt_b64}",IT=600000,KEYNAME="{KEYNAME}";
const b64=u=>btoa(String.fromCharCode(...new Uint8Array(u))),ub=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function open_(raw){{const key=await crypto.subtle.importKey("raw",ub(raw),"AES-GCM",false,["decrypt"]);
  const r=await fetch("app.enc",{{cache:"no-cache"}});const b=new Uint8Array(await r.arrayBuffer());
  const html=new TextDecoder().decode(await crypto.subtle.decrypt({{name:"AES-GCM",iv:b.slice(0,12)}},key,b.slice(12)));
  sessionStorage.setItem(KEYNAME,raw);document.open();document.write(html);document.close();}}
async function derive(pw){{const k=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveBits"]);
  return b64(await crypto.subtle.deriveBits({{name:"PBKDF2",hash:"SHA-256",salt:ub(SALT),iterations:IT}},k,256));}}
const saved=sessionStorage.getItem(KEYNAME)||localStorage.getItem(KEYNAME);
if(saved)open_(saved).catch(()=>{{localStorage.removeItem(KEYNAME);sessionStorage.removeItem(KEYNAME)}});
document.getElementById("f").onsubmit=async e=>{{e.preventDefault();const err=document.getElementById("err");err.textContent="Unlocking…";
  try{{const rem=document.getElementById("rem").checked;const raw=await derive(document.getElementById("pw").value.trim());if(rem)localStorage.setItem(KEYNAME,raw);try{{await open_(raw)}}catch(z){{localStorage.removeItem(KEYNAME);throw z}}}}
  catch(x){{err.textContent="Wrong password. Try again."}}}};
if("serviceWorker" in navigator && location.protocol.startsWith("http"))navigator.serviceWorker.register("sw.js").catch(()=>{{}});
</script>
</body></html>
"""


def sw_js(version: str) -> str:
    return """// Network-first for the gate and app.enc; runtime-cache everything else same-origin.
// Encrypted PDFs may be cached; plaintext charts are never stored in this repo.
const C="onebody-__VERSION__";
self.addEventListener("install",e=>{self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const r=e.request; const u=new URL(r.url);
  if(r.method!=="GET"||u.origin!==location.origin)return;
  const fresh=u.pathname.endsWith("app.enc")||u.pathname.endsWith("index.html")||r.mode==="navigate";
  if(fresh){
    e.respondWith(fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(r,cp))}return res}).catch(()=>caches.match(r)));
  }else{
    e.respondWith(caches.match(r).then(hit=>hit||fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(r,cp))}return res})));
  }
});
""".replace("__VERSION__", version)


MANIFEST = """{
  "name": "One Body Worship Night",
  "short_name": "One Body",
  "description": "Set charts for the Flourish One Body worship night",
  "start_url": "./index.html",
  "scope": "./",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#1e3a32",
  "theme_color": "#1e3a32",
  "icons": [
    { "src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
"""

ROBOTS = "User-agent: *\nDisallow: /\n"


def publish(staging: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for p in dest.iterdir():
        if p.name == ".git":
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    for p in staging.iterdir():
        target = dest / p.name
        if p.is_dir():
            shutil.copytree(p, target)
        else:
            shutil.copy2(p, target)


def encrypt_charts(key: bytes, songs: dict, dest_files: Path) -> int:
    n = 0
    seen: set[str] = set()
    for ch in iter_chart_entries(songs):
        fn = ch.get("file")
        if not fn or fn in seen:
            continue
        seen.add(fn)
        src = CHARTS / fn
        if not src.is_file():
            continue
        data = src.read_bytes()
        if not data.startswith(b"%PDF"):
            print(f"  warning: {fn} is not a PDF (skipped; will show as chart needed)", file=sys.stderr)
            ch["present"] = False
            continue
        (dest_files / (fn + ".enc")).write_bytes(encrypt(key, data))
        n += 1
    return n


def main() -> None:
    password = get_password()
    salt = get_salt()
    key = derive_key(password, salt)
    del password

    songs = load_songs()
    mark_present(songs)
    version = songs.get("version") or die("songs.json is missing version")

    if not (VENDOR_SRC / "pdfjs").is_dir():
        die("vendor/pdfjs is missing")
    if not (ICONS_SRC / "icon-192.png").is_file():
        die("icons are missing")

    staging = Path(tempfile.mkdtemp(prefix="onebody-build-"))
    n_pdf = 0
    try:
        (staging / "files").mkdir()
        (staging / "icons").mkdir()

        inner = build_inner_html(build_songs_js(songs))
        (staging / "app.enc").write_bytes(encrypt(key, inner))

        n_pdf = encrypt_charts(key, songs, staging / "files")

        salt_b64 = b64encode(salt).decode("ascii")
        (staging / "index.html").write_text(gate_html(salt_b64), encoding="utf-8")
        (staging / "sw.js").write_text(sw_js(version), encoding="utf-8")
        (staging / "manifest.webmanifest").write_text(MANIFEST, encoding="utf-8")
        (staging / "robots.txt").write_text(ROBOTS, encoding="utf-8")
        (staging / ".nojekyll").write_text("")

        for icon in ICONS_SRC.glob("*"):
            if icon.is_file():
                shutil.copy2(icon, staging / "icons" / icon.name)

        shutil.copytree(VENDOR_SRC, staging / "vendor")

        publish(staging, OUT)
        publish(staging, DOCS)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    missing = [ch.get("file") for ch in iter_chart_entries(songs) if ch.get("file") and not ch.get("present")]
    print(f"Built site at {OUT} (also synced to {DOCS})")
    print(f"  version: {version}")
    print(f"  app.enc bytes: {(OUT / 'app.enc').stat().st_size}")
    print(f"  encrypted chart/lyric PDFs: {n_pdf}")
    if missing:
        print(f"  chart needed ({len(missing)}):")
        for fn in missing:
            print(f"    - {fn}")
    print("  (password and key material not printed)")


if __name__ == "__main__":
    main()
