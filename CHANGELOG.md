# Changelog

All notable changes to Klarity will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.8.0] - 2026-04-26

### Added

- **SUPER Mode** — New third model mode providing maximum quality AI-powered image restoration using [SUPIR-v0Q](https://github.com/Fanghua-Yu/SUPIR) (Scaling Up Pyramidal Image Restoration)
  - Uses Stable Diffusion XL-based diffusion model for perceptual-driven restoration
  - All quality parameters hardcoded to the official "Quality" preset for best possible output
  - Two processing operations: `enhance` (AI restoration to 1024x1024) and `enhance-frame-gen` (enhance + RIFE heavy frame interpolation)
  - Output fixed at 1024x1024 resolution
- **`supir_arch.py`** — Standalone SUPIR inference architecture wrapping the official SUPIR model
  - Handles model loading, dependency checking, and inference pipeline
  - Uses Wavelet color fixing, linear CFG scheduling (4.0 → 7.5), and 50 EDM sampling steps
  - Auto-resizes any input to 1024x1024 before processing
- **`super-deps.txt`** — Additional pip dependencies required exclusively for SUPER mode
  - Packages: diffusers, transformers, accelerate, omegaconf, einops, open-clip-torch, k-diffusion, pytorch-lightning, safetensors
- **Runtime dependency check** — SUPER mode verifies all required packages are installed via `pip list` before attempting model loading, with clear error messages pointing to `super-deps.txt`
- **`-super` CLI flag** — New global flag to activate SUPER mode from the command line
  - Example: `python src/klarity.py -super enhance image.jpg`
  - Auto-activates when `enhance` or `enhance-frame-gen` commands are used without `-heavy` or `-lite`
- **Interactive mode SUPER support** — Interactive CLI now offers SUPER mode as option 3 in model selection, with restricted operations (enhance only for images, enhance + enhance-frame-gen for videos)
- **GUI SUPER support** — SUPER mode available in GUI mode selector with same two operations

### Changed

- `select_model_mode()` now offers 3 options: Heavy, Lite, Super
- `model_downloader.py` updated with SUPER model download logic
  - SUPIR-v0Q.ckpt downloaded from Google Drive shared folder
  - Dependent models (CLIP-ViT-L/14, CLIP-ViT-bigG, SDXL base) stored in `models/enhancer/` with original filenames
  - GDrive folder download handling with temp file cleanup
- `klarity.py` import block updated to include `ensure_super_models` from model_downloader
- Model mode validation expanded to accept `'super'` alongside `'heavy'` and `'lite'`

### Technical Details

- **SUPIR Quality Preset Parameters:**
  - `s_cfg=7.5` (linear CFG from 4.0 to 7.5)
  - `s_churn=5`, `s_noise=1.003`
  - `edm_steps=50` (Euler sampling)
  - `color_fix_type=Wavelet`
  - `ae_dtype=bf16` (mandatory — fp16 causes NaN outputs)
  - `diff_dtype=fp16`
  - `restoration_scale=-1.0` (full restoration)
- **System Requirements for SUPER Mode:**
  - GPU: 24GB+ VRAM recommended (e.g., NVIDIA RTX 3090/4090)
  - CPU-only: 32GB+ system memory required
  - Models stored in `models/enhancer/` directory
- **Model Sources:**
  - SUPIR: [Fanghua-Yu/SUPIR](https://github.com/Fanghua-Yu/SUPIR) (Apache 2.0 License)
  - SDXL: Stability AI
  - CLIP: OpenAI
  - Frame generation in enhance-frame-gen uses existing RIFE Heavy model

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

