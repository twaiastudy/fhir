import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, ttk
import requests
import datetime
import threading
import random
import json

# ==========================================
# ─── Global Configuration ───
# ==========================================
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

SYSTEM_PATIENT = "https://aicoach.aiatw.org/patient-id"
SYSTEM_STAFF = "https://aicoach.aiatw.org/staff-id"

class AdvancedFHIRGateway(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("生理訊號上傳閘道器與 AI 分析系統")
        self.geometry("1100x880") 
        
        # 預設 FHIR 伺服器
        self.fhir_server_base = "http://localhost:8000"
        
        # LLM 設定變數
        self.llm_provider = tk.StringVar(value="Ollama")
        self.llm_model = tk.StringVar(value="llama3")
        self.llm_api_key = tk.StringVar(value="")
        self.ollama_url = tk.StringVar(value="http://localhost:11434")
        
        self.font_title = ("Arial", 22, "bold")
        self.font_body = ("Arial", 18, "bold")
        self.font_input = ("Arial", 20)
        self.font_table = ("Arial", 14)
        
        self.tabview = ctk.CTkTabview(self, width=1060, height=830)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_upload = self.tabview.add("📤 資料量測與上傳")
        self.tab_query = self.tabview.add("🔍 歷史結果查詢")
        self.tab_llm = self.tabview.add("🤖 智能分析與建議")
        self.tab_settings = self.tabview.add("⚙️ 系統設定")
        
        self.is_verified = False
        
        # 病患資訊變數
        self.pat_name_var = tk.StringVar(value="尚未載入")
        self.pat_gender_var = tk.StringVar(value="-")
        self.pat_dob_var = tk.StringVar(value="-")
        self.current_server_patient_id = None 
        
        # 問卷調查變數 (高血壓、服藥)
        self.has_hypertension = tk.BooleanVar(value=False)
        self.is_taking_meds = tk.BooleanVar(value=False)
        
        self.setup_upload_tab()
        self.setup_query_tab()
        self.setup_llm_tab()
        self.setup_settings_tab()
        
    # ==========================================
    # ─── Tab 1: 資料量測與上傳 ───
    # ==========================================
    def setup_upload_tab(self):
        top_frame = ctk.CTkFrame(self.tab_upload, fg_color="#F0F4F8", corner_radius=12)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(top_frame, text="🧑‍⚕️ 操作員:", font=self.font_body).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.user_entry = ctk.CTkEntry(top_frame, width=150, height=40, font=self.font_input)
        self.user_entry.grid(row=0, column=1, padx=5, pady=15)
        self.user_entry.insert(0, "NURSE_667")
        
        ctk.CTkLabel(top_frame, text="💳 病患 ID:", font=self.font_body, text_color="#1A73E8").grid(row=0, column=2, padx=(15, 5), pady=15, sticky="w")
        self.pid_entry = ctk.CTkEntry(top_frame, width=280, height=40, font=self.font_input, placeholder_text="請刷條碼...")
        self.pid_entry.grid(row=0, column=3, padx=5, pady=15)
        self.pid_entry.bind("<Return>", lambda event: self.fetch_patient_info()) 
        
        btn_search_pat = ctk.CTkButton(top_frame, text="🔍 查詢", font=self.font_body, width=80, height=40, command=self.fetch_patient_info)
        btn_search_pat.grid(row=0, column=4, padx=10, pady=15)

        info_frame = ctk.CTkFrame(self.tab_upload, fg_color="#E3F2FD", corner_radius=8)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(info_frame, text="👤 姓名:", font=("Arial", 16, "bold")).grid(row=0, column=0, padx=(20, 5), pady=10)
        ctk.CTkLabel(info_frame, textvariable=self.pat_name_var, font=("Arial", 16), text_color="#0D47A1").grid(row=0, column=1, padx=(0, 20), pady=10)

        ctk.CTkLabel(info_frame, text="⚧ 性別:", font=("Arial", 16, "bold")).grid(row=0, column=2, padx=(10, 5), pady=10)
        ctk.CTkLabel(info_frame, textvariable=self.pat_gender_var, font=("Arial", 16), text_color="#0D47A1").grid(row=0, column=3, padx=(0, 20), pady=10)

        ctk.CTkLabel(info_frame, text="🎂 生日:", font=("Arial", 16, "bold")).grid(row=0, column=4, padx=(10, 5), pady=10)
        ctk.CTkLabel(info_frame, textvariable=self.pat_dob_var, font=("Arial", 16), text_color="#0D47A1").grid(row=0, column=5, padx=(0, 20), pady=10)

        main_frame = ctk.CTkFrame(self.tab_upload, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=2)

        data_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        data_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        
        self.metrics = {
            "height": {"label": "🧍 身高 (cm)", "row": 0},
            "weight": {"label": "⚖️ 體重 (kg)", "row": 1},
            "sbp":    {"label": "❤️ 收縮壓 (mmHg)", "row": 2},
            "dbp":    {"label": "💙 舒張壓 (mmHg)", "row": 3},
            "grip_r": {"label": "💪 右手握力 (kg)", "row": 4},
            "grip_l": {"label": "💪 左手握力 (kg)", "row": 5},
        }
        
        self.entries = {}
        for key, info in self.metrics.items():
            ctk.CTkLabel(data_frame, text=info["label"], font=self.font_body, anchor="w").grid(row=info["row"], column=0, padx=15, pady=6, sticky="w")
            self.entries[key] = ctk.CTkEntry(data_frame, width=180, height=40, font=self.font_input, justify="center")
            self.entries[key].grid(row=info["row"], column=1, padx=10, pady=6)
            self.entries[key].bind("<KeyRelease>", lambda e: self.reset_verification())

        ctk.CTkCheckBox(data_frame, text="🛑 有高血壓病史", variable=self.has_hypertension, font=self.font_body, command=self.reset_verification).grid(row=6, column=0, columnspan=2, pady=(15, 5), sticky="w", padx=15)
        ctk.CTkCheckBox(data_frame, text="💊 目前正在服藥", variable=self.is_taking_meds, font=self.font_body, command=self.reset_verification).grid(row=7, column=0, columnspan=2, pady=5, sticky="w", padx=15)

        ctrl_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ctrl_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")
        
        self.btn_ble = ctk.CTkButton(ctrl_frame, text="🔊 讀取量測資料", font=self.font_title, height=90, fg_color="#28A745", command=self.mock_bluetooth)
        self.btn_ble.pack(fill="x", pady=10)
        
        self.btn_verify = ctk.CTkButton(ctrl_frame, text="👁️ 目視確認數據無誤", font=self.font_title, height=100, fg_color="#FFC107", text_color="black", command=self.verify_data)
        self.btn_verify.pack(fill="x", pady=20)

        action_frame = ctk.CTkFrame(self.tab_upload, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_upload = ctk.CTkButton(action_frame, text="📤 確認無誤，送出至 FHIR Server", font=self.font_title, height=60, fg_color="#1A73E8", state="disabled", command=self.submit_to_fhir)
        self.btn_upload.pack(fill="x")

    def fetch_patient_info(self):
        pid = self.pid_entry.get().strip()
        if not pid:
            messagebox.showinfo("提示", "請先輸入病患 ID 再進行查詢。")
            return
            
        self.pat_name_var.set("查詢中...")
        self.pat_gender_var.set("-")
        self.pat_dob_var.set("-")
        self.current_server_patient_id = None
        self.update()

        def run_search():
            try:
                url = f"{self.fhir_server_base}/Patient"
                params = {"identifier": f"{SYSTEM_PATIENT}|{pid}"}
                res = requests.get(url, params=params, timeout=10)
                
                if res.status_code == 200 and res.json().get("entry"):
                    resource = res.json()["entry"][0]["resource"]
                    self.current_server_patient_id = resource.get("id")
                    
                    name = "未知"
                    name_list = resource.get("name", [])
                    if name_list:
                        if "text" in name_list[0]:
                            name = name_list[0]["text"]
                        else:
                            family = name_list[0].get("family", "")
                            given = " ".join(name_list[0].get("given", []))
                            name = f"{family}{given}".strip()
                    
                    gender_en = resource.get("gender", "unknown")
                    gender_map = {"male": "男", "female": "女", "other": "其他", "unknown": "未知"}
                    gender_tw = gender_map.get(gender_en, "未知")
                    
                    dob = resource.get("birthDate", "未知")

                    self.after(0, lambda: self.pat_name_var.set(name))
                    self.after(0, lambda: self.pat_gender_var.set(gender_tw))
                    self.after(0, lambda: self.pat_dob_var.set(dob))
                else:
                    self.after(0, lambda: self.pat_name_var.set("新病患 (上傳時自動建立)"))
                    self.after(0, lambda: self.pat_gender_var.set("未知"))
                    self.after(0, lambda: self.pat_dob_var.set("未知"))
                    
            except Exception as e:
                self.after(0, lambda err=str(e): messagebox.showwarning("連線失敗", f"無法查詢病患資訊: {err}"))
                self.after(0, lambda: self.pat_name_var.set("查詢失敗"))

        threading.Thread(target=run_search, daemon=True).start()

    # ==========================================
    # ─── Tab 2: 歷史查詢 ───
    # ==========================================
    def setup_query_tab(self):
        filter_frame = ctk.CTkFrame(self.tab_query, fg_color="#F0F4F8", corner_radius=12)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(filter_frame, text="🔍 輸入查詢病患 ID:", font=self.font_body).pack(side="left", padx=15, pady=15)
        self.query_pid_entry = ctk.CTkEntry(filter_frame, width=320, height=40, font=self.font_input, placeholder_text="請輸入病患 ID...")
        self.query_pid_entry.pack(side="left", padx=10, pady=15)
        
        btn_search = ctk.CTkButton(filter_frame, text="🔎 開始查詢歷史", font=self.font_body, width=160, height=40, fg_color="#1A73E8", command=self.fetch_fhir_history)
        btn_search.pack(side="left", padx=15, pady=15)

        table_frame = ctk.CTkFrame(self.tab_query, corner_radius=12)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 14, "bold"))
        style.configure("Treeview", font=self.font_table, rowheight=35)
        
        columns = ("time", "height", "weight", "bp", "grip_r", "grip_l", "htn", "meds", "performer")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("time", text="上傳時間")
        self.tree.heading("height", text="身高")
        self.tree.heading("weight", text="體重")
        self.tree.heading("bp", text="血壓")
        self.tree.heading("grip_r", text="右握力")
        self.tree.heading("grip_l", text="左握力")
        self.tree.heading("htn", text="高血壓史") 
        self.tree.heading("meds", text="服藥中")  
        self.tree.heading("performer", text="操作員")
        
        self.tree.column("time", width=180, anchor="center")
        self.tree.column("height", width=60, anchor="center")
        self.tree.column("weight", width=60, anchor="center")
        self.tree.column("bp", width=100, anchor="center")
        self.tree.column("grip_r", width=70, anchor="center")
        self.tree.column("grip_l", width=70, anchor="center")
        self.tree.column("htn", width=80, anchor="center")  
        self.tree.column("meds", width=80, anchor="center") 
        self.tree.column("performer", width=100, anchor="center")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=(10,0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0,10), pady=10)

    # ==========================================
    # ─── Tab 3: 🤖 智能分析與建議 (LLM) ───
    # ==========================================
    def setup_llm_tab(self):
        top_frame = ctk.CTkFrame(self.tab_llm, fg_color="#F0F4F8", corner_radius=12)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top_frame, text="💳 病患 ID:", font=self.font_body).pack(side="left", padx=15, pady=15)
        self.llm_pid_entry = ctk.CTkEntry(top_frame, width=280, height=40, font=self.font_input, placeholder_text="請輸入病患 ID...")
        self.llm_pid_entry.pack(side="left", padx=5, pady=15)
        
        self.btn_llm_analyze = ctk.CTkButton(top_frame, text="✨ 產生 AI 分析與建議", font=self.font_body, fg_color="#673AB7", command=self.run_llm_analysis)
        self.btn_llm_analyze.pack(side="left", padx=15, pady=15)

        self.llm_output = ctk.CTkTextbox(self.tab_llm, font=("Arial", 16), wrap="word", corner_radius=12)
        self.llm_output.pack(fill="both", expand=True, padx=10, pady=10)
        self.llm_output.insert("0.0", "請輸入病患 ID 並點擊上方按鈕以開始分析...")
        self.llm_output.configure(state="disabled")

    def run_llm_analysis(self):
        pid = self.llm_pid_entry.get().strip()
        if not pid:
            messagebox.showwarning("提示", "請先輸入病患 ID。")
            return
            
        self.llm_output.configure(state="normal")
        self.llm_output.delete("0.0", tk.END)
        self.llm_output.insert("0.0", "⏳ 正在從 FHIR Server 讀取資料並請求 LLM 分析中，請稍候...")
        self.llm_output.configure(state="disabled")
        self.btn_llm_analyze.configure(state="disabled")

        def process():
            try:
                # 1. 向 FHIR Server 索取病患資料
                pat_url = f"{self.fhir_server_base}/Patient"
                pat_res = requests.get(pat_url, params={"identifier": f"{SYSTEM_PATIENT}|{pid}"}, timeout=10)
                
                if pat_res.status_code != 200 or not pat_res.json().get("entry"):
                    self.update_llm_output(f"❌ 找不到 ID [{pid}] 的病患資料。")
                    return
                
                server_patient_id = pat_res.json()["entry"][0]["resource"]["id"]
                obs_res = requests.get(f"{self.fhir_server_base}/Observation", params={"subject": f"Patient/{server_patient_id}"}, timeout=10)
                
                entries = obs_res.json().get("entry", [])
                if not entries:
                    self.update_llm_output("❌ 此病患沒有任何生理量測紀錄，無法進行分析。")
                    return
                
                # 2. 整理最新的一筆資料
                records_by_time = {}
                for entry in entries:
                    resource = entry.get("resource", {})
                    raw_time = resource.get("issued") or resource.get("effectiveDateTime") or "未知時間"
                    
                    if raw_time not in records_by_time:
                        records_by_time[raw_time] = {
                            "height": "-", "weight": "-", "bp": "-", "grip_r": "-", "grip_l": "-", "htn": "-", "meds": "-"
                        }
                    
                    code = resource.get("code", {}).get("coding", [{}])[0].get("code")
                    if code == "8302-2": records_by_time[raw_time]["height"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "29463-7": records_by_time[raw_time]["weight"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "92224-5": records_by_time[raw_time]["grip_r"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "92225-2": records_by_time[raw_time]["grip_l"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "55284-4": 
                        components = resource.get("component", [])
                        sbp, dbp = "-", "-"
                        for comp in components:
                            comp_code = comp.get("code", {}).get("coding", [{}])[0].get("code")
                            if comp_code == "8480-6": sbp = comp.get("valueQuantity", {}).get("value", "-")
                            if comp_code == "8462-4": dbp = comp.get("valueQuantity", {}).get("value", "-")
                        records_by_time[raw_time]["bp"] = f"{sbp}/{dbp}"
                    elif code == "Q-HTN-HX":
                        records_by_time[raw_time]["htn"] = "是" if resource.get("valueBoolean") else "否"
                    elif code == "Q-MED-CURRENT":
                        records_by_time[raw_time]["meds"] = "是" if resource.get("valueBoolean") else "否"

                # 取得最新的時間點紀錄
                latest_time = sorted(records_by_time.keys(), reverse=True)[0]
                latest_data = records_by_time[latest_time]
                
                prompt_data = (
                    f"身高: {latest_data['height']} cm\n"
                    f"體重: {latest_data['weight']} kg\n"
                    f"血壓: {latest_data['bp']} mmHg\n"
                    f"右手握力: {latest_data['grip_r']} kg\n"
                    f"左手握力: {latest_data['grip_l']} kg\n"
                    f"高血壓病史: {latest_data['htn']}\n"
                    f"目前正在服藥: {latest_data['meds']}\n"
                )

                # 3. 組合 Prompt 給 LLM
                prompt = (
                    f"你是一位專業的健康助理。以下是病患最新的生理數據與問卷回覆：\n\n{prompt_data}\n"
                    "請根據以上資料給予健康建議。請務必包含以下內容：\n"
                    "1. 【分級建議】：請給出明確分級（如：立刻就醫、定期追蹤、無異常）。如果數據都正常，請明確顯示「無異常」。\n"
                    "2. 【詳細分析】：針對該病患的身高、體重、血壓、握力、病史及是否服藥等資料，給予具體的參考建議。\n"
                    "3. 【強烈聲明】：在回覆結尾，必須強烈強調「以上分析僅供參考，不代表專業醫療診斷，如有疑慮請尋求專業醫師協助」。"
                )

                # 4. 呼叫 LLM API
                provider = self.llm_provider.get()
                model = self.llm_model.get().strip()
                
                if provider == "OpenAI":
                    api_key = self.llm_api_key.get().strip()
                    if not api_key:
                        self.update_llm_output("❌ 錯誤：尚未設定 OpenAI API Key。請至「系統設定」分頁填寫。")
                        return
                    
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
                    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
                    
                    if res.status_code == 200:
                        reply = res.json()["choices"][0]["message"]["content"]
                        self.update_llm_output(reply)
                    else:
                        self.update_llm_output(f"❌ OpenAI API 請求失敗：{res.text}")
                        
                elif provider == "Ollama":
                    base_url = self.ollama_url.get().strip()
                    payload = {"model": model, "prompt": prompt, "stream": False}
                    res = requests.post(f"{base_url}/api/generate", json=payload, timeout=60)
                    
                    if res.status_code == 200:
                        reply = res.json()["response"]
                        self.update_llm_output(reply)
                    else:
                        self.update_llm_output(f"❌ Ollama API 請求失敗：{res.text}")

            except Exception as e:
                self.update_llm_output(f"❌ 發生錯誤：{str(e)}")
            finally:
                self.after(0, lambda: self.btn_llm_analyze.configure(state="normal"))

        threading.Thread(target=process, daemon=True).start()

    def update_llm_output(self, text):
        self.after(0, lambda: self.llm_output.configure(state="normal"))
        self.after(0, lambda: self.llm_output.delete("0.0", tk.END))
        self.after(0, lambda: self.llm_output.insert("0.0", text))
        self.after(0, lambda: self.llm_output.configure(state="disabled"))

    # ==========================================
    # ─── Tab 4: 系統設定 ───
    # ==========================================
    def setup_settings_tab(self):
        settings_frame = ctk.CTkScrollableFrame(self.tab_settings, corner_radius=12)
        settings_frame.pack(fill="both", expand=True, padx=40, pady=20)

        # FHIR 設定
        ctk.CTkLabel(settings_frame, text="🏥 FHIR 伺服器端點設定", font=self.font_title).pack(pady=(20, 10))
        self.server_url_entry = ctk.CTkEntry(settings_frame, width=500, height=40, font=self.font_input, justify="center")
        self.server_url_entry.pack(pady=5)
        self.server_url_entry.insert(0, self.fhir_server_base)
        
        # 分隔線
        ctk.CTkFrame(settings_frame, height=2, fg_color="gray").pack(fill="x", padx=50, pady=30)

        # LLM 設定
        ctk.CTkLabel(settings_frame, text="🧠 LLM 模型與 API 設定", font=self.font_title).pack(pady=(10, 10))
        
        provider_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        provider_frame.pack(pady=5)
        ctk.CTkLabel(provider_frame, text="選擇服務商:", font=self.font_body).pack(side="left", padx=10)
        provider_menu = ctk.CTkOptionMenu(provider_frame, values=["Ollama", "OpenAI"], variable=self.llm_provider, font=self.font_body, width=150)
        provider_menu.pack(side="left", padx=10)

        model_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        model_frame.pack(pady=10)
        ctk.CTkLabel(model_frame, text="模型名稱 (Model):", font=self.font_body).pack(side="left", padx=10)
        self.model_entry = ctk.CTkEntry(model_frame, textvariable=self.llm_model, width=200, font=self.font_input)
        self.model_entry.pack(side="left", padx=10)

        key_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        key_frame.pack(pady=10)
        ctk.CTkLabel(key_frame, text="OpenAI API Key:", font=self.font_body).pack(side="left", padx=10)
        self.api_key_entry = ctk.CTkEntry(key_frame, textvariable=self.llm_api_key, width=350, font=self.font_input, show="*")
        self.api_key_entry.pack(side="left", padx=10)

        ollama_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ollama_frame.pack(pady=10)
        ctk.CTkLabel(ollama_frame, text="Ollama URL:", font=self.font_body).pack(side="left", padx=10)
        self.ollama_url_entry = ctk.CTkEntry(ollama_frame, textvariable=self.ollama_url, width=350, font=self.font_input)
        self.ollama_url_entry.pack(side="left", padx=10)

        btn_save = ctk.CTkButton(settings_frame, text="💾 儲存所有設定", font=self.font_title, height=50, width=200, command=self.save_settings)
        btn_save.pack(pady=40)

    def save_settings(self):
        new_url = self.server_url_entry.get().strip()
        if new_url:
            if new_url.endswith("/"): new_url = new_url[:-1]
            self.fhir_server_base = new_url
            self.server_url_entry.delete(0, tk.END)
            self.server_url_entry.insert(0, new_url)
            
            messagebox.showinfo("設定儲存", "✅ 所有系統與 LLM 設定已更新並儲存！")
        else:
            messagebox.showwarning("警告", "FHIR 伺服器網址不能為空！")

    # ==========================================
    # ─── 核心功能：讀取模擬 / 覆核 / 上傳 / 歷史 ───
    # ==========================================
    def mock_bluetooth(self):
        pid = self.pid_entry.get().strip()
        
        if not pid:
            now = datetime.datetime.now()
            test_pid = f"TW-TEST-{now.strftime('%m%d-%H%M')}-{random.randint(10, 99)}"
            self.pid_entry.insert(0, test_pid)
            
            self.pat_name_var.set(f"虛擬測試病患_{random.randint(100, 999)}")
            self.pat_gender_var.set(random.choice(["男", "女"]))
            
            start_date = datetime.date(1950, 1, 1)
            random_days = random.randint(0, 20000)
            self.pat_dob_var.set((start_date + datetime.timedelta(days=random_days)).strftime("%Y-%m-%d"))
            self.current_server_patient_id = None
        
        mock_data = {
            "height": str(round(random.uniform(150.0, 185.0), 1)),
            "weight": str(round(random.uniform(45.0, 95.0), 1)),  
            "sbp": str(random.randint(100, 145)),                 
            "dbp": str(random.randint(60, 95)),                   
            "grip_r": str(round(random.uniform(25.0, 55.0), 1)),  
            "grip_l": str(round(random.uniform(20.0, 50.0), 1))   
        }

        for key, value in mock_data.items():
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, value)

        self.has_hypertension.set(random.choice([True, False]))
        self.is_taking_meds.set(random.choice([True, False]))

        self.reset_verification()

    def reset_verification(self):
        self.is_verified = False
        self.btn_upload.configure(state="disabled")
        self.btn_verify.configure(text="👁️ 目視確認數據無誤", fg_color="#FFC107", text_color="black")

    def verify_data(self):
        if not self.pid_entry.get().strip():
            messagebox.showwarning("欄位遺漏", "請先輸入病患 ID！")
            return
        self.is_verified = True
        self.btn_verify.configure(text="✅ 數據已人工覆核", fg_color="#28A745", text_color="white")
        self.btn_upload.configure(state="normal")

    def submit_to_fhir(self):
        pid = self.pid_entry.get().strip()
        operator = self.user_entry.get().strip()
        if not pid: return

        data = {k: v.get().strip() for k, v in self.entries.items()}
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        self.btn_upload.configure(text="⏳ 正在上傳資料中...", state="disabled")
        self.update()

        def run_upload():
            headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
            
            try:
                server_patient_id = self.current_server_patient_id

                if not server_patient_id:
                    pat_check_url = f"{self.fhir_server_base}/Patient"
                    pat_check_res = requests.get(pat_check_url, params={"identifier": f"{SYSTEM_PATIENT}|{pid}"}, timeout=10)
                    if pat_check_res.status_code == 200 and pat_check_res.json().get("entry"):
                        server_patient_id = pat_check_res.json()["entry"][0]["resource"]["id"]

                if not server_patient_id:
                    gender_map = {"男": "male", "女": "female", "其他": "other"}
                    fhir_gender = gender_map.get(self.pat_gender_var.get(), "unknown")

                    patient_data = {
                        "resourceType": "Patient",
                        "identifier": [{"system": SYSTEM_PATIENT, "value": pid}],
                        "active": True,
                        "name": [{"use": "usual", "text": self.pat_name_var.get() if "尚未載入" not in self.pat_name_var.get() else "新建立病患"}]
                    }
                    if fhir_gender != "unknown": patient_data["gender"] = fhir_gender
                    if self.pat_dob_var.get() not in ["-", "未知"]: patient_data["birthDate"] = self.pat_dob_var.get()

                    pat_response = requests.post(f"{self.fhir_server_base}/Patient", json=patient_data, headers=headers, timeout=10)
                    if pat_response.status_code not in [200, 201]:
                        self.after(0, lambda: messagebox.showerror("錯誤", f"建立病患失敗: {pat_response.text}"))
                        return
                    server_patient_id = pat_response.json().get('id')
                    self.current_server_patient_id = server_patient_id

                observations_to_send = []
                
                def create_obs_json(loinc, display, val, unit):
                    if not val: return None
                    return {
                        "resourceType": "Observation",
                        "status": "final",
                        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                        "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": display}]},
                        "subject": {"reference": f"Patient/{server_patient_id}"},
                        "performer": [{"identifier": {"system": SYSTEM_STAFF, "value": operator}, "display": operator}],
                        "effectiveDateTime": now,
                        "valueQuantity": {"value": float(val), "unit": unit, "system": "http://unitsofmeasure.org", "code": unit}
                    }

                obs_list = [
                    create_obs_json("8302-2", "Body height", data.get("height"), "cm"),
                    create_obs_json("29463-7", "Body weight", data.get("weight"), "kg"),
                    create_obs_json("92224-5", "Grip strength Right hand", data.get("grip_r"), "kg"),
                    create_obs_json("92225-2", "Grip strength Left hand", data.get("grip_l"), "kg")
                ]
                observations_to_send.extend([obs for obs in obs_list if obs])

                sbp, dbp = data.get("sbp"), data.get("dbp")
                if sbp and dbp:
                    bp_obs = {
                        "resourceType": "Observation",
                        "status": "final",
                        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                        "code": {"coding": [{"system": "http://loinc.org", "code": "55284-4", "display": "Blood pressure systolic and diastolic"}]},
                        "subject": {"reference": f"Patient/{server_patient_id}"},
                        "performer": [{"identifier": {"system": SYSTEM_STAFF, "value": operator}, "display": operator}],
                        "effectiveDateTime": now,
                        "component": [
                            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]}, "valueQuantity": {"value": float(sbp), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
                            {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]}, "valueQuantity": {"value": float(dbp), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}}
                        ]
                    }
                    observations_to_send.append(bp_obs)

                survey_htn = {
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey", "display": "Survey"}]}],
                    "code": {"coding": [{"system": "https://aicoach.aiatw.org/questionnaire", "code": "Q-HTN-HX", "display": "History of Hypertension"}], "text": "高血壓病史"},
                    "subject": {"reference": f"Patient/{server_patient_id}"},
                    "performer": [{"identifier": {"system": SYSTEM_STAFF, "value": operator}, "display": operator}],
                    "effectiveDateTime": now,
                    "valueBoolean": self.has_hypertension.get()
                }
                observations_to_send.append(survey_htn)

                survey_meds = {
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey", "display": "Survey"}]}],
                    "code": {"coding": [{"system": "https://aicoach.aiatw.org/questionnaire", "code": "Q-MED-CURRENT", "display": "Currently taking medication"}], "text": "目前正在服藥"},
                    "subject": {"reference": f"Patient/{server_patient_id}"},
                    "performer": [{"identifier": {"system": SYSTEM_STAFF, "value": operator}, "display": operator}],
                    "effectiveDateTime": now,
                    "valueBoolean": self.is_taking_meds.get()
                }
                observations_to_send.append(survey_meds)

                success_count = 0
                for obs_data in observations_to_send:
                    response = requests.post(f"{self.fhir_server_base}/Observation", json=obs_data, headers=headers, timeout=10)
                    if response.status_code in [200, 201]: success_count += 1

                if success_count == len(observations_to_send):
                    self.after(0, lambda: messagebox.showinfo("大成功", f"成功寫入 {success_count} 筆資料！"))
                    self.after(0, lambda: self.query_pid_entry.delete(0, tk.END))
                    self.after(0, lambda: self.query_pid_entry.insert(0, pid))
                    self.after(0, self.clear_all)
                else:
                    self.after(0, lambda: messagebox.showwarning("部分失敗", "有部分資料未能上傳。"))
                    
            except Exception as e:
                self.after(0, lambda err=str(e): messagebox.showerror("錯誤", err))
            finally:
                self.after(0, lambda: self.btn_upload.configure(text="📤 確認無誤，送出至 FHIR Server", state="normal"))
                self.after(0, self.reset_verification)

        threading.Thread(target=run_upload, daemon=True).start()

    def fetch_fhir_history(self):
        pid = self.query_pid_entry.get().strip()
        if not pid: return
            
        for item in self.tree.get_children(): self.tree.delete(item)
            
        def run_query():
            try:
                pat_url = f"{self.fhir_server_base}/Patient"
                pat_res = requests.get(pat_url, params={"identifier": f"{SYSTEM_PATIENT}|{pid}"}, timeout=10)
                
                if pat_res.status_code != 200 or not pat_res.json().get("entry"):
                    self.after(0, lambda: messagebox.showinfo("查無病患", f"伺服器找不到 ID [{pid}] 的病患檔。"))
                    return
                
                server_patient_id = pat_res.json()["entry"][0]["resource"]["id"]
                obs_res = requests.get(f"{self.fhir_server_base}/Observation", params={"subject": f"Patient/{server_patient_id}"}, timeout=10)
                if obs_res.status_code != 200: return
                
                entries = obs_res.json().get("entry", [])
                if not entries:
                    self.after(0, lambda: messagebox.showinfo("查無資料", "此病患沒有任何紀錄。"))
                    return
                
                records_by_time = {}
                for entry in entries:
                    resource = entry.get("resource", {})
                    raw_time = resource.get("issued") or resource.get("effectiveDateTime") or "未知時間"
                    time_display = raw_time.split(".")[0].replace("T", " ") if "T" in raw_time else raw_time
                        
                    performer_list = resource.get("performer", [])
                    performer = "未知"
                    if performer_list: performer = performer_list[0].get("identifier", {}).get("value") or performer_list[0].get("display") or "未知"
                    
                    if time_display not in records_by_time:
                        records_by_time[time_display] = {
                            "height": "-", "weight": "-", "bp": "-", "grip_r": "-", "grip_l": "-", 
                            "htn": "-", "meds": "-", "performer": performer
                        }
                    
                    code = resource.get("code", {}).get("coding", [{}])[0].get("code")
                    if code == "8302-2": records_by_time[time_display]["height"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "29463-7": records_by_time[time_display]["weight"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "92224-5": records_by_time[time_display]["grip_r"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "92225-2": records_by_time[time_display]["grip_l"] = resource.get("valueQuantity", {}).get("value", "-")
                    elif code == "55284-4": 
                        components = resource.get("component", [])
                        sbp, dbp = "-", "-"
                        for comp in components:
                            comp_code = comp.get("code", {}).get("coding", [{}])[0].get("code")
                            if comp_code == "8480-6": sbp = comp.get("valueQuantity", {}).get("value", "-")
                            if comp_code == "8462-4": dbp = comp.get("valueQuantity", {}).get("value", "-")
                        records_by_time[time_display]["bp"] = f"{sbp}/{dbp}"
                    elif code == "Q-HTN-HX":
                        val = resource.get("valueBoolean")
                        records_by_time[time_display]["htn"] = "是" if val is True else "否" if val is False else "-"
                    elif code == "Q-MED-CURRENT":
                        val = resource.get("valueBoolean")
                        records_by_time[time_display]["meds"] = "是" if val is True else "否" if val is False else "-"

                for t_str, r in sorted(records_by_time.items(), reverse=True):
                    self.after(0, lambda t=t_str, data=r: self.tree.insert("", "end", values=(
                        t, data["height"], data["weight"], data["bp"], data["grip_r"], data["grip_l"], 
                        data["htn"], data["meds"], data["performer"]
                    )))
            except Exception as e:
                self.after(0, lambda err=str(e): messagebox.showerror("連線出錯", err))

        threading.Thread(target=run_query, daemon=True).start()

    def clear_all(self):
        self.pid_entry.delete(0, tk.END)
        for entry in self.entries.values(): entry.delete(0, tk.END)
        self.pat_name_var.set("尚未載入")
        self.pat_gender_var.set("-")
        self.pat_dob_var.set("-")
        self.has_hypertension.set(False)
        self.is_taking_meds.set(False)
        self.current_server_patient_id = None
        self.reset_verification()

if __name__ == "__main__":
    app = AdvancedFHIRGateway()
    app.mainloop()