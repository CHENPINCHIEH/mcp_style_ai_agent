import sqlite3
import re
import os
import json
from typing import Dict, Optional
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Retrieval Agent
# -----------------------------
class RetrievalAgent:
    def __init__(self, db_name="returns.db"):
        # 連線到 SQLite，檔案會自動建立
        self.conn = sqlite3.connect(db_name)
        self.create_table()
    
    def create_table(self):
        # 建立 table，如果已存在就忽略
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    order_id TEXT PRIMARY KEY,
                    product TEXT,
                    category TEXT,
                    return_reason TEXT,
                    cost REAL,
                    approved_flag TEXT,
                    store_name TEXT,
                    date TEXT
                )
            ''')

    # 從 CSV 初始化資料
    def ingest_csv(self, csv_path):
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            self.add_return({
                "order_id": str(row["order_id"]),
                "product": row["product"],
                "category": row["category"],
                "return_reason": row["return_reason"],
                "cost": float(row["cost"]),
                "approved_flag": row["approved_flag"],
                "store_name": row["store_name"],
                "date": row["date"]
            })
    
    # 新增退貨紀錄
    def add_return(self, record):
        with self.conn:
            self.conn.execute('''
                INSERT OR REPLACE INTO returns
                (order_id, product, category, return_reason, cost, approved_flag, store_name, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record["order_id"],
                record["product"],
                record.get("category", ""),
                record.get("return_reason", ""),
                record.get("cost", 0),
                record.get("approved_flag", ""),
                record["store_name"],
                record["date"]
            ))
        return self.get_all()
    
    # 取得所有紀錄
    def get_all(self):
        return pd.read_sql_query("SELECT * FROM returns", self.conn)

    def count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM returns")
        row = cur.fetchone()
        return int(row[0]) if row else 0

# -----------------------------
# Report Agent
# -----------------------------
class ReportAgent:
    def generate_report(self, df: pd.DataFrame, output_file="report.xlsx"):
        if df.empty:
            print("No data to generate report")
            return
        # Summary: count by product
        summary = df.groupby("product").size().reset_index(name="return_count")
        with pd.ExcelWriter(output_file) as writer:
            df.to_excel(writer, sheet_name="Returns", index=False)
            summary.to_excel(writer, sheet_name="Summary", index=False)
        print(f"Report saved to {output_file}")

# -----------------------------
# Coordinator
# -----------------------------
class Coordinator:
    def __init__(self, retrieval_agent, report_agent, ai_agent: Optional[object] = None):
        self.retrieval_agent = retrieval_agent
        self.report_agent = report_agent
        self.ai_agent = ai_agent if ai_agent is not None else AiIntentAgent()

    def handle_request(self, command, data=None):
        if command == "add_return":
            return self.retrieval_agent.add_return(data)
        elif command == "generate_report":
            df = self.retrieval_agent.get_all()
            self.report_agent.generate_report(df)
        elif command == "ingest_csv":
            self.retrieval_agent.ingest_csv(data)
        else:
            return "Unknown command"

    # -----------------------------
    # 對話模式：自然語言處理
    # -----------------------------
    def handle_message(self, message: str) -> str:
        text = message.strip()
        lowered = text.lower()

        # 系統會先用 AI 嘗試判斷使用者要做什麼（意圖），並抓出需要的關鍵資料（槽位）。如果沒有設定好 API，或是 AI 判斷失敗，就會改用傳統的關鍵字／規則比對方式來處理。
        if self.ai_agent and self.ai_agent.is_available:
            ai_result = self.ai_agent.analyze(text)
            if ai_result:
                intent = (ai_result.get("intent") or "").lower()
                fields = ai_result.get("fields") or {}

                if intent == "add_return":
                    # 嘗試用 AI 輸出的欄位建立紀錄，若不足再用規則補齊
                    merged = {
                        "order_id": fields.get("order_id", ""),
                        "product": fields.get("product", ""),
                        "store_name": fields.get("store_name", ""),
                        "date": fields.get("date", ""),
                        "category": fields.get("category", ""),
                        "return_reason": fields.get("return_reason", ""),
                        "cost": fields.get("cost", 0),
                        "approved_flag": fields.get("approved_flag", ""),
                    }

                    # 用規則式再嘗試補齊缺少的必填欄位
                    if not all(merged.get(k) for k in ["order_id", "product", "store_name", "date"]):
                        parsed = self._parse_add_return(text)
                        if isinstance(parsed, dict):
                            for k in ["order_id", "product", "store_name", "date"]:
                                if not merged.get(k) and parsed.get(k):
                                    merged[k] = parsed[k]
                        else:
                            # 規則式也失敗就回覆提示
                            return parsed

                    missing = [k for k in ["order_id", "product", "store_name", "date"] if not merged.get(k)]
                    if missing:
                        return f"缺少必要欄位：{', '.join(missing)}。請提供例如：order_id=R12345, product=滑鼠, store_name=台中店, date=2025-08-19"

                    record = {
                        "order_id": str(merged["order_id"]),
                        "product": merged["product"],
                        "category": merged.get("category", ""),
                        "return_reason": merged.get("return_reason", ""),
                        "cost": float(merged.get("cost", 0) or 0),
                        "approved_flag": merged.get("approved_flag", ""),
                        "store_name": merged["store_name"],
                        "date": merged["date"],
                    }
                    self.retrieval_agent.add_return(record)
                    total = self.retrieval_agent.count()
                    return f"已新增 目前資料總數 {total} 筆"

                if intent in {"list_all", "list", "show_all"}:
                    df = self.retrieval_agent.get_all()
                    if df.empty:
                        return "目前沒有資料"
                    return df.to_string(index=False)

                if intent in {"export_report", "export", "generate_report"}:
                    df = self.retrieval_agent.get_all()
                    output = "report.xlsx"
                    self.report_agent.generate_report(df, output_file=output)
                    return f"已匯出報表：{output}"
        if ("新增" in text or "加入" in text) and ("退貨" in text or "退貨紀錄" in text or "退貨資料" in text):
            record_or_error = self._parse_add_return(text)
            if isinstance(record_or_error, dict):
                self.retrieval_agent.add_return(record_or_error)
                total = self.retrieval_agent.count()
                return f"已新增 目前資料總數 {total} 筆"
            return record_or_error

        if ("列出" in text or "顯示" in text or "查看" in text) and ("所有" in text or "全部" in text or "資料" in text or "清單" in text):
            df = self.retrieval_agent.get_all()
            if df.empty:
                return "目前沒有資料"
            return df.to_string(index=False)

        if ("匯出" in text or "輸出" in text) and ("excel" in lowered or "報表" in text):
            df = self.retrieval_agent.get_all()
            output = "report.xlsx"
            self.report_agent.generate_report(df, output_file=output)
            return f"已匯出報表：{output}"

        return "抱歉，我目前支援：新增退貨、列出所有資料、將資料匯出成 Excel。"

    def _parse_add_return(self, text: str) -> Dict[str, str] | str:
        """從中文自然語言解析新增退貨所需欄位。
        必填：order_id, product, store_name, date (YYYY-MM-DD)
        若缺少必填欄位則回傳錯誤字串。
        """
        # 先嘗試解析 key=value 形式
        kv_pattern = r"(?P<key>order_id|product|store_name|date)\s*[:=]\s*(?P<val>[^,，\s]+)"
        fields: Dict[str, str] = {}
        for m in re.finditer(kv_pattern, text, flags=re.IGNORECASE):
            key = m.group("key").lower()
            val = m.group("val").strip()
            fields[key] = val

        # 自然語言關鍵片段
        if "order_id" not in fields:
            m = re.search(r"(訂單編號(?:是|為)?\s*|order_id\s*[:=]\s*)(?P<id>[A-Za-z][0-9A-Za-z_-]+)", text)
            if m:
                fields["order_id"] = m.group("id")

        if "date" not in fields:
            m = re.search(r"(退貨日期(?:是|為)?\s*|date\s*[:=]\s*)(?P<date>\d{4}-\d{2}-\d{2})", text)
            if m:
                fields["date"] = m.group("date")

        if "store_name" not in fields:
            # 來自台中店 / 在台中店
            m = re.search(r"(?:來自|在)(?P<store>[^\s的，,。]+店)", text)
            if m:
                fields["store_name"] = m.group("store")

        if "product" not in fields:
            # 的滑鼠退貨 / 的XXX退貨
            m = re.search(r"的(?P<prod>[^\s的，,。]+)退貨", text)
            if m:
                fields["product"] = m.group("prod")

        # 驗證必填
        required = ["order_id", "product", "store_name", "date"]
        missing = [k for k in required if k not in fields or not fields[k]]
        if missing:
            return f"缺少必要欄位：{', '.join(missing)}。請提供例如：order_id=R12345, product=滑鼠, store_name=台中店, date=2025-08-19"

        # 組裝成完整紀錄（選填給預設值）
        record: Dict[str, str] = {
            "order_id": fields["order_id"],
            "product": fields["product"],
            "category": "",
            "return_reason": "",
            "cost": 0,
            "approved_flag": "",
            "store_name": fields["store_name"],
            "date": fields["date"],
        }
        return record


# -----------------------------
# AI 意圖辨識 Agent（可選）
# -----------------------------
class AiIntentAgent:
    """以雲端 LLM 做意圖辨識與槽位抽取。

    - 透過環境變數設定：
      OPENAI_API_KEY：API 金鑰（必填，否則此 Agent 視為不可用）
      OPENAI_MODEL：模型名稱（預設 gpt-4o-mini）
      OPENAI_BASE_URL：自訂 API Base URL（選填，支援相容介面）

    - 若未設定金鑰或呼叫失敗，請呼叫端自行 fallback。
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        self.base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        self._openai = None
        self._client = None
        self._use_client = False
        self._warned_unavailable = False

        if not self.api_key:
            print("[AiIntentAgent] 未設定 OPENAI_API_KEY，AI 意圖辨識停用（將使用規則式解析）。")
            return

        try:
            # 延遲載入，避免專案在無 openai 套件時也能運作
            import openai  # type: ignore
            # 新版 SDK（1.x）使用 OpenAI 客戶端
            try:
                from openai import OpenAI  # type: ignore
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
                self._use_client = True
            except Exception as e:
                # 新版初始化失敗，嘗試舊版相容層
                print(f"[AiIntentAgent] 無法初始化新版 OpenAI 客戶端，改用舊版相容 API。原因：{e}")
                openai.api_key = self.api_key
                if self.base_url:
                    openai.base_url = self.base_url
                self._openai = openai
                self._use_client = False
        except Exception as e:
            print(f"[AiIntentAgent] 無法載入 openai 套件或初始化失敗，AI 意圖辨識停用。原因：{e}")
            self.api_key = ""
            self._openai = None
            self._client = None
            self._use_client = False

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(self, text: str) -> Optional[Dict]:
        if not self.is_available:
            if not getattr(self, "_warned_unavailable", False):
                print("[AiIntentAgent] OpenAI API 不可用（未設定或初始化失敗），跳過 AI 分析，使用規則式解析。")
                self._warned_unavailable = True
            return None

        system_prompt = (
            "你是意圖辨識與槽位抽取助手。根據使用者中文輸入，輸出純 JSON（不要任何多餘文字）。"
            "JSON 結構如下：{"
            "\"intent\": 一個字符串，取值只能是 [add_return, list_all, export_report, unknown],"
            "\"fields\": {\"order_id\": 字串, \"product\": 字串, \"store_name\": 字串, \"date\": YYYY-MM-DD, \"category\": 字串, \"return_reason\": 字串, \"cost\": 數字, \"approved_flag\": 字串}"
            "}. 若無對應欄位請留空或省略。"
        )

        try:
            if hasattr(self, "_client") and self._client and getattr(self, "_use_client", False):
                # 優先使用新版 SDK 的 chat.completions 介面
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    temperature=0.2,
                    max_tokens=300,
                )
                content = resp.choices[0].message.content if resp and resp.choices else ""
            elif self._openai:
                # 舊版相容呼叫
                resp = self._openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    temperature=0.2,
                    max_tokens=300,
                )
                content = resp["choices"][0]["message"]["content"] if resp else ""
            else:
                return None

            if not content:
                print("[AiIntentAgent] 收到空白的模型回覆，無法進行解析。")
                return None
            # 嘗試抽取第一個 JSON 物件
            content_str = content.strip()
            # 有些模型會在前後加上程式碼區塊標記
            if content_str.startswith("```"):
                content_str = content_str.strip("`\n ")
                if content_str.lower().startswith("json"):
                    content_str = content_str[4:].strip()
            try:
                data = json.loads(content_str)
            except Exception as e:
                preview = content_str[:200].replace("\n", " ")
                print(f"[AiIntentAgent] 解析模型輸出為 JSON 失敗。片段：{preview} 錯誤：{e}")
                return None
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"[AiIntentAgent] 呼叫模型發生錯誤：{e}")
            return None

        return None

# -----------------------------
# 使用範例
# -----------------------------
if __name__ == "__main__":
    retrieval = RetrievalAgent()
    report = ReportAgent()
    coord = Coordinator(retrieval, report)

    # 1. 從 CSV 初始化資料（若需要）
    try:
        coord.handle_request("ingest_csv", "sample.csv")
    except Exception:
        pass

    # 2. 簡易對話迴圈（可作為 MCP 伺服端接入的訊息處理器範例）
    print("對話模式已啟動。輸入 'exit' 離開。")
    while True:
        try:
            user = input("你：").strip()
        except EOFError:
            break
        if not user:
            continue
        if user.lower() in {"exit", "quit"}:
            break
        reply = coord.handle_message(user)
        print(f"系統：{reply}")
