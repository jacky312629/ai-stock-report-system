import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 以 src 的上一層作為專案根目錄
PROJECT_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = PROJECT_DIR / ".env"
TOKEN_PATH = PROJECT_DIR / "token.json"
REPORT_TXT_PATH = PROJECT_DIR / "report.txt"
REPORT_HTML_PATH = PROJECT_DIR / "report.html"
STOCK_CANDIDATES_PATH = PROJECT_DIR / "stock_candidates.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

load_dotenv(dotenv_path=ENV_PATH)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("未設定 OPENAI_API_KEY，請確認 github_project/.env")

client = OpenAI(api_key=api_key)