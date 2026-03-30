# Klarity Technical Guide

## Table of Contents

- [Introduction & Vision](#introduction--vision)
- [The Philosophy: Quality Over Speed](#the-philosophy-quality-over-speed)
- [Processing Modes Deep Dive](#processing-modes-deep-dive)
  - [Denoise: Noise Reduction](#denoise-noise-reduction)
  - [Deblur: Blur Removal](#deblur-blur-removal)
  - [Upscale: Super Resolution](#upscale-super-resolution)
  - [Clean: Combined Denoise + Deblur](#clean-combined-denoise--deblur)
  - [Full: Complete Enhancement Pipeline](#full-complete-enhancement-pipeline)
  - [Frame Generation: AI Interpolation](#frame-generation-ai-interpolation)
  - [Combined Video Modes](#combined-video-modes)
- [Model Modes: Heavy vs Lite](#model-modes-heavy-vs-lite)
- [AI Models Explained](#ai-models-explained)
- [CLI Reference](#cli-reference)
- [GUI Guide](#gui-guide)
- [Tips & Best Practices](#tips--best-practices)
- [Troubleshooting](#troubleshooting)

---

## Introduction & Vision

Klarity is a professional-grade image and video restoration tool that brings together multiple AI enhancement capabilities in a single, unified interface. Unlike online services that charge subscriptions or limit usage, Klarity runs entirely locally on your machine — no uploads, no queues, no recurring fees.

**What Klarity Actually Does:**

At its core, Klarity orchestrates state-of-the-art neural networks to perform visual restoration tasks. It can remove noise from low-light photos, fix motion blur from shaky cameras, upscale low-resolution images to 4x their original size, and generate smooth slow-motion videos through AI frame interpolation. Each of these capabilities uses models specifically trained for that task.

**Why Klarity Exists:**

The image enhancement market offers two paths: expensive commercial software with subscription models, or fragmented open-source tools that require technical knowledge to use. Professional tools like Topaz Labs deliver excellent results but at significant ongoing cost. Free alternatives exist but often require navigating command-line interfaces, managing model files manually, and understanding neural network architectures.

Klarity was built to bridge this gap. The goal was to create a local, free, open-source alternative that doesn't sacrifice quality while remaining accessible. It provides both a graphical interface for visual users and a comprehensive CLI for batch processing and automation.

**What Makes Klarity Different:**

Most restoration tools focus on a single enhancement type. Upscalers only upscale. Denoisers only denoise. Klarity takes a unified approach — recognizing that real-world content often needs multiple corrections simultaneously. A photo from a low-light event might be both noisy AND blurry. An old video might need cleaning AND upscaling AND frame interpolation. Klarity handles these combined workflows without requiring multiple tools.

---

## The Philosophy: Quality Over Speed

### We Don't Chase FPS

This is fundamental to Klarity's design. There are no "fast mode" shortcuts that sacrifice quality. The only metric that matters is producing output that actually looks better.

When we offer "Heavy" and "Lite" model modes, we're not offering a quality tradeoff — we're offering a hardware consideration. Lite models produce excellent results but are optimized for systems with limited resources. Heavy models deliver maximum quality for those with capable hardware. Neither mode uses degraded or quantized versions that compromise output fidelity.

**Why We Offer Two Modes Instead of Quality Sliders:**

Many tools offer a quality slider from 1-100. This creates a false impression that you can have 80% quality with 20% speed improvement. In neural network terms, this isn't how it works. A smaller model doesn't produce "slightly worse" results — it produces fundamentally different results optimized for different scenarios.

The Lite models in Klarity are trained independently for their specific purpose. They're not compressed versions of Heavy models. RealESRGAN-general-x4v3 (Lite) is a completely different architecture than RealESRGAN-x4plus (Heavy), designed from the ground up for efficient inference. This means Lite mode isn't "worse" — it's different, with characteristics that might actually be preferable for certain content.

**The Memory Reality:**

Image processing is manageable on most systems. A 4K image processed through the full pipeline might peak at 6-8GB VRAM. Video processing is another matter entirely. Each frame needs processing, intermediate results need storage, and memory accumulates across the pipeline. If you run out of memory, the solution isn't "use lower quality" — it's process shorter segments, reduce resolution before processing, or use Lite mode.

**System Requirements Explained:**

| Capability | CPU Only | GPU (4GB VRAM) | GPU (8GB+ VRAM) |
|------------|----------|----------------|-----------------|
| Image processing | Works (slow) | Fast | Very fast |
| Video 1080p | Works (very slow) | Good | Excellent |
| Video 4K | Painfully slow | May need Lite | Heavy mode OK |
| Frame generation | Works | Good | Excellent |

These aren't arbitrary numbers. They're based on actual testing across different hardware configurations.

---

## Processing Modes Deep Dive

### Denoise: Noise Reduction

**What It Does:**

Denoise removes unwanted noise from images and videos. Noise appears as random variations in brightness or color — those grainy specks you see in low-light photos, high-ISO images, or compressed videos. The AI identifies patterns that represent actual image content versus random noise artifacts, then reconstructs the clean image.

**How It Works:**

Klarity uses NAFNet-SIDD, a neural network specifically trained on the SIDD (Smartphone Image Denoising Dataset). This training exposed the model to thousands of noisy/clean image pairs, teaching it to recognize and remove noise patterns while preserving genuine image details. The network uses a selective kernel architecture that adapts its processing based on local image content — applying stronger denoising to smooth areas while preserving edges and textures.

**Why It's Useful:**

- Low-light photography improvement
- Old photo restoration
- Video quality enhancement
- Compressed image cleanup
- Security footage enhancement

**Best Practices:**

Denoising works best on actual noise. If your image is blurry, run deblur instead or before denoising. If it has both issues, use the Clean mode which applies both in optimal order. Over-denoising can create plastic-looking results — Klarity's model is trained to avoid this, but extremely noisy inputs may show some smoothing.

**Technical Notes:**

The NAFNet architecture processes images in a multi-scale manner, analyzing the image at different resolution levels to separate noise from detail. This hierarchical approach is why it's effective across different noise types and intensities.

---

### Deblur: Blur Removal

**What It Does:**

Deblur removes blur from images and videos. Whether it's motion blur from camera shake, out-of-focus blur from incorrect focus, or compression blur from low-quality sources — the AI attempts to reconstruct the sharp original image.

**How It Works:**

Klarity uses NAFNet-GoPro, trained on the GoPro dataset which contains thousands of blurry/sharp image pairs from action cameras. The model learned to recognize blur patterns and their corresponding sharp details. When you input a blurry image, it applies this learned knowledge to estimate what the sharp version should look like.

**Why It's Useful:**

- Motion blur from camera shake
- Out-of-focus image correction
- Security footage clarification
- Old photo restoration
- Sports/action photography

**Best Practices:**

Deblurring is most effective on motion blur and moderate focus blur. Severe out-of-focus blur (where the subject is completely indistinct) may not recover fully because the information is genuinely lost. For best results, ensure your image is properly exposed — underexposed blurry images are harder to restore.

**Limitations:**

Blur removal cannot recover information that doesn't exist. If a license plate is so blurry that the characters are indistinguishable, deblurring will sharpen edges but cannot magically reveal text that was never captured clearly. It can reconstruct probable details based on patterns, but real-world forensic applications require acknowledging these limits.

---

### Upscale: Super Resolution

**What It Does:**

Upscale increases image resolution using AI super-resolution. Unlike traditional upscaling (bicubic, lanczos) which just interpolates between existing pixels, AI upscaling hallucinates plausible details that weren't in the original image. Klarity supports 2x and 4x upscaling.

**How It Works:**

Klarity uses Real-ESRGAN, trained to upscale images while adding realistic details. The model learned from a large dataset of high-resolution images, understanding how textures, edges, and patterns should look at higher resolutions. When upscaling, it doesn't just enlarge pixels — it actively generates new detail that fits the image context.

**2x vs 4x Upscaling:**

| Factor | Output Resolution | Use Case |
|--------|-------------------|----------|
| **4x** | 4× input dimensions | Maximum enlargement, large prints |
| **2x** | 2× input dimensions | Moderate enhancement, smaller files |

**Technical Note:** 2x upscaling performs a 4x upscale first, then downscales using LANCZOS4 interpolation. This produces better results than native 2x upscaling because it leverages the full model capacity.

**Why It's Useful:**

- Enlarging small images for printing
- Improving low-resolution screenshots
- Enhancing web images for higher resolution displays
- Video upscaling (1080p → 4K)

**Best Practices:**

Upscaling works best on relatively clean input. A noisy, blurry image upscaled will become a larger noisy, blurry image. Use the Full mode (clean + upscale) for best results on degraded content. For already high-quality images, standalone upscaling preserves the original aesthetic while increasing resolution.

---

### Clean: Combined Denoise + Deblur

**What It Does:**

Clean applies both denoising and deblurring in optimal sequence. This is the recommended starting point for most restoration tasks, as real-world degraded images often suffer from both noise and blur.

**How It Works:**

The pipeline applies denoising first, then deblurring. This order is intentional: noise can interfere with blur detection, so removing noise first allows the deblur model to work more effectively. Each step uses its specialized NAFNet model.

**Processing Flow:**
```
Input Image → Denoise (NAFNet-SIDD) → Deblur (NAFNet-GoPro) → Output Image
```

**Why Use Clean Mode:**

Instead of running separate denoise and deblur operations, Clean mode:
- Processes in optimal order automatically
- Manages memory more efficiently
- Provides unified progress tracking
- Handles intermediate files transparently

**Best For:**

- Photos from old cameras
- Low-light images
- Compressed video frames
- Scanned documents
- Security camera footage

---

### Full: Complete Enhancement Pipeline

**What It Does:**

Full applies the complete enhancement pipeline: denoise, deblur, and upscale. This is the most comprehensive restoration mode, designed to maximize image quality through the entire processing chain.

**How It Works:**

```
Input Image → Denoise → Deblur → Upscale (2x or 4x) → Output Image
```

Each step feeds into the next. The denoised image is passed to deblur, then the cleaned image is upscaled. Memory is managed between steps to prevent accumulation.

**When to Use Full:**

- Maximum quality restoration needed
- Preparing images for large format printing
- Restoring old/archival photos
- Enhancing low-quality source material

**Memory Considerations:**

Full mode requires the most memory because all three models load sequentially. For 4K output from a 1080p input:
- 1080p input → denoise (processed at 1080p)
- Result → deblur (processed at 1080p)
- Result → upscale to 4K (peak memory usage)

If you encounter memory issues, try Lite mode or reduce input resolution.

---

### Frame Generation: AI Interpolation

**What It Does:**

Frame generation creates intermediate frames between existing video frames, effectively increasing frame rate for smooth slow-motion effects. A 30fps video can become 60fps or 120fps while maintaining natural motion.

**How It Works:**

Klarity uses RIFE (Real-Time Intermediate Flow Estimation), which analyzes motion between consecutive frames and generates new frames that represent intermediate moments. Unlike traditional frame blending which simply crossfades between frames, RIFE actually predicts where objects should be at intermediate time points.

**Parameters:**

| Parameter | Values | Description |
|-----------|--------|-------------|
| `--multi` | 2, 4 | Frame multiplier |
| `--fps` | number | Target FPS (auto if not specified) |
| `--scale` | 0.5, 1.0, 2.0 | Internal RIFE scale factor |

**Frame Multiplier Examples:**

| Multiplier | 30fps Input | Output FPS |
|------------|-------------|------------|
| 2x | 30fps | 60fps |
| 4x | 30fps | 120fps |

**Best For:**

- Creating smooth slow-motion from normal video
- Converting 24fps film to higher frame rates
- Smoothing action camera footage
- Enhancing animation smoothness

**Limitations:**

Frame generation works best on consistent motion. Rapid scene changes, complex overlapping motion, or extremely fast movement may produce artifacts. The AI interpolates based on visible motion — if objects disappear between frames, interpolation becomes guesswork.

---

### Combined Video Modes

**Clean-Frame-Gen:**

Denoise + Deblur + Frame Generation. For videos that need both restoration and smooth motion.

**Full-Frame-Gen:**

Complete pipeline plus frame generation. Maximum quality restoration with increased frame rate. This is the most intensive processing mode.

**Processing Flow:**
```
Video → Extract Frames → Denoise All → Deblur All → [Upscale All] → Generate Frames → Compile Video
```

**Memory and Time:**

Full-frame-gen is computationally intensive. A 1-minute 1080p video at 4x frame generation with Heavy models may take significant time even on capable hardware. Plan accordingly for batch processing.

---

## Model Modes: Heavy vs Lite

### Heavy Models (Default)

Optimized for maximum quality, designed for systems with adequate resources.

| Model | Architecture | Size | Purpose |
|-------|--------------|------|---------|
| Deblur | NAFNet-width64 | ~260 MB | Blur removal |
| Denoise | NAFNet-width64 | ~440 MB | Noise reduction |
| Upscale | RealESRGAN-x4plus | ~64 MB | Super resolution |
| Frame Gen | RIFE v4.25 | ~21 MB | Interpolation |

**Total Download:** ~785 MB

### Lite Models

Optimized for efficiency, designed for systems with limited resources or faster processing needs.

| Model | Architecture | Size | Purpose |
|-------|--------------|------|---------|
| Deblur | NAFNet-width32 | ~67 MB | Blur removal |
| Denoise | NAFNet-width32 | ~111 MB | Noise reduction |
| Upscale | RealESRGAN-general-x4v3 | ~16 MB | Super resolution |
| Frame Gen | RIFE v4.17 | ~10 MB | Interpolation |

**Total Download:** ~204 MB

### Choosing Between Modes

**Use Heavy when:**
- You have GPU with 6GB+ VRAM
- Maximum quality is the priority
- Processing time isn't critical
- Working with important/archival content

**Use Lite when:**
- Running on CPU only
- GPU has limited VRAM (4GB or less)
- Processing large batches quickly
- System has 8-12GB RAM

---

## AI Models Explained

### NAFNet (Nonlinear Activation Free Network)

NAFNet represents a departure from traditional neural network architectures by removing nonlinear activation functions (like ReLU) and replacing them with simplified operations that achieve better results with lower computational cost.

**Why NAFNet:**

Traditional image restoration networks used complex activation functions that added computational overhead without proportional quality gains. NAFNet demonstrated that simpler architectures can achieve state-of-the-art results by focusing on efficient information flow.

**Training Datasets:**

- **SIDD (for denoising):** Smartphone images with ground-truth clean versions
- **GoPro (for deblurring):** Action camera footage with motion blur

### Real-ESRGAN

Real-ESRGAN extends ESRGAN (Enhanced Super-Resolution Generative Adversarial Network) to handle real-world degradations, not just synthetic downsampling.

**Why Real-ESRGAN:**

Many super-resolution models are trained on artificially downsampled images, which don't match real-world low-resolution content. Real-ESRGAN was trained with a degradation simulation pipeline that mimics how images actually become low-resolution — including compression artifacts, sensor noise, and blur.

**Heavy vs Lite Variants:**

- **x4plus (Heavy):** RRDBNet architecture with 23 residual blocks
- **general-x4v3 (Lite):** SRVGGNetCompact with efficient convolution structure

### RIFE (Real-Time Intermediate Flow Estimation)

RIFE estimates optical flow between frames and uses it to generate intermediate frames at arbitrary time points.

**Why RIFE:**

Traditional frame interpolation used block matching or optical flow methods that struggled with complex motion. RIFE uses a neural network trained end-to-end for frame interpolation, learning to handle occlusions, motion boundaries, and texture synthesis simultaneously.

**Version Differences:**

- **v4.25 (Heavy):** Latest model with improved motion handling
- **v4.17 (Lite):** Earlier but still excellent, more efficient

---

## CLI Reference

### Global Flags

```bash
-heavy              # Use heavy models (default)
-lite               # Use lite models
--device {auto,cpu,gpu}  # Device selection
--cpu               # Force CPU (legacy)
```

### Commands

```bash
# Basic processing
python src/klarity.py denoise <input> [-o output]
python src/klarity.py deblur <input> [-o output]
python src/klarity.py upscale <input> [--upscale 2|4] [-o output]
python src/klarity.py clean <input> [-o output]
python src/klarity.py full <input> [--upscale 2|4] [-o output]

# Video frame generation
python src/klarity.py frame-gen <video> --multi 2|4 [--fps N] [-o output]
python src/klarity.py clean-frame-gen <video> --multi 2|4 [-o output]
python src/klarity.py full-frame-gen <video> --multi 2|4 [--upscale 2|4] [-o output]

# Utility
python src/klarity.py cli              # Interactive mode
python src/klarity.py download-models  # Pre-download models
python src/klarity.py info             # System information
```

### Examples

```bash
# Quick single enhancement
python src/klarity.py denoise photo.jpg
python src/klarity.py deblur image.png -o sharp.png

# Full pipeline
python src/klarity.py full old_photo.jpg --upscale 4

# Lite mode for speed
python src/klarity.py -lite full image.jpg

# Video slow-motion
python src/klarity.py frame-gen video.mp4 --multi 4 --fps 120

# Complete video restoration
python src/klarity.py -heavy full-frame-gen video.mp4 --multi 2 --upscale 2
```

---

## GUI Guide

### Interface Overview

The Klarity GUI provides a visual interface for all processing modes with real-time preview and comparison capabilities.

**Main Components:**

1. **File Input Area** — Drag & drop or browse for files
2. **Mode Selector** — Choose processing mode
3. **Options Panel** — Model mode, upscale factor, frame generation settings
4. **Preview Area** — Before/after comparison with slider
5. **Progress Bar** — Real-time processing status
6. **Save Controls** — Export processed files

### Comparison Views

**Slider View:** Drag the slider to compare before/after at any position

**Side-by-Side View:** See before and after simultaneously

**Single View:** Toggle between original and processed

### Zoom and Pan

- **Ctrl + Scroll:** Zoom in/out
- **Click + Drag:** Pan when zoomed
- **Reset:** Return to fit-to-window

---

## Tips & Best Practices

### Getting Better Results

**For Denoising:**
- Works best on actual noise, not compression artifacts
- Over-sharpened input may produce odd results
- Clean mode is better for noisy + blurry content

**For Deblurring:**
- Motion blur responds best to treatment
- Severe out-of-focus blur has limits
- Don't expect license plate recovery from severe blur

**For Upscaling:**
- Start with the cleanest source available
- Use Full mode for degraded content
- 2x sufficient for web content, 4x for printing

**For Frame Generation:**
- Works best on consistent motion
- Rapid cuts cause artifacts
- Higher multiplier = more potential for issues

### Workflow Recommendations

1. **Start with Clean mode** for most restoration needs
2. **Add upscaling** if resolution is too low
3. **Use Full mode** for maximum quality
4. **Apply frame generation** last, after restoration
5. **Use Lite mode** for testing, Heavy for final output

### Batch Processing

```bash
# Process multiple images
python src/klarity.py full image1.jpg image2.jpg image3.jpg

# Process entire folder
python src/klarity.py clean ./photos/

# Mixed input
python src/klarity.py full photo.jpg ./images/ video.mp4
```

---

## Troubleshooting

### Common Issues

**"Out of Memory" Error:**

- Switch to Lite mode
- Reduce input resolution
- Process shorter video segments
- Close other applications

**Slow Processing:**

- Check if GPU is being used (run `info` command)
- Ensure CUDA is properly installed
- Use Lite mode for faster results
- For video, consider processing key frames only

**Model Download Fails:**

- Check internet connection
- Try manual download from model sources
- Check disk space (~1GB for Heavy models)

**Poor Results:**

- Verify input isn't already heavily processed
- Try different modes (Clean vs Full)
- Check if input matches the problem (blur vs noise)
- Use Heavy mode for maximum quality

**Video Processing Fails:**

- Ensure ffmpeg is installed
- Check video format compatibility
- Try with shorter video first
- Verify sufficient disk space for temp files

### Getting Help

- **GitHub Issues:** https://github.com/HAKORADev/Klarity/issues
- **Check Guide.md** for detailed mode explanations
- **Run `info` command** to diagnose system configuration

---

## Version Information

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.
