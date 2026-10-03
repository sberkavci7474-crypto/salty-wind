#!/usr/bin/env python3
"""BLOCK JUU - Poki build scripti. index.html (kaynak) -> poki/index.html + three.min.js -> block-juu-poki.zip
Kullanım: python3 build-poki.py   (kaynak index.html DEĞİŞTİRİLMEZ)"""
import os, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'index.html')
OUT_DIR = os.path.join(ROOT, 'poki')
ZIP = os.path.join(ROOT, 'block-juu-poki.zip')

with open(SRC, encoding='utf-8', newline='') as f:
    html = f.read()

def rep(old, new, label):
    n = html.count(old)
    if n != 1:
        sys.exit('HATA: "%s" için hedef %d kez bulundu (1 bekleniyordu)' % (label, n))
    return html.replace(old, new)

# 1) three.js yerel + Poki SDK (senkron: oyun betiği çalışırken PokiSDK hazır olsun; async DEĞİL)
html = rep('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
           '<script src="https://game-cdn.poki.com/scripts/v2/poki-sdk.js"></script>\n<script src="three.min.js"></script>',
           'three.js script')

# 2) PWA metaları, manifest enjeksiyonu, otomatik tam ekran, debug kancası
html = rep('<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="BLOCK JUU"><meta name="theme-color" content="#1B2440">\n',
           '', 'PWA metalari')
html = rep("if (!/claude\\.ai|claudeusercontent|anthropic/.test(location.host) && location.protocol.startsWith('http')) { const l = document.createElement('link'); l.rel = 'manifest';",
           "if (false) { const l = document.createElement('link'); l.rel = 'manifest';", 'manifest enjeksiyonu')
html = rep("if (isTouchDev) { addEventListener('touchend', goFull, true); addEventListener('click', goFull, true); }\n",
           '', 'otomatik tam ekran')
html = rep("if (location.hash === '#debug') window.TR = ", "if (false) window.TR = ", 'debug kancasi')

# 3) Poki köprüsü
POKI_BRIDGE = r"""
/* ---------- Poki SDK köprüsü (portal derlemesi) ----------
   SDK yüklenmezse / reklam engelleyici varsa / hata verirse oyun tamamen oynanabilir kalır.
   Her SDK çağrısı window.PokiSDK varlığı + try/catch ile korunur. Bulut kaydı yok (yalnızca localStorage). */
const Poki = {
  ok: false, loaded: false, active: null, adMute: false, pend: false,
  sdk() { return window.PokiSDK || null; },
  applyAudio() { try { if (typeof SFX === 'undefined' || !SFX.ctx) return; if (this.adMute) SFX.ctx.suspend(); else SFX.ctx.resume(); } catch (e) {} },
  mute(m) { this.adMute = m; this.applyAudio(); },
  stop() { // reklamdan önce: oynanış durdu bildirimi (tick sonradan gameplayStart'ı geri çağırır)
    if (this.active) { this.active = false; try { const S = this.sdk(); S && S.gameplayStop(); } catch (e) {} }
  },
  tick() { // ana döngüden: ilk turda gameLoadingFinished, sonra yalnızca değişimde gameplayStart/Stop
    const S = this.sdk(); if (!S || !this.ok) return;
    if (!this.loaded) { this.loaded = true; try { S.gameLoadingFinished(); } catch (e) {} }
    const act = !panelOpen() && P.state !== 'dead' && !rotBlock && !document.hidden && !Ads.playing;
    if (act !== this.active) { this.active = act; try { act ? S.gameplayStart() : S.gameplayStop(); } catch (e) {} }
  },
  // Ödüllü reklam: done(true) yalnızca başarıyla izlenince ve en fazla bir kez çağrılır
  rewarded(done) {
    const NOVID = 'No video available right now · try again later';
    const S = this.sdk(); if (!S || Ads.playing) { if (!S) toast(NOVID); return; }
    let fin = false, safe = 0;
    const cleanup = ok => {
      if (fin) return; fin = true; clearTimeout(safe); Ads.playing = false; Poki.mute(false);
      if (ok) { try { done(true); } catch (e) { console.error(e); } } else toast(NOVID);
    };
    safe = setTimeout(() => cleanup(false), 60000); // güvenlik: Ads.playing asla takılı kalmasın
    this.stop();
    try {
      S.rewardedBreak(() => { Ads.playing = true; Poki.mute(true); }).then(ok => cleanup(!!ok), () => cleanup(false));
    } catch (e) { cleanup(false); }
  },
  // Ticari (geçiş) reklam: ölüm sonrası canlanmadan önce; fn tam bir kez çalışır, SDK yoksa/hata verirse hemen
  breakThen(fn) {
    if (this.pend) return; this.pend = true;
    let fin = false, safe = 0;
    const go = () => {
      if (fin) return; fin = true; clearTimeout(safe); Ads.playing = false; Poki.mute(false); Poki.pend = false;
      try { if (P.state === 'dead') fn(); } catch (e) { console.error(e); } // arada ödüllü canlanma olduysa tekrar canlandırma
    };
    const S = this.sdk(); if (!S) { go(); return; }
    safe = setTimeout(go, 60000);
    this.stop();
    try {
      S.commercialBreak(() => { Ads.playing = true; Poki.mute(true); }).then(go, go);
    } catch (e) { go(); }
  },
  ready: (async () => {
    await null; // Poki sabitinin başlatılması bitsin (TDZ): senkron yol da Poki.ok'u güvenle yazsın
    try { if (window.PokiSDK) await window.PokiSDK.init(); } catch (e) { /* reklam engelleyici: oyun devam eder, reklamlar yok */ }
    Poki.ok = true;
  })(),
};
"""
html = rep("'use strict';\n/* ==================================================================\n   Tuzlu Rüzgâr",
           "'use strict';" + POKI_BRIDGE + "/* ==================================================================\n   Tuzlu Rüzgâr", 'Poki koprusu')
html = rep('Save.update(rdt);', 'Save.update(rdt); Poki.tick();', 'Poki.tick cagrisi')
# reklam/dönme engeli sırasında da tick çalışsın: gameplayStop doğru zamanda gitsin
html = rep('if (rotBlock || Ads.playing) { last = now;', 'if (rotBlock || Ads.playing) { last = now; Poki.tick();', 'Poki.tick (duraklatma dali)')

# 4) Sahte geri sayım reklamı yerine gerçek Poki ödüllü reklamı
OLD_SHOW = """  show(done, sec) { // done(true) = reklam sonuna kadar izlendi; sec = reklam uzunluğu
    const el = $('#adPlay'), bar = $('#adBar'), n = $('#adN'), T = sec || 5, t0 = Date.now(); let fin = false; el.hidden = false; Ads.playing = true; n.textContent = T; bar.style.width = '0%';
    const tickAd = () => { if (fin) return; const el2 = (Date.now() - t0) / 1000, left = Math.max(0, Math.ceil(T - el2)); n.textContent = left; bar.style.width = Math.min(100, el2 / T * 100) + '%'; if (el2 >= T) { fin = true; clearInterval(iv); document.removeEventListener('visibilitychange', tickAd); el.hidden = true; Ads.playing = false; try { done(true); } catch (e) { console.error(e); } } };
    const iv = setInterval(tickAd, 250); document.addEventListener('visibilitychange', tickAd);
  },
"""
NEW_SHOW = """  show(done, sec) { // Poki ödüllü reklam: done(true) yalnızca başarıyla izlenince ve en fazla bir kez çağrılır
    Poki.rewarded(done);
  },
"""
html = rep(OLD_SHOW, NEW_SHOW, 'AdsProvider.show')

# 5) Ölüm sonrası canlanma: önce ticari reklam arası (ödüllü canlanma değil)
html = rep("if (P.deadT <= 0) { if (Board.active) { if (!Board.over) Board.lose(); } else respawn(); } return; }",
           "if (P.deadT <= 0) { if (Board.active) { if (!Board.over) Board.lose(); } else Poki.breakThen(respawn); } return; }",
           'olum -> canlanma ticari reklam')

# 6) Ok tuşları sayfayı kaydırmasın (Poki iframe gereksinimi); boşluk zaten engelli
html = rep("addEventListener('keydown', e => {\n  const k = keyOf(e); if (e.repeat",
           "addEventListener('keydown', e => {\n  const k = keyOf(e); if (k.startsWith('arrow')) e.preventDefault(); if (e.repeat",
           'ok tuslari preventDefault')

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
print('Tamam: poki/index.html, poki/three.min.js, block-juu-poki.zip')
