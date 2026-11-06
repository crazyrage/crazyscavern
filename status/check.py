# Server status for the website (CC 2026-11-06). GitHub runs this every 5 minutes (.github/workflows/status.yml in the
# Pages repo): it asks each game server how many are on (Steam's A2S_INFO query) and writes status.json, which the
# pages read. Humans only: bots are subtracted. Usage: python3 check.py servers.json status.json
import json, socket, struct, sys, time
from datetime import datetime, timezone

def cstr(d, i):
    j = d.index(b"\x00", i)
    return d[i:j].decode("utf-8", "replace"), j + 1

def info(addr, timeout=3.0):
    host, port = addr.rsplit(":", 1)
    q = b"\xff\xff\xff\xffTSource Engine Query\x00"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(q, (host, int(port)))
        d = s.recv(1400)
        if d[4] == 0x41:                       # challenge: ask again with it
            s.sendto(q + d[5:9], (host, int(port)))
            d = s.recv(1400)
    finally:
        s.close()
    i = 6
    _, i = cstr(d, i)                          # name
    mapname, i = cstr(d, i)
    _, i = cstr(d, i)                          # folder
    _, i = cstr(d, i)                          # game
    i += 2                                     # app id
    players, maxp, bots = d[i], d[i + 1], d[i + 2]
    return {"ok": True, "humans": max(0, players - bots), "max": maxp, "map": mapname}

def main():
    servers = json.load(open(sys.argv[1], encoding="utf-8"))
    out = {}
    for s in servers:
        r = {"ok": False}
        for _ in range(3):                     # retries: UDP can drop a packet, and a server changing map
            try:                               # doesn't answer for a few seconds (seen on TF2 EU)
                r = info(s["address"]); break
            except Exception as e:
                r = {"ok": False, "error": type(e).__name__}
                time.sleep(3)
        out[s["id"]] = r
    doc = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "servers": out}
    json.dump(doc, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
    up = sum(1 for v in out.values() if v.get("ok"))
    print(f"{up}/{len(out)} servers answered, {sum(v.get('humans', 0) for v in out.values())} people on")
    for k, v in out.items():
        print(f"  {k:18} {v}")

if __name__ == "__main__":
    main()
