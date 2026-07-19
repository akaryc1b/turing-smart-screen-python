# 常见错误排查

排查时先把问题分成四类：Python 环境、主题与字体、硬件传感器、屏幕通信。不要同时修改多个部分。

## 推荐的最小验证配置

```yaml
config:
  LANGUAGE: zh_CN
  THEME: 3.5inchTheme2-zh-CN
  HW_SENSORS: STATIC

display:
  REVISION: SIMU
```

运行：

```bash
python main.py
```

若能生成正确的 `screencap.png`，说明 Python、配置、词库和主题基本正常；再逐项切换真实传感器和真实屏幕。

## 导入错误或缺少依赖

典型提示：

```text
导入错误：...
```

确认当前 Python 和安装依赖的 Python 是同一个：

```bash
python --version
python -m pip --version
python -m pip install -r requirements.txt
```

虚拟环境未激活时，常出现“已经安装但仍找不到模块”。使用 `python -m pip`，不要混用 `pip`、`pip3` 和多个 Python 路径。

## Tkinter 未安装

验证：

```bash
python -m tkinter
```

Linux 常见解决方式：

```bash
sudo apt install python3-tk
```

macOS 应使用带 Tk 支持的 Python。Windows 官方 Python 安装器默认可选 Tcl/Tk 组件。

Tkinter 缺失只影响图形配置向导和主题编辑器；仍可手动编辑 `config.yaml`，但建议修复依赖。

## 配置文件无法加载

检查：

- `config.yaml` 是否为合法 YAML。
- 缩进是否使用空格并保持层级。
- `LANGUAGE` 是否为 `auto`、`en_US` 或 `zh_CN`。
- `REVISION`、`HW_SENSORS`、天气单位等内部值是否被误写成中文显示文本。
- 主题目录是否存在，`theme.yaml` 是否可解析。

恢复配置时不要覆盖硬件信息。可从仓库默认 `config.yaml` 复制结构，再逐项迁移本机值。

## 中文界面没有生效

1. 检查 `config.LANGUAGE`。
2. 关闭并重新打开配置窗口或主程序。
3. `auto` 模式下检查 `TURING_LANGUAGE`。
4. 检查 `locales/en_US.json` 和 `locales/zh_CN.json` 是否随源码或打包产物存在。
5. 确认 JSON 是 UTF-8 且没有语法错误。

Linux / macOS：

```bash
TURING_LANGUAGE=zh_CN python configure.py
```

Windows PowerShell：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
python configure.py
```

中文词条缺失时会显示英文，不应显示空字符串或中断程序。

## 中文显示为方框或空白

这是字体问题，不是翻译词库问题。

- 确认主题中文标签使用 `system:cjk` 或 `system:cjk-bold`。
- 安装系统中文字体。
- 重启程序清理字体扫描和 Pillow 字体缓存。
- Linux 运行 `fc-list :lang=zh` 检查可用中文字体。
- 查看日志中是否有“未找到可用的简体中文字体”提示。

详细步骤见[中文字体说明](fonts.md)。

## 主题找不到或主题配置错误

检查：

```text
res/themes/<THEME>/theme.yaml
```

以及：

- `config.THEME` 是否等于主题目录名。
- `DISPLAY_SIZE` 是否与配置向导选择的屏幕尺寸一致。
- `background.png` 等资源是否在主题目录。
- 字体相对路径是否位于 `res/fonts`。
- `FONT: system:cjk` 是否拼写正确。
- YAML 中的 `True` / `False`、节点名、坐标和尺寸是否有效。

使用主题编辑器定位坐标：

```bash
python theme-editor.py res/themes/3.5inchTheme2-zh-CN
```

## 文字溢出或动态刷新残影

- 减小字号或缩短中文标签。
- 为动态文字增加固定 `WIDTH` 和 `HEIGHT`。
- 使用 `BACKGROUND_IMAGE` 或 `BACKGROUND_COLOR` 清除旧内容。
- 数值使用等宽字体。
- 用最长可能值验证，例如 `100%`、高位温度、较长网络速率和长运行时间。

## 自动找不到串口

- Windows 在设备管理器确认 `COM` 端口。
- Linux 查看 `/dev/ttyACM*` 和 `/dev/ttyUSB*`。
- macOS 查看 `/dev/cu.*`。
- 确认数据线支持数据传输，不是仅充电线。
- 关闭厂商软件或其他占用串口的程序。
- 在 `config.yaml` 手动填写端口。

Linux 权限：

```bash
sudo usermod -aG dialout "$USER"
```

重新登录后生效。

## 无法打开串口或 USB 设备

串口被占用、用户权限不足、设备重新枚举或驱动异常都会导致失败。

- 关闭其他监控软件。
- 拔插屏幕并重新检查端口。
- `RESET_ON_STARTUP` 导致端口变化时可设为 `false`。
- Linux 为 PyUSB 型号配置 udev 权限规则。
- Windows 检查设备驱动和设备管理器错误状态。

不要通过无限重试或忽略异常掩盖真实通信问题。

## 休眠或唤醒后显示异常

Windows 主程序会处理电源广播：休眠时关闭显示，自动唤醒时重新开启并重绘静态图片和文字。

若唤醒后仍异常：

- 查看 Windows 消息处理日志。
- 确认屏幕没有被其他软件重新占用。
- 尝试禁用 USB 选择性挂起。
- 检查设备在唤醒后是否变更端口。

不要删除 `WM_POWERBROADCAST`、`WM_QUIT` 或隐藏窗口消息循环来规避问题；这些属于运行时退出与电源管理逻辑。

## 无法读取 CPU、GPU、风扇或温度

先区分“屏幕显示正常但某项数据为空”和“程序整体无法运行”。

- Windows：尝试 `LHM` 并以管理员身份运行，或切换 `PYTHON` 比较。
- Linux：安装 `lm-sensors`，运行 `sensors-detect` 后重启。
- NVIDIA：检查驱动和 GPUtil 兼容性。
- AMD：不同平台和 Python 版本的支持范围不同。
- macOS：部分底层传感器受系统权限和硬件接口限制。

使用 `STATIC` 或 `STUB` 验证主题，不要把不支持的传感器误判为主题错误。

## 天气城市搜索或天气数据失败

检查：

- OpenWeatherMap API 密钥是否有效。
- 是否订阅 One Call API 3.0。
- 经纬度是否正确。
- `WEATHER_UNITS` 是否为 `metric`、`imperial`、`standard`。
- `WEATHER_LANGUAGE` 是否为 API 语言代码。
- 代理、防火墙和系统时间是否正常。

接口状态错误应保留原状态码，便于区分无效密钥、限流和网络问题。

## Ping 始终失败

`ping3` 使用 ICMP，部分系统限制普通用户发送原始 ICMP 包。尝试：

- 使用可达的内网 IP 排除 DNS。
- 检查防火墙是否禁止 ICMP。
- 在 Linux 按发行版安全策略授予必要能力，而不是长期以 root 运行整个程序。
- 将 Ping 失败与屏幕通信问题分开处理。

## 打包版找不到词库

打包目录应包含：

```text
locales/en_US.json
locales/zh_CN.json
```

不要只复制 `main.exe`、`configure.exe` 或 `theme-editor.exe`。PyInstaller one-folder 产物依赖同目录资源；安装包应复制完整产物目录。

缺失中文词库时会回退英文；连英文词库也缺失时，翻译函数会安全返回键名或调用方提供的默认文本，但这表示打包不完整，应修复发布资源。

## CI 中 Dependency Review 失败

Dependency Review 与 Python 语法、单元测试和跨平台程序测试是不同检查。Fork 未启用 Dependency Graph、令牌权限不足或仓库安全设置不完整时，该工作流可能在代码无误的情况下失败。

处理顺序：

1. 打开失败 run。
2. 确认 Checkout 是否成功。
3. 读取 `Dependency Review` step 的完整日志。
4. 判断错误是依赖变更、权限还是 Dependency Graph 设置。
5. 只修复真实根因。

不要为了让 Fork 变绿而删除上游工作流、跳过步骤或静默忽略失败。若日志明确要求启用 Dependency Graph，需要仓库管理员在 GitHub 仓库设置中启用；代码连接器无法代替该仓库设置操作。

## 收集诊断信息

提交软件问题时至少提供：

- 操作系统和 Python 版本。
- 屏幕型号、尺寸、修订号和连接方式。
- 运行方式：源码、PyInstaller 目录、安装包。
- `config.yaml` 的相关字段，删除 API 密钥等敏感信息。
- 完整错误堆栈或 Actions job/step 日志。
- 使用 `SIMU + STATIC` 是否能复现。
- 所选主题和字体情况。

内部调试日志保留英文是有意设计，便于与上游 Issue、代码和搜索结果对应。
