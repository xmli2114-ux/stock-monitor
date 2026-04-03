#!/usr/bin/env python3
"""
A股放量异动监测脚本（GitHub Actions版）
- 直接调新浪K线接口，不依赖kline_sina等第三方库
- 只用 requests + pandas
"""
import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime

# ========== 配置区 ==========
STOCKS = [
    "sh603248",
    "sh300308",
    "sz002371",
    "sz300750",
    "sh601088",
    "sh600900",
    "sz300760",
]

DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")
MIN_RISE_PCT = 3.0
MIN_VOL_RATIO = 2.0
MAX_DIST_FROM_HIGH_PCT = 15.0
PUSH_COOLDOWN_MINUTES = 30
STATE_FILE = "/tmp/alert_state.json"
# ============================

def get_realtime_quote(code):
    url = f"https://hq.sinajs.cn/list={code}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.text.strip()
    parts = data.split('"')[1].split(',')
    if len(parts) < 32:
        return None
    try:
        return {
            "name": parts[0],
            "open": float(parts[1]) if parts[1] else 0,
            "yest_close": float(parts[2]) if parts[2] else 0,
            "current": float(parts[3]) if parts[3] else 0,
            "high": float(parts[4]) if parts[4] else 0,
            "low": float(parts[5]) if parts[5] else 0,
            "volume": float(parts[8]) if parts[8] else 0,
            "amount": float(parts[9]) if parts[9] else 0,
        }
    except (ValueError, IndexError):
        return None

def get_kline_data(code, scale=240, datalen=25):
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale={scale}&ma=no&datalen={datalen}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}
    resp = requests.get(url, headers=headers, timeout=10)
    try:
        df = pd.DataFrame(resp.json())
        for col in ["close", "open", "high", "low", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except:
        return None

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_dingtalk(msg):
    if not DINGTALK_WEBHOOK:
        print("⚠️ 未配置 DINGTALK_WEBHOOK，跳过推送")
        return
    payload = {"msgtype": "text", "text": {"content": f"📈 放量异动提醒\n\n{msg}"}}
    try:
        requests.post(DINGTALK_WEBHOOK, json=payload, timeout=10)
        print(f"✅ 钉钉推送成功")
    except Exception as e:
        print(f"❌ 钉钉推送失败: {e}")

def check_stock(code):
    try:
        quote = get_realtime_quote(code)
        if not quote:
            return None
        name = quote["name"]
        current = quote["current"]
        high = quote["high"]
        yest_close = quote["yest_close"]
        today_vol = quote["volume"]
        today_amount = quote["amount"]

        if yest_close == 0:
            return None

        rise_pct = (current - yest_close) / yest_close * 100

        df = get_kline_data(code, scale=240, datalen=25)
        if df is None or len(df) < 20:
            print(f"  [{name}] K线数据不足，跳过")
            return None

        vol_ma20 = df["volume"].iloc[-20:].mean()
        close_ma20 = df["close"].iloc[-20:].mean()

        high_52w = df["high"].iloc[-250:].max() if len(df) >= 250 else df["high"].max()
        dist_from_high = (high_52w - current) / high_52w * 100 if high_52w > 0 else 100

        vol_ratio = today_vol / vol_ma20 if vol_ma20 > 0 else 0

        print(f"  [{name}({code})] 现价:{current:.2f} 涨幅:{rise_pct:.2f}% 量比:{vol_ratio:.2f}倍 "
              f"均线:{close_ma20:.2f} 距高:{dist_from_high:.1f}%")

        if rise_pct < MIN_RISE_PCT:
            return None
        if vol_ratio < MIN_VOL_RATIO:
            return None
        if current < close_ma20:
            return None
        if dist_from_high < MAX_DIST_FROM_HIGH_PCT:
            return None

        return {
            "name": name,
            "code": code,
            "current": current,
            "rise_pct": rise_pct,
            "vol_ratio": vol_ratio,
            "ma20": close_ma20,
            "dist_from_high": dist_from_high,
            "amount": today_amount,
        }
    except Exception as e:
        print(f"  检查 {code} 失败: {e}")
        return None

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始放量异动检查...")
    state = load_state()
    alerts = []

    for code in STOCKS:
        result = check_stock(code)
        if result:
            last_push = state.get(code, 0)
            if (time.time() - last_push) < PUSH_COOLDOWN_MINUTES * 60:
                print(f"  [{result['name']}] 冷却中，跳过")
                continue
            alerts.append(result)
            state[code] = time.time()

    if alerts:
        msg_lines = []
        for a in alerts:
            line = (f"🔥 **{a['name']}({a['code'].upper().replace('SH','').replace('SZ','')})**\n"
                    f"   现价: {a['current']:.2f} | 涨幅: +{a['rise_pct']:.2f}%\n"
                    f"   量比: {a['vol_ratio']:.1f}倍 | 20日均线: {a['ma20']:.2f}\n"
                    f"   距高点: {a['dist_from_high']:.1f}% | 成交额: {a['amount']/1e8:.1f}亿")
            msg_lines.append(line)
        msg = "\n\n".join(msg_lines)
        send_dingtalk(msg)
        save_state(state)
        print(f"✅ 已推送 {len(alerts)} 条提醒")
        sys.exit(0)
    else:
        print("✅ 无异动")
        save_state(state)
        sys.exit(0)

if __name__ == "__main__":
    main()
