from mcp_returns import RetrievalAgent, ReportAgent, Coordinator
from datetime import datetime
import os

# 1. 刪掉舊資料庫（如果存在）
if os.path.exists("returns.db"):
    os.remove("returns.db")

# 2. 初始化 agent 與 coordinator
retrieval = RetrievalAgent()
report = ReportAgent()
coord = Coordinator(retrieval, report)

# 3. 從 CSV 初始化資料
coord.handle_request("ingest_csv", "sample.csv")
df = retrieval.get_all()
print("CSV ingest 完成，資料如下：")
print(df)

# 4. 新增多筆退貨（指令）
new_returns = [
    {
        "order_id": "R12346",
        "product": "滑鼠",
        "category": "配件",
        "return_reason": "故障",
        "cost": 120,
        "approved_flag": "Yes",
        "store_name": "台中店",
        "date": "2025-08-19"
    },
    {
        "order_id": "R12347",
        "product": "耳機",
        "category": "電子",
        "return_reason": "損壞",
        "cost": 250,
        "approved_flag": "No",
        "store_name": "高雄店",
        "date": "2025-08-19"
    }
]

for ret in new_returns:
    coord.handle_request("add_return", ret)

df = retrieval.get_all()
print("新增退貨後，資料如下：")
print(df)

# 5. 生成報表（指令）
coord.handle_request("generate_report")

# 6. 驗證報表是否存在
if os.path.exists("report.xlsx"):
    print("報表已成功生成: report.xlsx")
else:
    print("報表生成失敗")

# 6. 對話模式測試
reply = coord.handle_message("我要新增一筆來自台中店的滑鼠退貨 訂單編號是R99999 退貨日期是 2025-08-19")
print("Dialog reply:", reply)
assert "已新增" in reply

reply_list = coord.handle_message("列出所有資料")
print("List reply:\n", reply_list[:120])
assert "order_id" in reply_list

reply_export = coord.handle_message("將資料匯出成 excel")
print("Export reply:", reply_export)
assert "已匯出報表" in reply_export
