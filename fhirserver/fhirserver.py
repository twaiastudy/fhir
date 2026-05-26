import sqlite3
import json
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse

DB_FILE = "fhir.db"

# ==========================================
# ─── 資料庫初始化 ───
# ==========================================
def init_db():
    """初始化 SQLite 資料庫與資料表"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # 建立 Patient 表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                identifier_system TEXT,
                identifier_value TEXT,
                resource_data TEXT
            )
        ''')
        # 建立 Observation 表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS observations (
                id TEXT PRIMARY KEY,
                subject TEXT,
                resource_data TEXT
            )
        ''')
        conn.commit()
    print("📦 SQLite 資料庫初始化完成")

# FastAPI 伺服器生命週期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # 啟動時執行
    yield

app = FastAPI(title="微型 FHIR 伺服器 (AI Coach 專用 - SQLite 版)", lifespan=lifespan)

# 資料庫連線依賴函數
def get_db():
   
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # 讓結果可以用欄位名稱存取 (例如 row['id'])
    try:
        yield conn
    finally:
        conn.close()

# ==========================================
# ─── Patient 資源的 API 端點 ───
# ==========================================
@app.post("/Patient")
async def create_patient(request: Request, db: sqlite3.Connection = Depends(get_db)):
    """接收從 Gateway 傳來的 Patient JSON 並存入 SQLite"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    # 1. 產生一組全球唯一的伺服器資源 ID
    server_id = str(uuid.uuid4())
    data["id"] = server_id
    
    # 2. 擷取 identifier 供未來快速搜尋 (預設抓第一筆)
    sys, val = "", ""
    identifiers = data.get("identifier", [])
    if identifiers:
        sys = identifiers[0].get("system", "")
        val = identifiers[0].get("value", "")
        
    # 3. 存入資料庫
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO patients (id, identifier_system, identifier_value, resource_data) VALUES (?, ?, ?, ?)",
        (server_id, sys, val, json.dumps(data))
    )
    db.commit()
    
    print(f"[伺服器日誌] 成功建立 Patient, ID: {server_id}")
    return JSONResponse(status_code=201, content=data)

@app.get("/Patient")
async def search_patient(identifier: str = None, db: sqlite3.Connection = Depends(get_db)):
    """處理 Gateway 的病患查詢"""
    results = []
    cursor = db.cursor()
    
    if identifier:
        # 解析 FHIR 的 system|value 格式
        parts = identifier.split("|")
        req_system = parts[0] if len(parts) > 1 else ""
        req_value = parts[-1]
        
        # 依照條件查詢
        if req_system:
            cursor.execute(
                "SELECT resource_data FROM patients WHERE identifier_system = ? AND identifier_value = ?",
                (req_system, req_value)
            )
        else:
            cursor.execute(
                "SELECT resource_data FROM patients WHERE identifier_value = ?", 
                (req_value,)
            )
    else:
        # 若未提供條件，列出所有 Patient (實務上通常會做分頁限制)
        cursor.execute("SELECT resource_data FROM patients")

    # 取出結果並解析 JSON
    rows = cursor.fetchall()
    for row in rows:
        results.append({"resource": json.loads(row["resource_data"])})

    # 封裝成標準 FHIR Search Bundle 回傳
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(results),
        "entry": results
    }
    return bundle


# ==========================================
# ─── Observation (生理訊號) 的 API 端點 ───
# ==========================================
@app.post("/Observation")
async def create_observation(request: Request, db: sqlite3.Connection = Depends(get_db)):
    """接收從 Gateway 傳來的生理訊號並存入 SQLite"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    server_id = str(uuid.uuid4())
    data["id"] = server_id
    
    # 驗證是否有綁定 Patient
    subject_ref = data.get("subject", {}).get("reference", "")
    if not subject_ref.startswith("Patient/"):
        raise HTTPException(status_code=400, detail="Observation 必須包含有效的 subject reference")
        
    # 存入資料庫
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO observations (id, subject, resource_data) VALUES (?, ?, ?)",
        (server_id, subject_ref, json.dumps(data))
    )
    db.commit()
    
    # 擷取 LOINC Code 作為日誌顯示用
    code_display = data.get("code", {}).get("coding", [{}])[0].get("display", "未知訊號")
    print(f"[伺服器日誌] 成功接收生理訊號 ({code_display}), ID: {server_id}")
    
    return JSONResponse(status_code=201, content=data)

@app.get("/Observation")
async def search_observation(subject: str = None, db: sqlite3.Connection = Depends(get_db)):
    """處理 Gateway 的生理訊號查詢 (例如: subject=Patient/12345)"""
    results = []
    cursor = db.cursor()
    
    if subject:
        # 尋找綁定給特定 Patient 的所有 Observation
        cursor.execute("SELECT resource_data FROM observations WHERE subject = ?", (subject,))
    else:
        cursor.execute("SELECT resource_data FROM observations")

    # 取出結果並解析 JSON
    rows = cursor.fetchall()
    for row in rows:
        results.append({"resource": json.loads(row["resource_data"])})

    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(results),
        "entry": results
    }
    return bundle


if __name__ == "__main__":
    import uvicorn
    # 啟動伺服器，預設跑在 8000 port
    print("🚀 啟動自建微型 FHIR Server 於 http://127.0.0.1:8000")
    uvicorn.run("fhirserver:app", host="127.0.0.1", port=8000, reload=True) 
    # 備註: 若檔名不是 main.py，請將上方 "main:app" 修改為 "你的檔名:app"