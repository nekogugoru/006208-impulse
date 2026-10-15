"""抓 006208（富邦台50）最新收盤價，寫入 data/006208.json。

資料來源：臺灣證券交易所 STOCK_DAY（個股日成交資訊）。
只會寫入「已收盤」的交易日資料；今天還沒收盤或休市時，保留前一個交易日的價格。

股票分割：比對相鄰兩個交易日的收盤價，價格突然變成約 1/N（N = 2～20）就視為 1 拆 N，
記到 splits（date = 分割後第一個交易日）。App 會在分割生效日的「隔天」才把舊紀錄的股價換算成新股價。
自動偵測漏掉時，也可以直接編輯 data/006208.json 的 splits 手動加入。
"""
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

STOCK = "006208"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / f"{STOCK}.json"
TPE = timezone(timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (006208-impulse price updater)"}
TOL = 0.12  # 漲跌幅限制 10%，留一點餘裕


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def roc_to_iso(s):
    """'115/10/14' -> '2026-10-14'"""
    y, m, d = s.strip().split("/")
    return f"{int(y) + 1911:04d}-{int(m):02d}-{int(d):02d}"


def to_num(s):
    return float(str(s).replace(",", "").strip())


def month_rows(m):
    url = (
        "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        f"?response=json&date={m:%Y%m}01&stockNo={STOCK}"
    )
    data = get_json(url)
    if data.get("stat") != "OK" or not data.get("data"):
        return []
    fields = data.get("fields", [])
    i_date = fields.index("日期") if "日期" in fields else 0
    i_close = fields.index("收盤價") if "收盤價" in fields else 6
    rows = []
    for row in data["data"]:
        try:
            rows.append((roc_to_iso(row[i_date]), to_num(row[i_close])))
        except (ValueError, IndexError):
            continue  # 例如 '--' 表示當日無成交（分割停止交易期間也是）
    return rows


def recent_rows(now):
    """本月＋上個月的已收盤資料，依日期排序。"""
    prev = now.replace(day=1) - timedelta(days=1)
    rows = {}
    for m in (prev, now):
        for d, c in month_rows(m):
            rows[d] = c
    today = now.strftime("%Y-%m-%d")
    if (now.hour, now.minute) < (13, 30):
        rows.pop(today, None)  # 當天 13:30 前的資料視為尚未收盤
    return sorted(rows.items())


def split_ratio(before, after):
    """收盤從 before 變成 after，像不像分割？是的話回傳 N（1 拆 N）；反分割回傳 1/N。"""
    if before <= 0 or after <= 0:
        return None
    r = before / after
    for n in range(2, 21):
        if abs(r / n - 1) <= TOL:
            return n
        if abs((1 / r) / n - 1) <= TOL:
            return round(1 / n, 6)
    return None


def detect_splits(rows):
    found = []
    for (d0, c0), (d1, c1) in zip(rows, rows[1:]):
        n = split_ratio(c0, c1)
        if n:
            found.append({"date": d1, "ratio": n, "from": c0, "to": c1, "source": "auto"})
    return found


def merge_splits(old, new):
    by_date = {s["date"]: s for s in old}
    for s in new:
        by_date.setdefault(s["date"], s)  # 已存在（含手動填寫）的不覆蓋
    return sorted(by_date.values(), key=lambda s: s["date"])


def main():
    now = datetime.now(TPE)
    rows = recent_rows(now)
    if not rows:
        raise RuntimeError("找不到收盤價資料")
    date_iso, close = rows[-1]

    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    old_splits = old.get("splits", [])

    found = detect_splits(rows)
    # Actions 停擺好幾天時，再用上次存的價格比一次
    if old.get("close") and old.get("date") and old["date"] < rows[0][0]:
        n = split_ratio(old["close"], rows[0][1])
        if n:
            found.append({"date": rows[0][0], "ratio": n, "from": old["close"], "to": rows[0][1], "source": "auto"})
    splits = merge_splits(old_splits, found)
    for s in splits:
        if s not in old_splits:
            print(f"偵測到分割：{s['date']} 起 1 拆 {s['ratio']}（{s.get('from')} → {s.get('to')}）")

    if old.get("date") == date_iso and old.get("close") == close and splits == old_splits:
        print(f"沒有新資料，維持 {date_iso} 收盤 {close}")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "stock": STOCK,
                "close": close,
                "date": date_iso,
                "updatedAt": now.isoformat(timespec="seconds"),
                "source": "TWSE STOCK_DAY",
                "splits": splits,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"已更新：{date_iso} 收盤 {close}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
