# LoopKey - 自动循环按键宏工具

LoopKey 是一个图形化的自动按键宏工具，允许用户自定义按键序列并无限循环执行。它特别适用于需要重复按键操作的场景，如游戏中的自动化任务、测试或其他重复性工作。

## 功能特性

- ✅ **直观的GUI界面** - 使用Tkinter构建的现代化界面
- ⌨️ **丰富的按键支持** - 支持字母、数字、功能键(F1-F12)等所有键盘按键
- 🔁 **无限循环执行** - 按照设定的序列重复执行按键动作
- ⚙️ **灵活的参数配置** - 可为每个按键设置按下时长和后续延迟
- 🎲 **随机间歇时间** - 在每次循环完成后随机暂停一段时间
- 💾 **配置持久化** - 自动保存和加载用户的按键序列配置
- 🎛️ **快捷键控制** - 支持F9启动、F10停止宏脚本

## 安装说明

### 系统要求
- Python 3.12 或更高版本
- Windows、macOS或Linux操作系统

### 安装步骤

1. 克隆或下载此项目到您的计算机
2. 确保已安装Python 3.12+
3. 安装依赖库：
   ```bash
   pip install keyboard pyautogui sv-ttk
   ```
   
   或者如果你使用uv/pipenv/poetry等现代包管理器：
   ```bash
   # 如果使用 uv
   uv sync
   
   # 如果使用 poetry
   poetry install
   ```

## 项目结构

```
LoopKey/
├── main.py          # 主程序文件
├── pyproject.toml   # 项目依赖配置
├── macro_config.json # 用户配置文件（自动生成）
└── README.md        # 项目说明文档
```

## 依赖库

- [keyboard](https://github.com/boppreh/keyboard) - 键盘钩子和热键处理
- [pyautogui](https://github.com/asweigart/pyautogui) - GUI自动化控制
- [sv-ttk](https://github.com/rdbende/Sun-Valley-ttk-theme) - 现代化主题界面

## 许可证

该项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解更多详情。