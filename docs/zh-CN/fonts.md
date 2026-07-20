# 中文字体安装与字体回退

Pillow 绘制中文时需要包含对应中文字形的真实字体文件。字体“家族名称”、字体“文件路径”和主题中的 `FONT` 配置是三个不同概念：

- 字体家族名称：例如“Microsoft YaHei”或“PingFang SC”。
- 字体文件路径：例如 `C:\Windows\Fonts\msyh.ttc`。
- 主题字体配置：例如 `system:cjk` 或 `roboto-mono/RobotoMono-Regular.ttf`。

程序最终会把主题配置解析为 Pillow 可读取的真实文件路径。

## 主题字体别名

```yaml
FONT: system:cjk
```

请求常规中文字体。

```yaml
FONT: system:cjk-bold
```

请求粗体中文字体。系统只有常规字体或单一 TTC 字体集合时，可能由同一个文件满足两种请求。

只有这两个显式别名会启动系统字体发现。已有主题中的普通相对路径仍从 `res/fonts` 解析，不会被替换。

## Windows

发现顺序：

1. Microsoft YaHei
2. Microsoft YaHei UI
3. SimHei
4. SimSun
5. Noto Sans CJK SC

常见目录：

```text
C:\Windows\Fonts
%LOCALAPPDATA%\Microsoft\Windows\Fonts
```

Windows 10 / 11 中文语言组件通常包含微软雅黑。精简系统没有中文字体时，可在“设置 → 时间和语言 → 语言和区域”安装简体中文语言功能，或安装开源 Noto Sans CJK SC。

安装字体后重新启动程序。系统字体缓存和程序字体扫描缓存都可能需要重新加载。

## macOS

发现顺序：

1. PingFang SC
2. Hiragino Sans GB
3. Songti SC
4. Heiti SC
5. Noto Sans CJK SC

常见目录：

```text
/System/Library/Fonts
/Library/Fonts
~/Library/Fonts
```

现代 macOS 通常自带苹方。字体被“字体册”停用时，即使文件存在也可能无法正常使用；请在字体册中启用并验证字体。

## Linux

发现顺序：

1. Noto Sans CJK SC
2. Noto Sans SC
3. WenQuanYi Micro Hei
4. WenQuanYi Zen Hei
5. Source Han Sans SC

常见目录：

```text
/usr/share/fonts
/usr/local/share/fonts
~/.local/share/fonts
~/.fonts
```

Debian / Ubuntu 推荐：

```bash
sudo apt update
sudo apt install fonts-noto-cjk
fc-cache -f -v
```

也可安装文泉驿字体：

```bash
sudo apt install fonts-wqy-microhei fonts-wqy-zenhei
fc-cache -f -v
```

Fedora 系列可通过系统软件源搜索 `google-noto-sans-cjk`、`noto-sans-cjk` 或 `source-han-sans`。具体包名取决于发行版版本。

在容器、最小化 Linux 或无桌面系统中，通常默认没有 CJK 字体，需要在镜像或系统部署步骤中显式安装。

## 缺失字体时的行为

当主题使用 `system:cjk` 或 `system:cjk-bold`，但系统没有受支持字体时：

1. 程序输出本地化的明确错误提示。
2. 字体解析安全回退到仓库自带 Roboto Mono。
3. 程序继续运行，不因字体发现本身崩溃。

Roboto Mono 不包含完整中文字形，因此回退的目的是保持程序可运行并提示修复，不保证中文可正常显示。安装 CJK 字体后应重新运行程序。

## 性能与缓存

字体目录扫描结果会缓存。主题每帧刷新时不会重新遍历所有系统字体目录。测试和安装字体后的诊断代码可调用 `clear_font_cache()` 清理扫描缓存；普通用户直接重启程序即可。

Pillow 已加载的字体还会按“文件路径 + 字号”缓存在显示对象中，避免重复打开字体文件。

## 自定义绝对路径

高级用户可在主题中写绝对路径：

Windows：

```yaml
FONT: C:\Windows\Fonts\msyh.ttc
```

Linux / macOS：

```yaml
FONT: /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
```

绝对路径降低主题可移植性，不建议用于要分享给不同操作系统用户的社区主题。公开主题优先使用 `system:cjk` 别名。

## 字重说明

字体文件名称中的 `Bold`、`Semibold`、`Demibold` 等通常表示粗体。不同操作系统的 TTC 集合可能在一个文件中包含多个字重；Pillow 对字体集合的具体选择受字体内部结构影响。

当前主题别名只区分“常规”和“粗体”，不修改原主题格式，也不引入复杂字重协议。

## 字体许可

不要把微软雅黑、苹方、黑体、宋体等商业或系统字体直接提交到仓库。即使个人系统允许使用，也不等于许可证允许公开再分发。

新增字体二进制前必须：

- 确认开源许可证允许仓库和安装包再分发。
- 保留字体许可证文件和版权声明。
- 评估 Git 历史与发行包体积。
- 验证 Windows、macOS、Linux 和 PyInstaller 打包路径。

在未完成这些检查前，优先提供系统字体发现和安装说明。
