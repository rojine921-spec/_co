# 第 11 週：nand2tetris 虛擬機 (第 7、8 章)

## AI 使用聲明

- **使用的 AI 工具**：OpenAI ChatGPT（GPT-6）。
- **使用方式**：- **使用方式**：協助理解 nand2tetris 第 7、8 章的 VM Translator 規格、撰寫 JavaScript（Node.js）程式碼、整理 README 說明及設計測試範例。
- **使用範圍**：本作業的程式與文件有 AI 輔助產生的內容；提交者應自行閱讀程式、執行測試，並對最終提交結果負責。

## 專案說明

本專案使用 **Node.js（JavaScript）** 實作 nand2tetris 第 7、8 章的 **VM Translator**。

工作流程：

```text
.vm 虛擬機指令 ──VMTranslator.js──> .asm Hack 組合語言
                                     │
                                Hack Assembler
                                     ▼
                                  .hack
```

本程式是 **VM 轉譯器**，不是直接執行 VM 指令的 VM Emulator。

## 功能

- 算術與邏輯：`add sub neg eq gt lt and or not`
- 記憶體讀寫：`push`、`pop`，支援 `constant local argument this that temp pointer static`
- 流程控制：`label goto if-goto`
- 函式：`function call return`
- 單一 `.vm` 檔案轉譯為同名 `.asm`
- 整個資料夾內的多個 `.vm` 檔案合併為單一 `.asm`
- Bootstrap：自動在適當情況下初始化 `SP = 256`，若定義 `Sys.init` 則呼叫它
- 比較 `gt`、`lt` 時處理不同正負號，避免 16 位元減法溢位造成結果錯誤

## 操作步驟（Windows / macOS / Linux）

**先安裝 Node.js**，無須其他 npm 套件。

### A. 轉譯單一檔案

在終端機切換到本專案目錄後執行：

```bash
node VMTranslator.js examples/SimpleAdd.vm
```

輸出：`examples/SimpleAdd.asm`

### B. 轉譯整個資料夾

```bash
node VMTranslator.js examples/SysDemo
```

輸出：`examples/SysDemo/SysDemo.asm`

若資料夾內有 `Sys.init` 函式，產生的程式會從它開始執行。

### C. 測試程式

安裝 Python 3（選用），再執行：

```bash
python tests/test_vmtranslator.py
```

測試包含：基本運算、正負數比較、記憶體區段、流程控制、函式呼叫與返回、巢狀呼叫、不同 VM 檔案的 static 區段、錯誤指令檢查。

## 指令翻譯範例

輸入 `SimpleAdd.vm`：

```vm
push constant 7
push constant 8
add
```

輸出 `.asm`：

```asm
@7
D=A
@SP
A=M
M=D
@SP
M=M+1
@8
D=A
@SP
A=M
M=D
@SP
M=M+1
@SP
AM=M-1
D=M
A=A-1
M=D+M
```

當 Hack CPU Emulator 的 `SP` 初始值為 256，執行後 `RAM[256] = 15`，`SP = 257`。

## 檔案結構

```text
nand2tetris_VM16/
├── VMTranslator.js             主程式
├── README.md                   操作說明
├── examples/
│   ├── SimpleAdd.vm            加法範例
│   ├── SimpleAdd.asm           範例輸出
│   └── SysDemo/
│       ├── Sys.vm              程式進入點
│       ├── Main.vm             函式範例
│       └── SysDemo.asm         多檔翻譯結果
└── tests/
    └── test_vmtranslator.py    自動化測試
```

## 注意事項

- 預設：檔案模式不強制 Bootstrap（除非檔案中有 `Sys.init`）；資料夾模式初始化 SP，並在找到 `Sys.init` 時呼叫。
- 也可以使用 `--bootstrap` 強制產生 Bootstrap（需要有 `Sys.init`），或 `--no-bootstrap` 關閉。
- 目前使用內建自動化測試檢查輸出合法性及模擬執行結果；尚未宣稱通過 nand2tetris 官方的完整 `.tst` / `.cmp` 套件。

## 參考

- [nand2tetris Project 7](https://www.nand2tetris.org/project07)
- [nand2tetris Project 8](https://www.nand2tetris.org/project08)
- [老師提供的參考程式 08](https://github.com/ccc115a/co/tree/main/nand2tetris/08)
- [老師提供的 JavaScript VM 參考](https://github.com/ccc-js/hack-computer/tree/main/lib/vm)
