#!/usr/bin/env python3
"""BLOCK JUU - Y8 build scripti. index.html (kaynak) -> y8/index.html + three.min.js -> block-juu-y8.zip
Kullanım: python3 build-y8.py   (kaynak index.html DEĞİŞTİRİLMEZ)"""
import os, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'index.html')
OUT_DIR = os.path.join(ROOT, 'y8')
ZIP = os.path.join(ROOT, 'block-juu-y8.zip')

with open(SRC, encoding='utf-8', newline='') as f:
    html = f.read()

def rep(old, new, label):
    n = html.count(old)
    if n != 1:
        sys.exit('HATA: "%s" için hedef %d kez bulundu (1 bekleniyordu)' % (label, n))
    return html.replace(old, new)

# 1) three.js yerel + Y8 SDK
html = rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
           '<script src="https://cdn.y8.com/minimal-sdk/2-0/y8.min.js" async></script>\n<script src="three.min.js"></script>',
           'three.js script')

# 2) PWA metaları, manifest enjeksiyonu, otomatik tam ekran, debug kancası
html = rep('<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="BLOCK JUU"><meta name="theme-color" content="#1B2440">\n',
           '', 'PWA metalari')
html = rep("if (!/claude\\.ai|claudeusercontent|anthropic/.test(location.host) && location.protocol.startsWith('http')) { const l = document.createElement('link'); l.rel = 'manifest';",
           "if (false) { const l = document.createElement('link'); l.rel = 'manifest';", 'manifest enjeksiyonu')
html = rep("if (isTouchDev) { addEventListener('touchend', goFull, true); addEventListener('click', goFull, true); }\n",
           '', 'otomatik tam ekran')
html = rep("if (location.hash === '#debug') window.TR = ", "if (false) window.TR = ", 'debug kancasi')

# 3) Y8 köprüsü
Y8_BRIDGE = r"""
/* ---------- Y8 SDK köprüsü (portal derlemesi) ----------
   SDK yüklenmezse / hata verirse oyun tamamen oynanabilir kalır. Reklam yalnızca gerçek Y8 ödüllü reklamıdır. */
const Y8_APP_ID = '6ac1033ca654af47f466d448';   // Y8 geliştirici portalı → SDK Başlatma → Uygulama Kimliği
const Y8_GAME_ID = '285893';  // Y8 geliştirici portalı → SDK Başlatma → Oyun Kimliği (reklamlar için)
const Y8 = {
  sdk: null, ok: false, adMute: false, loaded: false, asked: false, cloudData: null, synced: false, started: false,
  applyAudio() { try { if (typeof SFX === 'undefined' || !SFX.ctx) return; if (this.adMute) SFX.ctx.suspend(); else SFX.ctx.resume(); } catch (e) {} },
  mute(m) { this.adMute = m; this.applyAudio(); },
  norm(v) { // loadData: söz / düz değer / {data} / {value}; JSON metni olabilir
    try {
      if (v && typeof v === 'object' && !(v.v === 1 || v.v === 2)) { if ('data' in v) v = v.data; else if ('value' in v) v = v.value; }
      if (typeof v === 'string') v = v ? JSON.parse(v) : null;
      if (v && typeof v === 'object' && !(v.v === 1 || v.v === 2) && ('data' in v || 'value' in v)) { v = 'data' in v ? v.data : v.value; if (typeof v === 'string') v = JSON.parse(v); }
      return v && typeof v === 'object' ? v : null;
    } catch (e) { return null; }
  },
  start() {
    if (this.started) return; this.started = true;
    try {
      const y8 = window.y8; if (!y8 || !y8.sdk) { this.started = false; return; }
      const sdk = y8.sdk();
      sdk.init({ appId: Y8_APP_ID, autoLogin: true }, { gameId: Y8_GAME_ID, preloadAdBreaks: 'auto', sound: 'on', onReady: () => {} });
      this.sdk = sdk; this.ok = true;
      // bulut kaydı yalnızca Y8 hesabıyla giriş yapılınca (otomatik giriş veya sonradan)
      try { sdk.onAuth((user, err) => { if (user && !err && !Y8.asked) { Y8.asked = true; Y8.loadSave(); } }); } catch (e) {}
    } catch (e) { this.ok = false; }
  },
  loadSave() { // bulut kaydı: sonucu bekle, Save hazır olunca tick içinde uygula
    const done = v => { Y8.cloudData = Y8.norm(v); Y8.loaded = true; };
    try { const r = this.sdk.loadData({ key: SAVE_KEY }); if (r && typeof r.then === 'function') r.then(done, () => done(null)); else done(r); } catch (e) { done(null); }
  },
  tick() { // ana döngüden: Save/cloud/game tanımlandıktan sonra tembel eşitleme (TDZ güvenli)
    if (this.synced || !this.ok || !this.loaded) return; this.synced = true;
    try {
      const d = this.cloudData, sdk = this.sdk;
      if (d && (d.v === 1 || d.v === 2) && (d.savedAt || 0) > (Save.loadedAt || 0) && game.mode === 'land') Save.apply(d);
      cloud = { set: x => { try { sdk.saveData({ key: SAVE_KEY, value: JSON.stringify(x), retries: true }); } catch (e) {} return Promise.resolve(); } };
      if (!d) markDirty();
    } catch (e) {}
  },
};
window.addEventListener('y8sdk.ready', () => Y8.start(), { once: true });
if (window.y8 && window.y8.emitReadyEvent) window.y8.emitReadyEvent(); // SDK önceden yüklendiyse
"""
html = rep("'use strict';\n/* ==================================================================\n   Tuzlu Rüzgâr",
           "'use strict';" + Y8_BRIDGE + "/* ==================================================================\n   Tuzlu Rüzgâr", 'Y8 koprusu')
html = rep('Save.update(rdt);', 'Save.update(rdt); Y8.tick();', 'Y8.tick cagrisi')

# 4) Sahte geri sayım reklamı yerine gerçek Y8 ödüllü reklamı
OLD_SHOW = """  show(done, sec) { // done(true) = reklam sonuna kadar izlendi; sec = reklam uzunluğu
    const el = $('#adPlay'), bar = $('#adBar'), n = $('#adN'), T = sec || 5, t0 = Date.now(); let fin = false; el.hidden = false; Ads.playing = true; n.textContent = T; bar.style.width = '0%';
    const tickAd = () => { if (fin) return; const el2 = (Date.now() - t0) / 1000, left = Math.max(0, Math.ceil(T - el2)); n.textContent = left; bar.style.width = Math.min(100, el2 / T * 100) + '%'; if (el2 >= T) { fin = true; clearInterval(iv); document.removeEventListener('visibilitychange', tickAd); el.hidden = true; Ads.playing = false; try { done(true); } catch (e) { console.error(e); } } };
    const iv = setInterval(tickAd, 250); document.addEventListener('visibilitychange', tickAd);
  },
"""
NEW_SHOW = """  show(done, sec) { // Y8 ödüllü reklam: done(true) yalnızca adViewed ile ve en fazla bir kez çağrılır
    const NOVID = 'No video available right now · try again later';
    const sdk = Y8.ok && Y8_GAME_ID ? Y8.sdk : null; if (!sdk || Ads.playing) { if (!sdk) toast(NOVID); return; }
    let fin = false, rewarded = false, dismissed = false, safe = 0;
    const cleanup = () => { if (fin) return; fin = true; clearTimeout(safe); Ads.playing = false; Y8.mute(false); if (!rewarded && !dismissed) toast(NOVID); };
    const grant = () => { if (rewarded) return; rewarded = true; try { done(true); } catch (e) { console.error(e); } };
    safe = setTimeout(cleanup, 60000); // güvenlik: Ads.playing asla takılı kalmasın
    try {
      const p = sdk.showAd({ type: 'reward', name: 'reward-ad',
        beforeAd: () => { Ads.playing = true; Y8.mute(true); }, // oyunu duraklat + sesi kapat
        afterAd: () => { Ads.playing = false; Y8.mute(false); },
        beforeReward: showAdFn => { try { showAdFn(); } catch (e) { cleanup(); } },
        adViewed: () => grant(),
        adDismissed: () => { dismissed = true; },
        adBreakDone: () => cleanup() });
      if (p && typeof p.catch === 'function') p.catch(() => cleanup());
    } catch (e) { cleanup(); }
  },
"""
html = rep(OLD_SHOW, NEW_SHOW, 'AdsProvider.show')

# Çıktı
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, 'index.html'), 'w', encoding='utf-8', newline='') as f:
    f.write(html)
shutil.copyfile(os.path.join(ROOT, 'three.min.js'), os.path.join(OUT_DIR, 'three.min.js'))
if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ('index.html', 'three.min.js'):
        z.write(os.path.join(OUT_DIR, name), name)
print('Tamam: y8/index.html, y8/three.min.js, block-juu-y8.zip')
