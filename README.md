# One Body Worship Night — Friday, November 13, 2026

Password-gated set site for Flourish / One Body, modeled on the music-droid/ucatholic encrypted static PWA (PBKDF2-SHA256 600k, AES-GCM, client-side unlock, vendored pdf.js).

The public GitHub repo and Pages site contain only the lock screen plus encrypted files. Raw chord/lyric PDFs and the team password are never committed.

The team password lives only at:

`/home/box/agent-data/flo/onebody-2026-11-13-password.txt`

Do not put the password in this repo, in chat, or in commit messages.

## Rebuild and redeploy after PDFs land in `charts/`

Drop chord PDFs using the filenames in `songs.json` (`chart.file` or `charts[].file`). Then, on the box:

```bash
cd /workspace/onebody-2026-11-13
./build.py
git add docs
git status   # confirm no raw PDFs, no password, no salt.bin
git commit -m "Rebuild One Body set site"
git push origin main
```

`build.py` reads the password from the file above (or from `ONEBODY_SITE_PASSWORD` if that env var is set). It encrypts the app and any referenced PDFs that exist into `site/`, then syncs `docs/` for GitHub Pages (`main` / `docs`).

Missing files are skipped and show as “chart needed” on the unlocked site. Justin’s originals currently use lyric PDFs labeled “Lyrics (chord chart coming)”:

- `charts/04-open-my-hearts-eyes-A-lyrics.pdf`
- `charts/08-the-potter-E-lyrics.pdf`

Lead and vocal charts are not published on this site (chord charts only).

GitHub repo: https://github.com/music-droid/onebody-2026-11-13

Pages URL: https://music-droid.github.io/onebody-2026-11-13/
