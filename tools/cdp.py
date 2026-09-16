"""Pilotage de Chrome via le Chrome DevTools Protocol — stdlib uniquement.

Nécessaire parce que le pane navigateur de l'app est masqué : requestAnimationFrame
y est gelé, donc les révélations au scroll (Clay en est truffé) ne se jouent jamais
et les captures reviennent blanches. Ici, Chrome tourne en headless=new, rAF tourne,
et Page.captureScreenshot rend en pleine résolution 1440 (ou 390).

Usage :
    from cdp import Chrome
    with Chrome(width=1440, height=900) as c:
        c.goto("https://clay.global")
        c.settle()
        c.step_scroll(0, 4000)          # défile par paliers, laisse jouer les reveals
        c.shot("refs/clay-home-01.png") # capture viewport
        data = c.js("document.title")
"""

import base64
import hashlib
import json
import os
import random
import socket
import struct
import subprocess
import time
import urllib.request

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class WS:
    """Client WebSocket minimal (RFC 6455), côté client, sans extension."""

    def __init__(self, url, timeout=90):
        assert url.startswith("ws://")
        rest = url[5:]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("handshake ws interrompu")
            buf += chunk
        head, _, tail = buf.partition(b"\r\n\r\n")
        # Le serveur inspecteur de Chrome renvoie un Sec-WebSocket-Accept qui ne suit
        # pas le calcul RFC 6455 ; on se contente donc du 101 + Upgrade (tout est local).
        if b"101" not in head.split(b"\r\n")[0] or b"pgrade" not in head:
            raise RuntimeError("handshake ws refuse: " + head.decode(errors="replace")[:300])
        self.buf = tail

    def _recv(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(max(65536, n - len(self.buf)))
            if not chunk:
                raise RuntimeError("socket fermee")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        payload = text.encode()
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            header = struct.pack("!BB", 0x81, 0x80 | n)
        elif n < 65536:
            header = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        else:
            header = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def recv(self):
        """Retourne le prochain message texte complet (gère fragments et ping)."""
        parts = []
        while True:
            b0, b1 = struct.unpack("!BB", self._recv(2))
            fin, opcode = b0 & 0x80, b0 & 0x0F
            length = b1 & 0x7F
            if length == 126:
                (length,) = struct.unpack("!H", self._recv(2))
            elif length == 127:
                (length,) = struct.unpack("!Q", self._recv(8))
            data = self._recv(length) if length else b""
            if opcode == 0x9:  # ping -> pong
                mask = os.urandom(4)
                self.sock.sendall(
                    struct.pack("!BB", 0x8A, 0x80 | len(data))
                    + mask
                    + bytes(b ^ mask[i % 4] for i, b in enumerate(data))
                )
                continue
            if opcode == 0x8:
                raise RuntimeError("ws close")
            parts.append(data)
            if fin:
                return b"".join(parts).decode("utf-8", "replace")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Chrome:
    def __init__(self, width=1440, height=900, dpr=1, port=None, headless=True, profile=None):
        self.width, self.height, self.dpr = width, height, dpr
        self.port = port or random.randint(9500, 9899)
        self.profile = profile or f"/tmp/cdp-profile-{self.port}"
        self._id = 0
        args = [
            CHROME,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.profile}",
            f"--window-size={width},{height}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--mute-audio",
            "about:blank",
        ]
        if headless:
            args.insert(1, "--headless=new")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = None
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=1) as r:
                    targets = json.load(r)
                pages = [t for t in targets if t.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.25)
        if not ws_url:
            raise RuntimeError("Chrome n'a pas ouvert son port de debug")
        self.ws = WS(ws_url)
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.set_viewport(width, height, dpr)

    # --- protocole -------------------------------------------------------
    def call(self, method, timeout=90, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(method)

    def js(self, expr, timeout=90):
        """Évalue une expression (top-level await autorisé) et renvoie la valeur."""
        r = self.call(
            "Runtime.evaluate",
            timeout=timeout,
            expression=f"(async()=>{{ return ({expr}); }})()",
            awaitPromise=True,
            returnByValue=True,
        )
        if r.get("exceptionDetails"):
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:600])
        return r["result"].get("value")

    # --- navigation ------------------------------------------------------
    def set_viewport(self, width, height, dpr=1, mobile=False):
        self.width, self.height, self.dpr = width, height, dpr
        self.call(
            "Emulation.setDeviceMetricsOverride",
            width=width,
            height=height,
            deviceScaleFactor=dpr,
            mobile=mobile,
        )

    def goto(self, url, wait=3.0):
        self.call("Page.navigate", url=url, timeout=120)
        time.sleep(wait)
        return self

    def settle(self, seconds=2.5):
        """Laisse tourner l'intro / le chargement des polices et des médias."""
        try:
            self.js("await document.fonts.ready.then(()=>1)")
        except Exception:
            pass
        time.sleep(seconds)
        return self

    def step_scroll(self, start, end, step=140, pause=0.06, settle=0.5):
        """Défile par paliers : indispensable, les reveals de Clay sont liés au scroll."""
        self.js(
            f"await (async()=>{{ for(let y={start}; y<={end}; y+={step}) "
            f"{{ window.scrollTo(0,y); await new Promise(r=>setTimeout(r,{int(pause*1000)})); }} "
            f"window.scrollTo(0,{end}); return 1; }})()",
            timeout=180,
        )
        time.sleep(settle)
        return self.js("window.scrollY")

    def scroll_to(self, y, settle=0.7):
        self.js(f"window.scrollTo(0,{y})")
        time.sleep(settle)
        return self

    # --- capture ---------------------------------------------------------
    def shot(self, path, clip=None, full=False, quality=None):
        params = {"format": "png", "captureBeyondViewport": bool(clip or full)}
        if clip:
            x, y, w, h = clip
            params["clip"] = {"x": x, "y": y, "width": w, "height": h, "scale": 1}
        elif full:
            m = self.call("Page.getLayoutMetrics")
            cs = m["cssContentSize"]
            params["clip"] = {"x": 0, "y": 0, "width": cs["width"], "height": cs["height"], "scale": 1}
        r = self.call("Page.captureScreenshot", timeout=180, **params)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path

    def close(self):
        try:
            self.ws.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
