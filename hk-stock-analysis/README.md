# 港股全市場股票分析系統

這是一個使用 Futu OpenAPI 的港股全市場技術分析系統。系統會掃描港股主板股票，套用流動性與基本條件過濾，逐隻計算技術指標，最後生成 Markdown 推薦報告。

## 功能

- 連接本地 Futu OpenD，預設 `127.0.0.1:11111`
- 支援港股代碼格式，例如 `HK.00700`、`HK.09988`
- 優先使用富途股票篩選器 API
- fallback 至全市場股票列表 + market snapshot 批量過濾
- 多線程掃描，預設 5 threads
- 限流控制，預設每秒最多 10 個 API request
- K 線快取 5 分鐘
- 使用 checkpoint 支援中斷後續掃
- 生成 Markdown 報告到 `reports/`

## 專案結構

```text
hk-stock-analysis/
├── config.py
├── futu_connector.py
├── stock_scanner.py
├── stock_analyzer.py
├── screener.py
├── recommender.py
├── report_generator.py
├── main.py
├── requirements.txt
├── README.md
└── reports/
```

## 安裝

請先安裝並啟動 Futu OpenD，並確認 OpenD 可在本機連接。

```bash
cd hk-stock-analysis
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 執行

```bash
python main.py
```

指定 OpenD 連接：

```bash
python main.py --host 127.0.0.1 --port 11111
```

顯示詳細 log：

```bash
python main.py --verbose
```

## 本機 Dashboard API

若要讓 GitHub Pages dashboard 接近實時讀取 Futu OpenD 數據，先啟動本機 API：

```bash
python dashboard_server.py
```

預設 API：

```text
http://127.0.0.1:8765/api/recommendations
http://127.0.0.1:8765/api/news
http://127.0.0.1:8765/api/health
```

Dashboard 會嘗試連接這個本機 API；如果連不到，就仍可手動匯入 `reports/*.md`。

對應 Web UI：

```text
https://victorsiuchung.github.io/my-personal-os/hk-stock-analyst-dashboard.html
```

在頁面按 `Connect Futu API`，即可嘗試讀取本機 `127.0.0.1:8765`。

## 交易計劃價位

系統會根據 K 線估算：

- 買入價：目前實時價 / 快照價
- 止蝕價：MA20 / 20 日低位支撐下方
- 止賺一階：風險回報約 1.5R 或近期阻力
- 止賺二階：風險回報約 2.5R

這些價位只是風險管理參考，不是保證可成交或盈利的建議。

## 財經消息來源

Dashboard / API 會顯示可信消息來源入口，並嘗試抓取公開標題：

- Bloomberg Markets
- Reuters Markets
- HKEX RSS / HKEXnews
- AAStocks Latest News

消息會用簡單關鍵字計算 `news_score`，再加到技術評分中。正式投資前應人工核實消息原文。

## 配置

可在 `config.py` 修改：

```python
MIN_MARKET_CAP = 10_0000_0000
MIN_TURNOVER = 100_0000
MIN_PRICE = 1.0
MIN_DAYS_LISTED = 60
TOP_N = 20
MAX_WORKERS = 5
RATE_LIMIT = 10
```

## 報告內容

報告會包含：

- 執行摘要
- Top 10 強烈推薦列表
- 分類推薦
- 各行業最佳推薦
- MACD 金叉股
- RSI 超賣反彈機會股
- 成交量異動股
- 布林帶突破股
- 買入價、止蝕價、止賺一階、止賺二階
- 風險提示

## 注意事項

- 富途 `get_cur_kline` 可能需要行情權限或訂閱，若個別股票 K 線獲取失敗，系統會跳過該股票繼續掃描。
- 富途 API 版本可能有欄位差異，`futu_connector.py` 已做保護式封裝，但如你的版本欄位名稱不同，可能需要微調。
- 本系統只作技術分析與研究用途，不構成投資建議。
- 新聞來源只作輔助參考。Bloomberg real-time machine-readable news feeds 通常屬付費 Bloomberg Professional / Enterprise 產品；本系統的免費模式只會抓取公開標題或保留來源入口。
