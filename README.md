# Fcitx5 for Android · 液态玻璃主题

仿 iOS 26「液态玻璃(Liquid Glass)」风格的 [Fcitx5 for Android](https://github.com/fcitx5-android/fcitx5-android) 键盘主题,提供浅色 / 深色两款,也可以用自己的壁纸生成。

| 浅色 LiquidGlassLight | 深色 LiquidGlassDark |
| --- | --- |
| ![light](preview/LiquidGlassLight.png) | ![dark](preview/LiquidGlassDark.png) |

> 预览图由脚本近似绘制,实际效果以手机上为准。

## 安装

1. 下载 `dist/` 里的 `LiquidGlassLight.zip` 和/或 `LiquidGlassDark.zip`。
2. 打开 Fcitx5 → **主题** → 右上角 **+** → **导入**,选中 zip。
3. 在 **主题** 页面把下面几项调成这样(玻璃效果主要靠它们):

| 设置项 | 推荐值 | 作用 |
| --- | --- | --- |
| 按键边框 | 开 | 按键独立成块,候选栏透明 |
| 按键边框描边 | 开 | 用高光色画出玻璃的亮边 |
| 按键圆角半径 | 10–14 dp | iOS 26 的大圆角 |
| 按键水平间距 | 3 dp | |
| 按键垂直间距 | 6–7 dp | |
| 按键涟漪效果 | 关 | iOS 风格的按下效果是整键高亮 |
| 跟随系统深色模式 | 开,浅色选 `LiquidGlassLight`,深色选 `LiquidGlassDark` | |

## 用自己的壁纸生成

把桌面壁纸做成毛玻璃背景,键盘看起来就像「透出」桌面:

```bash
pip install pillow numpy
```

```bash
python3 tools/build_theme.py --wallpaper ~/wallpaper.jpg --name MyGlass
```

生成 `dist/MyGlassLight.zip` 和 `dist/MyGlassDark.zip`,导入方法同上。不带参数运行会重新生成内置的两款主题。

## 原理与限制

Fcitx5 for Android 的自定义主题只支持「一张背景图 + 各部件颜色」,没有实时模糊、折射这类着色器效果,所以这里这样模拟液态玻璃:

- **背景**:对彩色光斑(或你的壁纸)做高斯模糊、提高饱和度、蒙一层白/黑,顶部加一道镜面高光和亮边,也就是 iOS 毛玻璃材质的做法;
- **按键**:用半透明白色叠在背景上,背景颜色会「透」过按键;
- **玻璃边缘**:把 `keyShadowColor` 设成半透明白色,配合「按键边框描边」,画出玻璃的折射亮边;
- **回车键**:iOS 系统蓝 `#0A84FF`。

背景是静态图片,不会像 iOS 那样随键盘后面的内容实时变化。要做到这一点只能修改输入法本身的源码(Android 12+ 的 `RenderEffect` 模糊)。

## 文件说明

```
tools/build_theme.py   主题生成脚本(配色、背景、打包、预览图)
dist/*.zip             可直接导入的主题包
preview/*.png          预览图
```

主题 JSON 格式参照 fcitx5-android 源码中的 `Theme.Custom` / `CustomThemeSerializer`(版本 2.1)。
