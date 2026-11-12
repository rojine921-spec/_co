
# 第十週：nand2tetris Hack 組譯器（Project 6）

## AI 使用聲明

- **使用的 AI 工具**：OpenAI ChatGPT（GPT-6）。
- **使用方式**：協助理解 nand2tetris Project 6 的 Hack 組譯器規格、撰寫 Python 程式碼、整理 README 說明及設計測試範例。
- **使用範圍**：本作業的程式與文件有 AI 輔助產生的內容；提交者應自行閱讀程式、執行測試，並對最終提交結果負責。

## 作業說明

使用 Python 3 實作 nand2tetris 第 6 專案的 Hack 組譯器，將 `.asm` 組合語言檔案翻譯為 16 位元二進位的 `.hack` 檔案。

## 實作內容

- 清理空白與 `//` 註解。
- 第一次掃描：記錄 `(LOOP)` 等標籤對應的 ROM 位址。
- 第二次掃描：翻譯 A 指令、C 指令，解析預設符號與變數。
- 新變數 RAM 位址從 16 開始配置。
- 對不合法的指令與超出範圍的位址回報錯誤。

## 執行方法

在此資料夾開啟終端機：

```bash
python assembler.py Add.asm
```

完成後會產生 `Add.hack`。

測試符號處理：

```bash
python assembler.py Sum.asm
```

## 測試與驗證

可使用 nand2tetris 官方第 6 章提供的 `Add.asm`、`Max.asm`、`Rect.asm`、`Pong.asm` 進行驗證，並與官方 Assembler 的輸出比對。

官方網站：https://www.nand2tetris.org/project06
