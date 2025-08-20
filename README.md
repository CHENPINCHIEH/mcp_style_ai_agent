# Returns & Warranty Insights (MCP-style)

## 簡介
這是一個 Python 小程式，採用 MCP-style 架構，包含兩個 Agent 與一個 Coordinator：

1. **Retrieval Agent**：  
   - 讀取 CSV 資料  
   - 管理 SQLite 資料庫  
   - 支援新增退貨紀錄  
   - 可取得所有退貨資料

2. **Report Agent**：  
   - 將資料生成 Excel 報表  
   - 包含 `Returns`（所有退貨紀錄）與 `Summary`（每個 product 的退貨數量）

3. **Coordinator**：  
   - 接收指令（Command）  
   - 分派給相應 Agent 執行

---

## 安裝需求

方式 A：使用 uv（建議）

```bash
uv venv
uv pip install -r requirements.txt
```

方式 B：使用 pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

方式 C：使用 Makefile（推薦快速上手）

```bash
make install
```

## 使用方法（含 Makefile）

1. 初始化資料:

將 CSV 資料 ingest 進 SQLite：

```bash
make ingest 
```

2. 新增退貨（對話與 API）

自然語言對話範例：

- 「我要新增一筆來自台中店的滑鼠退貨 訂單編號是R12346 退貨日期是 2025-08-19」
- 「新增一筆退貨：order_id=R12346, product=滑鼠, store_name=台中店, date=2025-08-19」

執行互動模式（本地端）：

```bash
make dialog
# 或
python mcp_returns.py
```
範例：

new_return = {
    "order_id": "R12346",
    "product": "滑鼠",
    "category": "配件",
    "return_reason": "故障",
    "cost": 120,
    "approved_flag": "Yes",
    "store_name": "台中店",
    "date": "2025-08-19"
}
coord.handle_request("add_return", new_return)

3. 列出與匯出

對話：

- 「列出所有資料」：會將目前 SQLite 內所有資料列出
- 「將資料匯出成 excel」：會生成 `report.xlsx`

API：

```python
coord.handle_request("generate_report")
```

生成 report.xlsx

Returns sheet：所有退貨紀錄

Summary sheet：每個 product 的退貨數量

### Makefile 指令

```bash
make help         # 顯示所有目標
make install      # 建立 venv 並安裝相依套件
make ingest       # 將 sample.csv 匯入 SQLite
make list         # 列出所有資料（走對話意圖）
make export       # 匯出 report.xlsx（走對話意圖）
make add-example  # 以中文自然語言新增一筆示例退貨
make dialog       # 啟動互動式對話模式
make test         # 執行測試腳本
make clean        # 刪除 returns.db 與 report.xlsx
```

## 對話意圖與解析規則

新增退貨需提供：

必填：order_id, product, store_name, date

選填：category, return_reason, cost, approved_flag

支援的意圖：新增退貨、列出所有資料、將資料匯出成 Excel。

必填欄位：order_id, product, store_name, date（YYYY-MM-DD）

可接受 key=value 或中文片語，例如「來自台中店的滑鼠退貨」「訂單編號是R12345」「退貨日期是 2025-08-19」。

## 專案檔案說明

- `mcp_returns.py`：核心程式，包含 `RetrievalAgent`、`ReportAgent`、`Coordinator` 與 `handle_message` 對話解析，直接執行可進入對話模式。
- `sample.csv`：範例退貨資料，提供初始化匯入。
- `returns.db`：SQLite 資料庫（執行後產生）。
- `report.xlsx`：匯出的 Excel 報表（執行匯出後產生）。
- `test_mcp_returns.py`：示範與驗證腳本（含對話模式測試）。
- `requirements.txt`：相依套件清單。
- `Makefile`：常用工作流程指令集合。

## 測試方法

確認 mcp_returns.py 與 sample.csv 在同一資料夾

### 執行：

python test_mcp_returns.py


### 驗證：

1. CSV 是否成功 ingest

2. 新增退貨是否成功

3. report.xlsx 是否生成

### 輸出說明

SQLite 資料庫檔案：returns.db

Excel 報表檔案：report.xlsx

Returns sheet：所有退貨紀錄

Summary sheet：每個 product 的退貨數量

### 注意事項

order_id 若重複，會使用 INSERT OR REPLACE 更新資料

缺少選填欄位會使用預設值（空字串或 0）