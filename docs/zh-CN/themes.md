# 主题制作与中文示例主题

项目主题位于 `res/themes/<主题目录>/`，通常包含：

```text
res/themes/MyTheme/
├── theme.yaml
├── background.png
└── preview.png
```

主题 YAML 描述图片、静态文字、传感器数据、坐标、尺寸、字体和刷新间隔。主题目录名会保存到 `config.yaml` 的 `config.THEME`，因此目录名应保持稳定。

## 使用中文示例主题

本汉化版本新增：

```text
res/themes/3.5inchTheme2-zh-CN
```

它是独立主题，不覆盖上游 `3.5inchTheme2`。适用于 320×480、3.5 英寸纵向布局，包含：

- 日期与时间。
- CPU、GPU、FPS 和温度。
- 内存与磁盘使用率。
- 有线、无线网络上传和下载速率。
- 系统运行时间。

配置方式：

```yaml
config:
  THEME: 3.5inchTheme2-zh-CN
```

建议先使用：

```yaml
config:
  HW_SENSORS: STATIC

display:
  REVISION: SIMU
```

运行 `python main.py` 后检查 `screencap.png`，确认字体、位置和数值区域正常，再切换真实硬件。

## 基本结构

### 显示信息

```yaml
display:
  DISPLAY_SIZE: 3.5"
  DISPLAY_ORIENTATION: portrait
  DISPLAY_RGB_LED: 44, 132, 255
```

- `DISPLAY_SIZE` 必须与目标屏幕匹配。
- `DISPLAY_ORIENTATION` 使用 `portrait` 或 `landscape`，不可翻译。
- `DISPLAY_RGB_LED` 仅对支持背板灯的硬件生效。

### 静态图片

```yaml
static_images:
  BACKGROUND:
    PATH: background.png
    X: 0
    Y: 0
    WIDTH: 320
    HEIGHT: 480
```

图片路径相对于当前主题目录。

### 静态文字

```yaml
static_text:
  MEMORY_LABEL:
    TEXT: "内存"
    X: 20
    Y: 196
    FONT: system:cjk-bold
    FONT_SIZE: 17
    FONT_COLOR: 79, 224, 181
    BACKGROUND_IMAGE: background.png
```

中文主题建议明确设置 `WIDTH` / `HEIGHT`，或确保文本不会超出背景区域。`BACKGROUND_IMAGE` 可用于恢复文字区域原背景，避免动态刷新留下残影。

### 动态数据

```yaml
STATS:
  MEMORY:
    INTERVAL: 5
    VIRTUAL:
      PERCENT_TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: 20
        Y: 222
        WIDTH: 120
        HEIGHT: 26
        FONT: roboto-mono/RobotoMono-Bold.ttf
        FONT_SIZE: 23
        FONT_COLOR: 241, 246, 255
        BACKGROUND_IMAGE: background.png
```

`SHOW`、`INTERVAL`、传感器节点名和单位行为属于主题协议，不能翻译。中文标签应放在 `static_text.*.TEXT` 中。

## 字体策略

中文主题可使用：

```yaml
FONT: system:cjk
```

或：

```yaml
FONT: system:cjk-bold
```

这两个是可选字体别名，程序会返回 Pillow 可读取的真实系统字体路径。普通社区主题仍使用 `res/fonts` 下的相对路径，例如：

```yaml
FONT: roboto-mono/RobotoMono-Bold.ttf
```

数值推荐使用等宽字体，中文标签使用 CJK 字体。这样既可避免数值宽度变化造成残影，也无需向仓库提交大型字体二进制文件。

详细平台字体顺序见[中文字体说明](fonts.md)。

## 中文排版建议

- 2～4 个汉字的短标签优先，避免把说明句放入小屏主题。
- 中文字号通常不能直接照搬英文字号；在相同字号下，汉字方框更宽更高。
- 动态数值保留足够宽度，例如 `100%`、`9999 RPM`、`1023.9 MB/s`。
- 给动态文字设置固定 `WIDTH` 和 `HEIGHT`，并使用背景图片或背景色清除旧内容。
- 日期格式可使用 Babel 格式，例如 `yyyy-MM-dd`；时间可用 `HH:mm:ss`。
- CPU、GPU、RAM、FPS 等通用缩写可保留。
- 不要把中文写入 `DISPLAY_SIZE`、`DISPLAY_ORIENTATION`、节点名、布尔值和传感器配置。

## 主题编辑器

启动：

```bash
python theme-editor.py res/themes/3.5inchTheme2-zh-CN
```

编辑器支持：

- 自动刷新主题预览。
- 放大和缩小。
- 单击查看坐标。
- 拖动查看区域的 X、Y、宽和高。
- 在 Windows、macOS 和 Linux 上打开主题文件。

命令行参数错误、主题配置错误和界面提示会根据当前语言显示。内部调试日志仍保留英文，便于搜索上游问题。

## 生成预览图

推荐使用模拟屏幕和静态传感器：

```yaml
config:
  THEME: 3.5inchTheme2-zh-CN
  HW_SENSORS: STATIC

display:
  REVISION: SIMU
```

运行主程序后，将生成的 `screencap.png` 检查无误，再复制为主题目录中的 `preview.png`。

预览检查项：

- 分辨率与主题尺寸一致。
- 没有“□”或空白中文字形。
- 所有文字和图表在屏幕范围内。
- 最长数值不会覆盖相邻区域。
- 动态刷新不会留下旧字残影。
- 没有把本机用户名、路径、API 密钥或其他私密信息写入预览。

## 不提交大型字体的原因

字体文件通常体积较大，而且许可条件不同。提交前必须确认：

- 许可证允许再分发和修改。
- 仓库保留字体许可证原文。
- 字体体积对 Git 历史和安装包可接受。
- PyInstaller 能正确打包。

当前中文主题优先使用系统字体发现。若目标设备没有中文字体，请按[字体安装说明](fonts.md)安装，而不是随意复制商业字体到仓库。
