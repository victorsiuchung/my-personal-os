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


# Hang Seng Index constituents.
# Source: Hang Seng Indexes Company review result dated 2026-05-22.
# Effective date: 2026-06-08. Number of constituents: 93.
HSI_CONSTITUENTS = [
    "HK.00001", "HK.00002", "HK.00003", "HK.00005", "HK.00006", "HK.00011",
    "HK.00012", "HK.00016", "HK.00027", "HK.00066", "HK.00101", "HK.00175",
    "HK.00241", "HK.00267", "HK.00285", "HK.00288", "HK.00291", "HK.00300",
    "HK.00316", "HK.00322", "HK.00386", "HK.00388", "HK.00669", "HK.00688",
    "HK.00700", "HK.00728", "HK.00762", "HK.00823", "HK.00836", "HK.00857",
    "HK.00868", "HK.00883", "HK.00939", "HK.00941", "HK.00960", "HK.00968",
    "HK.00981", "HK.00992", "HK.01024", "HK.01038", "HK.01044", "HK.01088",
    "HK.01093", "HK.01099", "HK.01109", "HK.01113", "HK.01177", "HK.01209",
    "HK.01211", "HK.01299", "HK.01378", "HK.01398", "HK.01519", "HK.01801",
    "HK.01810", "HK.01876", "HK.01928", "HK.01929", "HK.01997", "HK.02015",
    "HK.02020", "HK.02057", "HK.02269", "HK.02313", "HK.02318", "HK.02319",
    "HK.02359", "HK.02382", "HK.02388", "HK.02600", "HK.02618", "HK.02628",
    "HK.02688", "HK.02899", "HK.03690", "HK.03692", "HK.03750", "HK.03968",
    "HK.03988", "HK.03993", "HK.06160", "HK.06181", "HK.06618", "HK.06690",
    "HK.06862", "HK.09618", "HK.09633", "HK.09888", "HK.09901", "HK.09961",
    "HK.09988", "HK.09992", "HK.09999",
]


# 行業分類關鍵字，用於報告簡單歸類
INDUSTRY_KEYWORDS = {
    "科技股": ["騰訊", "阿里", "美團", "小米", "京東", "快手", "百度", "網易", "科技"],
    "金融股": ["銀行", "保險", "證券", "金融", "控股", "交易所"],
    "新能源": ["能源", "電力", "光伏", "新能源", "汽車", "電池", "比亞迪", "蔚來"],
    "消費股": ["消費", "零售", "食品", "飲品", "餐飲", "百貨", "藥", "體育"],
}
