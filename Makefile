# Makefile for MCP-style returns project

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help uv venv install dialog ingest list export add-example test clean clean-db clean-report

help:
	@echo "Targets:"
	@echo "  make install      # 建立 venv 並安裝相依套件"
	@echo "  make dialog       # 進入對話模式 (啟動互動式 chatbot)"
	@echo "  make ingest       # 將 sample.csv 匯入 SQLite"
	@echo "  make list         # 列出所有資料"
	@echo "  make export       # 匯出 Excel 報表 report.xlsx"
	@echo "  make add-example  # 用中文自然語言新增一筆示例退貨"
	@echo "  make test         # 執行測試腳本"
	@echo "  make clean        # 刪除 returns.db、report.xlsx 與 .venv"

uv:
	uv venv
	uv pip install -r requirements.txt

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# 啟動互動式對話模式
dialog: install
	$(PYTHON) mcp_returns.py

# 將 sample.csv 匯入資料庫
ingest: install
	$(PYTHON) - <<-'PY'
	from mcp_returns import RetrievalAgent, ReportAgent, Coordinator
	coord = Coordinator(RetrievalAgent(), ReportAgent())
	coord.handle_request("ingest_csv", "sample.csv")
	print("CSV ingest 完成")
	PY

# 列出所有資料（經由對話意圖）
list: install
	$(PYTHON) - <<-'PY'
	from mcp_returns import RetrievalAgent, ReportAgent, Coordinator
	coord = Coordinator(RetrievalAgent(), ReportAgent())
	print(coord.handle_message("列出所有資料"))
	PY

# 匯出報表（經由對話意圖）
export: install
	$(PYTHON) - <<-'PY'
	from mcp_returns import RetrievalAgent, ReportAgent, Coordinator
	coord = Coordinator(RetrievalAgent(), ReportAgent())
	print(coord.handle_message("將資料匯出成 excel"))
	PY

# 用中文自然語言新增一筆示例退貨
add-example: install
	$(PYTHON) - <<-'PY'
	from mcp_returns import RetrievalAgent, ReportAgent, Coordinator
	coord = Coordinator(RetrievalAgent(), ReportAgent())
	coord.handle_request("ingest_csv", "sample.csv")
	print(coord.handle_message("我要新增一筆來自台中店的滑鼠退貨 訂單編號是R12346 退貨日期是 2025-08-19"))
	PY

# 執行測試
test: install
	$(PYTHON) test_mcp_returns.py

# 清除輸出
clean: clean-db clean-report
	rm -rf .venv
	@echo "已清除 returns.db、report.xlsx 與 .venv 虛擬環境"

clean-db:
	rm -f returns.db

clean-report:
	rm -f report.xlsx
