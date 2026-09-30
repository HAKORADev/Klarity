## Klarity {{VERSION}} — Desktop Binaries

Pre-built desktop binaries for Linux and Windows. No Python, no pip, no cloning — just download, extract, and run.

---

## 📦 Downloads

| Platform | File | Size |
|----------|------|------|
| **Linux** (x86_64) | `klarity-cpu-linux_{{VERSION}}.tar.gz` | ~330 MB |
| **Windows** (x86_64) | `klarity-cpu-windows_{{VERSION}}.zip` | ~210 MB |

---

## 🚀 Quick Start

### Linux

```bash
# Download and extract
tar xzf klarity-cpu-linux_{{VERSION}}.tar.gz
cd klarity

# Launch GUI
./klarity gui

# Or launch interactive CLI
./klarity cli

# Optional: set up shortcuts & shell alias
./install.sh
```

### Windows

```
1. Download and extract klarity-cpu-windows_{{VERSION}}.zip
2. Double-click klarity.exe to launch the GUI
```

**Handy batch files included:**

| File | What it does |
|------|-------------|
| `klarity.exe` | Main binary — launches GUI (double-click to open) |
| `cli.bat` | Opens interactive CLI mode |
| `cmd.bat` | Opens a command prompt in the Klarity folder |
| `install.bat` | Creates desktop shortcut, Start Menu entry, and adds Klarity to PATH |

> After running `install.bat`, you can open a **new** command prompt and use `klarity` from anywhere.

---

## 🔄 What's New in {{VERSION}}

{{WHATS_NEW}}

> **Full changelog:** See [CHANGELOG.md](https://github.com/HAKORADev/Klarity/blob/main/CHANGELOG.md)

---

## 📂 What's Inside

The app icon lives **inside** the binary — the Windows executable carries it (file icon, window and taskbar) and there are no loose logo files to lose.

```
klarity/
├── klarity / klarity.exe ← main binary (GUI + CLI, icon embedded)
├── _internal/            ← Python runtime + all dependencies
├── models/               ← AI models (auto-downloaded on first use)
├── cli.sh / cli.bat      ← launch interactive CLI mode
└── install.sh / install.bat ← shortcut & alias installer
```

---

## 🧠 CPU-Only Builds

These binaries ship with **CPU-only PyTorch**. Klarity is fully functional on CPU and works on virtually any modern PC. Output quality is identical to GPU — processing just takes longer.

| | GPU Build | CPU Build |
|--|-----------|-----------|
| Archive size | ~2.5 GB+ | ~210–330 MB |
| Output quality | Same | Same |
| Processing speed | Faster | Slower but perfectly usable |
| Hardware needed | NVIDIA GPU | Any PC |

> If you need GPU acceleration, [run from source](https://github.com/HAKORADev/Klarity#quick-start) with the CUDA version of PyTorch.

---

## ⚡ First Run

On first launch, Klarity will prompt you to download AI models. You pick a mode:

| Mode | Download Size | Quality | Speed |
|------|--------------|---------|-------|
| **Heavy** (default) | ~888 MB | Best | Slower |
| **Lite** | ~204 MB | Good | 20x faster |

Switch anytime via the GUI dropdown or the `-lite` / `-heavy` CLI flags.

---

## 📋 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB (Lite) | 16 GB+ (Heavy) |
| **GPU** | None | — |
| **Storage** | 2 GB + models | SSD recommended |
| **FFmpeg** | Required for video | — |

**FFmpeg install:**
- Linux: `sudo apt install ffmpeg`
- Windows: `winget install FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org)

---

## 🛠️ CLI Examples

```bash
# Image processing
klarity deblur photo.jpg
klarity denoise image.png
klarity upscale photo.jpg --upscale 4
klarity clean image.jpg              # denoise + deblur
klarity full image.jpg               # denoise + deblur + upscale

# Video processing (requires FFmpeg)
klarity frame-gen video.mp4 --multi 2
klarity clean-frame-gen video.mp4
klarity full-frame-gen video.mp4 --upscale 2

# Lite mode (faster, smaller models)
klarity -lite full image.jpg

# System info
klarity info
```

---

## Credits

- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) — Super-resolution models
- [HAT](https://github.com/XPixelGroup/HAT) — Hybrid Attention Transformer (Heavy upscale)
- [NAFNet](https://github.com/megvii-research/NAFNet) — Denoising and deblurring models
- [RIFE](https://github.com/hzwer/Practical-RIFE) — Frame interpolation models
