# 第12週：Jack 語言編譯器（Jack Compiler）

## 作業目的

使用 Python 實作 nand2tetris 的 Jack 語言編譯器，將 `.jack` 原始程式轉換為 `.vm` 虛擬機指令，並使用第 11 章 Project 進行編譯測試。

## 程式檔案

- `JackCompiler.py`：Jack 語言編譯器。
- `TestCompiler.py`：自動搜尋並編譯測試資料中的 Jack 檔案。

## 執行方式

在 `week12` 資料夾開啟終端機，執行：

```powershell
python TestCompiler.py ../11
```

## 測試資料與結果

測試來源：[第 11 章 Project](https://github.com/rojine921-spec/_co/tree/main/11)。

| 測試專案 | 檔案數量 | 編譯結果 |
| --- | ---: | --- |
| Average | 1 | PASS |
| ComplexArrays | 1 | PASS |
| ConvertToBin | 1 | PASS |
| Pong | 4 | PASS |
| Seven | 1 | PASS |
| Square | 3 | PASS |
| 合計 | 11 | 11/11 PASS |

終端機測試結果：

```text
Compilation: 11/11 passed
Runtime correctness must be checked in VM Emulator.
```

全部 11 個 Jack 檔案皆成功編譯，編譯成功率為 100%。此結果僅代表編譯成功，尚未透過 VM Emulator 驗證實際執行的正確性。

## AI 使用聲明

本作業使用 ChatGPT 協助撰寫 Jack 編譯器、自動化測試程式、排除路徑問題及整理 README 文件，並由本人在 VS Code 中實際執行編譯測試。
