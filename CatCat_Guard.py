import os
import sys
import json

# --- 1. 取得應用程式真實執行路徑 (解決 PyInstaller 打包路徑迷航問題) ---
def get_app_dir():
    if getattr(sys, 'frozen', False):
        # 如果是被打包成執行檔
        app_path = sys.executable
        # 針對 macOS .app 套件的特殊處理：往上退 4 層回到 .app 所在的資料夾
        if sys.platform == 'darwin' and '.app/Contents/MacOS' in app_path:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(app_path))))
        # Windows 或一般情況下，直接取執行檔所在資料夾
        return os.path.dirname(app_path)
    else:
        # 如果是直接執行 .py 原始碼
        return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

# --- 2. 初次使用：必要套件檢查與防呆提示 ---
try:
    import customtkinter as ctk
    import cv2
    import numpy as np
    import requests 
    from PIL import Image, ImageDraw
    import pystray
    from pystray import MenuItem as item
    from flask import Flask, Response
    import logging
except ImportError as e:
    print("\n" + "=" * 75)
    print("🚨ERROR：Lost Python Libraries！")
    print(f"LOST: {e.name}")
    print("-" * 75)
    print("   pip install customtkinter opencv-python numpy requests pillow pystray ultralytics flask\n")
    print("=" * 75 + "\n")
    sys.exit(1)

# --- YOLO 單獨處理（torch/torchvision 版本不符時不中止程式，僅停用 AI 功能）---
HAS_YOLO = False
HAS_FLASK = True
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except (ImportError, RuntimeError) as e:
    print("\n" + "=" * 75)
    print("⚠️  WARNING：YOLO / PyTorch 載入失敗，AI 辨識功能將停用。")
    print(f"   原因：{e}")
    print("-" * 75)
    print("   請執行以下指令修正 torch 與 torchvision 版本衝突：")
    print()
    print("   pip uninstall torch torchvision torchaudio ultralytics -y")
    print("   pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 \\")
    print("       --index-url https://download.pytorch.org/whl/cpu")
    print("   pip install ultralytics")
    print()
    print("   （若有 NVIDIA GPU，將 cpu 改為 cu118）")
    print("=" * 75 + "\n")

# --- 3. 載入其他內建與標準套件 ---
import threading
import time
import socket
import ctypes
import subprocess
import math  
import platform
import urllib.request
import stat
from datetime import datetime
from tkinter import filedialog, messagebox

# ============================================================
# --- 雙語系統 / Bilingual System (外部 lang.json) ---
# 自動讀取外部 lang.json 檔案，如果遺失則自動產生預設檔案
# ============================================================
import locale as _locale

def _detect_lang():
    try:
        lang = _locale.getdefaultlocale()[0] or ""
        if lang.startswith("zh"):
            return "zh"
    except:
        pass
    return "en"

# Use a list so the value can be mutated at runtime (simple mutable container)
_LANG = [_detect_lang()]

# 預設字典，用來防止 json 遺失或毀損時可以自動恢復
_DEFAULT_T = {
    "app_title":              {"zh": "CatCat Guard 智慧監控系統",        "en": "CatCat Guard Smart Monitor"},
    "already_running":        {"zh": "程式已經在執行中！",                    "en": "App is already running!"},
    "cam_starting":           {"zh": "正在啟動攝影機與 AI 模型...",           "en": "Starting camera & AI model..."},
    "cam_not_found":          {"zh": "❌ 找不到攝影機設備",                   "en": "❌ Camera device not found"},
    "btn_manual_off":         {"zh": "手動監控: OFF",                        "en": "Manual Monitor: OFF"},
    "btn_manual_on":          {"zh": "停止監控",                             "en": "Stop Monitor"},
    "btn_saver_off":          {"zh": "螢保監控: OFF",                        "en": "Screensaver: OFF"},
    "btn_saver_on":           {"zh": "螢保監控: ON",                         "en": "Screensaver: ON"},
    "btn_schedule_off":       {"zh": "排程監控: OFF",                        "en": "Schedule: OFF"},
    "btn_schedule_on":        {"zh": "排程監控: ON",                         "en": "Schedule: ON"},
    "status_idle":            {"zh": "💤 待機中",                            "en": "💤 Idle"},
    "status_prefix":          {"zh": "狀態: ",                               "en": "Status: "},
    "status_monitoring":      {"zh": "🔴 監控中",                            "en": "🔴 Monitoring"},
    "status_alarm":           {"zh": "⚠️ 警報! 電腦喚醒",                   "en": "⚠️ Alert! PC Woken Up"},
    "status_standby":         {"zh": "⏳ 待命中",                            "en": "⏳ Standby"},
    "trig_manual":            {"zh": "手動",                                  "en": "Manual"},
    "trig_schedule":          {"zh": "排程",                                  "en": "Sched"},
    "trig_saver":             {"zh": "螢保",                                  "en": "ScreenSvr"},
    "btn_live_on":            {"zh": "開啟直播",                              "en": "Start Live"},
    "btn_live_off":           {"zh": "關閉直播",                              "en": "Stop Live"},
    "btn_live_connecting":    {"zh": "連線中...",                             "en": "Connecting..."},
    "live_url_placeholder":   {"zh": "直播網址",                              "en": "Live stream URL"},
    "live_getting_url":       {"zh": "正在獲取專屬網址...",                   "en": "Fetching stream URL..."},
    "live_closed":            {"zh": "直播已關閉",                            "en": "Stream closed"},
    "btn_copy":               {"zh": "複製",                                  "en": "Copy"},
    "btn_copied":             {"zh": "已複製!",                               "en": "Copied!"},
    "btn_no_url":             {"zh": "無網址",                                "en": "No URL"},
    "schedule_hint":          {"zh": "排程設定 (需開啟上方「排程監控」才會生效)", "en": "Schedule Settings (requires Schedule mode ON)"},
    "sched_slot":             {"zh": "時段",                                  "en": "Slot"},
    "sched_start":            {"zh": "開始:",                                 "en": "Start:"},
    "sched_end":              {"zh": "結束:",                                 "en": "End:"},
    "tg_enable":              {"zh": "啟用 Telegram",                        "en": "Enable Telegram"},
    "btn_test":               {"zh": "測試",                                  "en": "Test"},
    "btn_folder":             {"zh": "資料夾",                                "en": "Folder"},
    "ai_label":               {"zh": "AI 獨立辨識:",                          "en": "AI Detection:"},
    "ai_person":              {"zh": "人物",                                  "en": "Person"},
    "ai_pet":                 {"zh": "寵物",                                  "en": "Pet"},
    "ai_vehicle":             {"zh": "車輛",                                  "en": "Vehicle"},
    "ai_door":                {"zh": "YOLO面積深度軌跡",                      "en": "YOLO Depth Tracking"},
    "btn_set_door":           {"zh": "框選範圍",                              "en": "Set Zone"},
    "sens_label":             {"zh": "傳統動態靈敏:",                         "en": "Motion Sensitivity:"},
    "door_tip_title":         {"zh": "提示",                                  "en": "Tip"},
    "door_tip_check_first":   {"zh": "請先勾選「YOLO面積深度軌跡」再進行範圍設定！", "en": "Please enable 'YOLO Depth Tracking' before setting the zone!"},
    "door_dialog_title":      {"zh": "設定面積深度軌跡 (共 6 次點擊)",        "en": "Set Depth Tracking Zone (6 Clicks)"},
    "door_dialog_body":       {
        "zh": (
            "💡 解決下半身遮擋的最強物理判定：\n\n"
            "👉 第 1~2 點 (門框開關 - 紫線)：\n"
            "   請畫在門的最上方。系統只看門是否有動。\n\n"
            "👉 第 3~6 點 (門口感測區 - 綠框)：\n"
            "   請依序點擊 4 次，沿著門口畫出一個「綠色四邊形」。\n"
            "   當門開啟時，系統會偵測綠框內人員的【身體面積大小】：\n"
            "   👁️‍🗨️ 人體變大 (面積增加) = 靠近鏡頭 = 進入！\n"
            "   👁️‍🗨️ 人體變小 (面積縮小) = 遠離鏡頭 = 離開！\n\n"
            "🛡️ 只要人走過來變大就一定能觸發！"
        ),
        "en": (
            "💡 Best physical detection even with lower-body occlusion:\n\n"
            "👉 Points 1-2 (Door frame toggle - purple line):\n"
            "   Click along the top of the door. Watches for movement here.\n\n"
            "👉 Points 3-6 (Entry sensing zone - green quad):\n"
            "   Click 4 times to draw a green quadrilateral around the doorway.\n"
            "   When the door opens, the system measures body area in the zone:\n"
            "   👁️‍🗨️ Body LARGER (area increases) = approaching = ENTER!\n"
            "   👁️‍🗨️ Body SMALLER (area decreases) = moving away = EXIT!\n\n"
            "🛡️ Anyone walking toward the camera will always trigger!"
        ),
    },
    "door_done_title":        {"zh": "完成",                                  "en": "Done"},
    "door_done_body":         {"zh": "面積深度門禁設定完成！",                 "en": "Depth tracking zone configured!"},
    "src_manual":             {"zh": "手動",     "en": "Manual"},
    "src_schedule":           {"zh": "排程",     "en": "Schedule"},
    "src_saver":              {"zh": "螢幕保護",  "en": "Screensaver"},
    "ai_caption_prefix":      {"zh": "\n🤖 AI 偵測: ", "en": "\n🤖 AI Detected: "},
    "snap_caption":           {"zh": "📸 [{host}] 的即時畫面",               "en": "📸 Live snapshot from [{host}]"},
    "tg_test_ok":             {"zh": "✅ [{host}] 連接成功。",                "en": "✅ [{host}] Connection successful."},
    "tg_test_msg_title":      {"zh": "成功",                                  "en": "Success"},
    "tg_test_msg_body":       {"zh": "測試訊息已發送，並已自動為您配置 Bot 快捷選單！", "en": "Test message sent and Bot menu configured!"},
    "tray_show":              {"zh": "開啟",     "en": "Show"},
    "tray_quit":              {"zh": "結束",     "en": "Quit"},
    "tray_tooltip":           {"zh": "安全監控",  "en": "Security Monitor"},
    "flask_title":            {"zh": "{host} - CatCat Guard 智慧監控直播",          "en": "{host} - CatCat Guard Live Monitor"},
    "flask_heading":          {"zh": "🎥 [{host}] 即時監控畫面",              "en": "🎥 [{host}] Live Camera Feed"},
    "flask_img_alt":          {"zh": "監控畫面載入中...",                     "en": "Loading stream..."},
    "flask_footer":           {"zh": "連線安全加密由 Cloudflare 提供",        "en": "Secured by Cloudflare"},
    "cf_unknown_os":          {"zh": "⚠️ 未知的作業系統，略過 Cloudflare 下載", "en": "⚠️ Unknown OS, skipping Cloudflare download"},
    "cf_first_run":           {"zh": "📦 偵測到初次使用，正在為您的系統下載 Cloudflare Tunnel...", "en": "📦 First run — downloading Cloudflare Tunnel..."},
    "cf_extracting":          {"zh": "📦 檔案下載完成，正在自動解壓縮...",    "en": "📦 Download complete, extracting..."},
    "cf_ready":               {"zh": "✅ Cloudflare Tunnel 下載與設定完成！隨時可用。", "en": "✅ Cloudflare Tunnel ready!"},
    "cf_fail":                {"zh": "❌ 下載或解壓失敗: {e}",                "en": "❌ Download/extraction failed: {e}"},
    "cf_no_url_fail":         {"zh": "無法取得網址，請重試",                  "en": "Could not get URL, please retry"},
    "live_tg_opened":         {"zh": "{prefix}🎥 公開視訊串流已開啟！\n\n🌐 Cloudflare 免費一次性連線：\n{url}\n\n💡 提醒：關閉程式或輸入 /live_off 後，此網址將永久失效。",
                               "en": "{prefix}🎥 Live stream is online!\n\n🌐 Cloudflare one-time URL:\n{url}\n\n💡 Note: URL expires when you quit or type /live_off."},
    "live_tg_no_url":         {"zh": "{prefix}⚠️ 無法取得 Cloudflare 網址，請確認網路或稍後再試。",
                               "en": "{prefix}⚠️ Could not get Cloudflare URL. Check network and retry."},
    "live_tg_fail":           {"zh": "{prefix}❌ Cloudflare 啟動失敗: {e}",   "en": "{prefix}❌ Cloudflare startup failed: {e}"},
    "live_tg_stopped":        {"zh": "{prefix}🛑 視訊串流通道已從主機端關閉。", "en": "{prefix}🛑 Live stream stopped from host."},
    "tg_cmd_on":              {"zh": "🟢 啟動手動監控",            "en": "🟢 Start manual monitoring"},
    "tg_cmd_off":             {"zh": "🔴 停止手動監控",            "en": "🔴 Stop manual monitoring"},
    "tg_cmd_ai_on":           {"zh": "🤖 開啟預設 AI 模式",        "en": "🤖 Enable default AI mode"},
    "tg_cmd_ai_off":          {"zh": "⚙️ 關閉所有 AI 模式",        "en": "⚙️ Disable all AI modes"},
    "tg_cmd_photo":           {"zh": "📸 拍攝現場即時照片",         "en": "📸 Take a live snapshot"},
    "tg_cmd_live_on":         {"zh": "🎥 開啟 Cloudflare 視訊直播","en": "🎥 Start Cloudflare live stream"},
    "tg_cmd_live_off":        {"zh": "🛑 關閉視訊直播",             "en": "🛑 Stop live stream"},
    "tg_cmd_hide":            {"zh": "⬇️ 隱藏主視窗",              "en": "⬇️ Hide main window"},
    "tg_cmd_show":            {"zh": "⬆️ 顯示主視窗",              "en": "⬆️ Show main window"},
    "tg_cmd_status":          {"zh": "📊 查詢目前狀態",             "en": "📊 Query current status"},
    "tg_cmd_quit":            {"zh": "🔌 遠端安全關閉程式",         "en": "🔌 Remote safe shutdown"},
    "tg_cmd_help":            {"zh": "ℹ️ 顯示指令說明",             "en": "ℹ️ Show command list"},
    "tg_r_manual_on":         {"zh": "{p}🟢 已啟動手動監控",             "en": "{p}🟢 Manual monitoring started"},
    "tg_r_manual_off":        {"zh": "{p}🔴 已停止手動監控",             "en": "{p}🔴 Manual monitoring stopped"},
    "tg_r_ai_on":             {"zh": "{p}🤖 已開啟預設 AI 模式 (人物+門禁)", "en": "{p}🤖 Default AI mode enabled (Person + Door)"},
    "tg_r_ai_off":            {"zh": "{p}⚙️ 已關閉所有 AI (切換為傳統)",  "en": "{p}⚙️ All AI disabled (classic motion)"},
    "tg_r_photo":             {"zh": "{p}📸 拍攝中...",                "en": "{p}📸 Taking snapshot..."},
    "tg_r_live_off":          {"zh": "{p}🛑 視訊串流通道已安全關閉。",   "en": "{p}🛑 Live stream safely closed."},
    "tg_r_hide_mac":          {"zh": "{p}⬇️ 已縮小至工作列",            "en": "{p}⬇️ Minimized to taskbar"},
    "tg_r_hide_win":          {"zh": "{p}⬇️ 已隱藏至常駐列",            "en": "{p}⬇️ Hidden to system tray"},
    "tg_r_show":              {"zh": "{p}⬆️ 已顯示主視窗",              "en": "{p}⬆️ Main window restored"},
    "tg_r_quit":              {"zh": "{p}🔌 收到關閉指令，系統即將安全關閉。", "en": "{p}🔌 Shutdown command received, closing..."},
    "tg_status_prefix":       {"zh": "{p}系統狀態：\n",                 "en": "{p}System Status:\n"},
    "tg_status_state":        {"zh": "狀態：{v}\n",                    "en": "State: {v}\n"},
    "tg_status_mode":         {"zh": "模式：{v}\n",                    "en": "Mode: {v}\n"},
    "tg_status_live":         {"zh": "直播：{v}\n",                    "en": "Live: {v}\n"},
    "tg_status_sens":         {"zh": "靈敏：{s} | 視窗：{w}",          "en": "Sens: {s} | Window: {w}"},
    "tg_state_monitoring":    {"zh": "🟢 監控中",                      "en": "🟢 Monitoring"},
    "tg_state_standby":       {"zh": "⏳ 待命",                        "en": "⏳ Standby"},
    "tg_state_stopped":       {"zh": "🔴 已停止",                      "en": "🔴 Stopped"},
    "tg_mode_ai":             {"zh": "🤖 AI",                          "en": "🤖 AI"},
    "tg_mode_classic":        {"zh": "⚙️ 傳統移動",                    "en": "⚙️ Classic Motion"},
    "tg_ai_person":           {"zh": "人",   "en": "Person"},
    "tg_ai_pet":              {"zh": "寵",   "en": "Pet"},
    "tg_ai_vehicle":          {"zh": "車",   "en": "Vehicle"},
    "tg_ai_door":             {"zh": "門禁", "en": "Door"},
    "tg_live_on_str":         {"zh": "🟢 開啟", "en": "🟢 ON"},
    "tg_live_off_str":        {"zh": "🔴 關閉", "en": "🔴 OFF"},
    "tg_win_hidden":          {"zh": "⬇️ 隱藏", "en": "⬇️ Hidden"},
    "tg_win_visible":         {"zh": "⬆️ 顯示", "en": "⬆️ Visible"},
    "tg_help_body":           {
        "zh": ("/on 或 /off - 🟢🔴 開關監控\n"
               "/ai_on 或 /ai_off - 🤖⚙️ 開關AI\n"
               "/photo - 📸 現場拍照\n"
               "/live_on 或 /live_off - 🎥🛑 開關視訊直播\n"
               "/hide 或 /show - ⬇️⬆️ 隱藏/顯示\n"
               "/status - 📊 查詢狀態\n"
               "/quit - 🔌 遠端關閉程式\n"
               "/help - ℹ️ 顯示此列表"),
        "en": ("/on or /off - 🟢🔴 Start/stop monitoring\n"
               "/ai_on or /ai_off - 🤖⚙️ Enable/disable AI\n"
               "/photo - 📸 Take a live photo\n"
               "/live_on or /live_off - 🎥🛑 Start/stop live stream\n"
               "/hide or /show - ⬇️⬆️ Hide/show window\n"
               "/status - 📊 Query status\n"
               "/quit - 🔌 Remote shutdown\n"
               "/help - ℹ️ Show this list"),
    },
    "settings_load_fail":     {"zh": "設定載入失敗: {e}",  "en": "Failed to load settings: {e}"},
    "settings_save_fail":     {"zh": "設定儲存失敗: {e}",  "en": "Failed to save settings: {e}"},
    "tg_menu_fail":           {"zh": "設定 Telegram 選單失敗: {e}", "en": "Failed to set Telegram menu: {e}"},
    "yolo_loading":           {"zh": "正在載入 YOLOv8n...", "en": "Loading YOLOv8n..."},
    "door_enter":             {"zh": "🚪 門禁結算：人員越線進入，判定為「進入」室內！", "en": "🚪 Door Event: Person crossed inward — ENTERED!"},
    "door_exit":              {"zh": "🚪 門禁結算：人員越線離開，判定為「離開」室外！", "en": "🚪 Door Event: Person crossed outward — EXITED!"},
    "lang_switch_btn":        {"zh": "🌐 EN",  "en": "🌐 中文"},
}

_T = {}
LANG_FILE = os.path.join(APP_DIR, "lang.json")

def load_language_file():
    global _T
    # 若檔案不存在，自動寫入預設設定
    if not os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, 'w', encoding='utf-8') as f:
                json.dump(_DEFAULT_T, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Cannot create lang.json: {e}")
            
    # 讀取 JSON
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            _T = json.load(f)
    except Exception as e:
        print(f"Failed to load lang.json: {e}")
        _T = _DEFAULT_T

# 程式啟動時載入語系
load_language_file()

def T(key):
    """Return localised string for the current language."""
    # 若 JSON 中遺失了某個 key，會自動 fallback 到 _DEFAULT_T
    entry = _T.get(key, _DEFAULT_T.get(key, {}))
    return entry.get(_LANG[0], entry.get("zh", key))

# 設定外觀模式
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Windows API 常數與全域設定 (套用絕對路徑)
SPI_GETSCREENSAVERRUNNING = 0x0072
CONFIG_FILE = os.path.join(APP_DIR, "monitor_config.json")

class MotionDetectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 防止重複開啟機制 ---
        try:
            self.instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.instance_socket.bind(('127.0.0.1', 65432))
        except socket.error:
            print(T("already_running")) 
            sys.exit()

        # --- 視窗基礎設定 ---
        self.title(T("app_title"))
        self.geometry("1150x950") # 稍微加寬以容納複製按鈕
        self.protocol('WM_DELETE_WINDOW', self.quit_app)
        self.bind("<Unmap>", self._check_minimized_event)
        self.bind("<Map>", self._check_restored_event)

        # --- 核心變數 ---
        self.hostname = socket.gethostname()
        self.is_running = True     
        self.detecting = False        
        self.is_window_hidden = False
        
        self.cam_missing = False      
        self.cam_loading = True       
        
        self.trigger_manual = False   
        self.trigger_saver = False    
        self.trigger_schedule = False 
        
        self.saver_armed = False      
        self.schedule_armed = False   
        
        self.intrusion_detected = False
        self.is_live_streaming = False
        self.cf_process = None
        
        self.cap = None            
        self.latest_frame = None      
        self.latest_jpeg_bytes = None  
        self.frame_lock = threading.Lock() 
        self.tray_icon = None      
        
        self.bg_model = None 

        # AI 模型變數
        self.yolo_model = None

        # 遠端控制與狀態變數
        self.force_take_photo = False
        self.last_update_id = 0
        self.track_state = {}  
        self.tg_commands_set = False  # 新增：記錄是否已設定 Telegram 選單

        # 自訂門禁範圍變數 (6點：2點門框線 + 4點感測區)
        self.custom_door_pts = []
        self.is_setting_door = False
        self.frame_width = 0
        self.frame_height = 0
        
        self.zone_persons = {} # 記錄在門口的人員面積與中心軌跡

        # 預設值 (套用絕對路徑)
        self.save_folder = os.path.join(APP_DIR, "captures")
        self.default_sensitivity = 80  
        self.schedule_data = [
            {"enable": False, "start": "09:00", "end": "18:00"},
            {"enable": False, "start": "22:00", "end": "06:00"},
            {"enable": False, "start": "12:00", "end": "13:00"}
        ]
        
        # Telegram & AI 預設變數
        self.tg_token = ""
        self.tg_chat_id = ""
        self.tg_enabled_default = False
        
        self.ai_person_default = True
        self.ai_pet_default = False
        self.ai_vehicle_default = False
        self.ai_door_default = False

        # --- 載入設定 ---
        self.load_settings()
        
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)

        # --- 初始化：自動檢查並下載 Cloudflare Tunnel ---
        threading.Thread(target=self._ensure_cloudflared, daemon=True).start()

        # --- 建立 GUI 介面 ---
        self._setup_ui()

        # --- 啟動執行緒 ---
        self.thread = threading.Thread(target=self.video_processing_thread, daemon=True)
        self.thread.start()

        self.monitor_thread = threading.Thread(target=self.monitor_logic, daemon=True)
        self.monitor_thread.start()
        
        self.tg_listener_thread = threading.Thread(target=self.telegram_listener, daemon=True)
        self.tg_listener_thread.start()
        
        self.update_video_display()

        # --- 啟動 Flask 直播伺服器 ---
        if HAS_FLASK:
            self.flask_app = Flask(__name__)
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            @self.flask_app.route('/')
            def index():
                return f'''
                <html>
                  <head>
                    <title>{self.hostname} - CatCat Guard 智慧監控直播</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                      body {{ background-color: #121212; color: #E0E0E0; text-align: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }}
                      h2 {{ color: #2ECC71; margin-bottom: 20px; }}
                      .stream-container {{ max-width: 800px; margin: 0 auto; padding: 10px; background-color: #000; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.8); }}
                      img {{ width: 100%; height: auto; border-radius: 8px; display: block; }}
                      .footer {{ margin-top: 20px; font-size: 0.9em; color: #777; }}
                    </style>
                  </head>
                  <body>
                    <h2>🎥 [{self.hostname}] 即時監控畫面</h2>
                    <div class="stream-container">
                      <img src="/video_feed" alt="監控畫面載入中...">
                    </div>
                    <div class="footer">連線安全加密由 Cloudflare 提供</div>
                  </body>
                </html>
                '''

            @self.flask_app.route('/video_feed')
            def video_feed():
                return Response(self.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
            
            threading.Thread(target=lambda: self.flask_app.run(host='0.0.0.0', port=5050, debug=False, use_reloader=False), daemon=True).start()

    def _ensure_cloudflared(self):
        system = sys.platform
        machine = platform.machine().lower()

        is_tgz = False
        if system == "win32":
            self.cf_filename = os.path.join(APP_DIR, "cloudflared.exe")
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        elif system == "darwin":
            self.cf_filename = os.path.join(APP_DIR, "cloudflared")
            is_tgz = True
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
        else:
            print("⚠️ 未知的作業系統，略過 Cloudflare 下載")
            return

        if not os.path.exists(self.cf_filename):
            print(f"📦 偵測到初次使用，正在為您的系統下載 Cloudflare Tunnel...")
            try:
                import ssl
                ssl._create_default_https_context = ssl._create_unverified_context
                
                if is_tgz:
                    tgz_path = self.cf_filename + ".tgz"
                    urllib.request.urlretrieve(url, tgz_path)
                    print("📦 檔案下載完成，正在自動解壓縮...")
                    import tarfile
                    with tarfile.open(tgz_path, "r:gz") as tar:
                        tar.extractall(path=APP_DIR)
                    os.remove(tgz_path) 
                else:
                    urllib.request.urlretrieve(url, self.cf_filename)
                
                if system != "win32":
                    st = os.stat(self.cf_filename)
                    os.chmod(self.cf_filename, st.st_mode | stat.S_IEXEC)
                print("✅ Cloudflare Tunnel 下載與設定完成！隨時可用。")
            except Exception as e:
                print(f"❌ 下載或解壓失敗: {e}")

    def generate_frames(self):
        while self.is_running:
            with self.frame_lock:
                frame_bytes = self.latest_jpeg_bytes
            if frame_bytes is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05) 

    def _check_minimized_event(self, event):
        if event.widget == self and self.state() == 'iconic':
            self.is_window_hidden = True
            if sys.platform != "darwin":
                self.after(100, self.minimize_to_tray)

    def _check_restored_event(self, event):
        if event.widget == self and self.state() == 'normal':
            self.is_window_hidden = False

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.save_folder = data.get("save_folder", self.save_folder)
                    self.default_sensitivity = data.get("sensitivity", 80) 
                    self.tg_token = data.get("tg_token", "")
                    self.tg_chat_id = data.get("tg_chat_id", "")
                    self.tg_enabled_default = data.get("tg_enabled", False)
                    
                    self.ai_person_default = data.get("ai_person", True)
                    self.ai_pet_default = data.get("ai_pet", False)
                    self.ai_vehicle_default = data.get("ai_vehicle", False)
                    self.ai_door_default = data.get("ai_door", False)
                    
                    # 確保讀取的是 6 個點的設定
                    self.custom_door_pts = data.get("custom_door_pts", [])
                    if len(self.custom_door_pts) != 6:
                        self.custom_door_pts = []
                    
                    saved_schedules = data.get("schedules", [])
                    if len(saved_schedules) == 3:
                        self.schedule_data = saved_schedules
            except Exception as e:
                print(T("settings_load_fail").format(e=e))

    def save_settings(self):
        current_schedules = []
        for sched_ui in self.schedules_ui:
            current_schedules.append({
                "enable": sched_ui["enable"].get(),
                "start": sched_ui["start"].get(),
                "end": sched_ui["end"].get()
            })
        
        data = {
            "save_folder": self.save_folder,
            "sensitivity": self.sensitivity_slider.get(),
            "schedules": current_schedules,
            "tg_token": self.entry_tg_token.get(),
            "tg_chat_id": self.entry_tg_chat_id.get(),
            "tg_enabled": self.chk_tg_enable.get(),
            "ai_person": self.ai_person_var.get(),
            "ai_pet": self.ai_pet_var.get(),
            "ai_vehicle": self.ai_vehicle_var.get(),
            "ai_door": self.ai_door_var.get(),
            "custom_door_pts": self.custom_door_pts
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(T("settings_save_fail").format(e=e))

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.video_frame = ctk.CTkFrame(self, fg_color="black")
        self.video_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.video_label = ctk.CTkLabel(self.video_frame, text=T("cam_starting"), text_color="white", font=("Arial", 16))
        self.video_label.pack(expand=True)
        self.video_label.bind("<Button-1>", self.on_video_click)

        self.control_panel = ctk.CTkFrame(self)
        self.control_panel.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.btn_manual = ctk.CTkButton(self.control_panel, text=T("btn_manual_off"), command=self.toggle_manual, font=("Arial", 14, "bold"), height=40, width=140, fg_color="#1f6aa5")
        self.btn_manual.grid(row=1, column=0, padx=15, pady=15)

        self.btn_saver = ctk.CTkButton(self.control_panel, text=T("btn_saver_off"), command=self.toggle_saver, font=("Arial", 14, "bold"), height=40, width=140, fg_color="gray")
        self.btn_saver.grid(row=1, column=1, padx=15, pady=15)

        self.btn_schedule = ctk.CTkButton(self.control_panel, text=T("btn_schedule_off"), command=self.toggle_schedule, font=("Arial", 14, "bold"), height=40, width=140, fg_color="gray")
        self.btn_schedule.grid(row=1, column=2, padx=15, pady=15)

        self.status_label = ctk.CTkLabel(self.control_panel, text=T("status_prefix") + T("status_idle").replace("💤 ","💤 "), font=("Arial", 14), text_color="gray")
        self.status_label.grid(row=1, column=3, padx=20, sticky="w")

        # 直播區塊
        self.btn_live = ctk.CTkButton(self.control_panel, text=T("btn_live_on"), command=self.toggle_live, font=("Arial", 14, "bold"), height=40, width=100, fg_color="#E67E22", hover_color="#D35400")
        self.btn_live.grid(row=1, column=4, padx=(20, 5), pady=15)

        self.live_url_entry = ctk.CTkEntry(self.control_panel, width=220, placeholder_text=T("live_url_placeholder"), state="readonly", font=("Arial", 12))
        self.live_url_entry.grid(row=1, column=5, padx=(5, 5), sticky="w")

        self.btn_copy_live = ctk.CTkButton(self.control_panel, text=T("btn_copy"), command=self.copy_live_url, font=("Arial", 12, "bold"), height=30, width=50, fg_color="#34495E", hover_color="#2C3E50")
        self.btn_copy_live.grid(row=1, column=6, padx=(0, 10), sticky="w")

        self.schedule_frame = ctk.CTkFrame(self)
        self.schedule_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.lbl_schedule_hint = ctk.CTkLabel(self.schedule_frame, text=T("schedule_hint"), font=("Arial", 12), text_color="#AAAAAA")
        self.lbl_schedule_hint.grid(row=0, column=0, columnspan=5, pady=(10, 5), sticky="w", padx=20)

        self.schedules_ui = [] 
        for i in range(3):
            saved = self.schedule_data[i]
            check_var = ctk.BooleanVar(value=saved["enable"])
            chk = ctk.CTkCheckBox(self.schedule_frame, text=f"{T('sched_slot')} {i+1}", variable=check_var)
            chk.grid(row=i+1, column=0, padx=20, pady=5)
            
            lbl_start = ctk.CTkLabel(self.schedule_frame, text=T("sched_start"))
            lbl_start.grid(row=i+1, column=1, padx=5)
            start_entry = ctk.CTkEntry(self.schedule_frame, width=80)
            start_entry.insert(0, saved["start"])
            start_entry.grid(row=i+1, column=2, padx=5)
            
            lbl_end = ctk.CTkLabel(self.schedule_frame, text=T("sched_end"))
            lbl_end.grid(row=i+1, column=3, padx=5)
            end_entry = ctk.CTkEntry(self.schedule_frame, width=80)
            end_entry.insert(0, saved["end"])
            end_entry.grid(row=i+1, column=4, padx=5)
            
            self.schedules_ui.append({"enable": check_var, "start": start_entry, "end": end_entry, "chk_ui": chk, "lbl_start": lbl_start, "lbl_end": lbl_end})

        if not self.schedule_armed:
            self.schedule_frame.grid_remove()

        self.tg_frame = ctk.CTkFrame(self)
        self.tg_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.tg_enable_var = ctk.BooleanVar(value=self.tg_enabled_default)
        self.chk_tg_enable = ctk.CTkCheckBox(self.tg_frame, text=T("tg_enable"), variable=self.tg_enable_var, font=("Arial", 12, "bold"), text_color="#3498DB")
        self.chk_tg_enable.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(self.tg_frame, text="Token:").grid(row=0, column=1, padx=2)
        self.entry_tg_token = ctk.CTkEntry(self.tg_frame, width=160, placeholder_text="123456:ABC-DEF...")
        self.entry_tg_token.insert(0, self.tg_token)
        self.entry_tg_token.grid(row=0, column=2, padx=2)
        
        ctk.CTkLabel(self.tg_frame, text="ID:").grid(row=0, column=3, padx=2)
        self.entry_tg_chat_id = ctk.CTkEntry(self.tg_frame, width=90, placeholder_text="123456789")
        self.entry_tg_chat_id.insert(0, self.tg_chat_id)
        self.entry_tg_chat_id.grid(row=0, column=4, padx=2)

        self.btn_test_tg = ctk.CTkButton(self.tg_frame, text=T("btn_test"), width=50, fg_color="#F39C12", hover_color="#D68910", command=self.test_telegram)
        self.btn_test_tg.grid(row=0, column=5, padx=10)

        # ── 語言切換按鈕 / Language switch button (移動至此處) ──
        self.btn_lang = ctk.CTkButton(
            self.tg_frame, text=T("lang_switch_btn"),
            command=self.switch_language,
            font=("Arial", 12, "bold"), height=30, width=70,
            fg_color="#2C3E50", hover_color="#1A252F"
        )
        self.btn_lang.grid(row=0, column=6, padx=(10, 15), sticky="e")
        self.tg_frame.grid_columnconfigure(6, weight=1)

        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.btn_path = ctk.CTkButton(self.bottom_frame, text=T("btn_folder"), command=self.select_folder, fg_color="#555555", width=60)
        self.btn_path.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        
        self.ai_person_var = ctk.BooleanVar(value=self.ai_person_default)
        self.ai_pet_var = ctk.BooleanVar(value=self.ai_pet_default)
        self.ai_vehicle_var = ctk.BooleanVar(value=self.ai_vehicle_default)
        self.ai_door_var = ctk.BooleanVar(value=self.ai_door_default)

        ai_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        ai_frame.grid(row=0, column=1, rowspan=2, padx=10, sticky="w")
        
        self.lbl_ai = ctk.CTkLabel(ai_frame, text=T("ai_label"), font=("Arial", 12, "bold"), text_color="#2ECC71")
        self.lbl_ai.grid(row=0, column=0, padx=(0, 10))
        
        self.chk_ai_person = ctk.CTkCheckBox(ai_frame, text=T("ai_person"), variable=self.ai_person_var, width=70)
        self.chk_ai_pet = ctk.CTkCheckBox(ai_frame, text=T("ai_pet"), variable=self.ai_pet_var, width=60)
        self.chk_ai_vehicle = ctk.CTkCheckBox(ai_frame, text=T("ai_vehicle"), variable=self.ai_vehicle_var, width=70)
        
        self.chk_ai_door = ctk.CTkCheckBox(ai_frame, text=T("ai_door"), variable=self.ai_door_var, text_color="#D2B4DE", width=170)
        self.btn_set_door = ctk.CTkButton(ai_frame, text=T("btn_set_door"), width=70, height=24, fg_color="#9B59B6", hover_color="#8E44AD", command=self.start_setting_door)

        self.chk_ai_person.grid(row=0, column=1, padx=5, pady=2)
        self.chk_ai_pet.grid(row=0, column=2, padx=5, pady=2)
        self.chk_ai_vehicle.grid(row=0, column=3, padx=5, pady=2)
        self.chk_ai_door.grid(row=0, column=4, padx=5, pady=2)
        self.btn_set_door.grid(row=0, column=5, padx=5, pady=2)
        
        if not HAS_YOLO:
            for chk in [self.chk_ai_person, self.chk_ai_pet, self.chk_ai_vehicle, self.chk_ai_door]:
                chk.configure(state="disabled")

        sens_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        sens_frame.grid(row=0, column=2, rowspan=2, padx=(20, 10), sticky="e")
        self.bottom_frame.grid_columnconfigure(2, weight=1)
        
        self.lbl_sens = ctk.CTkLabel(sens_frame, text=T("sens_label"), font=("Arial", 11))
        self.lbl_sens.pack(side="left", padx=(0, 5))
        
        # 加入 L (低) 標示
        ctk.CTkLabel(sens_frame, text="L", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(side="left", padx=(0, 2))
        
        self.sensitivity_slider = ctk.CTkSlider(sens_frame, from_=5, to=100, number_of_steps=95, width=100)
        self.sensitivity_slider.set(self.default_sensitivity)
        self.sensitivity_slider.pack(side="left", padx=2)
        
        # 加入 H (高) 標示
        ctk.CTkLabel(sens_frame, text="H", font=("Arial", 11, "bold"), text_color="#E74C3C").pack(side="left", padx=(2, 5))

    def select_folder(self):
        selected_path = filedialog.askdirectory()
        if selected_path:
            self.save_folder = selected_path

    def copy_live_url(self):
        url = self.live_url_entry.get()
        if url and url.startswith("http"):
            self.clipboard_clear()
            self.clipboard_append(url)
            self.btn_copy_live.configure(text=T("btn_copied"), fg_color="#27AE60")
            self.after(2000, lambda: self.btn_copy_live.configure(text=T("btn_copy"), fg_color="#34495E"))
        else:
            self.btn_copy_live.configure(text=T("btn_no_url"), fg_color="#C0392B")
            self.after(2000, lambda: self.btn_copy_live.configure(text=T("btn_copy"), fg_color="#34495E"))

    def switch_language(self):
        """Toggle between zh and en, then redraw all UI text."""
        _LANG[0] = "en" if _LANG[0] == "zh" else "zh"
        self._refresh_ui_text()

    def _refresh_ui_text(self):
        """Redraw every translatable widget after a language switch."""
        self.title(T("app_title"))
        self.btn_lang.configure(text=T("lang_switch_btn"))

        # Control panel buttons
        self.btn_manual.configure(
            text=T("btn_manual_on") if self.trigger_manual else T("btn_manual_off"))
        self.btn_saver.configure(
            text=T("btn_saver_on") if self.saver_armed else T("btn_saver_off"))
        self.btn_schedule.configure(
            text=T("btn_schedule_on") if self.schedule_armed else T("btn_schedule_off"))
        self.btn_live.configure(
            text=T("btn_live_off") if getattr(self, 'is_live_streaming', False) else T("btn_live_on"))
        self.btn_copy_live.configure(text=T("btn_copy"))
        
        self.live_url_entry.configure(placeholder_text=T("live_url_placeholder"))

        # Schedule frame labels
        self.lbl_schedule_hint.configure(text=T("schedule_hint"))
        for i, s_ui in enumerate(self.schedules_ui):
            s_ui["chk_ui"].configure(text=f"{T('sched_slot')} {i+1}")
            s_ui["lbl_start"].configure(text=T("sched_start"))
            s_ui["lbl_end"].configure(text=T("sched_end"))

        # Bottom frame
        self.btn_path.configure(text=T("btn_folder"))
        self.btn_test_tg.configure(text=T("btn_test"))
        self.chk_tg_enable.configure(text=T("tg_enable"))
        self.chk_ai_person.configure(text=T("ai_person"))
        self.chk_ai_pet.configure(text=T("ai_pet"))
        self.chk_ai_vehicle.configure(text=T("ai_vehicle"))
        self.chk_ai_door.configure(text=T("ai_door"))
        self.btn_set_door.configure(text=T("btn_set_door"))

        # Anonymous labels now stored as instance attributes
        self.lbl_ai.configure(text=T("ai_label"))
        self.lbl_sens.configure(text=T("sens_label"))

        # Update video status labels if camera is not active yet
        if getattr(self, "cam_missing", False):
            self.video_label.configure(text=T("cam_not_found"))
        elif getattr(self, "cam_loading", False):
            self.video_label.configure(text=T("cam_starting"))

        # Redraw dynamic status label
        self.update_ui_state()

    # --- 終極防護：YOLO面積深度軌跡 (無視遮擋與逆光) ---
    def start_setting_door(self):
        if not self.ai_door_var.get():
            messagebox.showinfo(T("door_tip_title"), T("door_tip_check_first"))
            self.ai_door_var.set(True)
        self.custom_door_pts = []
        self.is_setting_door = True
        messagebox.showinfo(T("door_dialog_title"), T("door_dialog_body"))

    def on_video_click(self, event):
        if not getattr(self, 'is_setting_door', False):
            return
        if self.frame_width == 0 or self.frame_height == 0:
            return

        scale_x = self.frame_width / 640.0
        scale_y = self.frame_height / 480.0

        real_x = int(event.x * scale_x)
        real_y = int(event.y * scale_y)

        self.custom_door_pts.append([real_x, real_y])

        if len(self.custom_door_pts) == 6: 
            self.is_setting_door = False
            self.save_settings() 
            messagebox.showinfo(T("door_done_title"), T("door_done_body"))

    def play_audio(self, filename):
        full_path = os.path.join(APP_DIR, filename)
        if not os.path.exists(full_path):
            return
        def _play():
            try:
                if sys.platform == "darwin": subprocess.Popen(["afplay", full_path])
                elif sys.platform == "win32":
                    import winsound
                    winsound.PlaySound(full_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else: subprocess.Popen(["aplay", full_path])
            except: pass
        threading.Thread(target=_play, daemon=True).start()

    def send_telegram_photo(self, photo_path, caption):
        token = self.entry_tg_token.get().strip()
        chat_id = self.entry_tg_chat_id.get().strip()
        if not token or not chat_id: return
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(url, files={'photo': photo}, data={'chat_id': chat_id, 'caption': caption}, timeout=15)
        except: pass

    def send_tg_text(self, text, token=None, chat_id=None):
        if not token or not chat_id:
            token = self.entry_tg_token.get().strip()
            chat_id = self.entry_tg_chat_id.get().strip()
        if not token or not chat_id: return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, data={'chat_id': chat_id, 'text': text}, timeout=10)
        except: pass

    def set_telegram_commands(self, token):
        url = f"https://api.telegram.org/bot{token}/setMyCommands"
        commands = [
            {"command": "on",       "description": T("tg_cmd_on")},
            {"command": "off",      "description": T("tg_cmd_off")},
            {"command": "ai_on",    "description": T("tg_cmd_ai_on")},
            {"command": "ai_off",   "description": T("tg_cmd_ai_off")},
            {"command": "photo",    "description": T("tg_cmd_photo")},
            {"command": "live_on",  "description": T("tg_cmd_live_on")},
            {"command": "live_off", "description": T("tg_cmd_live_off")},
            {"command": "hide",     "description": T("tg_cmd_hide")},
            {"command": "show",     "description": T("tg_cmd_show")},
            {"command": "status",   "description": T("tg_cmd_status")},
            {"command": "quit",     "description": T("tg_cmd_quit")},
            {"command": "help",     "description": T("tg_cmd_help")},
        ]
        try:
            requests.post(url, json={"commands": commands}, timeout=5)
        except Exception as e:
            print(T("tg_menu_fail").format(e=e))

    def telegram_listener(self):
        while self.is_running:
            try:
                if self.chk_tg_enable.get() and self.entry_tg_token.get() and self.entry_tg_chat_id.get():
                    token = self.entry_tg_token.get().strip()
                    chat_id = self.entry_tg_chat_id.get().strip()
                    
                    # 如果尚未設定過快捷選單，則自動向 Telegram 註冊
                    if not getattr(self, 'tg_commands_set', False):
                        self.set_telegram_commands(token)
                        self.tg_commands_set = True
                        
                    url = f"https://api.telegram.org/bot{token}/getUpdates"
                    params = {'offset': self.last_update_id + 1, 'timeout': 10}
                    res = requests.get(url, params=params, timeout=15)
                    data = res.json()
                    
                    if data.get('ok') and data['result']:
                        for update in data['result']:
                            self.last_update_id = update['update_id']
                            if 'message' in update and 'text' in update['message']:
                                msg = update['message']
                                if str(msg['chat']['id']) == chat_id:
                                    if time.time() - msg.get('date', 0) < 60:
                                        self.process_telegram_command(msg['text'].strip().lower(), token, chat_id)
                else: time.sleep(2)
            except: time.sleep(3)

    def _start_cloudflare_tunnel(self, from_tg=False):
        if getattr(self, 'cf_process', None) is not None:
            self.cf_process.terminate()
            self.cf_process = None
        
        try:
            cmd = [self.cf_filename, "tunnel", "--url", "http://127.0.0.1:5050"]
            self.cf_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            tunnel_url = None
            start_time = time.time()
            import re
            
            while time.time() - start_time < 15:
                line = self.cf_process.stderr.readline()
                if not line: break
                match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if match:
                    tunnel_url = match.group(1)
                    break

            if tunnel_url:
                self.is_live_streaming = True
                self.after(0, lambda: self._update_live_ui(tunnel_url))
                
                if self.chk_tg_enable.get():
                    prefix = f"[{self.hostname}] "
                    live_msg = T("live_tg_opened").format(prefix=prefix, url=tunnel_url)
                    self.send_tg_text(live_msg)
            else:
                self.cf_process.terminate()
                self.cf_process = None
                self.is_live_streaming = False
                self.after(0, lambda: self._update_live_ui_fail(T("cf_no_url_fail")))
                if self.chk_tg_enable.get():
                    prefix = f"[{self.hostname}] "
                    self.send_tg_text(T("live_tg_no_url").format(prefix=prefix))
        except Exception as e:
            self.is_live_streaming = False
            self.after(0, lambda err=e: self._update_live_ui_fail(T("cf_fail").format(e=err)))
            if self.chk_tg_enable.get():
                prefix = f"[{self.hostname}] "
                self.send_tg_text(T("live_tg_fail").format(prefix=prefix, e=e))
            
        self.after(0, self.update_ui_state)

    def _update_live_ui(self, url):
        self.live_url_entry.configure(state="normal")
        self.live_url_entry.delete(0, 'end')
        self.live_url_entry.insert(0, url)
        self.live_url_entry.configure(state="readonly")
        self.btn_live.configure(text=T("btn_live_off"), fg_color="#C0392B", state="normal")
        self.btn_copy_live.configure(state="normal")

    def _update_live_ui_fail(self, msg):
        self.live_url_entry.configure(state="normal")
        self.live_url_entry.delete(0, 'end')
        self.live_url_entry.insert(0, msg)
        self.live_url_entry.configure(state="readonly")
        self.btn_live.configure(text=T("btn_live_on"), fg_color="#E67E22", state="normal")
        
    def toggle_live(self):
        if getattr(self, 'is_live_streaming', False):
            self.stop_live()
        else:
            self.btn_live.configure(text=T("btn_live_connecting"), fg_color="gray", state="disabled")
            self.live_url_entry.configure(state="normal")
            self.live_url_entry.delete(0, 'end')
            self.live_url_entry.insert(0, T("live_getting_url"))
            self.live_url_entry.configure(state="readonly")
            threading.Thread(target=self._start_cloudflare_tunnel, daemon=True).start()

    def stop_live(self, from_tg=False):
        self.is_live_streaming = False
        if getattr(self, 'cf_process', None) is not None:
            self.cf_process.terminate()
            self.cf_process = None
        
        self.live_url_entry.configure(state="normal")
        self.live_url_entry.delete(0, 'end')
        self.live_url_entry.insert(0, T("live_closed"))
        self.live_url_entry.configure(state="readonly")
        
        self.btn_live.configure(text=T("btn_live_on"), fg_color="#E67E22", state="normal")
        
        if self.chk_tg_enable.get() and not from_tg:
            prefix = f"[{self.hostname}] "
            self.send_tg_text(T("live_tg_stopped").format(prefix=prefix))

    def process_telegram_command(self, command, token, chat_id):
        p = f"[{self.hostname}] "
        if command == '/on':
            self.trigger_manual = True
            self.after(0, self.refresh_detection_state)
            self.send_tg_text(T("tg_r_manual_on").format(p=p), token, chat_id)
        elif command == '/off':
            self.trigger_manual = False
            self.after(0, self.refresh_detection_state)
            self.send_tg_text(T("tg_r_manual_off").format(p=p), token, chat_id)
        elif command == '/ai_on':
            self.after(0, lambda: [self.chk_ai_person.select(), self.chk_ai_door.select()])
            self.send_tg_text(T("tg_r_ai_on").format(p=p), token, chat_id)
        elif command == '/ai_off':
            self.after(0, lambda: [self.chk_ai_person.deselect(), self.chk_ai_pet.deselect(), self.chk_ai_vehicle.deselect(), self.chk_ai_door.deselect()])
            self.send_tg_text(T("tg_r_ai_off").format(p=p), token, chat_id)
        elif command == '/photo':
            self.send_tg_text(T("tg_r_photo").format(p=p), token, chat_id)
            self.force_take_photo = True
        elif command == '/live_on':
            self.after(0, lambda: self.btn_live.configure(text=T("btn_live_connecting"), fg_color="gray", state="disabled"))
            self.after(0, lambda: (self.live_url_entry.configure(state="normal"),
                                   self.live_url_entry.delete(0, 'end'),
                                   self.live_url_entry.insert(0, T("live_getting_url")),
                                   self.live_url_entry.configure(state="readonly")))
            threading.Thread(target=self._start_cloudflare_tunnel, args=(True,), daemon=True).start()
        elif command == '/live_off':
            self.after(0, lambda: self.stop_live(from_tg=True))
            self.send_tg_text(T("tg_r_live_off").format(p=p), token, chat_id)
        elif command == '/hide':
            self.is_window_hidden = True
            self.after(0, self.minimize_to_tray)
            key = "tg_r_hide_mac" if sys.platform == "darwin" else "tg_r_hide_win"
            self.send_tg_text(T(key).format(p=p), token, chat_id)
        elif command == '/show':
            self.is_window_hidden = False
            self.after(0, lambda: self.show_window(None, None))
            self.send_tg_text(T("tg_r_show").format(p=p), token, chat_id)
        elif command == '/quit':
            self.send_tg_text(T("tg_r_quit").format(p=p), token, chat_id)
            self.after(1000, self.quit_app)
        elif command in ['/status', '/start', '/help']:
            if self.detecting:
                triggers = []
                if self.trigger_manual:  triggers.append(T("trig_manual"))
                if self.trigger_schedule: triggers.append(T("trig_schedule"))
                if self.trigger_saver:   triggers.append(T("trig_saver"))
                state_str = f"{T('tg_state_monitoring')} ({'+'.join(triggers)})"
            else:
                armed = []
                if self.saver_armed:    armed.append(T("trig_saver"))
                if self.schedule_armed: armed.append(T("trig_schedule"))
                state_str = f"{T('tg_state_standby')} ({'+'.join(armed)})" if armed else T("tg_state_stopped")
            
            ai_list = []
            if self.ai_person_var.get():  ai_list.append(T("tg_ai_person"))
            if self.ai_pet_var.get():     ai_list.append(T("tg_ai_pet"))
            if self.ai_vehicle_var.get(): ai_list.append(T("tg_ai_vehicle"))
            if self.ai_door_var.get():    ai_list.append(T("tg_ai_door"))
            mode_str = f"{T('tg_mode_ai')} ({'/'.join(ai_list)})" if ai_list else T("tg_mode_classic")
            sens_str  = f"{int(self.sensitivity_slider.get())}%"
            win_str   = T("tg_win_hidden") if self.is_window_hidden else T("tg_win_visible")
            live_str  = T("tg_live_on_str") if getattr(self, 'is_live_streaming', False) else T("tg_live_off_str")
            
            status_msg = (T("tg_status_prefix").format(p=p) +
                          T("tg_status_state").format(v=state_str) +
                          T("tg_status_mode").format(v=mode_str) +
                          T("tg_status_live").format(v=live_str) +
                          T("tg_status_sens").format(s=sens_str, w=win_str))

            if command == '/status':
                self.send_tg_text(status_msg, token, chat_id)
            else:
                reply_msg = f"{status_msg}\n\n{T('tg_help_body')}"
                self.send_tg_text(reply_msg, token, chat_id)

    def test_telegram(self):
        token = self.entry_tg_token.get().strip()
        chat_id = self.entry_tg_chat_id.get().strip()
        if not token or not chat_id: return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            res = requests.post(url, data={'chat_id': chat_id, 'text': T("tg_test_ok").format(host=self.hostname)}, timeout=10)
            if res.status_code == 200:
                self.set_telegram_commands(token)
                messagebox.showinfo(T("tg_test_msg_title"), T("tg_test_msg_body"))
        except: pass

    def refresh_detection_state(self):
        self.detecting = self.trigger_manual or self.trigger_saver or self.trigger_schedule
        self.update_ui_state()

    def update_ui_state(self):
        self.btn_manual.configure(
            text=T("btn_manual_on") if self.trigger_manual else T("btn_manual_off"),
            fg_color="#C0392B" if self.trigger_manual else "#1f6aa5")
        self.btn_saver.configure(
            text=T("btn_saver_on") if self.saver_armed else T("btn_saver_off"),
            fg_color="#27AE60" if self.saver_armed else "gray")
        self.btn_schedule.configure(
            text=T("btn_schedule_on") if self.schedule_armed else T("btn_schedule_off"),
            fg_color="#8E44AD" if self.schedule_armed else "gray")

        if self.detecting:
            triggers = []
            if self.trigger_manual:   triggers.append(T("trig_manual"))
            if self.trigger_schedule: triggers.append(T("trig_schedule"))
            if self.trigger_saver:    triggers.append(T("trig_saver"))
            if self.intrusion_detected:
                msg, color = T("status_alarm"), "#FF8800"
            else:
                msg, color = f"{T('status_monitoring')} ({'+'.join(triggers)})", "#E74C3C"
        else:
            armed = []
            if self.saver_armed:    armed.append(T("trig_saver"))
            if self.schedule_armed: armed.append(T("trig_schedule"))
            if armed:
                msg, color = f"{T('status_standby')} ({'+'.join(armed)})", "#3498DB"
            else:
                msg, color = T("status_idle"), "gray"
        self.status_label.configure(text=T("status_prefix") + msg, text_color=color)

    def toggle_manual(self):
        self.trigger_manual = not self.trigger_manual
        self.refresh_detection_state()

    def toggle_saver(self):
        self.saver_armed = not self.saver_armed
        if not self.saver_armed: self.trigger_saver = self.intrusion_detected = False
        self.refresh_detection_state()

    def toggle_schedule(self):
        self.schedule_armed = not self.schedule_armed
        if self.schedule_armed: self.schedule_frame.grid() 
        else: self.schedule_frame.grid_remove() 
        if not self.schedule_armed: self.trigger_schedule = False
        self.refresh_detection_state()

    def is_screensaver_active(self):
        if sys.platform == "win32":
            try:
                is_running = ctypes.c_int()
                ctypes.windll.user32.SystemParametersInfoW(SPI_GETSCREENSAVERRUNNING, 0, ctypes.byref(is_running), 0)
                return is_running.value != 0
            except: return False
        return False

    def check_schedule_time(self):
        now = datetime.now().time()
        for sched in self.schedules_ui:
            if sched["enable"].get():
                try:
                    start = datetime.strptime(sched["start"].get(), "%H:%M").time()
                    end = datetime.strptime(sched["end"].get(), "%H:%M").time()
                    if start <= end:
                        if start <= now < end: return True
                    else: 
                        if start <= now or now < end: return True
                except ValueError: pass
        return False

    def monitor_logic(self):
        while self.is_running:
            try:
                if self.schedule_armed:
                    in_time = self.check_schedule_time()
                    if in_time != self.trigger_schedule:
                        self.trigger_schedule = in_time
                        self.after(0, self.refresh_detection_state)
                if self.saver_armed:
                    if self.is_screensaver_active():
                        if not self.trigger_saver:
                            self.trigger_saver = True
                            self.after(0, self.refresh_detection_state)
                    else:
                        if self.trigger_saver and not self.intrusion_detected:
                            self.intrusion_detected = True
                            self.after(0, self.refresh_detection_state)
                time.sleep(1)
            except: time.sleep(1)

    def update_video_display(self):
        if self.is_running:
            frame_to_show = None
            with self.frame_lock:
                if self.latest_frame is not None:
                    frame_to_show = self.latest_frame
            if frame_to_show is not None and self.winfo_exists():
                try:
                    imgtk = ctk.CTkImage(light_image=frame_to_show, dark_image=frame_to_show, size=(640, 480))
                    self.video_label.configure(image=imgtk, text="")
                except: pass
            self.after(30, self.update_video_display)

    def save_current_frame(self, frame, prefix="capture_"):
        target_dir = os.path.join(self.save_folder, time.strftime("%Y%m%d"))
        if not os.path.exists(target_dir): os.makedirs(target_dir)
        filename = os.path.join(target_dir, f"{prefix}{time.strftime('%Y%m%d_%H%M%S')}.jpg")
        cv2.imwrite(filename, frame)
        return filename

    def video_processing_thread(self):
        if HAS_YOLO:
            try:
                print(T("yolo_loading"))
                model_path = os.path.join(APP_DIR, "yolov8n.pt")
                self.yolo_model = YOLO(model_path) 
            except: pass

        self.cap = cv2.VideoCapture(0)
        ret, frame1 = self.cap.read()
        self.cam_loading = False
        
        if not ret: 
            self.cam_missing = True
            self.after(0, lambda: self.video_label.configure(text=T("cam_not_found"), text_color="red"))
            return
        
        self.frame_height, self.frame_width = frame1.shape[:2]
        
        gray = cv2.GaussianBlur(cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY), (21, 21), 0)
        self.bg_model = gray.copy().astype("float")
        
        last_capture_time = 0.0
        last_tg_send_time = 0.0 
        kernel = np.ones((5, 5), np.uint8)

        while self.is_running:
            ret, frame2 = self.cap.read()
            if not ret: break
            
            h, w = frame2.shape[:2]
            self.frame_height, self.frame_width = h, w
            current_time = time.time()
            valid_trigger = False
            ai_caption = ""
            overlay = frame2.copy()
            
            if self.force_take_photo:
                self.force_take_photo = False
                filename = self.save_current_frame(frame2, prefix="manual_")
                threading.Thread(target=self.send_telegram_photo, args=(filename, f"📸 [{self.hostname}] 的即時畫面"), daemon=True).start()

            # --- 畫面繪製：正在畫 6 點的時候 ---
            if self.is_setting_door:
                for i, pt in enumerate(self.custom_door_pts):
                    if i < 2:
                        cv2.circle(overlay, tuple(pt), 5, (255, 0, 255), -1) # 門框紫線
                        if i == 1:
                            cv2.line(overlay, tuple(self.custom_door_pts[0]), tuple(pt), (255, 0, 255), 2) 
                    elif i >= 2:
                        cv2.circle(overlay, tuple(pt), 5, (0, 255, 0), -1) # 綠框
                        if i > 2:
                            cv2.line(overlay, tuple(self.custom_door_pts[i-1]), tuple(pt), (0, 255, 0), 2)
                        if i == 5:
                            cv2.line(overlay, tuple(self.custom_door_pts[5]), tuple(self.custom_door_pts[2]), (0, 255, 0), 2)
                        
                cv2.putText(overlay, f"Setting Door: Click {len(self.custom_door_pts)+1}/6", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            ai_classes = set()
            if self.ai_person_var.get() or self.ai_door_var.get(): ai_classes.add(0) # 門禁系統強制啟用人體辨識
            if self.ai_vehicle_var.get(): ai_classes.update([1, 2, 3])
            if self.ai_pet_var.get(): ai_classes.update([15, 16])

            force_send_event = False
            door_event_msg = ""
            
            gray = cv2.GaussianBlur(cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY), (21, 21), 0)
            cv2.accumulateWeighted(gray, self.bg_model, 0.05)
            frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.bg_model))
            
            actual_threshold = 105 - self.sensitivity_slider.get()
            thresh = cv2.threshold(frame_delta, actual_threshold, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, kernel, iterations=2)
            
            # =========================================================
            # 🔥 YOLO AI 追蹤與遮罩 (製造隱形斗篷)
            # =========================================================
            yolo_results = None
            person_mask = np.zeros_like(thresh)
            tracked_persons = []
            
            if ai_classes and self.yolo_model is not None and not self.is_setting_door:
                yolo_results = self.yolo_model.track(frame2, classes=list(ai_classes), conf=0.35, persist=True, verbose=False, tracker="bytetrack.yaml")
                for r in yolo_results:
                    boxes = r.boxes
                    if boxes.id is not None:
                        for tid, cid, conf, xyxy in zip(boxes.id.int().cpu().tolist(), boxes.cls.int().cpu().tolist(), boxes.conf.float().cpu().tolist(), boxes.xyxy.int().cpu().tolist()):
                            if cid == 0: 
                                x1, y1, x2, y2 = xyxy
                                
                                # 🔥 核心修復：YOLO 的框有時候會切齊髮際線，導致頭頂產生殘影觸發紫線！
                                # 我們將遮罩「往上擴張 20%」、「左右擴張 15%」，徹底把人的所有邊緣吃掉！
                                h_box = y2 - y1
                                w_box = x2 - x1
                                exp_y1 = max(0, int(y1 - h_box * 0.20))
                                exp_x1 = max(0, int(x1 - w_box * 0.15))
                                exp_x2 = min(w, int(x2 + w_box * 0.15))
                                
                                # 將擴張後的人體框畫成白色遮罩
                                cv2.rectangle(person_mask, (exp_x1, exp_y1), (exp_x2, y2), 255, -1)
                                tracked_persons.append({'id': tid, 'bbox': (x1, y1, x2, y2), 'conf': conf})

            # 使用 Kernel 膨脹，再次確保沒有任何殘影外漏 (對付陰影與反光)
            kernel_large = np.ones((15, 15), np.uint8)
            person_mask_dilated = cv2.dilate(person_mask, kernel_large, iterations=2) 
            pure_env_thresh = cv2.bitwise_and(thresh, cv2.bitwise_not(person_mask_dilated))

            cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            motion_boxes = []
            for c in cnts:
                if cv2.contourArea(c) > 800:
                    mx, my, mw, mh = cv2.boundingRect(c)
                    motion_boxes.append((mx, my, mx + mw, my + mh))

            if self.detecting:
                # =========================================================
                # 【AI 門框變形】 + 【YOLO面積深度軌跡 (無視下半身遮擋)】
                # =========================================================
                if self.ai_door_var.get() and len(self.custom_door_pts) == 6 and not self.is_setting_door:
                    pt_door1 = self.custom_door_pts[0]
                    pt_door2 = self.custom_door_pts[1]
                    green_poly = np.array(self.custom_door_pts[2:6], np.int32)
                    
                    # 繪製 UI
                    cv2.line(overlay, tuple(pt_door1), tuple(pt_door2), (255, 0, 255), 3)
                    cv2.polylines(overlay, [green_poly], True, (0, 255, 0), 2)
                    
                    # -----------------------------------------------------
                    # 系統一：【AI 濾除門框變形檢測】
                    # -----------------------------------------------------
                    mask_door = np.zeros_like(thresh)
                    cv2.line(mask_door, tuple(pt_door1), tuple(pt_door2), 255, 20)
                    
                    door_thresh = cv2.bitwise_and(pure_env_thresh, mask_door)
                    motion_pixels = cv2.countNonZero(door_thresh)
                    door_area = math.hypot(pt_door2[0]-pt_door1[0], pt_door2[1]-pt_door1[1]) * 20
                    door_ratio = (motion_pixels / door_area) if door_area > 0 else 0
                    
                    cv2.putText(overlay, f"Door Motion: {door_ratio:.3f}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                    
                    # 依據最新照片實測：確保防護力場生效後，將門檻設為 1.5% (0.015) 抓取開門瞬間！
                    if door_area > 50 and door_ratio > 0.015:
                        self.door_trigger_time = current_time
                        
                    # 狀態燈號顯示 (移至前面判定，作為進出的嚴格守門員)
                    # 【重要修正】：將寬限時間從 12 秒大幅縮短為 4 秒！
                    # 正常開關門、走進走出的動作約在 3~4 秒內完成。
                    # 超過 4 秒後門若無動作，立刻切回 STANDBY，阻斷任何室內走動的誤判。
                    is_door_open = (hasattr(self, 'door_trigger_time') and (current_time - self.door_trigger_time < 4.0))
                    
                    if is_door_open:
                        cv2.line(overlay, tuple(pt_door1), tuple(pt_door2), (0, 0, 255), 5) # 門開紅燈
                        cv2.putText(overlay, "DOOR: ACTIVE", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        cv2.putText(overlay, "DOOR: STANDBY", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)

                    # -----------------------------------------------------
                    # 系統二：【YOLO 人體面積深度軌跡 (Depth Tracking - 終極防護版)】
                    # -----------------------------------------------------
                    current_tids_in_zone = []
                    
                    # 🚨 最強防呆：只有當門被打開過 (is_door_open 為 True)，才允許啟動進出判斷！
                    if is_door_open:
                        for p in tracked_persons:
                            tid = p['id']
                            px1, py1, px2, py2 = p['bbox']
                            
                            pw = px2 - px1
                            ph = py2 - py1
                            person_cx = px1 + pw // 2
                            person_cy = py1 + ph // 2
                            feet_y = py2
                            current_area = pw * ph
                            
                            # 放寬判定：只要人體中心點 或 腳底(py2) 在綠框內，就判定為在感測區
                            if (cv2.pointPolygonTest(green_poly, (person_cx, person_cy), False) >= 0 or 
                                cv2.pointPolygonTest(green_poly, (person_cx, feet_y), False) >= 0):
                                
                                current_tids_in_zone.append(tid)
                                cv2.circle(overlay, (person_cx, person_cy), 8, (0, 165, 255), -1)
                                
                                # 移除舊版強制延長時間的 Bug，完全依賴紫線的物理動作
                                
                                # 註冊並記錄此人的「深度軌跡」
                                if tid not in self.zone_persons:
                                    self.zone_persons[tid] = {'history': [], 'reported': False}
                                
                                self.zone_persons[tid]['history'].append({
                                    'area': current_area,
                                    'y2': feet_y,
                                    'bbox': (px1, py1, px2, py2)
                                })

                                # 保留約 2 秒的軌跡 (以 30fps 估算，保留 60 幀)
                                if len(self.zone_persons[tid]['history']) > 60:
                                    self.zone_persons[tid]['history'].pop(0)

                                # 👉【即時面積深度分析】
                                if not self.zone_persons[tid]['reported']:
                                    hist = self.zone_persons[tid]['history']
                                    if len(hist) >= 5: # 觀察 5 幀，確認趨勢
                                        first_state = hist[0]
                                        curr_state = hist[-1]
                                        
                                        area_ratio = curr_state['area'] / first_state['area']
                                        dy2 = curr_state['y2'] - first_state['y2']
                                        
                                        # 嚴格條件：面積需膨脹超過 35%，且腳底座標明顯往下 (Y增加) -> 才是真正「走近」
                                        if area_ratio > 1.35 and dy2 > 15:
                                            self.play_audio("in.wav")
                                            door_event_msg = f"🚪 門禁：人員由遠走近，判定為「進入」室內！"
                                            force_send_event = True
                                            self.zone_persons[tid]['reported'] = True
                                            self.last_cross_bbox = curr_state['bbox']
                                            
                                        # 嚴格條件：面積需縮小超過 25%，且腳底座標明顯往上 (Y減少) -> 才是真正「走遠」
                                        elif area_ratio < 0.75 and dy2 < -15:
                                            self.play_audio("out.wav")
                                            door_event_msg = f"🚪 門禁：人員由近走遠，判定為「離開」室外！"
                                            force_send_event = True
                                            self.zone_persons[tid]['reported'] = True
                                            self.last_cross_bbox = curr_state['bbox']
                                            
                        # 👉 【離框結算機制 (Checkout)】過濾室內橫向走動的干擾
                        for tid in list(self.zone_persons.keys()):
                            if tid not in current_tids_in_zone:
                                if not self.zone_persons[tid]['reported']:
                                    hist = self.zone_persons[tid]['history']
                                    if len(hist) >= 5: 
                                        first_state = hist[0]
                                        last_state = hist[-1]
                                        
                                        area_ratio = last_state['area'] / first_state['area']
                                        dy2 = last_state['y2'] - first_state['y2']
                                        
                                        # 提取歷史中的最大與最小面積，計算最大變化幅度
                                        areas = [s['area'] for s in hist]
                                        max_min_ratio = max(areas) / min(areas) if min(areas) > 0 else 1
                                        
                                        # 只有在軌跡中出現過 >30% 的面積變化，才認定有發生「深度位移」
                                        if max_min_ratio > 1.30:
                                            if area_ratio > 1.25 and dy2 > 10:
                                                self.play_audio("in.wav")
                                                door_event_msg = f"🚪 門禁結算：人員越線進入，判定為「進入」室內！"
                                                force_send_event = True
                                            elif area_ratio < 0.80 and dy2 < -10:
                                                self.play_audio("out.wav")
                                                door_event_msg = f"🚪 門禁結算：人員越線離開，判定為「離開」室外！"
                                                force_send_event = True
                                            
                                del self.zone_persons[tid]
                                
                    else:
                        # 🚨 門處於關閉/靜止狀態時，強制清空所有綠框的追蹤紀錄！
                        # 這樣無論室內的人怎麼走動、紅框多大，都不可能產生進出的判定。
                        self.zone_persons.clear()

                # =========================================================
                # 原有的 YOLO 辨識邏輯
                # =========================================================
                if yolo_results is not None and not self.is_setting_door:
                    TARGET_CLASSES = {0: "Person", 1: "Bicycle", 2: "Car", 3: "Motorcycle", 15: "Cat", 16: "Dog"}
                    detected_counts = {val: 0 for val in TARGET_CLASSES.values()}
                    total_targets = 0
                    current_ids = []
                    
                    for r in yolo_results:
                        boxes = r.boxes
                        clss = boxes.cls.int().cpu().tolist()
                        confs = boxes.conf.float().cpu().tolist()
                        xyxys = boxes.xyxy.int().cpu().tolist()
                        has_ids = boxes.id is not None
                        track_ids = boxes.id.int().cpu().tolist() if has_ids else [None] * len(clss)
                        
                        for track_id, cls_id, conf, xyxy in zip(track_ids, clss, confs, xyxys):
                            if cls_id in TARGET_CLASSES:
                                label = TARGET_CLASSES[cls_id]
                                x1, y1, x2, y2 = xyxy
                                
                                trigger_this = False
                                if label == "Person" and self.ai_person_var.get(): trigger_this = True
                                elif label in ["Cat", "Dog"] and self.ai_pet_var.get(): trigger_this = True
                                elif label in ["Bicycle", "Car", "Motorcycle"] and self.ai_vehicle_var.get(): trigger_this = True
                                
                                object_has_motion = False
                                for (mx1, my1, mx2, my2) in motion_boxes:
                                    if x1 < mx2 and x2 > mx1 and y1 < my2 and y2 > my1:
                                        object_has_motion = True
                                        break
                                
                                if track_id is not None:
                                    if trigger_this: current_ids.append(track_id)
                                    if track_id not in self.track_state:
                                        self.track_state[track_id] = {
                                            'last_motion_time': current_time if object_has_motion else 0,
                                            'missing': 0
                                        }
                                    else:
                                        self.track_state[track_id]['missing'] = 0
                                        
                                    if object_has_motion:
                                        self.track_state[track_id]['last_motion_time'] = current_time
                                        
                                    is_active_motion = (current_time - self.track_state[track_id].get('last_motion_time', 0) < 2.5)
                                else:
                                    is_active_motion = object_has_motion
                                
                                if trigger_this:
                                    if is_active_motion:
                                        detected_counts[label] += 1
                                        total_targets += 1
                                        
                                    if label == "Person": color = (0, 0, 255)
                                    elif label in ["Cat", "Dog"]: color = (0, 165, 255)
                                    else: color = (255, 255, 0)
                                    
                                    if not is_active_motion and track_id is not None:
                                        status_text = " (Static)"
                                        color = (150, 150, 150) 
                                    else:
                                        status_text = ""
                                        
                                    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 4)
                                    id_str = f" #{track_id}" if track_id is not None else ""
                                    cv2.putText(overlay, f"{label}{id_str}{status_text} {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

                    for tid in list(self.track_state.keys()):
                        if tid not in current_ids:
                            self.track_state[tid]['missing'] = self.track_state[tid].get('missing', 0) + 1
                            if self.track_state[tid]['missing'] > 10:
                                del self.track_state[tid]
                    
                    if total_targets > 0:
                        valid_trigger = True
                        details = [f"{v} {k}" for k, v in detected_counts.items() if v > 0]
                        ai_caption = "\n🤖 AI 偵測: " + "、".join(details) if details else ""

                elif not self.is_setting_door:
                    if len(motion_boxes) > 0:
                        valid_trigger = True
                        for (mx1, my1, mx2, my2) in motion_boxes:
                            cv2.rectangle(overlay, (mx1, my1), (mx2, my2), (0, 255, 0), 2)

                if door_event_msg:
                    valid_trigger = True
                    ai_caption = f"\n{door_event_msg}" + ai_caption

            if valid_trigger or self.is_setting_door:
                cv2.addWeighted(overlay, 0.5, frame2, 0.5, 0, frame2)

            ret_jpg, buffer = cv2.imencode('.jpg', frame2, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret_jpg:
                with self.frame_lock:
                    self.latest_jpeg_bytes = buffer.tobytes()
                
            if valid_trigger and not self.is_setting_door:
                if current_time - last_capture_time > 1.0 or force_send_event:
                    filename = self.save_current_frame(frame2)
                    last_capture_time = current_time

                    if self.chk_tg_enable.get() and (current_time - last_tg_send_time > 5.0 or force_send_event):
                        src = "手動" if self.trigger_manual else "排程" if self.trigger_schedule else "螢幕保護"
                        caption = f"⚠️ 警報！[{self.hostname}] 偵測到異常活動。\n🕒 時間: {time.strftime('%H:%M:%S')}\n🔍 觸發: {src}監控{ai_caption}"
                        threading.Thread(target=self.send_telegram_photo, args=(filename, caption), daemon=True).start()
                        last_tg_send_time = current_time

            pil_image = Image.fromarray(cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB))
            with self.frame_lock: self.latest_frame = pil_image
            time.sleep(0.03)
            
        self.cap.release()

    def minimize_to_tray(self):
        self.is_window_hidden = True
        if sys.platform == "darwin": return self.iconify()
        if self.tray_icon: return
        try:
            self.withdraw()
            color = (142, 68, 173) if (self.saver_armed or self.schedule_armed) else (0, 120, 255)
            img = Image.new('RGB', (64, 64), color=color) 
            draw = ImageDraw.Draw(img)
            draw.ellipse((16, 16, 48, 48), fill="white")
            draw.ellipse((24, 24, 40, 40), fill=color)
            self.tray_icon = pystray.Icon("MotionDetector", img, T("tray_tooltip"), (item(T("tray_show"), self.show_window, default=True), item(T("tray_quit"), self.quit_app)))
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except: self.deiconify()

    def show_window(self, _icon=None, _item=None):
        if self.tray_icon: 
            self.tray_icon.stop()
            self.tray_icon = None
        self.after(0, self._restore_window)

    def _restore_window(self):
        self.is_window_hidden = False
        self.deiconify()
        self.state('normal')
        self.lift()

    def quit_app(self, _icon=None, _item=None):
        self.save_settings()
        if getattr(self, 'cf_process', None):
            try: self.cf_process.terminate()
            except: pass
        self.is_running = False
        try: self.instance_socket.close()
        except: pass
        if self.tray_icon: self.tray_icon.stop()
        self.quit()
        sys.exit()

if __name__ == "__main__":
    app = MotionDetectorApp()
    app.mainloop()