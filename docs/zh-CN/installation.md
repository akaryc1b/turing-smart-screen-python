# 安装说明

本文同时说明如何使用发布页中的打包产物，以及如何从源代码运行项目。发行包中的语言词库、中文主题和其他资源必须与可执行文件保持在同一应用目录中。

## 系统与 Python 要求

源码运行需要：

- Python 3.9 或更高版本。
- Windows 10 / 11、主流 Linux 发行版、macOS，或支持 Python 的 Raspberry Pi 系统。
- Tkinter，用于配置向导和主题编辑器。
- 对应屏幕所需的串口、USB 或 HID 访问权限。

建议使用官方 CPython，并为项目创建独立虚拟环境。不要在系统 Python 中混装多个版本的硬件监控依赖。使用项目发布的 Windows 或 Linux 打包产物时，不需要另外安装 Python。

## 获取代码

需要源码安装时执行：

```bash
git clone https://github.com/akaryc1b/turing-smart-screen-python.git
cd turing-smart-screen-python
```

如需跟踪原始英文项目，可另外配置 `upstream`，参见[同步上游](upstream-sync.md)。

## Windows

### 使用发行包（推荐）

若发布页提供 Windows 产物，可选择：

- `*-windows.exe`：安装程序，适合普通用户；
- `*-portable-windows.zip`：portable 便携压缩包，适合免安装或故障排查；
- `*-debug-*`：带控制台输出的调试版本，仅用于定位问题。

安装程序支持简体中文，并会根据 Windows 语言显示安装界面。安装器中的 PawnIO 驱动说明也提供中英文版本。升级安装默认保留现有主题和配置，避免覆盖用户修改。

使用 portable 压缩包时必须完整解压，不要只复制 `main.exe`、`configure.exe` 或 `theme-editor.exe`。解压后的目录中应包含 `locales`、`res`、`external` 和 `config.yaml`。

应用默认跟随配置项和系统语言。需要临时强制简体中文时，可以在 PowerShell 中执行：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
.\configure.exe
```

变量仅对当前 PowerShell 会话及其启动的程序生效。恢复自动检测：

```powershell
Remove-Item Env:TURING_LANGUAGE -ErrorAction SilentlyContinue
```

### 从源代码安装

#### 1. 安装 Python

安装 Python 3.9+，并在安装器中启用“Add Python to PATH”。验证：

```powershell
python --version
```

#### 2. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

PowerShell 禁止执行激活脚本时，可在当前用户范围调整策略，或直接使用：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe configure.py
```

#### 3. 配置和运行

```powershell
python configure.py
python main.py
```

使用 LibreHardwareMonitor 读取完整传感器时，通常需要以管理员身份运行。若不希望使用管理员权限，可在配置向导中选择 Python 硬件库；可用指标取决于硬件和驱动。

串口屏通常显示为 `COM3`、`COM4` 等。若 `AUTO` 无法识别，请在设备管理器中确认端口并手动选择。

## Linux

### 使用 Linux 打包产物

若发布页提供 `*-linux.tar.gz`，完整解压后运行：

```bash
tar -xzf turing-system-monitor-<版本>-linux.tar.gz -C turing-system-monitor
cd turing-system-monitor
TURING_LANGUAGE=zh_CN ./configure
```

也可以运行兼容入口：

```bash
./turing-smart-screen
```

打包产物仍需要正确的 USB、串口权限以及系统字体。中文主题优先使用系统 CJK 字体；未检测到支持字体时会给出提示，并安全回退到随程序提供的 Roboto Mono，程序不会因缺少中文字体而崩溃。

### 从源代码安装

#### 1. 安装系统依赖

不同发行版的软件包名称不同。Debian / Ubuntu 常见依赖：

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip python3-tk libusb-1.0-0
```

需要读取风扇或主板温度时，可安装并配置：

```bash
sudo apt install lm-sensors
sudo sensors-detect
```

按 `sensors-detect` 的提示完成后重启，再运行 `sensors` 验证。

#### 2. 创建虚拟环境并安装 Python 依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

#### 3. USB 与串口权限

常见串口设备为 `/dev/ttyACM0` 或 `/dev/ttyUSB0`。当前用户通常需要加入 `dialout` 组：

```bash
sudo usermod -aG dialout "$USER"
```

退出桌面会话并重新登录后生效。不要长期使用 `sudo python main.py` 代替正确的设备权限配置。

TURZX USB 型号通过 PyUSB 访问时，还可能需要 udev 规则。先使用 `lsusb` 确认设备，再根据设备的 VID/PID 创建最小权限规则。修改规则后执行：

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 4. 配置和运行

```bash
python configure.py
python main.py
```

无图形桌面或仅通过 SSH 运行时，配置向导可能无法打开。可直接编辑 `config.yaml`，并使用 `SIMU` 模式先验证环境。

## macOS

当前项目主要提供源码运行方式。

### 1. 安装 Python 与 Tkinter

优先使用包含可用 Tk 支持的 Python 3.9+。验证：

```bash
python3 --version
python3 -m tkinter
```

第二条命令应打开一个 Tk 测试窗口。若失败，请更换带 Tk 的 Python 安装或按 Python 发行版说明安装 Tcl/Tk。

### 2. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 配置和运行

```bash
TURING_LANGUAGE=zh_CN python configure.py
python main.py
```

也可以在配置向导中把界面语言设置为简体中文，之后无需保留环境变量。

macOS 的托盘事件循环与其他平台不同，主程序会在托盘运行阶段阻塞。退出时请使用托盘菜单或向前台进程发送正常终止信号，不要直接强制结束进程，以便程序清空显示队列并关闭屏幕。

## 打包产物的完整性

PyInstaller 产物会把以下资源放在应用资源根目录：

- `locales/en_US.json`
- `locales/zh_CN.json`
- `res/themes/3.5inchTheme2-zh-CN/theme.yaml`
- `res/themes/3.5inchTheme2-zh-CN/background.png`
- `res/themes/3.5inchTheme2-zh-CN/preview.png`
- `res/fonts/roboto-mono/RobotoMono-Regular.ttf`
- `config.yaml`
- `external/`

源码运行时从仓库根目录加载资源；冻结运行时通过 PyInstaller 的资源根目录加载。项目 CI 会实际构建 Windows 正式版、Windows Debug 版和 Linux 版，并在归档或发布前检查上述文件、可执行程序、中文词库加载、中文主题图片以及缺少 CJK 字体时的安全回退。

如果手动移动打包产物，请始终复制整个 `turing-system-monitor` 目录。任何缺失资源都应视为不完整安装，不建议通过单独补复制某个可执行文件解决。

## 首次验证建议

1. 先将屏幕型号设为“模拟显示屏”或把 `display.REVISION` 设为 `SIMU`。
2. 选择与主题尺寸一致的主题。
3. 把硬件监控方式设为 `STATIC`，排除传感器差异。
4. 运行主程序，确认生成 `screencap.png`。
5. 再切换真实硬件、串口和传感器读取方式。

此顺序可以把应用目录完整性、语言词库、主题、字体、Python 环境和硬件通信问题分开定位。
