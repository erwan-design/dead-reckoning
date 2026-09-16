"""Battleship Duo — export vidéo d'une partie simulée.

Filme le jeu publié (?prod) dans Chrome, image par image, sur une horloge
virtuelle : chaque image avance le temps d'exactement 1/FPS, avec de vrais clics.

  1. servir le dossier du projet sur http://localhost:4620 (config « naval-keyart »)
  2. python3 tools/record-video.py --out /tmp/frames          (images PNG 1260 × 1860)
  3. ffmpeg -framerate 30 -i /tmp/frames/f%04d.png -c:v libx264 -preset slow -crf 16 \
            -pix_fmt yuv420p -movflags +faststart exports/battleship-duo-gameplay-1260x1860.mp4

Options : --theatre 0-3 (Morning, Squall, Night, Storm), --fps, --secs, --only 0,60,120 (test).
"""
import sys, os, json, time, base64, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import Chrome

ap = argparse.ArgumentParser()
ap.add_argument('--out', default='frames')
ap.add_argument('--only', default='')          # comma list of frame numbers to save (test mode)
ap.add_argument('--theatre', type=int, default=0)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--secs', type=float, default=10.0)
A = ap.parse_args()
FPS = A.fps; N = int(round(A.secs*FPS)); DT = 1000.0/FPS
ONLY = set(int(x) for x in A.only.split(',') if x)
os.makedirs(A.out, exist_ok=True)

W_CSS, H_CSS = 744, 1098
DSF = 1860/1098

VIRTUAL = r"""
(() => {
  /* the same match every take */
  let seed = 0x5eed1260;
  Math.random = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  let vt = 0; const T0 = Date.now();
  const rafs = new Map(); let rid = 0;
  const timers = new Map(); let tid = 0;
  performance.now = () => vt;
  Date.now = () => T0 + vt;
  window.requestAnimationFrame = cb => { rafs.set(++rid, cb); return rid; };
  window.cancelAnimationFrame = id => { rafs.delete(id); };
  const add = (fn, ms, a, every) => { timers.set(++tid, { t: vt + (+ms || 0), fn, a, every }); return tid; };
  window.setTimeout = (fn, ms, ...a) => add(fn, ms, a, 0);
  window.setInterval = (fn, ms, ...a) => add(fn, ms, a, Math.max(1, +ms || 1));
  window.clearTimeout = window.clearInterval = id => { timers.delete(id); };
  window.__vstep = (ms) => {
    vt += ms;
    for(const [id, T] of [...timers]){
      if(T.t > vt) continue;
      if(T.every) T.t += T.every; else timers.delete(id);
      try { typeof T.fn === 'function' ? T.fn(...T.a) : (0, eval)(T.fn); } catch(e){ console.error(e); }
    }
    for(const a of document.getAnimations()){
      if(!a.__v){ a.__v = true; a.__ct = 0; a.pause(); }
      a.__ct += ms;
      try { a.currentTime = a.__ct; } catch(e){}
    }
    const cbs = [...rafs.values()]; rafs.clear();
    for(const cb of cbs){ try { cb(vt); } catch(e){ console.error(e); window.__verr = String(e); } }
    return vt;
  };
})();
"""

TAPFX = r"""
window.__tapfx = (x, y) => {
  const root = document.createElement('div');
  root.style.cssText = 'position:fixed;left:'+x+'px;top:'+y+'px;width:0;height:0;z-index:99;pointer-events:none';
  const dot = document.createElement('i'), ring = document.createElement('i');
  dot.style.cssText = 'position:absolute;left:-17px;top:-17px;width:34px;height:34px;border-radius:50%;'
    + 'background:rgba(240,250,248,.30);border:1.5px solid rgba(255,255,255,.85);box-shadow:0 0 18px rgba(157,240,220,.55);opacity:0';
  ring.style.cssText = 'position:absolute;left:-17px;top:-17px;width:34px;height:34px;border-radius:50%;'
    + 'border:2px solid rgba(190,250,236,.95);opacity:0';
  root.append(ring, dot); document.body.append(root);
  dot.animate([{opacity:0, transform:'scale(1.35)'}, {opacity:1, transform:'scale(1)', offset:.28},
               {opacity:1, transform:'scale(.82)', offset:.40}, {opacity:1, transform:'scale(.9)', offset:.55},
               {opacity:0, transform:'scale(.9)'}], {duration:620, fill:'forwards'});
  ring.animate([{opacity:0, transform:'scale(.8)', offset:0}, {opacity:0, transform:'scale(.8)', offset:.26},
                {opacity:.9, transform:'scale(.9)', offset:.30}, {opacity:0, transform:'scale(2.6)'}],
               {duration:620, fill:'forwards', easing:'ease-out'});
  return 1;
};
"""

STAGE = r"""
window.__stage = () => {
  const G = CON_GROUPS, key = c => c[0] + ',' + c[1];
  const U = SIM.us, E = SIM.them;
  const gi3 = G.findIndex(g => g.cells.length === 3), gi2 = G.findIndex(g => g.cells.length === 2), gi4 = G.findIndex(g => g.cells.length === 4);
  // their cruiser already on the bottom
  G[gi3].hit.fill(true); for(const c of G[gi3].cells){ ENEMY_SHOT.add(key(c)); U.K[c[1]*10 + c[0]] = 3; }
  U.gone.add('e' + gi3); U.sunk = 1; U.left.splice(U.left.indexOf(3), 1);
  wreckReveal(gi3, []);
  const w = EWRECKS[EWRECKS.length - 1]; if(w){ w.rise = 1; w.u = 1; }
  // one square found on their escort, one on their carrier
  const c2 = G[gi2].cells[0]; G[gi2].hit[0] = true; ENEMY_SHOT.add(key(c2)); U.K[c2[1]*10 + c2[0]] = 2;
  const c4 = G[gi4].cells[1]; G[gi4].hit[1] = true; ENEMY_SHOT.add(key(c4)); U.K[c4[1]*10 + c4[0]] = 2;
  // water on their plot
  const free = []; for(let x=0;x<10;x++) for(let z=0;z<10;z++) if(!hullUnder(x, z)) free.push([x, z]);
  for(let i=0, n=0; i<free.length && n<8; i += 7, n++){ ENEMY_SHOT.add(key(free[i])); U.K[free[i][1]*10 + free[i][0]] = 1; }
  pushContacts();
  // her submarine lost, her cruiser burning
  const sub = shipNamed('submarine'); OWN_HITS.submarine = new Set([0, 1]);
  for(const c of [[1,7],[1,8]]) OWN_SHOT.add(key(c));
  WRECKS.push({ sh: sub, u: 1 });
  OWN_HITS.cruiser = new Set([1]); OWN_SHOT.add('6,2');
  const fp = cellW(6.5, 2.5, 0); ownFire(fp, 'cruiser'); scar(shipNamed('cruiser'), fp, 15.0);
  for(const f of FIRES) if(f.goal > 0) f.k = 1;
  for(const c of [[0,1],[4,0],[9,3],[3,6],[8,8],[5,9],[0,4]]) OWN_SHOT.add(key(c));
  LASTIN = { label:'Missile G3 · hit', kind:'hit' };
  LASTSHOT = { label:'Missile ' + colLetter(c2[0]) + (c2[1] + 1) + ' · hit', kind:'hit' };
  CD.cat.t = CD.cat.n; CD.flare.t = CD.flare.n; CD.tor.t = 2;
  SIM.turnN = 7; MATCH.turn = 7; MATCH.t = 252; MATCH.dirty = true;
  U.moves = 10; U.shots = 12; U.hits = 5; E.moves = 9; E.shots = 10; E.hits = 3; E.sunk = 1;
  SIM.side = 'us'; SIM.phase = 'think'; SIM.wait = 0.35; SIM.speed = 1.6;
  window.__target = G[gi2].cells[1];
  refreshUI();
  return { target: window.__target, wreck: !!w };
};
window.__cellPt = (gx, gz) => {
  const r = canvas.getBoundingClientRect(); plotPick(r.left + 5, r.top + 5);
  const v = cellW(gx + 0.5, gz + 0.5, 0).project(_pickCam); const hh = r.height/2, y0 = r.top + (ANIM.swap ? hh : 0);
  return { x: r.left + (v.x + 1)/2*r.width, y: y0 + (1 - v.y)/2*hh };
};
"""

def secs(t): return int(round(t*FPS))

with Chrome(width=W_CSS, height=H_CSS, dpr=DSF) as c:
    c.call('Page.addScriptToEvaluateOnNewDocument', source=VIRTUAL)
    c.call('Page.navigate', url='http://localhost:4620/index.html?prod', timeout=120)
    for _ in range(80):
        time.sleep(0.25)
        try:
            if c.js("typeof frame === 'function' && typeof __vstep === 'function' && document.readyState === 'complete'"): break
        except Exception: pass
    c.js("(() => { " + TAPFX + STAGE + " return 1; })()")
    # the title leaves the match quickly on film
    c.js("(() => { const st = document.createElement('style'); st.textContent = 'body:not(.s-attract):not(.s-setup) #brand{transition:opacity 420ms ease 0ms!important}'; document.head.append(st); return 1; })()")
    # full-bleed tablet at the video's size, full resolution, no auto downgrade
    c.js("(() => { document.body.classList.remove('ipad'); ANIM.ipad = false; PR_MAX = %f; guard = -1; fit(); return [renderer.getPixelRatio(), innerWidth, innerHeight]; })()" % DSF)
    # pre-roll: the title fills its bar and offers the way in
    for i in range(int(5.2*FPS)):
        c.js("__vstep(%f)" % DT)
    print('preroll', c.js("({screen:SCREEN, cta: document.getElementById('tgo').classList.contains('on'), pr: renderer.getPixelRatio(), err: window.__verr || null})"))

    def pos(sel):
        return c.js("(() => { const e = document.querySelector('%s'); if(!e) return null; const b = e.getBoundingClientRect(); return {x:b.left + b.width/2, y:b.top + b.height/2}; })()" % sel)
    def move(x, y):
        c.call('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y)
    def press(x, y):
        c.call('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y)
        c.call('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', clickCount=1)
        c.call('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', clickCount=1)
    LEAD = 5   # the finger shows this many frames before the press
    pending = {}
    def tap_at(frame, getter, after=None):
        pending.setdefault(frame - LEAD, []).append(('fx', getter))
        pending.setdefault(frame, []).append(('press', getter, after))
    def at(frame, fn):
        pending.setdefault(frame, []).append(('fn', fn))

    tgt = {}
    tap_at(secs(0.8), lambda: pos('#tgo'))
    tap_at(secs(1.85), lambda: pos('#scr-setup [data-lv="2"]'))
    tap_at(secs(2.45), lambda: pos('#scr-setup [data-e="%d"]' % A.theatre))
    tap_at(secs(3.2), lambda: pos('#scr-setup .go.prim'),
           after=lambda: tgt.update(c.js("__stage()")))
    at(secs(4.0), lambda: move(**c.js("__cellPt(__target[0], __target[1])")))
    tap_at(secs(4.45), lambda: c.js("__cellPt(__target[0], __target[1])"))
    at(secs(4.9), lambda: c.js("(() => { SIM.force = [2, 3]; enemyMissile(); SIM.force = null; return 1; })()"))
    for k in range(secs(7.9), secs(8.2)):
        at(k, lambda: c.js("(() => { if(SIM.phase === 'think') SIM.wait = Math.min(SIM.wait, 0.02); return 1; })()"))
    tap_at(secs(8.2), lambda: pos('#rail [data-a="cat"]'))
    at(secs(8.38), lambda: move(**c.js("__cellPt(4, 4)")))
    tap_at(secs(8.7), lambda: c.js("__cellPt(4, 4)"))

    cache = {}
    t0 = time.time()
    for f in range(N):
        for act in pending.get(f, []):
            if act[0] == 'fx':
                p = act[1](); cache[f + LEAD] = p
                if p: c.js("__tapfx(%f, %f)" % (p['x'], p['y']))
            elif act[0] == 'press':
                p = cache.get(f) or act[1]()
                if p: press(p['x'], p['y'])
                if act[2]: act[2]()
                print('%.2fs tap' % (f/FPS), p and (round(p['x']), round(p['y'])), c.js("({screen:SCREEN, mine: typeof simYourMove === 'function' && simYourMove(), w: SIM.weapon, phase: SIM.phase})"))
            elif act[0] == 'fn':
                act[1]()
        c.js("__vstep(%f)" % DT)
        if not ONLY or f in ONLY:
            r = c.call('Page.captureScreenshot', format='png', optimizeForSpeed=True)
            with open(os.path.join(A.out, 'f%04d.png' % f), 'wb') as fh: fh.write(base64.b64decode(r['data']))
        if f % 30 == 0:
            print('%.1fs' % (f/FPS), c.js("({s:SCREEN, mis:+ANIM.mis.toFixed(2), es:+ESALVO.u.toFixed(2), cat:+ANIM.cat.toFixed(2), cine:+CINE.w.toFixed(2), bar: (document.querySelector('#simbar .sl')||{}).innerText, err: window.__verr || null})"), round(time.time()-t0, 1))
    print('done', round(time.time()-t0, 1), 's', 'target', tgt)
