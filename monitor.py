#!/usr/bin/env python3
"""
A鑲¤嚜鍔ㄥ寲閫夎偂鐩洏绯荤粺
姣忔棩鑷姩鐩戞帶鐩爣鑲＄エ涔板崠鐐癸紝閫氳繃閽夐拤鎺ㄩ€?"""
import os
import sys
import json
import time
from datetime import datetime

from kline_sina import analyze_stock, get_realtime_price, format_alert
from dingtalk import send_text, send_buy_alert

# ===================== 閰嶇疆鍖?=====================

# 瑕佺洃鎺х殑鑲＄エ鍒楄〃
# 鏍煎紡: (浠ｇ爜, 鍚嶇О, 涔板叆鍖洪棿浣? 涔板叆鍖洪棿楂? 姝㈡崯浠?
STOCKS = [
    ("603248", "閿″崕绉戞妧", 27.3, 27.7, 25.5),
    # 鍙互缁х画娣诲姞鏇村鑲＄エ锛屼緥濡傦細
    # ("002560", "閫氳揪鑲′唤", 10.0, 10.5, 9.0),
    # ("603803", "鐟炴柉搴疯揪", 12.5, 13.0, 11.5),
]

# 鏄惁鍙彂閫侀噸瑕佹彁閱掞紙涓嶅湪涔板叆鍖洪棿鐨勪笉鍙戯級
ALERT_ONLY = False

# ================================================

def main():
    print(f"=== A鑲＄洴鐩樼郴缁?{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    results = []
    alerts = []
    
    for code, name, target_low, target_high, stop_loss in STOCKS:
        print(f"\n鍒嗘瀽 {name}锛坽code}锛?..")
        
        stock = analyze_stock(code, name, target_low, target_high, stop_loss)
        results.append(stock)
        
        if stock.get("error"):
            print(f"  鉂?{stock['error']}")
            continue
        
        current = stock["current"]
        print(f"  褰撳墠浠? {current:.2f} | 鐘舵€? {stock['status']}")
        print(f"  {stock['signal']}")
        
        # 涔板叆/姝㈡崯淇″彿 -> 绔嬪嵆鍙戦€侀拤閽?        if stock["status"] in ("buy", "stop"):
            alerts.append(stock)
            send_buy_alert(stock)
        elif not ALERT_ONLY:
            send_text(format_alert(stock))
        
        time.sleep(2)  # 閬垮厤璇锋眰杩囧揩
    
    # 姹囨€绘姤鍛?    print("\n" + "="*50)
    print("馃搳 鐩戞帶姹囨€?)
    print("="*50)
    
    summary = [f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} 鐩戞帶鎶ュ憡\n"]
    
    buy_count = sum(1 for s in results if s.get("status") == "buy")
    stop_count = sum(1 for s in results if s.get("status") == "stop")
    
    print(f"鐩戞帶鑲＄エ鏁? {len(results)}")
    print(f"涔板叆淇″彿: {buy_count} 鍙?)
    print(f"姝㈡崯淇″彿: {stop_count} 鍙?)
    
    for stock in results:
        if stock.get("error"):
            continue
        emoji = "馃幆" if stock["status"] == "buy" else "馃毃" if stock["status"] == "stop" else "鈴?
        print(f"{emoji} {stock['name']}: {stock['current']:.2f} ({stock['status']})")
    
    # 濡傛灉鏈夐噸瑕佷俊鍙凤紝鍙戦€佹眹鎬?    if alerts:
        summary_msg = f"馃毃 **浠婃棩閲嶈淇″彿锛坽len(alerts)}鍙級**\n\n"
        for s in alerts:
            summary_msg += f"- **{s['name']}** {s['current']:.2f}鍏?| {s['signal']}\n"
        summary_msg += f"\n_瑙﹀彂鏃堕棿: {datetime.now().strftime('%H:%M')}_"
        # send_text(summary_msg)  # 宸茬粡鍦ㄤ笂闈㈠崟鐙彂閫佷簡
    
    print("\n鉁?妫€鏌ュ畬鎴?)
    
    # 濡傛灉鏈変拱鍏ユ垨姝㈡崯淇″彿锛宔xit code = 0锛堣Е鍙?Actions锛?    # 娌℃湁淇″彿鏃?exit code = 1锛堝畨闈欓€€鍑猴級
    if alerts:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
