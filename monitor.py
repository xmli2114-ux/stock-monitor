#!/usr/bin/env python3
"""A股放量异动监测脚本 - GitHub Actions版 (调试版)"""
import os, sys, json, time, requests, pandas as pd
from datetime import datetime

STOCKS = ["sh603248","sh300308","sz002371","sz300750","sh601088","sh600900","sz300760"]
DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")
MIN_RISE_PCT, MIN_VOL_RATIO = 3.0, 2.0
MAX_DIST_FROM_HIGH_PCT = 15.0
PUSH_COOLDOWN_MINUTES = 30
STATE_FILE = "/tmp/alert_state.json"

def get_realtime_quote(code):
    url = f"https://hq.sinajs.cn/list={code}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        parts = resp.text.strip().split('"')[1].split(",")
        if len(parts) < 32: return None
        return {
            "name": parts[0], "open": float(parts[1]) if parts[1] else 0,
            "yest_close": float(parts[2]) if parts[2] else 0, "current": float(parts[3]) if parts[3] else 0,
            "high": float(parts[4]) if parts[4] else 0, "low": float(parts[5]) if parts[5] else 0,
            "volume": float(parts[8]) if parts[8] else 0, "amount": float(parts[9]) if parts[9] else 0
        }
    except Exception as e:
        print(f"[NETWORK ERROR] get_realtime_quote({code}): {e}")
        return None

def get_kline_data(code, scale=240, datalen=25):
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale={scale}&ma=no&datalen={datalen}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()
        if not data or (isinstance(data, list) and len(data) == 0):
            print(f"[DATA ERROR] get_kline_data({code}): empty response")
            return None
        df = pd.DataFrame(data)
        for col in ["close","open","high","low","volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception as e:
        print(f"[NETWORK ERROR] get_kline_data({code}): {e}")
        return None

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f: json.dump(state, f)
    except Exception as e:
        print(f"[FS ERROR] save_state: {e}")

def send_dingtalk(msg):
    if not DINGTALK_WEBHOOK:
        print("[WARN] DINGTALK_WEBHOOK not set, skip push"); return
    payload = {"msgtype": "text", "text": {"content": f"Stock Alert:\n{msg}"}}
    try:
        r = requests.post(DINGTALK_WEBHOOK, json=payload, timeout=10)
        print(f"[OK] DingTalk pushed: {r.status_code}")
    except Exception as e:
        print(f"[FAIL] DingTalk: {e}")

def check_stock(code):
    try:
        quote = get_realtime_quote(code)
        if not quote: return None
        name, current = quote["name"], quote["current"]
        high, yest_close = quote["high"], quote["yest_close"]
        today_vol, today_amount = quote["volume"], quote["amount"]
        if yest_close == 0: return None
        rise_pct = (current - yest_close) / yest_close * 100
        df = get_kline_data(code)
        if df is None or len(df) < 20:
            print(f"  [{name}] K-line data insufficient or network error"); return None
        vol_ma20 = df["volume"].iloc[-20:].mean()
        close_ma20 = df["close"].iloc[-20:].mean()
        high_52w = df["high"].iloc[-250:].max() if len(df) >= 250 else df["high"].max()
        dist_from_high = (high_52w - current) / high_52w * 100 if high_52w > 0 else 100
        vol_ratio = today_vol / vol_ma20 if vol_ma20 > 0 else 0
        print(f"  [{name}] price={current:.2f} rise={rise_pct:.2f}% vol={vol_ratio:.2f}x ma20={close_ma20:.2f} dist={dist_from_high:.1f}%")
        if rise_pct < MIN_RISE_PCT: return None
        if vol_ratio < MIN_VOL_RATIO: return None
        if current < close_ma20: return None
        if dist_from_high < MAX_DIST_FROM_HIGH_PCT: return None
        return {"name": name, "code": code, "current": current, "rise_pct": rise_pct,
                "vol_ratio": vol_ratio, "ma20": close_ma20, "dist_from_high": dist_from_high, "amount": today_amount}
    except Exception as e:
        print(f"  [{code}] exception: {e}")
        return None

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Stock monitor starting...")
    print(f"[DEBUG] Python: {sys.version}")
    print(f"[DEBUG] DINGTALK_WEBHOOK set: {bool(DINGTALK_WEBHOOK)}")
    state = load_state()
    alerts = []
    for code in STOCKS:
        result = check_stock(code)
        if result:
            last = state.get(code, 0)
            if (time.time() - last) < PUSH_COOLDOWN_MINUTES * 60:
                print(f"  [{result['name']}] in cooldown, skip"); continue
            alerts.append(result); state[code] = time.time()
    if alerts:
        msg = "\n".join([f"{a['name']}({a['code']}) price={a['current']:.2f} rise=+{a['rise_pct']:.2f}% vol={a['vol_ratio']:.1f}x ma20={a['ma20']:.2f} dist={a['dist_from_high']:.1f}%" for a in alerts])
        send_dingtalk(msg); save_state(state)
        print(f"[OK] {len(alerts)} alerts pushed"); sys.exit(0)
    else:
        print("[OK] No alerts"); save_state(state); sys.exit(0)

if __name__ == "__main__":
    main()
