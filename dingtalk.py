import requests
import json
import os

DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")

def send_text(message):
    """鍙戦€佹枃鏈秷鎭埌閽夐拤"""
    if not DINGTALK_WEBHOOK:
        print("鈿狅笍 鏈厤缃?DINGTALK_WEBHOOK锛岃烦杩囧彂閫?)
        print(message)
        return False
    
    url = DINGTALK_WEBHOOK
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "A鑲＄洃鎺ф彁閱?,
            "text": message
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            print(f"鉁?閽夐拤娑堟伅鍙戦€佹垚鍔?)
            return True
        else:
            print(f"鉂?閽夐拤鍙戦€佸け璐? {result}")
            return False
    except Exception as e:
        print(f"鉂?閽夐拤璇锋眰寮傚父: {e}")
        return False

def send_buy_alert(stock, additional_msg=""):
    """鍙戦€佷拱鍏ユ彁閱?""
    status_emoji = {
        "buy": "馃幆",
        "above": "鈴?,
        "below": "馃憖",
        "stop": "馃毃",
    }
    emoji = status_emoji.get(stock["status"], "馃搳")
    
    msg = f"""{emoji} **{stock['name']}锛坽stock['code']}锛?* 鐩戞帶鎻愰啋

馃搷 褰撳墠浠? **{stock['current']:.2f}** 鍏冿紙浠婃棩 {stock['pct_chg']:+.2f}%锛?
馃幆 涔板叆鍖洪棿: {stock['target_low']} - {stock['target_high']} 鍏?馃洃 姝㈡崯浠? {stock['stop_loss']} 鍏?
馃搻 鍧囩嚎: MA5={stock['ma5']:.2f} MA10={stock['ma10']:.2f} MA20={stock['ma20']:.2f}
馃搳 閲忔瘮: {stock['vol_ratio']:.2f}x | 10鏃ヤ綆={stock['low10']:.2f} 楂?{stock['high10']:.2f}

{stock['signal']}
{additional_msg}
"""
    return send_text(msg)
