# Changelog

All notable changes to Klarity will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.5.1] - 2026-09-30

### Fixed

- **Video processing on newer FFmpeg versions** — FFmpeg 9.0 removed the deprecated `-vsync` option, which made every video mode (frame-gen, clean-frame-gen, full-frame-gen) fail with `Unrecognized option 'vsync'` ([#1](https://github.com/HAKORADev/Klarity/issues/1))
  - Frame extraction and frame compilation now probe the installed FFmpeg at runtime and use `-fps_mode passthrough` when available, falling back to `-vsync 0` on older builds — every FFmpeg version works
  - The probe runs a 1-frame test encode with `-fps_mode passthrough`, then `-vsync 0`, and falls back to parsing `ffmpeg -version`; the result is probed once and cached per session
- **Windows startup crash in the packaged build** — `klarity.exe` failed on launch with `WinError 1114` while loading the torch DLLs; the torch CPU wheel ships `api-ms-win-crt-*` forwarder stubs inside `torch/lib`, and the frozen loader choked on them (the real UCRT lives in System32) — the stubs are now stripped from the bundle at build time
- **GUI processing in the packaged Windows/Linux builds** — the frozen GUI spawned `klarity.exe` with the source path of `klarity.py` as the first argument, which the frozen binary cannot read (the source lives inside the executable), so every processing run died at startup while the CLI worked fine; the spawn is now frozen-aware and talks to the bundled CLI directly
- **Download Models button in the packaged builds** — same frozen spawn problem, the button silently did nothing; fixed the same way
- **Cancel could hang until the next output line** — cancelling only flipped a flag while the worker was blocked reading the CLI's output; the process is now terminated immediately on cancel, and closing the window during processing exits promptly too
- **Frame extraction could hang on long videos** — ffmpeg was started with an unread stderr pipe, so once its progress output filled the 64 KB pipe buffer it blocked forever; extraction now runs quiet, and a non-zero ffmpeg exit is reported instead of failing later with a confusing error
- **Target FPS below the source rate picked the maximum** — asking for 10 FPS on a 24 FPS video clamped to 48 FPS (the maximum); values below the minimum now clamp to the minimum, in all three frame-gen modes
- **`--scale` was accepted but ignored** — the RIFE scale flag now actually reaches the frame generation model

### Changed

- Removed dead assignments in `klarity.py` and `gui.py` (leftover variables with no effect), unused imports and dead `global` statements
- A failed frame-blending step now warns and falls back to the unblended frames instead of silently producing a broken video
- The app icon now lives inside the binary: the Windows executable carries the Klarity icon (Explorer, taskbar and shortcuts all use it), and the GUI window/taskbar icon is loaded from the icon bundled inside the package — no more loose `logo.png`/`logo.ico` sitting beside the binary
- The Windows installer creates shortcuts through properly quoted PowerShell commands and points their icons at the executable itself

### Added

- GitHub Actions workflow that builds CPU-only binaries for Linux and Windows from the repo, with CLI smoke tests on both runners (`--help` + `info`)
- Packaging helpers now live in the repo: `klarity.spec` plus `packaging/linux/` (`cli.sh`, `install.sh`) and `packaging/windows/` (`cli.bat`, `cmd.bat`, `install.bat`, `logo.ico`)
  - The Windows installer's PowerShell shortcut commands are fixed — the `$` variables had been stripped, so desktop and Start Menu shortcuts were never actually created in v0.7.0

---

## [0.7.5] - 2026-04-21

### Changed

- Replaced Heavy mode upscale model from **Real-ESRGAN-x4plus** to **Real-HAT-GAN-sharper** (Real_HAT_GAN_SRx4_sharper) for significantly improved perceptual quality
  - Architecture upgraded from RRDBNet (CNN, 2021) to HAT (Hybrid Attention Transformer, 2023)
  - Model parameters: 20.8M (up from ~16.7M)
  - Weight file size: ~167 MB (up from ~64 MB)
  - Source: [HAT by XPixelGroup](https://github.com/XPixelGroup/HAT) (Apache 2.0 License)
  - New architecture file: `hat_gan_arch.py` (standalone, no basicsr dependency)
  - Heavy download size increased from ~785 MB to ~888 MB
- Updated `process_upscale()` padding to use `modulo=16` (window_size) with `reflect` mode for HAT compatibility
- Updated `pad_image()` default padding mode to `reflect`

### Added

- `hat_gan_arch.py` — Standalone HAT (Hybrid Attention Transformer) architecture for Heavy upscale mode
- `einops` to requirements.txt (dependency for HAT architecture)

### Technical Notes

- The Lite upscale model (Real-ESRGAN-general-x4v3) is unchanged
- Disk filename for Heavy upscale model remains `upscale-heavy.pth`
- `sr_arch.py` retains `SRVGGNetCompact` for Lite mode; `RRDBNet` is no longer used

---

## [0.7.0] - 2026-03-29

### Added

- **Initial Public Release** of Klarity - AI-powered image/video restoration tool
- **9 Processing Modes:**
  - `denoise` - Remove noise using NAFNet-SIDD
  - `deblur` - Remove blur using NAFNet-GoPro
  - `upscale` - 2x or 4x super-resolution using Real-ESRGAN
  - `clean` - Combined denoise + deblur pipeline
  - `full` - Complete restoration pipeline (denoise + deblur + upscale)
  - `frame-gen` - AI frame interpolation using RIFE
  - `clean-frame-gen` - Clean + frame generation for video
  - `full-frame-gen` - Full restoration + frame generation for video
- **Dual Model Modes:**
  - **Heavy** (default): Maximum quality with NAFNet-width64, RealESRGAN-x4plus, RIFE v4.25
  - **Lite**: Faster processing with NAFNet-width32, RealESRGAN-general-x4v3, RIFE v4.17
- **GUI Interface:**
  - Drag & drop file support
  - Real-time preview with comparison slider
  - Multiple view modes (slider, side-by-side, single)
  - Zoom and pan controls (Ctrl+scroll, click-drag)
  - Progress tracking with status updates
  - Dark theme optimized for image viewing
- **CLI Interface:**
  - Interactive mode with guided prompts
  - Direct command-line processing
  - Batch file and folder processing
  - JSON progress output for integration
- **Automatic Model Download:**
  - Models download automatically on first use
  - Pre-download command for offline use
  - Progress tracking for downloads
  - Source fallbacks for reliability
- **Flexible Upscaling:**
  - 4x upscale for maximum resolution
  - 2x upscale with LANCZOS4 optimization
- **Frame Generation Options:**
  - 2x and 4x frame multipliers
  - Custom target FPS support
  - RIFE scale factor adjustment
- **Device Selection:**
  - Auto-detect GPU with CPU fallback
  - Force CPU or GPU selection
  - System info command for diagnostics
- **Multi-File Processing:**
  - Process multiple files in one command
  - Folder batch processing
  - Mixed input type support
- **Output Management:**
  - Automatic output naming with suffixes
  - Custom output path support
  - Organized output structure

### Technical Features

- **NAFNet Architecture:**
  - Nonlinear Activation Free Network for efficient processing
  - Separate models for denoising (SIDD) and deblurring (GoPro)
  - Multi-scale processing for detail preservation
- **Real-ESRGAN Integration:**
  - RRDBNet for Heavy mode (23 residual blocks)
  - SRVGGNetCompact for Lite mode (efficient architecture)
  - Real-world degradation training
- **RIFE Frame Interpolation:**
  - Optical flow estimation for intermediate frames
  - Handles complex motion and occlusions
  - Arbitrary time-point frame generation
- **Video Processing Pipeline:**
  - FFmpeg integration for extraction/compilation
  - Audio preservation during processing
  - Temporary file management

### Supported Formats

**Images:** `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`, `.webp`

**Videos:** `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.flv`, `.wmv`, `.m4v`

### Dependencies

- Python 3.8+
- PyTorch
- OpenCV (opencv-python)
- NumPy
- tqdm
- requests
- PyQt5
- FFmpeg (for video processing)

### Model Sources

**Heavy Models (~785 MB total):**
- Deblur: NAFNet-GoPro-width64 (Google Drive)
- Denoise: NAFNet-SIDD-width64 (Google Drive)
- Upscale: RealESRGAN-x4plus (GitHub)
- Frame Gen: RIFE v4.25 (Google Drive)

**Lite Models (~204 MB total):**
- Deblur: NAFNet-GoPro-width32 (Google Drive)
- Denoise: NAFNet-SIDD-width32 (Google Drive)
- Upscale: RealESRGAN-general-x4v3 (GitHub)
- Frame Gen: RIFE v4.17 (Google Drive)

### Credits

- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) - Super-resolution models
- [NAFNet](https://github.com/megvii-research/NAFNet) - Denoising and deblurring models
- [RIFE](https://github.com/hzwer/Practical-RIFE) - Frame interpolation models
- [BasicSR](https://github.com/XPixelGroup/BasicSR) - AI image/video framework

---

