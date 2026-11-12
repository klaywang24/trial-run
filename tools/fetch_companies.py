"""One-off: company names and logos for the dashboard. Not run by CI.

Names and websites come from Yahoo (yfinance .info: longName, website). ETFs have no website in Yahoo, so the
issuer's domain is filled in by hand and marked source=issuer. Chinese names are common usage, filled in by hand;
blank where there is no settled Chinese name. Logos are the site's favicon via Google's favicon service
(Clearbit's logo API is shut down), cached in assets/logos/ so the daily run needs no network for them.
Run: .venv/bin/python -m tools.fetch_companies
"""
import csv, pathlib, time, urllib.request
import yfinance as yf

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT, LOGOS = ROOT / "data/meta/companies.csv", ROOT / "assets/logos"
ZH = {"AAPL": "苹果", "NVDA": "英伟达", "MSFT": "微软", "META": "Meta", "AMZN": "亚马逊", "GOOGL": "谷歌母公司 Alphabet",
      "AMD": "AMD", "NET": "Cloudflare", "MU": "美光", "LRCX": "泛林", "APP": "AppLovin", "GEV": "GE Vernova",
      "LITE": "Lumentum", "PLTR": "Palantir", "TSM": "台积电", "AVGO": "博通", "SPCX": "SpaceX", "GRMN": "佳明",
      "MSGK": "尼克斯队母公司 MSG", "V": "Visa", "MA": "万事达", "AXP": "美国运通", "LLY": "礼来",
      "XLE": "能源行业 ETF", "SPDV": "标普500高股息价值 ETF", "KO": "可口可乐", "BRK-B": "伯克希尔",
      "BIL": "1-3 个月美债 ETF", "SPY": "标普500 ETF", "QQQ": "纳指100 ETF"}
ISSUER = {"XLE": "https://www.ssga.com", "BIL": "https://www.ssga.com", "SPY": "https://www.ssga.com",
          "SPDV": "https://www.aamlive.com", "QQQ": "https://www.invesco.com"}


def main():
    rows = []
    for t in ZH:
        i = yf.Ticker(t).info
        site, src = i.get("website"), "yahoo"
        if not site:
            site, src = ISSUER[t], "issuer"
        dom = site.split("//")[-1].split("/")[0].removeprefix("www.")
        rows.append({"ticker": t, "name_en": i.get("longName") or i.get("shortName"), "name_zh": ZH[t],
                     "website": site, "domain": dom, "type": i.get("quoteType", ""), "website_source": src,
                     "fetched": time.strftime("%Y-%m-%d")})
        png = LOGOS / f"{t}.png"
        req = urllib.request.Request(f"https://www.google.com/s2/favicons?domain={dom}&sz=64",
                                     headers={"User-Agent": "trial-run-dashboard"})
        try:
            png.write_bytes(urllib.request.urlopen(req, timeout=20).read())
            print(t, rows[-1]["name_en"], dom, png.stat().st_size, "bytes")
        except Exception as e:           # no favicon: the dashboard draws a letter badge instead
            png.unlink(missing_ok=True); rows[-1]["logo"] = ""
            print(t, rows[-1]["name_en"], dom, "no logo:", e); continue
        rows[-1]["logo"] = f"assets/logos/{t}.png"
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
