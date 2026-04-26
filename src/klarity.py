import os
import sys
import argparse
import glob
import shutil
import subprocess
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta

import torch
import cv2
import numpy as np
from tqdm import tqdm

import warnings
warnings.filterwarnings("ignore")

JSON_PROGRESS = False

try:
    from model_downloader import ensure_models, check_internet_connection, set_model_mode, get_model_mode, get_model_paths_for_mode, MODEL_INFO, ensure_super_models
except ImportError:
    def ensure_models(*args, **kwargs):
        print("Warning: model_downloader module not found. Auto-download disabled.")
        return True
    def check_internet_connection():
        return True
    def set_model_mode(mode):
        pass
    def get_model_mode():
        return 'heavy'
    def get_model_paths_for_mode(script_dir, mode=None):
        return {
            'deblur': os.path.join(script_dir, 'models', f'deblur-{mode or "heavy"}.pth'),
            'denoise': os.path.join(script_dir, 'models', f'denoise-{mode or "heavy"}.pth'),
            'upscale': os.path.join(script_dir, 'models', f'upscale-{mode or "heavy"}.pth'),
            'rife': os.path.join(script_dir, 'models', f'framegen-{mode or "heavy"}.pkl'),
        }
    MODEL_INFO = {}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
TEMP_DIR = os.path.join(SCRIPT_DIR, "tmp")

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}

device = None
device_preference = None

NAFNET_CONFIGS = {
    'deblur': {
        'heavy': {
            'width': 64,
            'middle_blk_num': 1,
            'enc_blk_nums': [1, 1, 1, 28],
            'dec_blk_nums': [1, 1, 1, 1],
        },
        'lite': {
            'width': 32,
            'middle_blk_num': 1,
            'enc_blk_nums': [1, 1, 1, 28],
            'dec_blk_nums': [1, 1, 1, 1],
        },
    },
    'denoise': {
        'heavy': {
            'width': 64,
            'middle_blk_num': 12,
            'enc_blk_nums': [2, 2, 4, 8],
            'dec_blk_nums': [2, 2, 2, 2],
        },
        'lite': {
            'width': 32,
            'middle_blk_num': 12,
            'enc_blk_nums': [2, 2, 4, 8],
            'dec_blk_nums': [2, 2, 2, 2],
        },
    },
}

class ProgressTracker:
    def __init__(self):
        self.total_files = 0
        self.current_file_idx = 0
        self.start_time = None
        self.current_file_start = None
        self.current_step = ""
        self.current_file_name = ""
        self.file_times = []
        self._last_update = 0

    def start_batch(self, total_files):
        self.total_files = total_files
        self.current_file_idx = 0
        self.start_time = time.time()
        self.file_times = []

    def start_file(self, file_name):
        self.current_file_idx += 1
        self.current_file_name = os.path.basename(file_name)
        self.current_file_start = time.time()
        self.current_step = "Loading"

    def set_step(self, step_name):
        self.current_step = step_name

    def finish_file(self):
        if self.current_file_start:
            elapsed = time.time() - self.current_file_start
            self.file_times.append(elapsed)
            return elapsed
        return 0

    def get_elapsed_str(self):
        if not self.start_time:
            return "00:00"
        elapsed = time.time() - self.start_time
        return self._format_time(elapsed)

    def get_eta_str(self):
        if len(self.file_times) < 2:
            return "calculating..."
        avg_time = sum(self.file_times) / len(self.file_times)
        remaining_files = self.total_files - self.current_file_idx
        eta_seconds = avg_time * remaining_files
        return self._format_time(eta_seconds)

    def _format_time(self, seconds):
        if seconds < 3600:
            return time.strftime("%M:%S", time.gmtime(seconds))
        return time.strftime("%H:%M:%S", time.gmtime(seconds))

    def print_status(self, force=False):
        global JSON_PROGRESS
        now = time.time()
        if not force and (now - self._last_update) < 0.1:
            return
        self._last_update = now
        elapsed = self.get_elapsed_str()
        eta = self.get_eta_str()
        progress_pct = (self.current_file_idx / self.total_files * 100) if self.total_files > 0 else 0
        display_name = self.current_file_name
        if len(display_name) > 35:
            display_name = display_name[:32] + "..."

        if JSON_PROGRESS:
            json_output = json.dumps({
                'percent': int(progress_pct),
                'step': self.current_step,
                'file': display_name,
                'file_num': self.current_file_idx,
                'total_files': self.total_files,
                'elapsed': elapsed,
                'eta': eta
            })
            print(json_output)
            sys.stdout.flush()
        else:
            status = f"\r[{self.current_file_idx}/{self.total_files}] ({progress_pct:5.1f}%) | {elapsed} elapsed, ETA: {eta} | {display_name} | {self.current_step}"
            status = status.ljust(120)
            sys.stdout.write(status)
            sys.stdout.flush()

    def print_newline(self):
        sys.stdout.write("\n")
        sys.stdout.flush()

progress = ProgressTracker()

class StepProgressBar:
    def __init__(self, steps, file_name=""):
        self.steps = steps
        self.current_step_idx = 0
        self.file_name = file_name
        self.bar_width = 30

    def update(self, step_name):
        self.current_step_idx += 1
        progress_pct = self.current_step_idx / self.steps * 100
        filled = int(self.bar_width * self.current_step_idx / self.steps)
        bar = "█" * filled + "░" * (self.bar_width - filled)
        display_name = self.file_name
        if len(display_name) > 25:
            display_name = display_name[:22] + "..."
        status = f"\r  {display_name} [{bar}] {self.current_step_idx}/{self.steps} ({progress_pct:5.1f}%) - {step_name}"
        status = status.ljust(100)
        sys.stdout.write(status)
        sys.stdout.flush()

    def finish(self):
        bar = "█" * self.bar_width
        status = f"\r  {self.file_name[:25]:<25} [{bar}] {self.steps}/{self.steps} (100.0%) - Done!"
        status = status.ljust(100)
        sys.stdout.write(status)
        sys.stdout.flush()
        print()

def get_model_paths():
    mode = get_model_mode()
    return get_model_paths_for_mode(SCRIPT_DIR, mode)

def check_and_download_models():
    mode = get_model_mode()
    model_paths = get_model_paths()
    ensure_models(SCRIPT_DIR, model_paths, auto_download=True, prompt=True, mode=mode)

def check_gpu():
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return True, gpu_name, f"{gpu_memory:.1f}GB"
    return False, "CPU", "N/A"

def get_device(force_cpu=False, device_type=None):
    global device
    if device is not None:
        return device
    if force_cpu or device_type == 'cpu':
        device = torch.device('cpu')
        print("Device: CPU")
        return device
    if device_type == 'gpu':
        if torch.cuda.is_available():
            device = torch.device('cuda')
            print(f"Device: GPU ({torch.cuda.get_device_name(0)})")
        else:
            print("GPU requested but not available - falling back to CPU")
            device = torch.device('cpu')
        return device
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print(f"Device: GPU ({torch.cuda.get_device_name(0)})")
    else:
        device = torch.device('cpu')
        print("Device: CPU (no GPU available)")
    return device

def select_device():
    global device, device_preference
    has_gpu, gpu_name, gpu_memory = check_gpu()
    print("\n" + "-"*40)
    print("Select device:")
    if has_gpu:
        print(f"  1. CPU")
        print(f"  2. GPU ({gpu_name}, {gpu_memory})")
    else:
        print(f"  1. CPU (only option available)")
        print(f"  2. GPU (not available)")
    print("\n  Press Enter for auto-detect (GPU if available, else CPU)")
    choice = input("> ").strip()
    if choice == '':
        if has_gpu:
            device = torch.device('cuda')
            print(f"\nUsing GPU: {gpu_name} ({gpu_memory})")
        else:
            device = torch.device('cpu')
            print("\nUsing CPU (no GPU available)")
    elif choice == '1':
        device = torch.device('cpu')
        print("\nUsing CPU")
    elif choice == '2':
        if has_gpu:
            device = torch.device('cuda')
            print(f"\nUsing GPU: {gpu_name} ({gpu_memory})")
        else:
            print("\nGPU requested but not available - falling back to CPU")
            device = torch.device('cpu')
    else:
        print("\nInvalid choice, auto-detecting...")
        if has_gpu:
            device = torch.device('cuda')
            print(f"Using GPU: {gpu_name} ({gpu_memory})")
        else:
            device = torch.device('cpu')
            print("Using CPU")
    return device

def select_model_mode():
    print("\n" + "="*60)
    print("SELECT MODEL MODE")
    print("="*60)
    print("\n  1. Heavy  - Better quality, larger models (default)")
    print("  2. Lite   - Faster processing, smaller models")
    print("  3. Super  - Maximum quality AI restoration (SUPIR, requires extra deps)")
    print("")
    print("  Heavy models: NAFNet-width64, Real-HAT-GAN-sharper, RIFE-v4.25")
    print("  Lite models:  NAFNet-width32, Real-ESRGAN-general-x4v3, RIFE-v4.17")
    print("  Super model:  SUPIR-v0Q (AI restoration, ~6.7GB)")
    while True:
        choice = input("\nSelect mode (1, 2, or 3): ").strip()
        if choice == '1' or choice == '':
            return 'heavy'
        elif choice == '2':
            return 'lite'
        elif choice == '3':
            return 'super'
        else:
            print(f"Invalid input: '{choice}'. Please enter 1, 2, or 3.")

deblur_model = None
denoise_model = None
upscale_model = None
framegen_model = None
enhance_super_model = None

def load_deblur_model():
    global deblur_model
    if deblur_model is not None:
        return deblur_model
    mode = get_model_mode()
    model_paths = get_model_paths()
    sys.path.insert(0, MODELS_DIR)
    from nafnet_arch import NAFNetLocal
    config = NAFNET_CONFIGS['deblur'].get(mode, NAFNET_CONFIGS['deblur']['heavy'])
    model = NAFNetLocal(
        img_channel=3,
        width=config['width'],
        middle_blk_num=config['middle_blk_num'],
        enc_blk_nums=config['enc_blk_nums'],
        dec_blk_nums=config['dec_blk_nums'],
    )
    deblur_model_path = model_paths['deblur']
    checkpoint = torch.load(deblur_model_path, map_location='cpu')
    state_dict = checkpoint.get('params', checkpoint.get('state_dict', checkpoint))
    for k in list(state_dict.keys()):
        if k.startswith('module.'):
            state_dict[k[7:]] = state_dict.pop(k)
    model.load_state_dict(state_dict)
    model = model.to(get_device())
    model.eval()
    deblur_model = model
    print(f"Loaded deblur model: {mode.upper()} (width={config['width']})")
    return model

def load_denoise_model():
    global denoise_model
    if denoise_model is not None:
        return denoise_model
    mode = get_model_mode()
    model_paths = get_model_paths()
    sys.path.insert(0, MODELS_DIR)
    from nafnet_arch import NAFNet
    config = NAFNET_CONFIGS['denoise'].get(mode, NAFNET_CONFIGS['denoise']['heavy'])
    model = NAFNet(
        img_channel=3,
        width=config['width'],
        middle_blk_num=config['middle_blk_num'],
        enc_blk_nums=config['enc_blk_nums'],
        dec_blk_nums=config['dec_blk_nums'],
    )
    denoise_model_path = model_paths['denoise']
    checkpoint = torch.load(denoise_model_path, map_location='cpu')
    state_dict = checkpoint.get('params', checkpoint.get('state_dict', checkpoint))
    for k in list(state_dict.keys()):
        if k.startswith('module.'):
            state_dict[k[7:]] = state_dict.pop(k)
    model.load_state_dict(state_dict)
    model = model.to(get_device())
    model.eval()
    denoise_model = model
    print(f"Loaded denoise model: {mode.upper()} (width={config['width']})")
    return model

def load_upscale_model():
    global upscale_model
    if upscale_model is not None:
        return upscale_model
    mode = get_model_mode()
    model_paths = get_model_paths()
    sys.path.insert(0, SCRIPT_DIR)
    if mode == 'heavy':
        from hat_gan_arch import HAT
        model = HAT(
            upscale=4,
            in_chans=3,
            img_size=64,
            window_size=16,
            compress_ratio=3,
            squeeze_factor=30,
            conv_scale=0.01,
            overlap_ratio=0.5,
            img_range=1.,
            depths=[6, 6, 6, 6, 6, 6],
            embed_dim=180,
            num_heads=[6, 6, 6, 6, 6, 6],
            mlp_ratio=2,
            upsampler='pixelshuffle',
            resi_connection='1conv',
        )
        model_name = "Real-HAT-GAN-sharper"
    else:
        from sr_arch import SRVGGNetCompact
        model = SRVGGNetCompact(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_conv=32,
            upscale=4,
            act_type='prelu'
        )
        model_name = "RealESRGAN-general-x4v3"
    checkpoint = torch.load(model_paths['upscale'], map_location='cpu')
    state_dict = checkpoint.get('params_ema', checkpoint.get('params', checkpoint.get('state_dict', checkpoint)))
    for k in list(state_dict.keys()):
        if k.startswith('module.'):
            state_dict[k[7:]] = state_dict.pop(k)
    model.load_state_dict(state_dict)
    model = model.to(get_device())
    model.eval()
    upscale_model = model
    print(f"Loaded upscale model: {mode.upper()} ({model_name})")
    return model

def load_framegen_model():
    global framegen_model
    if framegen_model is not None:
        return framegen_model
    mode = get_model_mode()
    model_paths = get_model_paths()
    sys.path.insert(0, SCRIPT_DIR)
    from rife_arch import RIFE
    model = RIFE(mode=mode)
    model.load_model(MODELS_DIR, mode=mode)
    model.eval()
    model.device()
    framegen_model = model
    version = "4.25" if mode == 'heavy' else "4.17"
    print(f"Loaded frame generation model: {mode.upper()} (RIFE v{version})")
    return model

def pad_image(img, modulo=32):
    h, w = img.shape[2], img.shape[3]
    new_h = ((h - 1) // modulo + 1) * modulo
    new_w = ((w - 1) // modulo + 1) * modulo
    pad_h = new_h - h
    pad_w = new_w - w
    if pad_h > 0 or pad_w > 0:
        img = torch.nn.functional.pad(img, (0, pad_w, 0, pad_h), mode='reflect')
    return img, (h, w)

def process_nafnet(model, img_tensor):
    with torch.no_grad():
        padded, (h, w) = pad_image(img_tensor)
        output = model(padded)
        return output[:, :, :h, :w]

def process_upscale(model, img_tensor):
    with torch.no_grad():
        padded, (h, w) = pad_image(img_tensor, modulo=16)
        output = model(padded)
        new_h, new_w = h * 4, w * 4
        return output[:, :, :new_h, :new_w]

def img2tensor(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.
    img = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0)
    return img.to(get_device())

def tensor2img(tensor):
    tensor = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    tensor = np.clip(tensor * 255, 0, 255).astype(np.uint8)
    tensor = cv2.cvtColor(tensor, cv2.COLOR_RGB2BGR)
    return tensor

def is_image(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS

def is_video(path):
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS

def get_files(path):
    path = Path(path)
    if path.is_file():
        return [str(path)]
    elif path.is_dir():
        files = []
        for ext in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            files.extend(path.glob(f"*{ext}"))
            files.extend(path.glob(f"*{ext.upper()}"))
        return sorted([str(f) for f in files])
    return []

def parse_multiple_paths(input_string):
    paths = []
    current = ""
    in_quotes = False
    quote_char = None
    i = 0
    while i < len(input_string):
        char = input_string[i]
        if char in ['"', "'"]:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
            else:
                current += char
        elif char in [' ', '\t'] and not in_quotes:
            if current.strip():
                paths.append(current.strip())
            current = ""
        else:
            current += char
        i += 1
    if current.strip():
        paths.append(current.strip())
    return paths

def categorize_path(path_str):
    path = Path(path_str)
    if not path.exists():
        cleaned = path_str.strip()
        if len(cleaned) == 0:
            return ('invalid', [])
        has_alnum = any(c.isalnum() for c in cleaned)
        if not has_alnum:
            return ('invalid', [])
        return ('not_exist', [])
    if path.is_file():
        if is_image(str(path)) or is_video(str(path)):
            return ('valid', [str(path)])
        else:
            return ('not_supported', [])
    elif path.is_dir():
        files = get_files(str(path))
        if files:
            return ('valid', files)
        else:
            return ('not_supported', [])
    else:
        return ('not_supported', [])

def categorize_multiple_paths(path_list):
    result = {
        'valid': [],
        'not_exist': [],
        'not_supported': [],
        'invalid': [],
        'all_valid_files': []
    }
    for path_str in path_list:
        category, valid_files = categorize_path(path_str)
        if category == 'valid':
            result['valid'].append((path_str, valid_files))
            result['all_valid_files'].extend(valid_files)
        elif category == 'not_exist':
            result['not_exist'].append(path_str)
        elif category == 'not_supported':
            result['not_supported'].append(path_str)
        else:
            result['invalid'].append(path_str)
    return result

def display_path_summary(categorized, max_display=5):
    valid = categorized['valid']
    not_exist = categorized['not_exist']
    not_supported = categorized['not_supported']
    invalid = categorized['invalid']
    total_paths = len(valid) + len(not_exist) + len(not_supported) + len(invalid)
    if total_paths == 0:
        return
    print("\n" + "-"*60)
    print("INPUT PATH SUMMARY")
    print("-"*60)
    if valid:
        print(f"\n✓ VALID ({len(valid)}):")
        display_count = min(len(valid), max_display)
        for i in range(display_count):
            orig_path, files = valid[i]
            if len(files) == 1:
                print(f"   {orig_path}")
            else:
                print(f"   {orig_path}/ ({len(files)} files)")
        if len(valid) > max_display:
            remaining = len(valid) - max_display
            print(f"   ... +{remaining} more valid")
    if not_exist:
        print(f"\n✗ NOT FOUND ({len(not_exist)}):")
        display_count = min(len(not_exist), max_display)
        for i in range(display_count):
            print(f"   {not_exist[i]}")
        if len(not_exist) > max_display:
            remaining = len(not_exist) - max_display
            print(f"   ... +{remaining} more not found")
    if not_supported:
        print(f"\n⚠ NOT SUPPORTED ({len(not_supported)}):")
        display_count = min(len(not_supported), max_display)
        for i in range(display_count):
            print(f"   {not_supported[i]}")
        if len(not_supported) > max_display:
            remaining = len(not_supported) - max_display
            print(f"   ... +{remaining} more not supported")
    if invalid:
        print(f"\n? INVALID INPUT ({len(invalid)}):")
        display_count = min(len(invalid), max_display)
        for i in range(display_count):
            print(f"   {invalid[i]}")
        if len(invalid) > max_display:
            remaining = len(invalid) - max_display
            print(f"   ... +{remaining} more invalid")
    valid_file_count = len(categorized['all_valid_files'])
    if valid_file_count > 0:
        print(f"\n→ {valid_file_count} file(s) ready to process from {len(valid)} valid path(s)")
    else:
        print(f"\n→ No valid files found to process")

def generate_output_path(input_path, mode, output_arg=None):
    input_path = Path(input_path)
    if output_arg:
        output_path = Path(output_arg)
        is_folder = (str(output_path).endswith('/') or
                     str(output_path).endswith('\\') or
                     output_path.is_dir() or
                     (output_path.suffix == '' and not output_path.exists()))
        if is_folder:
            suffix = get_mode_suffix(mode)
            return str(output_path / f"{input_path.stem}{suffix}{input_path.suffix}")
        return str(output_arg)
    suffix = get_mode_suffix(mode)
    parent = input_path.parent
    return str(parent / f"{input_path.stem}{suffix}{input_path.suffix}")

def get_mode_suffix(mode):
    suffixes = {
        'denoise': '_denoised',
        'deblur': '_deblurred',
        'upscale': '_upscaled',
        'clean': '_cleaned',
        'full': '_enhanced',
        'frame-gen': '_generated',
        'clean-frame-gen': '_clean_generated',
        'full-frame-gen': '_full_enhanced',
        'enhance': '_enhanced',
        'enhance-frame-gen': '_enhanced_generated',
    }
    return suffixes.get(mode, '_processed')

def ensure_ffmpeg():
    if shutil.which('ffmpeg') is None:
        raise RuntimeError("ffmpeg not found. Please install ffmpeg to process videos.")

def extract_frames(video_path, output_dir, desc="Extracting frames"):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vsync', '0',
        os.path.join(output_dir, '%08d.png')
    ]
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    with tqdm(total=total_frames, desc=desc, unit="frames",
              bar_format="{l_bar}{bar:30}{r_bar}") as pbar:
        while process.poll() is None:
            if os.path.exists(output_dir):
                current_frames = len([f for f in os.listdir(output_dir) if f.endswith('.png')])
                pbar.update(current_frames - pbar.n)
            time.sleep(0.1)
        if os.path.exists(output_dir):
            current_frames = len([f for f in os.listdir(output_dir) if f.endswith('.png')])
            pbar.update(current_frames - pbar.n)

def extract_audio(video_path, audio_path):
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'copy',
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0

def get_video_info(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return fps, frame_count, width, height

def frames_to_video(frames_dir, output_path, fps, audio_path=None, desc="Compiling video"):
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    total_frames = len(frames)
    temp_video = output_path + '_temp.mp4'
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-i', os.path.join(frames_dir, '%08d.png'),
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '18',
        '-progress', 'pipe:2',
        temp_video
    ]
    compiled_frames = [0]
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1)

    def _read_ffmpeg_progress(pipe):
        for raw_line in iter(pipe.readline, b''):
            decoded = raw_line.decode('utf-8', errors='ignore').strip()
            if decoded.startswith('frame='):
                try:
                    compiled_frames[0] = int(decoded.split('=')[1].strip())
                except (ValueError, IndexError):
                    pass
        pipe.close()

    reader = threading.Thread(target=_read_ffmpeg_progress, args=(process.stderr,), daemon=True)
    reader.start()

    last_reported = [0]
    with tqdm(total=total_frames, desc=desc, unit="frames",
              bar_format="{desc} | {n_fmt}/{total_fmt} frames {bar:25} {percentage:5.1f}% | {elapsed}<{remaining}, {rate_fmt}{postfix}") as pbar:
        while process.poll() is None:
            time.sleep(0.05)
            current = compiled_frames[0]
            if current > last_reported[0]:
                pbar.update(current - last_reported[0])
                last_reported[0] = current
                remaining = total_frames - current
                pbar.set_postfix_str(f"{remaining} remaining")
        reader.join(timeout=2)
        final = compiled_frames[0]
        if final > last_reported[0]:
            pbar.update(final - last_reported[0])
            last_reported[0] = final
        fill_needed = max(0, total_frames - pbar.n)
        if fill_needed > 0:
            pbar.update(fill_needed)
        pbar.set_postfix_str("")
    if audio_path and os.path.exists(audio_path):
        cmd = [
            'ffmpeg', '-y',
            '-i', temp_video,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0?',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and os.path.exists(output_path):
            os.remove(temp_video)
            return
    if os.path.exists(temp_video):
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(temp_video, output_path)

def blend_frames_for_fps(frames_dir, target_fps, original_fps):
    ratio = target_fps / original_fps
    if ratio <= 1:
        return frames_dir
    blended_dir = frames_dir + '_blended'
    os.makedirs(blended_dir, exist_ok=True)
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(original_fps),
        '-i', os.path.join(frames_dir, '%08d.png'),
        '-vf', f'minterpolate=fps={target_fps}:mi_mode=blend',
        '-vsync', '0',
        os.path.join(blended_dir, '%08d.png')
    ]
    subprocess.run(cmd, capture_output=True)
    return blended_dir

def process_image_denoise(img, step_bar=None):
    if step_bar:
        step_bar.update("Denoising...")
    else:
        progress.set_step("Denoising")
        progress.print_status()
    model = load_denoise_model()
    tensor = img2tensor(img)
    output = process_nafnet(model, tensor)
    return tensor2img(output)

def process_image_deblur(img, step_bar=None):
    if step_bar:
        step_bar.update("Deblurring...")
    else:
        progress.set_step("Deblurring")
        progress.print_status()
    model = load_deblur_model()
    tensor = img2tensor(img)
    output = process_nafnet(model, tensor)
    return tensor2img(output)

def process_image_upscale(img, step_bar=None, upscale_factor=4):
    if step_bar:
        step_bar.update(f"Upscaling x{upscale_factor}...")
    else:
        progress.set_step(f"Upscaling x{upscale_factor}")
        progress.print_status()
    model = load_upscale_model()
    tensor = img2tensor(img)
    output = process_upscale(model, tensor)
    result = tensor2img(output)
    if upscale_factor == 2:
        h, w = result.shape[:2]
        new_h, new_w = h // 2, w // 2
        result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    return result

def process_image_clean(img, step_bar=None):
    img = process_image_denoise(img, step_bar)
    img = process_image_deblur(img, step_bar)
    return img

def process_image_full(img, step_bar=None, upscale_factor=4):
    img = process_image_denoise(img, step_bar)
    img = process_image_deblur(img, step_bar)
    img = process_image_upscale(img, step_bar, upscale_factor)
    return img

def check_super_deps():
    required = ['diffusers', 'transformers', 'accelerate', 'omegaconf', 'einops', 'open_clip', 'k_diffusion', 'pytorch_lightning']
    try:
        import subprocess
        result = subprocess.run(['pip', 'list', '--format=freeze'], capture_output=True, text=True)
        installed = result.stdout.lower()
        missing = []
        aliases = {
            'open_clip': 'open-clip-torch',
            'k_diffusion': 'k-diffusion',
            'pytorch_lightning': 'pytorch-lightning',
        }
        for dep in required:
            pkg_name = aliases.get(dep, dep)
            if pkg_name.replace('-', '_') not in installed.replace('-', '_'):
                missing.append(dep)
        if missing:
            print("\n" + "="*60)
            print("ERROR: Missing dependencies for SUPER mode!")
            print("="*60)
            print(f"Missing packages: {', '.join(missing)}")
            print("\nInstall with: pip install -r super-deps.txt")
            print("The super-deps.txt file is in the Klarity project root.")
            print("="*60)
            sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not check SUPER dependencies: {e}")

def load_enhance_super_model():
    global enhance_super_model
    if enhance_super_model is not None:
        return enhance_super_model
    check_super_deps()
    sys.path.insert(0, SCRIPT_DIR)
    from supir_arch import SUPIRProcessor
    enhance_super_model = SUPIRProcessor(MODELS_DIR)
    enhance_super_model.load_model(get_device())
    print("Loaded enhance model: SUPER (SUPIR-v0Q)")
    return enhance_super_model

def process_image_enhance_super(img, step_bar=None):
    if step_bar:
        step_bar.update("SUPIR enhancing...")
    else:
        progress.set_step("SUPIR enhancing")
        progress.print_status()
    model = load_enhance_super_model()
    h, w = img.shape[:2]
    img_resized = cv2.resize(img, (1024, 1024), interpolation=cv2.INTER_LANCZOS4)
    result = model.enhance(img_resized, get_device(), step_bar=step_bar)
    return result

def get_rife_scale():
    return 1.0

def get_rife_padding_divisor(scale=1.0):
    return max(64, int(64 / scale))

def pad_for_rife(img, scale=1.0):
    divisor = get_rife_padding_divisor(scale)
    h, w = img.shape[:2]
    new_h = ((h - 1) // divisor + 1) * divisor
    new_w = ((w - 1) // divisor + 1) * divisor
    if new_h > h or new_w > w:
        img = np.pad(img, ((0, new_h - h), (0, new_w - w), (0, 0)), mode='edge')
    return img, (h, w)

def generate_frames(frames_dir, output_dir, multi=2):
    model = load_framegen_model()
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    if len(frames) < 2:
        raise ValueError("Need at least 2 frames for generation")
    os.makedirs(output_dir, exist_ok=True)
    scale = get_rife_scale()
    output_idx = 0
    total_pairs = len(frames) - 1
    total_output_frames = len(frames) * multi - (multi - 1)
    pbar = tqdm(total=total_output_frames, desc=f"Generating (x{multi})", unit="frame",
              bar_format="{desc} | Frame {n_fmt}/{total_fmt} {bar:25} {percentage:5.1f}% | {elapsed}<{remaining} {postfix}")
    for i in range(total_pairs):
        pbar.set_postfix_str(f"| pair {i+1}/{total_pairs} [frame {i+1}\u2192{i+2}]")
        img0 = cv2.imread(os.path.join(frames_dir, frames[i]))
        img1 = cv2.imread(os.path.join(frames_dir, frames[i + 1]))
        img0, (orig_h, orig_w) = pad_for_rife(img0, scale)
        img1, _ = pad_for_rife(img1, scale)
        img0_tensor = img2tensor(img0)
        img1_tensor = img2tensor(img1)
        cv2.imwrite(os.path.join(output_dir, f'{output_idx:08d}.png'), img0[:orig_h, :orig_w])
        output_idx += 1
        pbar.update(1)
        for j in range(multi - 1):
            timestep = (j + 1) / multi
            with torch.no_grad():
                mid = model.inference(img0_tensor, img1_tensor, timestep, scale)
            mid_img = tensor2img(mid)
            cv2.imwrite(os.path.join(output_dir, f'{output_idx:08d}.png'), mid_img[:orig_h, :orig_w])
            output_idx += 1
            pbar.update(1)
    last_frame = cv2.imread(os.path.join(frames_dir, frames[-1]))
    cv2.imwrite(os.path.join(output_dir, f'{output_idx:08d}.png'), last_frame)
    pbar.update(1)
    pbar.set_postfix_str("")
    return total_output_frames

class _SilentStepBar:
    def update(self, msg):
        pass

def process_video_frames_step(frames_dir, output_dir, frames, step_name, process_func):
    os.makedirs(output_dir, exist_ok=True)
    total = len(frames)
    silent = _SilentStepBar()
    with tqdm(total=total, desc=step_name, unit="frame",
              bar_format="{desc} | Frame {n_fmt}/{total_fmt} {bar:25} {percentage:5.1f}% | {elapsed}<{remaining}, {rate_fmt}") as pbar:
        for frame_name in frames:
            img = cv2.imread(os.path.join(frames_dir, frame_name))
            img = process_func(img, step_bar=silent)
            cv2.imwrite(os.path.join(output_dir, frame_name), img)
            pbar.update(1)

def process_video_multistep(video_path, output_path, steps, audio_path):
    original_fps, frame_count, width, height = get_video_info(video_path)
    frames_dir = os.path.join(TEMP_DIR, "frames")
    current_dir = frames_dir
    progress.set_step("Extracting frames")
    progress.print_status()
    extract_frames(video_path, frames_dir, desc="Extracting frames")
    extract_audio(video_path, audio_path)
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    for i, (step_name, process_func) in enumerate(steps):
        step_output_dir = os.path.join(TEMP_DIR, f"step_{i}")
        progress.set_step(step_name)
        progress.print_status()
        process_video_frames_step(current_dir, step_output_dir, frames, step_name, process_func)
        current_dir = step_output_dir
    sample_frame = cv2.imread(os.path.join(current_dir, frames[0]))
    new_height, new_width = sample_frame.shape[:2]
    progress.set_step("Compiling video")
    progress.print_status()
    frames_to_video(current_dir, output_path, original_fps,
                   audio_path if os.path.exists(audio_path) else None,
                   desc="Compiling video")
    return new_width, new_height

def process_video_enhance_super_frame_gen(video_path, output_path, multi=2, fps=None):
    ensure_ffmpeg()
    original_fps, frame_count, width, height = get_video_info(video_path)
    min_fps = original_fps
    max_fps = original_fps * multi
    if fps is None:
        fps = max_fps
    elif fps < min_fps:
        fps = max_fps
    elif fps > max_fps:
        fps = max_fps
    frames_dir = os.path.join(TEMP_DIR, "frames")
    enhanced_dir = os.path.join(TEMP_DIR, "enhanced")
    gen_dir = os.path.join(TEMP_DIR, "generated")
    audio_path = os.path.join(TEMP_DIR, "audio.aac")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    progress.set_step("Extracting frames")
    progress.print_status()
    extract_frames(video_path, frames_dir, desc="Extracting frames")
    extract_audio(video_path, audio_path)
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    process_video_frames_step(frames_dir, enhanced_dir, frames, "SUPIR Enhancing frames", process_image_enhance_super)
    progress.set_step(f"Generating x{multi}")
    progress.print_status()
    enhanced_frames = sorted([f for f in os.listdir(enhanced_dir) if f.endswith('.png')])
    generate_frames_custom(enhanced_dir, gen_dir, enhanced_frames, multi)
    final_frames_dir = gen_dir
    if fps < max_fps:
        progress.set_step("Blending frames")
        progress.print_status()
        final_frames_dir = blend_frames_for_fps(gen_dir, fps, max_fps)
    progress.set_step("Compiling video")
    progress.print_status()
    frames_to_video(final_frames_dir, output_path, fps,
                   audio_path if os.path.exists(audio_path) else None,
                   desc="Compiling video")
    shutil.rmtree(TEMP_DIR)

def generate_frames_custom(frames_dir, output_dir, frames, multi=2):
    model = load_framegen_model()
    if len(frames) < 2:
        raise ValueError("Need at least 2 frames for generation")
    os.makedirs(output_dir, exist_ok=True)
    scale = get_rife_scale()
    output_idx = 0
    total_pairs = len(frames) - 1
    total_output_frames = len(frames) * multi - (multi - 1)
    pbar = tqdm(total=total_output_frames, desc=f"Generating (x{multi})", unit="frame",
              bar_format="{desc} | Frame {n_fmt}/{total_fmt} {bar:25} {percentage:5.1f}% | {elapsed}<{remaining} {postfix}")
    for i in range(total_pairs):
        pbar.set_postfix_str(f"| pair {i+1}/{total_pairs} [frame {i+1}\u2192{i+2}]")
        img0 = cv2.imread(os.path.join(frames_dir, frames[i]))
        img1 = cv2.imread(os.path.join(frames_dir, frames[i + 1]))
        img0, (orig_h, orig_w) = pad_for_rife(img0, scale)
        img1, _ = pad_for_rife(img1, scale)
        img0_tensor = img2tensor(img0)
        img1_tensor = img2tensor(img1)
        cv2.imwrite(os.path.join(output_dir, f'{output_idx:08d}.png'), img0[:orig_h, :orig_w])
        output_idx += 1
        pbar.update(1)
        for j in range(multi - 1):
            timestep = (j + 1) / multi
            with torch.no_grad():
                mid = model.inference(img0_tensor, img1_tensor, timestep, scale)
            mid_img = tensor2img(mid)
            cv2.imwrite(os.path.join(output_dir, f'{output_idx:08d}.png'), mid_img[:orig_h, :orig_w])
            output_idx += 1
            pbar.update(1)
    last_frame = cv2.imread(os.path.join(frames_dir, frames[-1]))
    cv2.imwrite(os.path.join(output_dir, f'{output_idx:08d}.png'), last_frame)
    pbar.update(1)
    pbar.set_postfix_str("")
    return total_output_frames

def process_video_frame_gen(video_path, output_path, multi=2, fps=None):
    ensure_ffmpeg()
    original_fps, frame_count, width, height = get_video_info(video_path)
    min_fps = original_fps
    max_fps = original_fps * multi
    if fps is None:
        fps = max_fps
    elif fps < min_fps:
        print(f"Warning: Target FPS {fps:.2f} below minimum ({min_fps:.2f}). Using max: {max_fps:.2f}")
        fps = max_fps
    elif fps > max_fps:
        print(f"Warning: Target FPS {fps:.2f} exceeds maximum ({max_fps:.2f}). Using max: {max_fps:.2f}")
        fps = max_fps
    frames_dir = os.path.join(TEMP_DIR, "frames")
    gen_dir = os.path.join(TEMP_DIR, "generated")
    audio_path = os.path.join(TEMP_DIR, "audio.aac")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    progress.set_step("Extracting frames")
    progress.print_status()
    extract_frames(video_path, frames_dir, desc="Extracting frames")
    extract_audio(video_path, audio_path)
    progress.set_step(f"Generating x{multi}")
    progress.print_status()
    generate_frames(frames_dir, gen_dir, multi)
    final_frames_dir = gen_dir
    if fps < max_fps:
        progress.set_step("Blending frames")
        progress.print_status()
        final_frames_dir = blend_frames_for_fps(gen_dir, fps, max_fps)
    progress.set_step("Compiling video")
    progress.print_status()
    frames_to_video(final_frames_dir, output_path, fps,
                   audio_path if os.path.exists(audio_path) else None,
                   desc="Compiling video")
    shutil.rmtree(TEMP_DIR)

def process_video_clean_frame_gen(video_path, output_path, multi=2, fps=None):
    ensure_ffmpeg()
    original_fps, frame_count, width, height = get_video_info(video_path)
    min_fps = original_fps
    max_fps = original_fps * multi
    if fps is None:
        fps = max_fps
    elif fps < min_fps:
        print(f"Warning: Target FPS {fps:.2f} below minimum ({min_fps:.2f}). Using max: {max_fps:.2f}")
        fps = max_fps
    elif fps > max_fps:
        print(f"Warning: Target FPS {fps:.2f} exceeds maximum ({max_fps:.2f}). Using max: {max_fps:.2f}")
        fps = max_fps
    frames_dir = os.path.join(TEMP_DIR, "frames")
    denoised_dir = os.path.join(TEMP_DIR, "denoised")
    cleaned_dir = os.path.join(TEMP_DIR, "cleaned")
    gen_dir = os.path.join(TEMP_DIR, "generated")
    audio_path = os.path.join(TEMP_DIR, "audio.aac")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    progress.set_step("Extracting frames")
    progress.print_status()
    extract_frames(video_path, frames_dir, desc="Extracting frames")
    extract_audio(video_path, audio_path)
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    process_video_frames_step(frames_dir, denoised_dir, frames, "Denoising frames", process_image_denoise)
    process_video_frames_step(denoised_dir, cleaned_dir, frames, "Deblurring frames", process_image_deblur)
    progress.set_step(f"Generating x{multi}")
    progress.print_status()
    generate_frames(cleaned_dir, gen_dir, multi)
    final_frames_dir = gen_dir
    if fps < max_fps:
        progress.set_step("Blending frames")
        progress.print_status()
        final_frames_dir = blend_frames_for_fps(gen_dir, fps, max_fps)
    progress.set_step("Compiling video")
    progress.print_status()
    frames_to_video(final_frames_dir, output_path, fps,
                   audio_path if os.path.exists(audio_path) else None,
                   desc="Compiling video")
    shutil.rmtree(TEMP_DIR)

def process_video_full_frame_gen(video_path, output_path, multi=2, fps=None, upscale_factor=4):
    ensure_ffmpeg()
    original_fps, frame_count, width, height = get_video_info(video_path)
    min_fps = original_fps
    max_fps = original_fps * multi
    if fps is None:
        fps = max_fps
    elif fps < min_fps:
        print(f"Warning: Target FPS {fps:.2f} below minimum ({min_fps:.2f}). Using max: {max_fps:.2f}")
        fps = max_fps
    elif fps > max_fps:
        print(f"Warning: Target FPS {fps:.2f} exceeds maximum ({max_fps:.2f}). Using max: {max_fps:.2f}")
        fps = max_fps
    frames_dir = os.path.join(TEMP_DIR, "frames")
    denoised_dir = os.path.join(TEMP_DIR, "denoised")
    cleaned_dir = os.path.join(TEMP_DIR, "cleaned")
    upscaled_dir = os.path.join(TEMP_DIR, "upscaled")
    gen_dir = os.path.join(TEMP_DIR, "generated")
    audio_path = os.path.join(TEMP_DIR, "audio.aac")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    progress.set_step("Extracting frames")
    progress.print_status()
    extract_frames(video_path, frames_dir, desc="Extracting frames")
    extract_audio(video_path, audio_path)
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    process_video_frames_step(frames_dir, denoised_dir, frames, "Denoising frames", process_image_denoise)
    process_video_frames_step(denoised_dir, cleaned_dir, frames, "Deblurring frames", process_image_deblur)
    process_video_frames_step(cleaned_dir, upscaled_dir, frames, f"Upscaling frames (x{upscale_factor})", lambda img, step_bar=None: process_image_upscale(img, step_bar, upscale_factor))
    frames = sorted([f for f in os.listdir(upscaled_dir) if f.endswith('.png')])
    progress.set_step(f"Generating x{multi}")
    progress.print_status()
    generate_frames(upscaled_dir, gen_dir, multi)
    final_frames_dir = gen_dir
    if fps < max_fps:
        progress.set_step("Blending frames")
        progress.print_status()
        final_frames_dir = blend_frames_for_fps(gen_dir, fps, max_fps)
    sample_frame = cv2.imread(os.path.join(final_frames_dir, frames[0]))
    new_height, new_width = sample_frame.shape[:2]
    progress.set_step("Compiling video")
    progress.print_status()
    frames_to_video(final_frames_dir, output_path, fps,
                   audio_path if os.path.exists(audio_path) else None,
                   desc="Compiling video")
    shutil.rmtree(TEMP_DIR)

def process_video(video_path, output_path, mode, upscale_factor=4):
    ensure_ffmpeg()
    mode_steps = {
        'denoise': [("Denoising frames", process_image_denoise)],
        'deblur': [("Deblurring frames", process_image_deblur)],
        'upscale': [(f"Upscaling frames (x{upscale_factor})", lambda img, step_bar=None: process_image_upscale(img, step_bar, upscale_factor))],
        'clean': [
            ("Denoising frames", process_image_denoise),
            ("Deblurring frames", process_image_deblur),
        ],
        'full': [
            ("Denoising frames", process_image_denoise),
            ("Deblurring frames", process_image_deblur),
            (f"Upscaling frames (x{upscale_factor})", lambda img, step_bar=None: process_image_upscale(img, step_bar, upscale_factor)),
        ],
        'enhance': [("SUPIR Enhancing frames", process_image_enhance_super)],
    }
    if mode not in mode_steps:
        raise ValueError(f"Unknown mode: {mode}")
    original_fps, frame_count, width, height = get_video_info(video_path)
    audio_path = os.path.join(TEMP_DIR, "audio.aac")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    new_width, new_height = process_video_multistep(
        video_path, output_path, mode_steps[mode], audio_path
    )
    shutil.rmtree(TEMP_DIR)
    return new_width, new_height

def process_single_file(input_path, output_path, mode, multi=2, fps=None, upscale_factor=4, show_progress=True):
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")
    is_img = is_image(input_path)
    is_vid = is_video(input_path)
    if not is_img and not is_vid:
        raise ValueError(f"Unsupported format: {input_path.suffix}")
    frame_gen_modes = ['frame-gen', 'clean-frame-gen', 'full-frame-gen', 'enhance-frame-gen']
    if mode in frame_gen_modes and is_img:
        raise ValueError(f"Frame generation mode '{mode}' only works with videos, not images.")
    if output_path is None:
        output_path = generate_output_path(input_path, mode)
    output_p = Path(output_path)
    valid_extensions = IMAGE_EXTENSIONS if is_img else VIDEO_EXTENSIONS
    if output_p.suffix.lower() not in valid_extensions:
        output_path = str(output_p.with_suffix(input_path.suffix))
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    if is_vid:
        if mode == 'frame-gen':
            process_video_frame_gen(str(input_path), output_path, multi, fps)
        elif mode == 'clean-frame-gen':
            process_video_clean_frame_gen(str(input_path), output_path, multi, fps)
        elif mode == 'full-frame-gen':
            process_video_full_frame_gen(str(input_path), output_path, multi, fps, upscale_factor)
        elif mode == 'enhance-frame-gen':
            process_video_enhance_super_frame_gen(str(input_path), output_path, multi, fps)
        else:
            process_video(str(input_path), output_path, mode, upscale_factor)
    else:
        img = cv2.imread(str(input_path))
        if img is None:
            raise ValueError(f"Failed to read image: {input_path}")
        mode_steps = {
            'denoise': 1,
            'deblur': 1,
            'upscale': 1,
            'clean': 2,
            'full': 3,
            'enhance': 1,
        }
        num_steps = mode_steps.get(mode, 1)
        step_bar = StepProgressBar(num_steps, input_path.name)
        process_funcs = {
            'denoise': lambda i: process_image_denoise(i, step_bar),
            'deblur': lambda i: process_image_deblur(i, step_bar),
            'upscale': lambda i: process_image_upscale(i, step_bar, upscale_factor),
            'clean': lambda i: process_image_clean(i, step_bar),
            'full': lambda i: process_image_full(i, step_bar, upscale_factor),
            'enhance': lambda i: process_image_enhance_super(i, step_bar),
        }
        if mode not in process_funcs:
            raise ValueError(f"Unknown mode: {mode}")
        result = process_funcs[mode](img)
        step_bar.finish()
        success = cv2.imwrite(output_path, result)
        if not success:
            raise IOError(f"Failed to write image: {output_path}")
    return output_path

def process_multiple_files(input_paths, output_arg, mode, multi=2, fps=None, upscale_factor=4, overwrite=True):
    total_files = len(input_paths)
    processed = 0
    errors = 0
    output_folder = None
    single_file_output = None
    output_files = []

    if output_arg:
        output_arg = output_arg.strip()
        output_path = Path(output_arg)

        if output_path.suffix:
            if total_files == 1:
                single_file_output = output_arg
            else:
                parent = output_path.parent
                if parent and str(parent) != '.':
                    output_folder = str(parent / output_path.stem)
                else:
                    output_folder = output_path.stem
        elif output_arg.endswith('/') or output_arg.endswith('\\'):
            output_folder = output_arg
        else:
            if total_files == 1:
                single_file_output = output_arg
            else:
                output_folder = output_arg
    else:
        if total_files == 1:
            first_input = Path(input_paths[0])
            mode_suffix = get_mode_suffix(mode)
            single_file_output = str(first_input.parent / f"{first_input.stem}{mode_suffix}{first_input.suffix}")
        else:
            first_input = Path(input_paths[0])
            output_folder = str(first_input.parent / f"{first_input.stem}_{mode}")

    progress.start_batch(total_files)
    print(f"\n{'='*60}")
    print(f"Processing {total_files} file(s) - Mode: {mode}")
    print(f"Model mode: {get_model_mode().upper()}")
    print(f"{'='*60}\n")

    for i, input_path in enumerate(input_paths, 1):
        try:
            if single_file_output:
                output_path = single_file_output
            elif output_folder:
                input_p = Path(input_path)
                mode_suffix = get_mode_suffix(mode)
                os.makedirs(output_folder, exist_ok=True)
                output_path = os.path.join(output_folder, f"{input_p.stem}{mode_suffix}{input_p.suffix}")
            else:
                output_path = None

            progress.start_file(input_path)
            progress.set_step("Loading")
            progress.print_status(force=True)
            process_single_file(input_path, output_path, mode, multi, fps, upscale_factor)
            elapsed = progress.finish_file()
            progress.set_step(f"Done ({elapsed:.1f}s)")
            progress.print_status(force=True)
            progress.print_newline()
            processed += 1
            if output_path:
                output_files.append(output_path)
        except Exception as e:
            progress.set_step(f"Error: {str(e)[:30]}")
            progress.print_status(force=True)
            progress.print_newline()
            errors += 1

    print(f"\n{'='*60}")
    print(f"Completed: {processed}/{total_files} files")
    print(f"Total time: {progress.get_elapsed_str()}")
    if errors > 0:
        print(f"Errors: {errors}")
    print(f"{'='*60}")

    return output_files

def process_file_pairs(file_pairs, mode, multi=2, fps=None, upscale_factor=4, file_type="file"):
    total_files = len(file_pairs)
    if total_files == 0:
        return

    processed = 0
    errors = 0

    progress.start_batch(total_files)
    print(f"\n{'='*60}")
    print(f"Processing {total_files} {file_type}(s) - Mode: {mode}")
    print(f"Model mode: {get_model_mode().upper()}")
    print(f"{'='*60}\n")

    for i, (input_path, output_path) in enumerate(file_pairs, 1):
        try:
            progress.start_file(input_path)
            progress.set_step("Loading")
            progress.print_status(force=True)
            process_single_file(input_path, output_path, mode, multi, fps, upscale_factor)
            elapsed = progress.finish_file()
            progress.set_step(f"Done ({elapsed:.1f}s)")
            progress.print_status(force=True)
            progress.print_newline()
            processed += 1
        except Exception as e:
            progress.set_step(f"Error: {str(e)[:30]}")
            progress.print_status(force=True)
            progress.print_newline()
            errors += 1

    print(f"\n{'='*60}")
    print(f"Completed: {processed}/{total_files} {file_type}(s)")
    print(f"Total time: {progress.get_elapsed_str()}")
    if errors > 0:
        print(f"Errors: {errors}")
    print(f"{'='*60}")

def show_info():
    print("\n" + "="*60)
    print("KLARITY - Image/Video Restoration Tool")
    print("="*60)
    print(f"\nPython: {sys.version.split()[0]}")
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB")
    print(f"\nffmpeg: {'Available' if shutil.which('ffmpeg') else 'NOT FOUND'}")
    print(f"\nCurrent model mode: {get_model_mode().upper()}")
    print("\nModels (Heavy):")
    heavy_paths = get_model_paths_for_mode(SCRIPT_DIR, 'heavy')
    for name, path in heavy_paths.items():
        status = "✓ Found" if os.path.exists(path) else "✗ Missing"
        size = ""
        if os.path.exists(path):
            size = f" ({os.path.getsize(path) / (1024*1024):.1f} MB)"
        print(f"  {name}: {status}{size}")
    print("\nModels (Lite):")
    lite_paths = get_model_paths_for_mode(SCRIPT_DIR, 'lite')
    for name, path in lite_paths.items():
        status = "✓ Found" if os.path.exists(path) else "✗ Missing"
        size = ""
        if os.path.exists(path):
            size = f" ({os.path.getsize(path) / (1024*1024):.1f} MB)"
        print(f"  {name}: {status}{size}")
    print("\n" + "="*60)

def auto_download_models_for_mode():
    current_mode = get_model_mode()
    if current_mode == 'super':
        return ensure_super_models(SCRIPT_DIR, prompt=False)
    model_paths = get_model_paths()
    missing = []
    for key, path in model_paths.items():
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            missing.append(key)
    if not missing:
        return True
    print(f"\nMissing {current_mode} models detected: {', '.join(missing)}")
    print(f"Auto-downloading {current_mode} models...\n")
    result = ensure_models(SCRIPT_DIR, model_paths, auto_download=True, prompt=False, mode=current_mode)
    if result:
        print(f"\nAll {current_mode} models ready!\n")
    else:
        print(f"\nFailed to download some models. Please check your internet connection.\n")
    return result

def download_models_command(mode=None):
    print("\n" + "="*60)
    if mode:
        print(f"Downloading all {mode} models...")
        set_model_mode(mode)
    else:
        print("Downloading all required models...")
    print("="*60 + "\n")
    current_mode = get_model_mode()
    if current_mode == 'super':
        result = ensure_super_models(SCRIPT_DIR, prompt=False)
        if result:
            print("\n" + "="*60)
            print("All SUPER models downloaded successfully!")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("Failed to download SUPER models. Please check your connection.")
            print("="*60)
        return
    model_paths = get_model_paths()
    result = ensure_models(SCRIPT_DIR, model_paths, auto_download=True, prompt=False, mode=current_mode)
    if result:
        print("\n" + "="*60)
        print(f"All {current_mode} models downloaded successfully!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("Some models failed to download. Please check your connection.")
        print("="*60)

def interactive_mode():
    global device
    print("\n" + "="*60)
    print("KLARITY - Image/Video Restoration Tool")
    print("="*60)
    mode = select_model_mode()
    set_model_mode(mode)
    print(f"\nModel mode set to: {mode.upper()}")
    if mode == 'super':
        ensure_super_models(SCRIPT_DIR, prompt=True)
    else:
        check_and_download_models()
    if os.path.exists(TEMP_DIR):
        print(f"\nCleaning up leftover temp folder from previous session...")
        try:
            shutil.rmtree(TEMP_DIR)
            print("Temp folder cleaned successfully.")
        except Exception as e:
            print(f"Warning: Could not clean temp folder: {e}")
    if mode == 'super':
        image_modes = {
            '1': 'enhance',
        }
        video_modes = {
            '1': 'enhance',
            '2': 'enhance-frame-gen',
        }
    else:
        image_modes = {
            '1': 'denoise',
            '2': 'deblur',
            '3': 'upscale',
            '4': 'clean',
            '5': 'full',
        }
        video_modes = {
            '1': 'denoise',
            '2': 'deblur',
            '3': 'upscale',
            '4': 'clean',
            '5': 'full',
            '6': 'frame-gen',
            '7': 'clean-frame-gen',
            '8': 'full-frame-gen',
        }
    device_selected = device is not None
    while True:
        while True:
            print("\n" + "-"*60)
            print("INPUT SELECTION")
            print("-"*60)
            print("\nEnter input path(s) - separate multiple paths with spaces")
            print("Use quotes for paths with spaces, or 'q' to quit:")
            input_arg = input("> ").strip()
            if input_arg.lower() in ['q', 'quit', 'exit']:
                print("\nExiting Klarity. Goodbye!")
                return
            if not input_arg:
                print("Error: No input provided. Please enter at least one path or 'q' to quit.")
                continue
            parsed_paths = parse_multiple_paths(input_arg)
            if not parsed_paths:
                print("Error: Could not parse any paths from input. Please try again.")
                continue
            categorized = categorize_multiple_paths(parsed_paths)
            display_path_summary(categorized)
            input_paths = categorized['all_valid_files']
            if not input_paths:
                print("\n" + "-"*40)
                has_errors = categorized['not_exist'] or categorized['not_supported'] or categorized['invalid']
                if has_errors:
                    print("Options:")
                    print("  1. Enter different paths")
                    print("  2. Exit")
                    retry_choice = input("\nSelect option (1 or 2): ").strip()
                    if retry_choice == '1':
                        continue
                    else:
                        print("\nExiting Klarity. Goodbye!")
                        return
                else:
                    print("Please enter valid paths.")
                    continue
            else:
                break
        input_entries = []
        for orig_path, valid_files in categorized['valid']:
            entry = {
                'original_path': orig_path,
                'is_folder': Path(orig_path).is_dir(),
                'images': [f for f in valid_files if is_image(f)],
                'videos': [f for f in valid_files if is_video(f)],
                'name': Path(orig_path).name if Path(orig_path).is_dir() else Path(orig_path).stem
            }
            input_entries.append(entry)
        input_entries.sort(key=lambda x: x['name'].lower())
        total_image_inputs = sum(1 for e in input_entries if e['images'])
        total_video_inputs = sum(1 for e in input_entries if e['videos'])
        total_images = sum(len(e['images']) for e in input_entries)
        total_videos = sum(len(e['videos']) for e in input_entries)
        print(f"\n" + "-"*60)
        print("FILES TO PROCESS")
        print("-"*60)
        print(f"  Total inputs: {len(input_entries)}")
        print(f"  Images: {total_images} (from {total_image_inputs} input{'s' if total_image_inputs != 1 else ''})")
        print(f"  Videos: {total_videos} (from {total_video_inputs} input{'s' if total_video_inputs != 1 else ''})")
        process_images = False
        process_videos = False
        while True:
            if total_images > 0:
                choice = input("\nProcess images? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    process_images = True
                else:
                    print("  → Images ignored")
            if total_videos > 0:
                choice = input("\nProcess videos? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    process_videos = True
                else:
                    print("  → Videos ignored")
            if not process_images and not process_videos:
                print("\nError: Nothing selected to process.")
                retry = input("Would you like to try again? (y/n): ").strip().lower()
                if retry in ['y', 'yes']:
                    continue
                else:
                    print("\nExiting Klarity. Goodbye!")
                    return
            else:
                break
        image_mode = None
        image_upscale_factor = 4
        if process_images:
            print("\n" + "-"*60)
            print("IMAGE SETTINGS")
            print("-"*60)
            if mode == 'super':
                print("\nSelect mode for images:")
                print("  1. Enhance (SUPIR AI restoration)")
                while True:
                    choice = input("\nSelect mode (1): ").strip()
                    if choice == '1' or choice == '':
                        image_mode = 'enhance'
                        break
                    else:
                        print(f"Error: Invalid choice '{choice}'. Please enter 1.")
            else:
                print("\nSelect mode for images:")
                print("  1. Denoise (remove noise)")
                print("  2. Deblur (remove blur)")
                print("  3. Upscale (4x upscaling)")
                print("  4. Clean (denoise + deblur)")
                print("  5. Full (denoise + deblur + upscale)")
                while True:
                    choice = input("\nSelect mode (1-5): ").strip()
                    if choice in image_modes:
                        image_mode = image_modes[choice]
                        break
                    else:
                        print(f"Error: Invalid choice '{choice}'. Please enter a number from 1 to 5.")
            if image_mode in ['upscale', 'full']:
                print("\nUpscale factor options:")
                print("  4 = 4x upscale (default)")
                print("  2 = 2x upscale")
                while True:
                    upscale_choice = input("Select upscale factor (2 or 4, default 4): ").strip()
                    if upscale_choice == '' or upscale_choice == '4':
                        image_upscale_factor = 4
                        break
                    elif upscale_choice == '2':
                        image_upscale_factor = 2
                        break
                    else:
                        print(f"Error: Invalid choice '{upscale_choice}'. Please enter 2 or 4.")
        video_mode = None
        multi = 2
        fps = None
        video_upscale_factor = 4
        if process_videos:
            print("\n" + "-"*60)
            print("VIDEO SETTINGS")
            print("-"*60)
            if mode == 'super':
                print("\nSelect mode for videos:")
                print("  1. Enhance (SUPIR AI restoration)")
                print("  2. Enhance + Frame Generation")
                while True:
                    choice = input("\nSelect mode (1-2): ").strip()
                    if choice == '1' or choice == '':
                        video_mode = 'enhance'
                        break
                    elif choice == '2':
                        video_mode = 'enhance-frame-gen'
                        break
                    else:
                        print(f"Error: Invalid choice '{choice}'. Please enter 1 or 2.")
                if video_mode == 'enhance-frame-gen':
                    print("\nFrame multiplier options:")
                    print("  2 = double the frame rate")
                    print("  4 = quadruple the frame rate")
                    while True:
                        multi_choice = input("Select multiplier (2 or 4, default 2): ").strip()
                        if multi_choice == '' or multi_choice == '2':
                            multi = 2
                            break
                        elif multi_choice == '4':
                            multi = 4
                            break
                        else:
                            print(f"Error: Invalid choice '{multi_choice}'. Please enter 2 or 4.")
            else:
                print("\nSelect mode for videos:")
                print("  1. Denoise (remove noise)")
                print("  2. Deblur (remove blur)")
                print("  3. Upscale (4x upscaling)")
                print("  4. Clean (denoise + deblur)")
                print("  5. Full (denoise + deblur + upscale)")
                print("  6. Frame Generation (interpolate video frames)")
                print("  7. Clean + Frame Generation")
                print("  8. Full + Frame Generation")
                while True:
                    choice = input("\nSelect mode (1-8): ").strip()
                    if choice in video_modes:
                        video_mode = video_modes[choice]
                        break
                    else:
                        print(f"Error: Invalid choice '{choice}'. Please enter a number from 1 to 8.")
            if video_mode in ['upscale', 'full']:
                print("\nUpscale factor options:")
                print("  4 = 4x upscale (default)")
                print("  2 = 2x upscale")
                while True:
                    upscale_choice = input("Select upscale factor (2 or 4, default 4): ").strip()
                    if upscale_choice == '' or upscale_choice == '4':
                        video_upscale_factor = 4
                        break
                    elif upscale_choice == '2':
                        video_upscale_factor = 2
                        break
                    else:
                        print(f"Error: Invalid choice '{upscale_choice}'. Please enter 2 or 4.")
            if video_mode == 'full-frame-gen':
                print("\nUpscale factor options:")
                print("  4 = 4x upscale (default)")
                print("  2 = 2x upscale")
                while True:
                    upscale_choice = input("Select upscale factor (2 or 4, default 4): ").strip()
                    if upscale_choice == '' or upscale_choice == '4':
                        video_upscale_factor = 4
                        break
                    elif upscale_choice == '2':
                        video_upscale_factor = 2
                        break
                    else:
                        print(f"Error: Invalid choice '{upscale_choice}'. Please enter 2 or 4.")
            if video_mode in ['frame-gen', 'clean-frame-gen', 'full-frame-gen']:
                print("\nFrame multiplier options:")
                print("  2 = double the frame rate")
                print("  4 = quadruple the frame rate")
                while True:
                    multi_choice = input("Select multiplier (2 or 4, default 2): ").strip()
                    if multi_choice == '' or multi_choice == '2':
                        multi = 2
                        break
                    elif multi_choice == '4':
                        multi = 4
                        break
                    else:
                        print(f"Error: Invalid choice '{multi_choice}'. Please enter 2 or 4.")
                single_video_inputs = [e for e in input_entries if e['videos']]
                video_count = sum(len(e['videos']) for e in single_video_inputs)
                if video_count == 1:
                    video_path = single_video_inputs[0]['videos'][0]
                    original_fps, _, _, _ = get_video_info(video_path)
                    min_fps = original_fps
                    max_fps = original_fps * multi
                    fps_input = input(f"Target FPS [{min_fps:.2f}/{max_fps:.2f}] (press Enter for max): ").strip()
                    if fps_input:
                        try:
                            fps = float(fps_input)
                        except ValueError:
                            print("Invalid FPS, using auto max")
                else:
                    fps_input = input("Target FPS (press Enter for auto max): ").strip()
                    if fps_input:
                        try:
                            fps = float(fps_input)
                        except ValueError:
                            print("Invalid FPS, using auto max")
        print("\n" + "-"*60)
        print("OUTPUT SETTINGS")
        print("-"*60)
        print("\nPress Enter for auto-default, or enter custom path.")
        print("For folders: outputs to a new folder with processed files.")
        print("For files: outputs next to original with suffix.\n")
        image_input_idx = 0
        video_input_idx = 0
        input_outputs = {}
        for entry in input_entries:
            input_path = entry['original_path']
            is_folder = entry['is_folder']
            input_name = entry['name']
            images = entry['images'] if process_images else []
            videos = entry['videos'] if process_videos else []
            input_outputs[input_path] = {'images': None, 'videos': None}
            if images:
                image_input_idx += 1
                image_count = len(images)
                tracker = f"images [{image_input_idx}/{total_image_inputs}]"
                display_name = input_name if is_folder else Path(input_path).name
                if is_folder:
                    default_output = str(Path(input_path).parent / f"{input_name}_{image_mode}")
                    print(f"\n{tracker} \"{display_name}/\" ({image_count} images)")
                    print(f"  Auto: {default_output}/")
                else:
                    if image_count == 1:
                        default_output = str(Path(input_path).parent / f"{input_name}_{image_mode}{Path(input_path).suffix}")
                        print(f"\n{tracker} \"{display_name}\"")
                        print(f"  Auto: {default_output}")
                    else:
                        default_output = str(Path(input_path).parent / f"{input_name}_{image_mode}")
                        print(f"\n{tracker} \"{display_name}\" ({image_count} images)")
                        print(f"  Auto: {default_output}/")
                user_output = input("> ").strip()
                if user_output:
                    if user_output.startswith('"') and user_output.endswith('"'):
                        user_output = user_output[1:-1]
                    input_outputs[input_path]['images'] = user_output
                else:
                    input_outputs[input_path]['images'] = default_output
            if videos:
                video_input_idx += 1
                video_count = len(videos)
                tracker = f"videos [{video_input_idx}/{total_video_inputs}]"
                display_name = input_name if is_folder else Path(input_path).name
                if is_folder:
                    default_output = str(Path(input_path).parent / f"{input_name}_{video_mode}")
                    print(f"\n{tracker} \"{display_name}/\" ({video_count} videos)")
                    print(f"  Auto: {default_output}/")
                else:
                    if video_count == 1:
                        default_output = str(Path(input_path).parent / f"{input_name}_{video_mode}{Path(input_path).suffix}")
                        print(f"\n{tracker} \"{display_name}\"")
                        print(f"  Auto: {default_output}")
                    else:
                        default_output = str(Path(input_path).parent / f"{input_name}_{video_mode}")
                        print(f"\n{tracker} \"{display_name}\" ({video_count} videos)")
                        print(f"  Auto: {default_output}/")
                user_output = input("> ").strip()
                if user_output:
                    if user_output.startswith('"') and user_output.endswith('"'):
                        user_output = user_output[1:-1]
                    input_outputs[input_path]['videos'] = user_output
                else:
                    input_outputs[input_path]['videos'] = default_output
        if not device_selected:
            print("\n" + "-"*60)
            print("DEVICE SELECTION")
            print("-"*60)
            select_device()
            device_selected = True
        else:
            print(f"\nUsing previously selected device: {device}")

        image_pairs = []
        video_pairs = []

        for entry in input_entries:
            input_path = entry['original_path']
            images = entry['images'] if process_images else []
            videos = entry['videos'] if process_videos else []

            if images:
                user_output = input_outputs[input_path]['images']
                for img_file in images:
                    output = generate_output_path(img_file, image_mode, output_arg=user_output)
                    image_pairs.append((img_file, output))

            if videos:
                user_output = input_outputs[input_path]['videos']
                for vid_file in videos:
                    output = generate_output_path(vid_file, video_mode, output_arg=user_output)
                    video_pairs.append((vid_file, output))

        if image_pairs:
            process_file_pairs(image_pairs, image_mode, multi=2, fps=None, upscale_factor=image_upscale_factor, file_type="image")

        if video_pairs:
            process_file_pairs(video_pairs, video_mode, multi, fps, upscale_factor=video_upscale_factor, file_type="video")

        print("\n" + "="*60)
        print("ALL PROCESSING COMPLETE!")
        print("="*60)
        print("\nWhat would you like to do next?")
        print("  1. Process again (start fresh)")
        print("  2. Exit")
        post_choice = input("\nSelect option (1 or 2): ").strip()
        if post_choice == '1':
            print("\nStarting fresh session...")
            if os.path.exists(TEMP_DIR):
                try:
                    shutil.rmtree(TEMP_DIR)
                except Exception:
                    pass
            continue
        else:
            print("\nExiting Klarity. Goodbye!")
            return

def main():
    global JSON_PROGRESS

    parser = argparse.ArgumentParser(
        description="KLARITY - Image/Video Restoration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python klarity.py                          # Launch GUI (default)
  python klarity.py cli                      # Interactive CLI mode
  python klarity.py denoise image.jpg        # Denoise image
  python klarity.py -lite denoise image.jpg  # Denoise with lite model
  python klarity.py -heavy upscale video.mp4 # Upscale with heavy model
  python klarity.py frame-gen video.mp4 --multi 2  # Frame interpolation
  python klarity.py -super enhance image.jpg # SUPIR AI restoration
  python klarity.py enhance image.jpg        # SUPIR AI restoration (auto-detects super)
        """
    )
    parser.add_argument('command', nargs='?', default='gui',
                       help="Command: gui (default), cli, denoise, deblur, upscale, clean, full, enhance, enhance-frame-gen, frame-gen, clean-frame-gen, full-frame-gen, info, download-models")
    parser.add_argument('input', nargs='?', help="Input file or folder")
    parser.add_argument('-o', '--output', help="Output file or folder")
    parser.add_argument('--multi', type=int, choices=[2, 4], default=2,
                       help="Frame multiplier for frame-gen (2 or 4)")
    parser.add_argument('--upscale', type=int, choices=[2, 4], default=4,
                       help="Upscale factor (2 or 4, default 4)")
    parser.add_argument('--fps', type=float, help="Target FPS for frame generation")
    parser.add_argument('--scale', type=float, choices=[0.5, 1.0, 2.0], default=1.0,
                       help="RIFE scale factor")
    parser.add_argument('--device', choices=['cpu', 'gpu', 'auto'], default='auto',
                       help="Device to use (cpu, gpu, or auto)")
    parser.add_argument('--cpu', action='store_true', help="Force CPU (legacy, same as --device cpu)")
    parser.add_argument('-heavy', action='store_true', help="Use heavy models (default, better quality)")
    parser.add_argument('-lite', action='store_true', help="Use lite models (faster, smaller)")
    parser.add_argument('-super', action='store_true', help="Use SUPER mode (SUPIR AI restoration, requires extra deps)")
    parser.add_argument('--json-progress', action='store_true', help="Output progress as JSON (for GUI)")
    args = parser.parse_args()

    JSON_PROGRESS = args.json_progress

    super_commands = ['enhance', 'enhance-frame-gen']
    if args.lite and args.heavy:
        print("Error: Cannot specify both -lite and -heavy flags")
        return
    if args.super and (args.lite or args.heavy):
        print("Error: Cannot combine -super with -lite or -heavy flags")
        return
    if args.command in super_commands and not args.lite and not args.heavy:
        set_model_mode('super')
    elif args.super:
        set_model_mode('super')
    elif args.lite:
        set_model_mode('lite')
    elif args.heavy:
        set_model_mode('heavy')
    else:
        set_model_mode('heavy')
    _mode = get_model_mode()
    if _mode == 'super':
        ensure_super_models(SCRIPT_DIR, prompt=False)

    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
            if not JSON_PROGRESS:
                print("Cleaned up leftover temporary folder.")
        except Exception as e:
            if not JSON_PROGRESS:
                print(f"Warning: Could not clean temp folder: {e}")

    if args.command == 'gui' or args.command is None:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            gui_path = os.path.join(script_dir, "gui.py")
            if os.path.exists(gui_path):
                from gui import main as gui_main
                gui_main()
            else:
                print("Error: gui.py not found. Please ensure gui.py is in the same directory.")
                print("Falling back to CLI mode...")
                interactive_mode()
        except ImportError as e:
            print(f"Error: Could not import GUI: {e}")
            print("Make sure PyQt5 is installed: pip install PyQt5")
            print("Falling back to CLI mode...")
            interactive_mode()
        return

    if args.command == 'cli':
        interactive_mode()
        return
    if args.command == 'info':
        show_info()
        return
    if args.command == 'download-models':
        download_models_command()
        return
    if not args.input:
        print("Error: Input path required")
        print("Usage: python klarity.py <command> <input> [-o output]")
        print("\nCommands: denoise, deblur, upscale, clean, full, enhance, frame-gen, clean-frame-gen, full-frame-gen, enhance-frame-gen")
        print("\nModel modes: -heavy (default), -lite, -super")
        return
    if not auto_download_models_for_mode():
        print("Cannot continue without required models.")
        return
    force_cpu = args.cpu or args.device == 'cpu'
    device_type = None if args.device == 'auto' else args.device
    get_device(force_cpu=force_cpu, device_type=device_type)
    input_paths = get_files(args.input)
    if not input_paths:
        if os.path.exists(args.input):
            input_paths = [args.input]
        else:
            print(f"Error: Input not found: {args.input}")
            return

    result = process_multiple_files(input_paths, args.output, args.command, args.multi, args.fps, args.upscale)

    if JSON_PROGRESS and result:
        output_file = result[0] if isinstance(result, list) else result
        json_output = json.dumps({
            'percent': 100,
            'step': 'Complete',
            'output': output_file
        })
        print(json_output)
        sys.stdout.flush()

if __name__ == '__main__':
    main()
