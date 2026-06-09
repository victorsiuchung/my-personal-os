"""港股全市場股票分析系統配置檔。"""

from pathlib import Path


# 專案路徑
BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"
CACHE_DIR = BASE_DIR / ".cache"
CHECKPOINT_FILE = CACHE_DIR / "scan_checkpoint.pkl"


# 富途 OpenD 連接
FUTU_HOST = "127.0.0.1"
FUTU_PORT = 11111


# 篩選條件
MIN_MARKET_CAP = 10_0000_0000  # 10 億港元
MIN_TURNOVER = 100_0000  # 100 萬港元
MIN_PRICE = 1.0  # 1 港元
MIN_DAYS_LISTED = 60  # 上市至少 60 日
MIN_AVG_VOLUME_20D = 1_000_000  # 過去 20 日平均成交量


# 分析參數
TOP_N = 20
MAX_WORKERS = 5
RATE_LIMIT = 10  # 每秒最多 10 個 API 請求
KLINE_COUNT = 200
KLINE_CACHE_SECONDS = 300
MARKET = "HK"


# 股票篩選器分頁 / 掃描安全參數
STOCK_FILTER_PAGE_SIZE = 200
SNAPSHOT_BATCH_SIZE = 400  # 富途 market snapshot 官方支援每次最多 400 個
SCAN_RESUME = True


# 行業分類關鍵字，用於報告簡單歸類
INDUSTRY_KEYWORDS = {
    "科技股": ["騰訊", "阿里", "美團", "小米", "京東", "快手", "百度", "網易", "科技"],
    "金融股": ["銀行", "保險", "證券", "金融", "控股", "交易所"],
    "新能源": ["能源", "電力", "光伏", "新能源", "汽車", "電池", "比亞迪", "蔚來"],
    "消費股": ["消費", "零售", "食品", "飲品", "餐飲", "百貨", "藥", "體育"],
}

