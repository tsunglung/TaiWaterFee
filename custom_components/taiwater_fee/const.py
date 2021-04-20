"""Constants of the TaiWater Fee component."""

DEFAULT_NAME = "TaiWater Fee"
DOMAIN = "taiwater_fee"
DOMAINS = ["sensor"]
DATA_KEY = "sensor.taiwater_fee"

ATTR_BILLING_MONTH = "billing_month"
ATTR_BILLING_DATE = "billing_date"
ATTR_PAYMENT = "payment"
ATTR_WATER_CONSUMPTION = "water_consumption"
ATTR_DURATION = "duration"
ATTR_BILL_AMOUNT = "billing_amount"
ATTR_HTTPS_RESULT = "https_result"
ATTR_LIST = [
    ATTR_BILLING_MONTH,
    ATTR_BILLING_DATE,
    ATTR_PAYMENT,
    ATTR_WATER_CONSUMPTION,
    ATTR_DURATION,
    ATTR_BILL_AMOUNT,
    ATTR_HTTPS_RESULT
]

CONF_WATERID = "waterid"
CONF_COOKIE = "cookie"
CONF_CSRF = "csrf"
CONF_VERIFYTOKEN1 = "verifytoken1"
CONF_VERIFYTOKEN2 = "verifytoken2"
ATTRIBUTION = "Powered by TaiWater Fee Data"

HA_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36 OPR/38.0.2220.41"
BASE_URL = 'https://www.water.gov.tw/ch/EQuery/WaterFeeQuerySearch?nodeid=753'

REQUEST_TIMEOUT = 10  # seconds
