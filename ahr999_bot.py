#!/usr/bin/env python3
"""
AHR999 自动定投机器人 — 部署到 GitHub Actions / VPS
====================================================
环境变量:
  OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE
"""

import os, json, math, time, hmac, base64, hashlib
import urllib.request, urllib.error
from datetime import datetime, timezone, date

# ── Config ─────────────────────────────────────────────
GENESIS    = date(2009, 1, 3)
MA_PERIOD  = 200
LOW_ZONE   = 0.45
DCA_ZONE   = 1.2
HIGH_ZONE  = 2.0
EXP_POW    = 5.84
EXP_INT    = -17.01
UNIT       = 20.66   # USD per DCA unit
HEAVY_MULT = 3       # 3x in heavy buy zone

API_KEY    = os.environ["OKX_API_KEY"]
SECRET_KEY = os.environ["OKX_SECRET_KEY"]
PASSPHRASE = os.environ["OKX_PASSPHRASE"]
BASE_URL   = "https://www.okx.com"

# ── OKX API helpers ────────────────────────────────────
def okx_request(method, path, body=None):
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    body_str = json.dumps(body) if body else ""
    sign_msg = f"{ts}{method}{path}{body_str}"
    sign = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), sign_msg.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{path}"
    data = body_str.encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"API Error: {err}")
        return None

# ── AHR999 helpers ────────────────────────────────────
def coin_age_days(ts_ms):
    return (datetime.fromtimestamp(int(ts_ms)/1000, tz=timezone.utc).date() - GENESIS).days

def exponential_valuation(ts_ms):
    days = coin_age_days(ts_ms)
    return 10 ** (EXP_POW * math.log10(days) + EXP_INT) if days > 0 else 1.0

def geometric_mean(values):
    return math.exp(sum(math.log(v) for v in values) / len(values))

def get_candles():
    """Fetch 300 daily candles from OKX"""
    path = "/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=300"
    resp = okx_request("GET", path)
    if resp and resp.get("code") == "0":
        candles = [{"time": int(d[0]), "close": float(d[4])} for d in resp["data"]]
        candles.sort(key=lambda x: x["time"])
        return candles
    return None

def calculate_ahr999(candles):
    p = candles[-1]["close"]
    gm = geometric_mean([c["close"] for c in candles[-MA_PERIOD:]])
    ev = exponential_valuation(candles[-1]["time"])
    return (p / gm) * (p / ev), p, gm, ev

def get_balance():
    resp = okx_request("GET", "/api/v5/account/balance")
    if resp and resp.get("code") == "0":
        for d in resp["data"]:
            if d["ccy"] == "USDT":
                return float(d["availBal"])
    return 0

def get_btc_holding():
    resp = okx_request("GET", "/api/v5/account/balance")
    if resp and resp.get("code") == "0":
        for d in resp["data"]:
            if d["ccy"] == "BTC":
                return float(d["availBal"])
    return 0

def place_spot_order(side, sz, tgt_ccy="quote_ccy"):
    """Place spot market order. sz is in quote currency units."""
    body = {
        "instId": "BTC-USDT",
        "tdMode": "cash",
        "side": side,
        "ordType": "market",
        "sz": str(sz),
        "tgtCcy": tgt_ccy
    }
    resp = okx_request("POST", "/api/v5/trade/order", body)
    return resp

# ── Main ──────────────────────────────────────────────
def main():
    print(f"\n=== AHR999 Bot === {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

    # 1. Fetch candles
    candles = get_candles()
    if not candles:
        print("Failed to fetch candles")
        return

    # 2. Calculate AHR999
    ahr999, price, gm200, exp_val = calculate_ahr999(candles)
    zone = ("HEAVY_BUY" if ahr999 < LOW_ZONE else
            "DCA" if ahr999 < DCA_ZONE else
            "PAUSE" if ahr999 < HIGH_ZONE else "SELL")

    # 3. Get balance
    usdt = get_balance()
    btc_holding = get_btc_holding()

    print(f"BTC: ${price:,.2f} | GM200: ${gm200:,.0f} | EV: ${exp_val:,.0f}")
    print(f"AHR999: {ahr999:.4f} | Zone: {zone}")
    print(f"Balance: ${usdt:,.2f} USDT | {btc_holding:.8f} BTC")

    # 4. Execute strategy
    action = "NONE"
    if ahr999 < LOW_ZONE:
        amount = min(UNIT * HEAVY_MULT, usdt)
        if amount > 1:
            resp = place_spot_order("buy", amount)
            if resp and resp.get("code") == "0":
                action = f"BUY ${amount:.0f} (3x DCA)"
                print(f">>> {action}")
            else:
                print(f"Order failed: {resp}")
        else:
            print(f"Insufficient USDT: ${usdt:.2f} < ${UNIT*HEAVY_MULT:.0f}")

    elif ahr999 < DCA_ZONE:
        amount = min(UNIT, usdt)
        if amount > 1:
            resp = place_spot_order("buy", amount)
            if resp and resp.get("code") == "0":
                action = f"BUY ${amount:.0f} (1x DCA)"
                print(f">>> {action}")
        else:
            print(f"Insufficient USDT: ${usdt:.2f}")

    elif ahr999 >= HIGH_ZONE:
        if btc_holding > 0.0001:
            sell_sz = btc_holding * 0.5
            resp = place_spot_order("sell", sell_sz, "base_ccy")
            if resp and resp.get("code") == "0":
                action = f"SELL {sell_sz:.6f} BTC (50%)"
                print(f">>> {action}")

    if action == "NONE":
        print(">>> No action (PAUSE zone or no funds)")

    print(f"Result: {action} | AHR999={ahr999:.4f} | BTC=${price:,.0f}")
    return action

if __name__ == "__main__":
    main()
