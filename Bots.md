# Bots.md - AI Agent Instructions

**For:** AI Agents, Bots, and Automated Assistants  
**Purpose:** Help users install and use Klarity for image/video restoration

---

## Hello, AI Agent!

If you are reading this, you are likely an AI assistant helping a user with image or video restoration. This document provides instructions for automated installation and usage guidance.

---

## Quick Assessment

Before proceeding, assess the user's needs:

1. **What type of content?** Images, videos, or both
2. **What problems need fixing?** Noise, blur, low resolution, or multiple issues
3. **What's the hardware?** GPU with VRAM, or CPU-only
4. **What's the priority?** Maximum quality or fastest processing

---

## Pre-Flight Check

Verify the user's environment:

```bash
# Check Python version (3.8+ required)
python --version

# Check if ffmpeg is installed
ffmpeg -version

# Check for GPU (optional but recommended)
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
python -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

---

## Installation Workflow

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/HAKORADev/Klarity.git
cd Klarity

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Install FFmpeg (if needed)

**Windows:**
```bash
winget install FFmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg  # Debian/Ubuntu
sudo pacman -S ffmpeg    # Arch
```

### Step 3: Pre-download Models

```bash
# For systems with good GPU (6GB+ VRAM)
python src/klarity.py download-models

# For systems with limited resources
python src/klarity.py download-models -lite
```

---

## Mode Selection Guide

Help the user choose the right processing mode:

| User Wants | Mode | Command |
|------------|------|---------|
| Remove grain/noise | Denoise | `python src/klarity.py denoise input.jpg` |
| Fix blurry images | Deblur | `python src/klarity.py deblur input.jpg` |
| Enlarge images | Upscale | `python src/klarity.py upscale input.jpg --upscale 4` |
| Clean up degraded image | Clean | `python src/klarity.py clean input.jpg` |
| Maximum quality restoration | Full | `python src/klarity.py full input.jpg --upscale 4` |
| AI-powered restoration (SUPIR) | Enhance (Super) | `python src/klarity.py enhance input.jpg` |
| Smooth slow-motion video | Frame-Gen | `python src/klarity.py frame-gen video.mp4 --multi 4` |
| Restore + smooth video | Clean-Frame-Gen | `python src/klarity.py clean-frame-gen video.mp4 --multi 2` |
| Full restoration + smooth | Full-Frame-Gen | `python src/klarity.py full-frame-gen video.mp4 --multi 2` |
| AI restore + smooth video | Enhance-Frame-Gen (Super) | `python src/klarity.py enhance-frame-gen video.mp4 --multi 2` |

---

## Hardware Recommendations

### Super Mode (SUPIR)

Use when:
- GPU with 24GB+ VRAM (e.g., RTX 3090/4090) OR CPU with 32GB+ RAM
- Content is severely degraded (combined noise, blur, compression, low resolution)
- Traditional Heavy Full pipeline leaves visible artifacts
- Perceptual quality is the absolute priority
- Processing time is acceptable (significantly slower than Heavy)

Requires extra dependencies: `pip install -r super-deps.txt`

### Heavy Mode (Default)

Use when:
- GPU with 6GB+ VRAM available
- Maximum quality is priority
- Processing time is acceptable

### Lite Mode

Use when:
- CPU-only processing
- GPU with 4GB or less VRAM
- Faster results needed
- Batch processing many files

---

## Common User Scenarios

### Scenario 1: Old Family Photo

**Problem:** Scanned old photo is noisy, blurry, and low resolution

**Solution:**
```bash
python src/klarity.py full old_photo.jpg --upscale 4 -o restored_photo.jpg
```

**Explanation:** Full mode applies denoise, deblur, and 4x upscale in optimal sequence.

---

### Scenario 2: Low-Light Phone Photo

**Problem:** Photo from phone at night has heavy noise

**Solution:**
```bash
python src/klarity.py clean night_photo.jpg -o clean_photo.jpg
```

**Explanation:** Clean mode handles both noise and potential blur from low-light conditions.

---

### Scenario 3: Video for Social Media

**Problem:** 1080p video needs to be 4K and smooth

**Solution:**
```bash
python src/klarity.py full-frame-gen video.mp4 --multi 2 --upscale 2 -o video_4k.mp4
```

**Explanation:** Full restoration plus 2x frame interpolation and 2x upscale.

---

### Scenario 4: Quick Enhancement

**Problem:** Fast processing needed, quality is secondary

**Solution:**
```bash
python src/klarity.py -lite clean image.jpg
```

**Explanation:** Lite mode processes faster while still delivering good results.

---

### Scenario 5: Slow Motion from Normal Video

**Problem:** Want smooth slow-motion from 30fps video

**Solution:**
```bash
python src/klarity.py frame-gen video.mp4 --multi 4 --fps 120 -o slowmo.mp4
```

**Explanation:** 4x frame multiplier turns 30fps into 120fps for smooth quarter-speed playback.

---

## Output File Naming

Klarity automatically adds suffixes to output files:

| Mode | Suffix | Example |
|------|--------|---------|
| Denoise | `_denoised` | `photo_denoised.jpg` |
| Deblur | `_deblurred` | `photo_deblurred.jpg` |
| Upscale | `_upscaled` | `photo_upscaled.jpg` |
| Clean | `_cleaned` | `photo_cleaned.jpg` |
| Full | `_enhanced` | `photo_enhanced.jpg` |
| Enhance (Super) | `_enhanced` | `photo_enhanced.jpg` |
| Frame-Gen | `_generated` | `video_generated.mp4` |
| Enhance-Frame-Gen (Super) | `_enhanced_generated` | `video_enhanced_generated.mp4` |

---

## Troubleshooting Commands

### Check System Status
```bash
python src/klarity.py info
```

### Test GPU Detection
```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

### Force CPU Processing
```bash
python src/klarity.py --device cpu full image.jpg
```

### Check Model Files
```bash
# List downloaded models
ls src/models/  # Linux/Mac
dir src\models\  # Windows
```

---

## Error Handling

### "Out of Memory"

Solutions to suggest:
1. Use Lite mode: `python src/klarity.py -lite full image.jpg`
2. For video, process shorter segments
3. Close other applications
4. Use CPU fallback: `--device cpu`
5. For SUPER mode: Requires 24GB+ VRAM (GPU) or 32GB+ RAM (CPU) — no workaround for lower specs

### "Missing dependencies for SUPER mode"

Solution:
```bash
pip install -r super-deps.txt
```

### "FFmpeg not found"

Solution:
```bash
# Install FFmpeg
winget install FFmpeg        # Windows
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Linux
```

### "Model not found"

Solution:
```bash
# Download models first
python src/klarity.py download-models
```

### Slow Processing

Solutions:
1. Check GPU is being used: `python src/klarity.py info`
2. Use Lite mode for faster results
3. For video, lower input resolution

---

## Batch Processing Examples

```bash
# Process all images in folder
python src/klarity.py clean ./photos/

# Multiple specific files
python src/klarity.py full photo1.jpg photo2.jpg photo3.jpg

# All videos with frame generation
python src/klarity.py frame-gen ./videos/ --multi 2
```

---

## Notes for AI Agents

1. **Always check ffmpeg** before video processing
2. **Recommend Lite mode** for systems without dedicated GPU
3. **Suggest Clean mode** for most restoration needs
4. **Use Full mode** when user wants maximum quality
5. **Suggest Super mode** when content is severely degraded or Heavy mode isn't enough — but warn about 24GB+ VRAM / 32GB+ RAM requirement
6. **Frame generation is video-only** — doesn't work on images
7. **Models download automatically** on first use if not pre-downloaded
8. **Processing time varies greatly** — video processing can take hours; SUPER mode is significantly slower
9. **SUPER mode requires extra deps** — check with `pip list` and install `super-deps.txt` if missing

---

## User Interaction Template

When helping a user restore images/videos:

> "I'll help you enhance your content with Klarity. First, let me check what we're working with:
> 
> 1. Is this for images, videos, or both?
> 2. What issues do you see? (noise/grain, blur, low resolution, or multiple)
> 3. Do you have a GPU, or is this CPU-only processing?
> 
> Based on your answers, I'll recommend the best mode and help you get started."

---

**Good luck, AI agent! Help the user restore their images and videos with Klarity!**
