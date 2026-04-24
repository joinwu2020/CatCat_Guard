# 🐾 CatCat Guard

這是一個基於 Python 開發的桌面監控與動態偵測應用程式 (Motion Detector)。
具備Telegram Bot 操控/回報 機制，並可輕鬆打包為獨立執行檔。

## ✨ 功能特色

* **動態偵測**: 使用 OpenCV 進行影像與動作捕捉。
* **系統列支援**: 可縮小至 Windows/macOS 系統列 (Tray icon) 於背景執行。
* **現代化 UI**: 使用 `customtkinter` 打造美觀的深色/淺色主題介面。
* **網頁推流 (Web Stream)**: 內建 Flask 伺服器，支援遠端查看狀態或畫面。
* **Telegram Bot**: 支援 Telegram Bot API，支援遠端設定/狀態顯示/畫面截圖。
* **路徑自動校正**: 內建路徑偵測，完美相容 `PyInstaller` 打包後的執行檔環境。

## 🛠️ 安裝與執行

### 1. 下載專案

```bash
git clone [https://github.com/joinwu2020/CatCat_Guard.git](https://github.com/joinwu2020/CatCat_Guard.git)
cd CatCat_Guard
```

2. 安裝必要的套件

建議使用虛擬環境 (Virtual Environment)，然後安裝 requirements.txt 中的套件：
```bash
pip install -r requirements.txt
```

3. 執行程式
```bash
python CatCat_Guard.py
```

📦 打包成執行檔

本程式已經處理好 PyInstaller 打包後的路徑問題。你可以使用以下指令將其打包為單一執行資料夾：
```bash
pyinstaller --noconfirm --onedir --windowed "CatCat_Guard.py"
```

## 🤖 如何建立 Telegram Bot (使用 BotFather)

若要使用本程式的自動提醒功能，你需要先建立一個 Telegram Bot 並取得 **API Token**。

### 1. 啟動 BotFather
* 在 Telegram 中搜尋 `@BotFather` 並開啟對話，或點擊此連結：[https://t.me/botfather](https://t.me/botfather)
* 點擊 **Start**。

### 2. 建立新 Bot
* 輸入指令：`/newbot`
* **設定名稱 (Name)**：這是 Bot 的顯示名稱（例如：`My CatCat Guard`）。
* **設定使用者名稱 (Username)**：這是 Bot 的唯一帳號，結尾必須是 `bot`（例如：`catcat_guard_2026_bot`）。

### 3. 取得 API Token
* 建立成功後，BotFather 會傳送一段訊息，其中包含你的 **HTTP API Token**（看起來像是一串數字與英文字母的組合，例如 `12345678:AA...`）。
* **請妥善保管此 Token，切勿外流！**

### 4. 取得你的 Chat ID
為了讓 Bot 知道要傳訊息給「誰」，你需要取得你的個人 Chat ID：
* 在 Telegram 搜尋 `@userinfobot` 並點擊 Start。
* 它會回傳你的 `Id`（一串數字），這就是你的 **Chat ID**。

---

### ⚠️ 安全提醒 (Security Note)
* **請勿**將你的 API Token 直接寫死在程式碼中並上傳到 GitHub 公開儲存庫。
* 建議使用 `.env` 檔案或 `config.json` 來儲存 Token，並確保將這些檔案列入 `.gitignore`。


📄 授權條款

This project is licensed under the MIT License.
