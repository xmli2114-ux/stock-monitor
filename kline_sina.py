import requests
import pandas as pd
import time

def get_kline_sina(code, days=60):
    """
    鏂版氮璐㈢粡鏃绾挎帴鍙?    code: 6寮€澶?sh, 0/3寮€澶?sz
    杩斿洖: DataFrame
    """
    if code.startswith("6"):
        symbol = f"sh{code}"
    else:
        symbol = f"sz{code}"
    
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/"
    }
    
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            data = resp.json()
            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                df["day"] = pd.to_datetime(df["day"])
                df = df.sort_values("day")
                df = df.astype({
                    "open": float, "high": float, 
                    "low": float, "close": float, "volume": float
                })
                return df
        except Exception:
            time.sleep(2)
    return None

def get_realtime_price(code):
    """鑾峰彇瀹炴椂浠锋牸"""
    if code.startswith("6"):
        symbol = f"sh{code}"
    else:
        symbol = f"sz{code}"
    
    url = f"https://hq.sinajs.cn/list={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.sina.com.cn/"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        content = resp.content.decode("gbk")
        parts = content.split('"')[1].split(",")
        return {
            "name": parts[0],
            "open": float(parts[1]),
            "close": float(parts[2]) if parts[2] else None,  # 鏄ㄦ敹
            "current": float(parts[3]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "volume": int(parts[8]) if parts[8] else 0,
            "date": parts[30] if len(parts) > 30 else "",
            "time": parts[31] if len(parts) > 31 else "",
        }
    except Exception:
        return None

def analyze_stock(code, name, target_low, target_high, stop_loss):
    """
    鍒嗘瀽鍗曞彧鑲＄エ
    杩斿洖: dict with analysis results
    """
    df = get_kline_sina(code, days=30)
    if df is None or len(df) < 5:
        return {"code": code, "name": name, "error": "鏁版嵁鑾峰彇澶辫触"}
    
    # 璁＄畻鎸囨爣
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["vol_ma5"] = df["volume"].rolling(5).mean()
    df["pct_chg"] = df["close"].pct_change() * 100
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    current = last["close"]
    ma5 = last["ma5"] if pd.notna(last["ma5"]) else 0
    ma10 = last["ma10"] if pd.notna(last["ma10"]) else 0
    ma20 = last["ma20"] if pd.notna(last["ma20"]) else 0
    vol_ratio = last["volume"] / last["vol_ma5"] if last["vol_ma5"] > 0 else 1
    
    # 杩戞湡楂樹綆鐐?    low10 = df.tail(10)["low"].min()
    high10 = df.tail(10)["high"].max()
    low20 = df.tail(20)["low"].min()
    
    # 鍒ゆ柇鐘舵€?    status = "watch"
    signal = ""
    
    if target_low <= current <= target_high:
        status = "buy"
        signal = f"馃幆 杩涘叆涔板叆鍖洪棿锛佸綋鍓嶄环 {current:.2f}锛屽湪 {target_low}-{target_high} 涔嬮棿"
    elif current < target_low:
        status = "below"
        signal = f"浠锋牸 {current:.2f} 浣庝簬涔板叆鍖洪棿涓嬮檺 {target_low}锛岀户缁瓑寰?
    elif current > target_high:
        status = "above"
        signal = f"浠锋牸 {current:.2f} 楂樹簬涔板叆鍖洪棿涓婇檺 {target_high}锛岀瓑寰呭洖璋?
    
    if current < stop_loss:
        status = "stop"
        signal = f"鈿狅笍 浠锋牸 {current:.2f} 璺岀牬姝㈡崯浠?{stop_loss}锛佸缓璁嚭鍦?
    
    return {
        "code": code,
        "name": name,
        "current": current,
        "target_low": target_low,
        "target_high": target_high,
        "stop_loss": stop_loss,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "vol_ratio": vol_ratio,
        "low10": low10,
        "high10": high10,
        "low20": low20,
        "pct_chg": last["pct_chg"],
        "status": status,
        "signal": signal,
    }

def format_alert(stock):
    """鏍煎紡鍖栭拤閽夋秷鎭?""
    s = stock
    status_emoji = {
        "buy": "馃幆",
        "above": "鈴?,
        "below": "馃憖",
        "stop": "馃毃",
        "watch": "馃搳"
    }
    emoji = status_emoji.get(s["status"], "馃搳")
    
    msg = f"""鑲＄エ {emoji} **{s['name']}锛坽s['code']}锛?* 鐩戞帶鎶ュ憡

馃搷 褰撳墠浠? **{s['current']:.2f}** 鍏?馃搱 浠婃棩娑ㄨ穼: {s['pct_chg']:+.2f}%

馃幆 涔板叆鍖洪棿: {s['target_low']} - {s['target_high']} 鍏?馃洃 姝㈡崯浠? {s['stop_loss']} 鍏?
馃搻 鍧囩嚎鐘舵€?
  MA5: {s['ma5']:.2f}  MA10: {s['ma10']:.2f}  MA20: {s['ma20']:.2f}
  閲忔瘮: {s['vol_ratio']:.2f}x

馃搳 鏀拺/鍘嬪姏:
  10鏃ヤ綆: {s['low10']:.2f}  10鏃ラ珮: {s['high10']:.2f}
  20鏃ヤ綆: {s['low20']:.2f}

{s['signal']}
"""
    return msg
