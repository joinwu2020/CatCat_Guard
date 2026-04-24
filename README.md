# 🐾 CatCat Guard

這是一個基於 Python 開發的桌面監控與動態偵測應用程式 (Motion Detector)。
具備系統列 (System Tray) 圖示支援以及防呆防錯機制，並可輕鬆打包為獨立執行檔。

## ✨ 功能特色

* **動態偵測**: 使用 OpenCV 進行影像與動作捕捉。
* **系統列支援**: 可縮小至 Windows/macOS 系統列 (Tray icon) 於背景執行。
* **現代化 UI**: 使用 `customtkinter` 打造美觀的深色/淺色主題介面。
* **網頁推流 (Web Stream)**: 內建 Flask 伺服器，支援遠端查看狀態或畫面。
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

📄 授權條款

This project is licensed under the MIT License.
