<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>One Body Worship Night</title>
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#1e3a32">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="One Body">
<link rel="apple-touch-icon" href="icons/icon-180.png">
<link rel="icon" type="image/png" href="icons/icon-192.png">
<link rel="manifest" href="manifest.webmanifest">
<style>
__CSS__
</style>
</head>
<body>
<header class="top">
  <div class="brand"><img src="icons/icon-192.png" alt="" width="40" height="40"><div><h1>One Body</h1><p id="event-sub"></p></div></div>
  <p class="date" id="event-date"></p>
</header>
<div id="meta" class="meta" hidden></div>
<main id="songs" aria-live="polite"></main>
<footer class="foot"><p>For the One Body / Flourish team only. Please don't share these files.</p><p id="ver"></p></footer>

<div id="viewer" class="viewer" hidden role="dialog" aria-modal="true" aria-labelledby="v-title">
  <div class="v-bar">
    <button class="v-btn" id="v-close" aria-label="Close">✕</button>
    <div class="v-titles"><strong id="v-title"></strong><span id="v-sub"></span></div>
    <button class="v-btn" id="v-out" aria-label="Zoom out">−</button>
    <button class="v-btn v-fit" id="v-fit" aria-label="Fit width">Fit</button>
    <button class="v-btn" id="v-in" aria-label="Zoom in">+</button>
  </div>
  <div class="v-scroll" id="v-scroll"><div class="v-pages" id="v-pages"></div></div>
  <div class="v-status" id="v-status"></div>
</div>
<script>
__SONGS__
</script>
<script type="module">
__APPJS__
</script>
</body>
</html>
