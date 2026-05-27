# AI 智慧健康社區 × FHIR Gateway/Server

## 專案簡介
本專案以「智慧宅、健康宅、照護宅」為理念，串聯社區健康中心與住戶，整合生理量測、問卷、AI 分析與 FHIR 標準，打造可擴展的健康資料平台。  
架構分為 FHIR Gateway（資料整合/上傳）與 FHIR Server（資料中台/查詢），可結合 AgentHub 與本地/雲端 AI 模型進行健康分析。

---

## 架構說明

1. **資料感測層**  
	- 血壓計、體重計、身高計、穿戴裝置、App/LINE 問卷  
	- 透過藍芽/API 取得資料

2. **FHIR Gateway（gateway/mac_gateway.py）**  
	- 藍芽讀取生理數據、問卷輸入  
	- 護理/技術人員覆核後，上傳 FHIR Server  
	- 技術：Python、Tkinter/CustomTkinter GUI

3. **FHIR Server（fhirserver/fhirserver.py）**  
	- FastAPI 實作，支援 Patient/Observation 等 FHIR 資源  
	- SQLite（POC）或 PostgreSQL（正式）儲存  
	- 提供 RESTful API 查詢/寫入

4. **AI/AgentHub 協作層**  
	- 可串接 AgentHub 多 Agent 協作、地端 LLM（Ollama、Gemma、Llama3 等）或雲端 API  
	- 進行健康風險分析、個人化建議、醫療審核

---

## 安裝與啟動

### 1. 安裝依賴
```bash
pip install fastapi uvicorn customtkinter requests
```

### 2. 啟動 FHIR Server
```bash
cd fhirserver
uvicorn fhirserver:app --reload
```
伺服器啟動後，API 介面預設於 http://localhost:8000

### 3. 啟動 Gateway GUI
```bash
cd gateway
python mac_gateway.py
```
可於 GUI 介面輸入/讀取生理數據並上傳。

---

## API 範例

- 建立 Patient:  
  `POST /Patient`  
  輸入 FHIR Patient JSON，回傳帶有伺服器 id 的完整物件

- 查詢 Patient:  
  `GET /Patient?identifier=system|value`  
  依 identifier 查詢病患

- 建立 Observation:  
  `POST /Observation`  
  上傳生理量測資料

---

## 典型流程

1. 住戶於社區健康中心量測生理數據，或填寫健康問卷
2. Gateway 由藍芽/手動輸入資料，經人員確認後上傳 FHIR Server
3. FHIR Server 儲存資料，支援 API 查詢
4. AgentHub/AI 取得資料進行分析，產生健康建議
5. 經醫師/管理師審核後，推送建議給住戶或健康管理人員

---

## 進階應用

- 可串接本地 LLM（Ollama、Gemma 等）或雲端 GPT-4o、Claude、Gemini
- 支援多 Agent 協作、健康風險評估、社區服務推薦
- 資料可回寫至 FHIR，形成健康管理閉環

---

## 參考資源

- [AgentHub](https://github.com/speedthunder/agenthub)
- [HL7 FHIR 標準](https://www.hl7.org/fhir/)

---

如需更詳細的 API 文件或架構圖，請參考程式註解與上述連結。
