# 运行与交付

## 创建独立项目

环境：Node.js、Python 3；Apple 配对可用跨平台 Python + Pillow + FFmpeg/ffprobe，或 macOS 的 Swift/AVFoundation/ImageIO/Photos；`.pvt` 打包本身用 Python。预先查 `command -v`；缺环境如实记录。Remotion 当前模板锁定 4.0.530，升级时所有 @remotion 包版本一致并重跑渲染。遵循 [Remotion 许可证](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)。

在下面命令中把路径替换为实际绝对路径。`SKILL_DIR` 是本 skill 目录，`PROJECT_DIR` 是本次独立工作目录。只复制项目所需资产，避免污染 skill。

```bash
mkdir -p "$PROJECT_DIR"
cp -R "$SKILL_DIR/assets/remotion/." "$PROJECT_DIR/"
cd "$PROJECT_DIR"
npm ci --no-audit --no-fund
```

先按分镜改写 `src/index.tsx`，再接入 `data.json` 与 `public/media/` 素材。随附 composition 是折线示例，仅用于起步和工具链验证；场景、图片对比、过程演示等应替换其布局，不把所有内容硬塞进示例图表。图表适用时也明确主数字所属主体。图片加载与 emoji 处理见 [图片与图标](visual-assets.md)。

正式内容先校验对应结构，再核对来源和算式。下列 validate_data.py 适用于随附的时间序列合约；其他内容使用项目内相应校验，不伪造日期来迎合它：

```bash
python3 "$SKILL_DIR/scripts/validate_data.py" "$PROJECT_DIR/data.json"
npm run typecheck
npm run render
```

仅验证工具链时在 validator 与 render 末尾各加 `--allow-demo`。合成数据必须保持 demo=true 和醒目标记，不能冒充小米、苹果或北京实测。

`render.mjs` 导出 90 帧、30 fps 的 H.264/yuv420p MP4，JPEG 封面以及 0/30/60/78 帧 PNG。改时长或节奏时同步改 composition 与 coverFrame，确保封面处于可读停留段。`out/render.json` 记录 coverTime，不手工猜时间。

模板使用 Remotion 管理的 Chrome Headless Shell、`gl: swangle` 软件图形、PNG 帧、单并发及关闭并行编码，导出 BT.709 的 H.264/yuv420p。保留这些稳定性起点；性能调优或使用 `LIVECANVAS_BROWSER` 指定其他 Chromium 时，先验证完整帧序列，不把可启动等同于渲染兼容。这只是渲染工程，不能用来访问用户浏览器账号。中文字体须在渲染机存在；若用自带字体，等待加载后渲染，并保留许可。

## 逐帧防闪屏检查

固定抽帧、完整解码成功及 PHLivePhoto 加载通过，都不能排除单帧拼贴、重复顶栏或局部错位。渲染完成后扫描全部解码帧，再检查被标记帧及其前后帧：

```bash
python3 "$SKILL_DIR/scripts/check_video_frames.py" "$PROJECT_DIR/out/motion.mp4" \
  --output "$PROJECT_DIR/out/frame-scan.json"
# 画面存在全程不变的标题等区域时，按实际原始像素坐标指定，不能包含动画：
python3 "$SKILL_DIR/scripts/check_video_frames.py" "$PROJECT_DIR/out/motion.mp4" \
  --static-region 0,0,1080,280 --output "$PROJECT_DIR/out/frame-scan.json"
```

示例区域只适用于该处确实全程静止的版式，不是固定安全区。工具检查每对相邻帧的平均亮度差；默认整帧阈值 12/255、静止区域 0.5/255。结果 `review_required` / 退出码 1 表示需要检查，2 表示工具失败，不能记作通过。阈值是异常筛查起点，不是医学或平台防闪烁认证。正常硬切可用 `--allow-cut-frame 90` 明确允许进入新场景的帧；只按已知分镜声明，不能拿白名单掩盖未知坏帧。

短卡建议同时生成较密的全片缩略图，观察是否有标题复制、画面拼贴、黑白帧或裁切变化。播放预览，分别检查封面切换、动画内部与循环边界。若用户报告 MP4 和实况都闪，先检查源 MP4，再查封装；不要将文件存在、加载通过或六张正常抽帧当作完整画面验收。

出现坏帧时保留带帧号的证据，使用模板的稳定配置重新渲染。无需为防闪屏删除产品图、改写内容、取消主题动作或改为静态卡。若当前环境仍无法稳定渲染，记录实际失败，不能声称已修复。修复后重新扫描，重新生成封面、MP4、配对 MOV/JPEG、PVT 与预览，核对最终包内视频；禁止对已配对 MOV 普通转码。

在 qa.json 记录解码帧数、检查帧对数、静止区域坐标、阈值、异常帧数及实际视觉复核结果。文件检查通过与手机/接收应用播放验证分开记录。

## Live Photo 配对

Linux / Windows 走 [跨平台 Apple Live Photo](portable-live-photo.md)，不要在生成 MP4 后停止；macOS 也可用此路径。下面是 macOS 原生备选实现。

在 macOS 编译并运行随附工具，输出目录必须尚不存在：

```bash
mkdir -p "$PROJECT_DIR/.build"
swiftc -swift-version 5 "$SKILL_DIR/scripts/pair_live_photo.swift" -o "$PROJECT_DIR/.build/pair-live-photo"
"$PROJECT_DIR/.build/pair-live-photo" "$PROJECT_DIR/out/cover.jpg" "$PROJECT_DIR/out/motion.mp4" "$PROJECT_DIR/out/live" 2.6 30
```

时间和 fps 应来自 render.json。工具会拒绝音轨、非 H.264、尺寸不匹配和越界封面时间。需要音频时扩展为保留音轨的 writer，不偷偷删音频。当前脚本使用仍可编译的同步 AVFoundation 接口，SDK 可能给出弃用警告；升级 SDK 后重新编译验证。

脚本写新 JPEG 的 MakerApple 17、MOV 的共享 content identifier、still-image-time timed metadata track；视频包直接重封装，不重新编码。随后读回图片/视频标识与时间轨道，调用 `PHLivePhoto.request` 加载。保存 `manifest.json`；本机加载失败时退出非零但保留已生成资源和诊断。最多一次针对明确原因修复后重试，缺运行环境/系统权限时停止反复调用并报告。

配对器验证不了封面内容是否真的等于视频对应帧；该一致性由同源 Remotion 渲染和画面核对保证。成功后不要用普通 ffmpeg 再处理 live.mov。

参考：[Apple PhotoKit 加载验证](https://developer.apple.com/documentation/photos/phlivephotoinfoerrorkey)、[Apple 配对资源保存](https://developer.apple.com/documentation/avfoundation/capturing-and-saving-live-photos)、[格式参考](https://github.com/LimitPoint/LivePhoto)。

## 检查与传输

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,codec_type,width,height,r_frame_rate -of json "$PROJECT_DIR/out/motion.mp4"
ffprobe -v error -show_streams -show_format -of json "$PROJECT_DIR/out/live/live.mov"
```

检查封面与抽帧，播放 MP4；覆盖主要图片动作、转场、素材加载、数值变化和封面一致性。改为多幕时同步增加各幕抽帧位置。Sources.md 记录实测/模型、点数、采样、汇率/股本/聚合方法。不得只检查文件存在。

配对成功后必须执行 [直接交付](direct-delivery.md)：生成 `主题名称.pvt` 资源包，注明接收应用兼容性。相册导入不属于默认流程，只有另行明确请求时才执行。单独交付两个资源并让用户手动配对，不符合直接 Live 图的交付标准。保留 `package-receipt.json` 和 `delivery.json`，记录配对验证、本机加载（跨平台未执行时为 not_available）与包完整性结果。

建议 `qa.json`：

```json
{
  "data": {"structural": "passed", "factCheck": "not_tested", "asOf": "YYYY-MM-DD"},
  "render": {"video": "passed", "cover": "passed", "visualReview": "not_tested"},
  "livePhoto": {"metadata": "not_tested", "localLoad": "not_tested", "package": "not_tested", "photosImport": "not_requested", "macPlayback": "not_tested", "iPhonePlayback": "not_tested"},
  "socialUpload": "not_tested",
  "wallpaper": "not_tested",
  "notes": []
}
```

只更新实际获得证据的字段，保存失败原因和下一步。交付短答优先提供可观看预览，附 .pvt 资源包链接，附截止日、验证范围；封面/视频仅作预览，不把未测设备结果描述为完成。
