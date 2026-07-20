# 配置向导与配置文件

项目可通过图形化配置向导 `configure.py` 或直接编辑 `config.yaml` 完成配置。界面中的中文仅用于显示，保存到配置文件的仍是稳定内部值。

## 启动配置向导

```bash
python configure.py
```

配置向导包含：

- 智能屏型号与屏幕尺寸。
- 串口或 USB 通信方式。
- 显示方向和亮度。
- 主题选择和主题编辑器入口。
- 硬件监控方式。
- 有线、无线网卡和 CPU 风扇。
- 天气、Ping 和界面语言。

保存后可直接运行主程序：

```bash
python main.py
```

## 界面语言

### 配置文件

```yaml
config:
  LANGUAGE: auto
```

支持值：

| 值 | 含义 |
|---|---|
| `auto` | 先读取 `TURING_LANGUAGE`，再跟随系统区域设置，无法识别时使用英文 |
| `en_US` | 英文 |
| `zh_CN` | 简体中文 |

语言更改通常在重新打开当前窗口或重新启动程序后生效。

### 环境变量

`TURING_LANGUAGE` 可在不改配置文件的情况下影响 `auto` 模式，也可帮助配置文件加载前的启动错误选择语言。

Windows PowerShell：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
python main.py
```

Linux / macOS：

```bash
TURING_LANGUAGE=zh_CN python main.py
```

环境变量无效或语言不受支持时，程序安全回退英文。

## 屏幕通信

### 串口

```yaml
config:
  COM_PORT: "AUTO"
```

`AUTO` 表示按已选择的屏幕型号自动查找。自动识别失败时，可手动设置：

```yaml
config:
  COM_PORT: "COM3"          # Windows
  # COM_PORT: "/dev/ttyACM0" # Linux
```

`COM_PORT` 是协议输入，不应翻译为中文。

### 硬件修订号

```yaml
display:
  REVISION: A
```

常见稳定值：

- `A`：Turing 3.5 英寸和部分 UsbPCMonitor。
- `B`：XuanFang 3.5 英寸 revision B / 旗舰版。
- `C`：部分 Turing 2.1 / 2.8 / 5 / 8.8 英寸设备。
- `D`：奇叶智显 3.5 英寸。
- `TUR_USB`：部分 Turing 1.x USB 硬件版本。
- `WEACT_A`、`WEACT_B`：WeAct Studio Display FS V1。
- `SIMU`：模拟显示。

这些值参与设备选择和协议分派，不能翻译，也不要用界面显示名称替换。

## 主题与方向

```yaml
config:
  THEME: 3.5inchTheme2-zh-CN

display:
  DISPLAY_REVERSE: false
```

`THEME` 保存 `res/themes` 下的目录名。主题中的 `DISPLAY_SIZE` 必须与所选屏幕尺寸兼容。

`DISPLAY_REVERSE` 是布尔值，用于反转主题定义的基础方向；不要写入中文“正常”或“反向”。

## 亮度与启动重置

```yaml
display:
  BRIGHTNESS: 20
  RESET_ON_STARTUP: true
```

部分 3.5 英寸 revision A 屏幕在高亮度下可能发热。建议从较低亮度开始。

某些设备启动重置后会重新枚举并改变串口号。出现此问题时可将 `RESET_ON_STARTUP` 设为 `false`。

## 硬件监控方式

```yaml
config:
  HW_SENSORS: AUTO
```

| 值 | 含义 |
|---|---|
| `AUTO` | Windows 优先选择 LibreHardwareMonitor，其他平台使用 Python 库 |
| `LHM` | Windows LibreHardwareMonitor，通常需要管理员权限 |
| `PYTHON` | 使用 psutil、GPUtil 等 Python 库 |
| `STUB` | 随机模拟数据，适合动态主题测试 |
| `STATIC` | 固定模拟数据，适合可重复截图和 CI |

这些值属于稳定枚举，必须保持英文大写。

## 网卡与 CPU 风扇

```yaml
config:
  ETH: "Ethernet"
  WLO: "Wi-Fi"
  CPU_FAN: AUTO
```

Linux / macOS 常见接口名为 `eth0`、`enp2s0`、`wlan0`、`wlp1s0`、`en0`；Windows 通常使用系统显示名称。填写错误时，网络速率可能始终为零。

`CPU_FAN: AUTO` 会尝试自动选择。Linux 未列出风扇时，先配置 `lm-sensors`；仍无法识别时，在配置向导中手动选择 `controller/fan` 形式的值。

## Ping

```yaml
config:
  PING: 8.8.8.8
```

可填写主机名或 IP。ICMP 在部分系统需要额外权限；Ping 数据失败不代表屏幕通信失败。

## 天气 API

```yaml
config:
  WEATHER_API_KEY: ""
  WEATHER_LATITUDE: 35.6762
  WEATHER_LONGITUDE: 139.6503
  WEATHER_UNITS: metric
  WEATHER_LANGUAGE: zh_cn
```

天气功能使用 OpenWeatherMap One Call API 3.0。只有主题显示天气时才需要配置。

温度单位稳定值：

- `metric`：摄氏度。
- `imperial`：华氏度。
- `standard`：开尔文。

`WEATHER_LANGUAGE` 保存 OpenWeatherMap 的语言代码，不是界面语言名称。请保留 API 规定的代码，不要保存“简体中文”等显示文本。

配置向导可按城市名称查询经纬度。城市搜索失败时依次检查 API 密钥、网络、城市名称和接口返回状态。

## 配置兼容原则

汉化不会修改以下类型的数据：

- 硬件协议与命令字。
- 修订号和屏幕型号内部值。
- 串口、USB 标识和网卡名称。
- 天气 API 参数与语言代码。
- 主题尺寸、目录名和 YAML 键。
- `AUTO`、`TUR_USB`、`SIMU`、`DISPLAY_REVERSE`、`metric`、`imperial`、`standard` 等稳定值。

中文只存在于词库、文档和主题显示文本中。这样可确保英文配置、旧配置和上游版本继续兼容。
