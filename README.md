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