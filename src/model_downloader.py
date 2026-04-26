import os
import sys
import re
import shutil
import zipfile
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

_model_mode = 'heavy'

GDRIVE_FILE_IDS_HEAVY = {
    'deblur': '1S0PVRbyTakYY9a82kujgZLbMihfNBLfC',
    'denoise': '14Fht1QQJ2gMlk4N1ERCRuElg8JfjrWWR',
    'rife': '1ZKjcbmt1hypiFprJPIKW0Tt0lr_2i7bg',
}

GDRIVE_FILE_IDS_LITE = {
    'deblur': '1Fr2QadtDCEXg6iwWX8OzeZLbHOx2t5Bj',
    'denoise': '1lsByk21Xw-6aW7epCwOQxvm6HYCQZPHZ',
    'rife': '1e9Qb4rm20UAsO7h9VILDwrpvTSHWWW8b',
}

GDRIVE_FILE_IDS_HEAVY_UPSCALE = {
    'upscale': '1EioFq5-mKmv1uqta_Byd9cgXp9SU3zjj',
}

GDRIVE_FILE_IDS_SUPER = {
    'enhancer': '1ohCIBV_RAej1zuiidHph5qXNuD4GRxO3',
}

DIRECT_URLS_LITE = {
    'upscale': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth',
}

MODEL_INFO = {
    'deblur': {
        'name_heavy': 'NAFNet-GoPro-width64 (Deblur Heavy)',
        'name_lite': 'NAFNet-GoPro-width32 (Deblur Lite)',
        'size_heavy': '~260 MB',
        'size_lite': '~67 MB',
        'target_heavy': 'deblur-heavy.pth',
        'target_lite': 'deblur-lite.pth',
    },
    'denoise': {
        'name_heavy': 'NAFNet-SIDD-width64 (Denoise Heavy)',
        'name_lite': 'NAFNet-SIDD-width32 (Denoise Lite)',
        'size_heavy': '~440 MB',
        'size_lite': '~111 MB',
        'target_heavy': 'denoise-heavy.pth',
        'target_lite': 'denoise-lite.pth',
    },
    'upscale': {
        'name_heavy': 'Real-HAT-GAN-sharper (Upscale Heavy)',
        'name_lite': 'Real-ESRGAN general-x4v3 (Upscale Lite)',
        'size_heavy': '~167 MB',
        'size_lite': '~16 MB',
        'target_heavy': 'upscale-heavy.pth',
        'target_lite': 'upscale-lite.pth',
    },
    'rife': {
        'name_heavy': 'RIFE v4.25 (Frame Gen Heavy)',
        'name_lite': 'RIFE v4.17 (Frame Gen Lite)',
        'size_heavy': '~21 MB',
        'size_lite': '~10 MB',
        'target_heavy': 'framegen-heavy.pkl',
        'target_lite': 'framegen-lite.pkl',
    },
    'enhancer': {
        'name': 'SUPIR-v0Q (SUPER Enhancer)',
        'size': '~5 GB',
        'target': 'SUPIR-v0Q.ckpt',
    },
}

TEMP_DOWNLOAD_FOLDER = "the_temp_folder"

def set_model_mode(mode):
    global _model_mode
    if mode not in ('heavy', 'lite', 'super'):
        raise ValueError(f"Invalid model mode: {mode}. Must be 'heavy', 'lite', or 'super'.")
    _model_mode = mode

def get_model_mode():
    return _model_mode

def check_internet_connection():
    try:
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return False

def cleanup_temp_folder(script_dir):
    temp_path = os.path.join(script_dir, TEMP_DOWNLOAD_FOLDER)
    if os.path.exists(temp_path):
        print(f"Cleaning up incomplete download folder: {temp_path}")
        try:
            shutil.rmtree(temp_path)
        except Exception as e:
            print(f"Warning: Could not remove temp folder: {e}")

def get_temp_download_folder(script_dir):
    temp_path = os.path.join(script_dir, TEMP_DOWNLOAD_FOLDER, "downloads")
    os.makedirs(temp_path, exist_ok=True)
    return temp_path

def download_with_progress(url, output_path, desc="Downloading"):
    try:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 // total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                sys.stdout.write(f"\r{desc}: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)")
                sys.stdout.flush()
        urllib.request.urlretrieve(url, output_path, progress_hook)
        print()
        return True
    except Exception as e:
        print(f"\nDownload failed: {e}")
        return False

def download_gdrive_file_requests(file_id, output_path, desc="Downloading"):
    if not HAS_REQUESTS:
        return None
    try:
        session = requests.Session()
        url = f'https://drive.google.com/uc?export=download&id={file_id}'
        response = session.get(url, timeout=30)
        uuid_match = re.search(r'name="uuid" value="([^"]+)"', response.text)
        uuid = uuid_match.group(1) if uuid_match else None
        if uuid:
            download_url = 'https://drive.usercontent.google.com/download'
            params = {
                'id': file_id,
                'export': 'download',
                'confirm': 't',
                'uuid': uuid
            }
            response = session.get(download_url, params=params, stream=True, timeout=30)
        else:
            response = session.get(url, stream=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(32768):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = min(100, downloaded * 100 // total_size)
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    sys.stdout.write(f"\r{desc}: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)")
                    sys.stdout.flush()
        print()
        return True
    except requests.exceptions.ConnectionError:
        print(f"\nConnection error - please check your internet connection")
        return False
    except requests.exceptions.Timeout:
        print(f"\nConnection timeout - please try again")
        return False
    except Exception as e:
        print(f"\nDownload failed: {e}")
        return False

def download_gdrive_file_urllib(file_id, output_path, desc="Downloading"):
    try:
        url = f'https://drive.google.com/uc?export=download&id={file_id}'
        try:
            response = urllib.request.urlopen(url, timeout=30)
            content = response.read()
            if b'confirm=' in content and b'href=' in content:
                href_match = re.search(rb'href="([^"]*confirm=([^"&]+)[^"]*)"', content)
                if href_match:
                    confirm_url = href_match.group(1).decode('utf-8')
                    if confirm_url.startswith('/'):
                        confirm_url = 'https://drive.google.com' + confirm_url
                    response = urllib.request.urlopen(confirm_url, timeout=300)
                    content = response.read()
            with open(output_path, 'wb') as f:
                f.write(content)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"File not found on Google Drive")
            else:
                print(f"HTTP Error {e.code}: {e.reason}")
            return False
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def download_gdrive_file(file_id, output_path, desc="Downloading"):
    print(f"{desc} from Google Drive (ID: {file_id[:10]}...)")
    if HAS_REQUESTS:
        result = download_gdrive_file_requests(file_id, output_path, desc)
        if result:
            return True
    print("Trying fallback method...")
    return download_gdrive_file_urllib(file_id, output_path, desc)

def extract_rife_zip(zip_path, target_dir, mode='heavy'):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            flownet_path = None
            for f in file_list:
                if f.endswith('flownet.pkl'):
                    flownet_path = f
                    break
            if not flownet_path:
                print("Error: flownet.pkl not found in RIFE zip")
                return False
            os.makedirs(target_dir, exist_ok=True)
            target_filename = f'framegen-{mode}.pkl'
            target_path = os.path.join(target_dir, target_filename)
            with zf.open(flownet_path) as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Extracted: {flownet_path} -> {target_path}")
            return True
    except zipfile.BadZipFile:
        print("Error: Invalid zip file")
        return False
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False

def get_model_paths_for_super(script_dir):
    models_dir = os.path.join(script_dir, 'models', 'enhancer')
    return {
        'enhancer': os.path.join(models_dir, 'SUPIR-v0Q.ckpt'),
    }

def download_gdrive_large_file(file_id, output_path, desc="Downloading"):
    try:
        import gdown
        url = f'https://drive.google.com/uc?id={file_id}'
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        print(f"{desc} via gdown (ID: {file_id[:10]}...)")
        gdown.download(url, output_path, quiet=False)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000000:
            with open(output_path, 'rb') as f:
                header = f.read(10)
            if header.startswith(b'<!') or header.startswith(b'<htm'):
                os.remove(output_path)
                print("Direct download returned HTML, trying folder-based download...")
                folder_url = f'https://drive.google.com/drive/folders/1yELzm5SvAi9e7kPcO_jPp2XkTs4vK6aR'
                temp_dir = os.path.join(os.path.dirname(output_path), 'gdown_temp')
                os.makedirs(temp_dir, exist_ok=True)
                gdown.download_folder(folder_url, output=temp_dir, quiet=False)
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        if f == 'SUPIR-v0Q.ckpt':
                            src = os.path.join(root, f)
                            with open(src, 'rb') as fh:
                                header = fh.read(10)
                            if not header.startswith(b'<!') and not header.startswith(b'<htm'):
                                shutil.copy2(src, output_path)
                            os.remove(src)
                            break
                shutil.rmtree(temp_dir, ignore_errors=True)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000000:
                    return True
                return False
            return True
        return False
    except ImportError:
        print("gdown not installed. Trying fallback method...")
        return download_gdrive_file(file_id, output_path, desc)
    except Exception as e:
        print(f"gdown download failed: {e}")
        print("Trying fallback method...")
        return download_gdrive_file(file_id, output_path, desc)

def ensure_super_models(script_dir, prompt=True):
    cleanup_temp_folder(script_dir)
    model_paths = get_model_paths_for_super(script_dir)
    existing = []
    missing = []
    for key, path in model_paths.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 1000:
                existing.append(key)
            else:
                missing.append(key)
        else:
            missing.append(key)
    if not missing:
        print("All SUPER models found!")
        return True
    print(f"\nMissing SUPER models: {len(missing)}")
    for key in missing:
        info = MODEL_INFO.get(key, {})
        name = info.get('name', key)
        size = info.get('size', 'unknown size')
        print(f"  - {name} ({size})")
    if not check_internet_connection():
        print("\n" + "="*60)
        print("ERROR: No internet connection detected!")
        print("Cannot download SUPER models. Please connect to the internet and try again.")
        print("="*60)
        return False
    if prompt:
        print("\nWould you like to download the missing SUPER models now? (y/n)")
        try:
            response = input("> ").strip().lower()
            if response != 'y':
                print("Download cancelled.")
                return False
        except EOFError:
            pass
    temp_dir = get_temp_download_folder(script_dir)
    for key in missing:
        info = MODEL_INFO.get(key, {})
        name = info.get('name', key)
        size = info.get('size', 'unknown')
        print(f"\n{'='*60}")
        print(f"Downloading: {name} ({size})")
        print(f"{'='*60}")
        try:
            enhancer_dir = os.path.join(script_dir, 'models', 'enhancer')
            os.makedirs(enhancer_dir, exist_ok=True)
            target_path = os.path.join(enhancer_dir, 'SUPIR-v0Q.ckpt')
            file_id = GDRIVE_FILE_IDS_SUPER.get(key)
            if file_id:
                temp_path = os.path.join(temp_dir, 'SUPIR-v0Q.ckpt')
                success = download_gdrive_large_file(file_id, temp_path, f"Downloading {name}")
                if success:
                    shutil.copy2(temp_path, target_path)
                    os.remove(temp_path)
                    print(f"Successfully downloaded: {name}")
                else:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    print(f"Failed to download: {name}")
                    return False
            else:
                print(f"No download source for: {name}")
                return False
        except KeyboardInterrupt:
            print("\n\nDownload interrupted by user.")
            cleanup_temp_folder(script_dir)
            return False
        except Exception as e:
            print(f"Error downloading {key}: {e}")
            return False
    cleanup_temp_folder(script_dir)
    model_paths = get_model_paths_for_super(script_dir)
    for key, path in model_paths.items():
        if not os.path.exists(path) or os.path.getsize(path) < 1000:
            print(f"\nWarning: SUPER model {key} still missing after download attempt.")
            return False
    print("\nAll SUPER models downloaded successfully!")
    return True

def get_model_paths_for_mode(script_dir, mode=None):
    if mode is None:
        mode = _model_mode
    models_dir = os.path.join(script_dir, 'models')
    return {
        'deblur': os.path.join(models_dir, f'deblur-{mode}.pth'),
        'denoise': os.path.join(models_dir, f'denoise-{mode}.pth'),
        'upscale': os.path.join(models_dir, f'upscale-{mode}.pth'),
        'rife': os.path.join(models_dir, f'framegen-{mode}.pkl'),
    }

def download_model(model_key, models_dir, temp_dir, mode=None):
    if mode is None:
        mode = _model_mode
    info = MODEL_INFO.get(model_key)
    if not info:
        print(f"Unknown model: {model_key}")
        return False
    name = info.get(f'name_{mode}', info.get('name_heavy', model_key))
    size = info.get(f'size_{mode}', info.get('size_heavy', 'unknown'))
    print(f"\n{'='*60}")
    print(f"Downloading: {name} ({size})")
    print(f"Mode: {mode.upper()}")
    print(f"{'='*60}")
    target_filename = info.get(f'target_{mode}', info.get('target_heavy', f'{model_key}-{mode}.pth'))
    target_path = os.path.join(models_dir, target_filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if mode == 'heavy':
        gdrive_ids = {**GDRIVE_FILE_IDS_HEAVY, **GDRIVE_FILE_IDS_HEAVY_UPSCALE}
        direct_urls = {}
    else:
        gdrive_ids = GDRIVE_FILE_IDS_LITE
        direct_urls = DIRECT_URLS_LITE
    if model_key == 'rife':
        zip_path = os.path.join(temp_dir, f'rife_{mode}_download.zip')
        if gdrive_ids.get(model_key):
            success = download_gdrive_file(
                gdrive_ids[model_key],
                zip_path,
                f"Downloading {name}"
            )
            if success:
                target_dir = models_dir
                success = extract_rife_zip(zip_path, target_dir, mode)
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                return success
        return False
    elif model_key == 'upscale':
        file_id = gdrive_ids.get(model_key)
        if file_id:
            return download_gdrive_file(file_id, target_path, f"Downloading {name}")
        elif direct_urls.get(model_key):
            return download_with_progress(direct_urls[model_key], target_path, f"Downloading {name}")
        return False
    else:
        file_id = gdrive_ids.get(model_key)
        if file_id:
            return download_gdrive_file(file_id, target_path, f"Downloading {name}")
        return False

def check_models_exist(models_dir, model_paths):
    existing = []
    missing = []
    for key, path in model_paths.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 1000:
                existing.append(key)
            else:
                missing.append(key)
        else:
            missing.append(key)
    return existing, missing

def ensure_models(script_dir, model_paths, auto_download=True, prompt=True, mode=None):
    if mode is None:
        mode = _model_mode
    cleanup_temp_folder(script_dir)
    mode_paths = get_model_paths_for_mode(script_dir, mode)
    existing, missing = check_models_exist(script_dir, mode_paths)
    if not missing:
        print(f"All {mode} models found!")
        return True
    print(f"\nMissing {mode} models: {len(missing)}")
    for key in missing:
        info = MODEL_INFO.get(key, {})
        name = info.get(f'name_{mode}', info.get('name_heavy', key))
        size = info.get(f'size_{mode}', info.get('size_heavy', 'unknown size'))
        print(f"  - {name} ({size})")
    if not auto_download:
        return False
    if not check_internet_connection():
        print("\n" + "="*60)
        print("ERROR: No internet connection detected!")
        print("Cannot download models. Please connect to the internet and try again.")
        print("="*60)
        return False
    if prompt:
        print("\nWould you like to download the missing models now? (y/n)")
        try:
            response = input("> ").strip().lower()
            if response != 'y':
                print("Download cancelled. Please download models manually.")
                return False
        except EOFError:
            pass
    temp_dir = get_temp_download_folder(script_dir)
    success_count = 0
    for key in missing:
        try:
            if download_model(key, os.path.join(script_dir, 'models'), temp_dir, mode):
                success_count += 1
                print(f"Successfully downloaded: {MODEL_INFO.get(key, {}).get(f'name_{mode}', key)}")
            else:
                print(f"Failed to download: {MODEL_INFO.get(key, {}).get(f'name_{mode}', key)}")
        except KeyboardInterrupt:
            print("\n\nDownload interrupted by user.")
            cleanup_temp_folder(script_dir)
            return False
        except Exception as e:
            print(f"Error downloading {key}: {e}")
    cleanup_temp_folder(script_dir)
    mode_paths = get_model_paths_for_mode(script_dir, mode)
    existing, missing = check_models_exist(script_dir, mode_paths)
    if missing:
        print(f"\nWarning: {len(missing)} model(s) still missing after download attempt.")
        print("Please try downloading manually or check your internet connection.")
        return False
    print(f"\nAll {mode} models downloaded successfully!")
    return True

if __name__ == '__main__':
    print("Model Downloader Test")
    print("="*60)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(script_dir, "models")
    for mode in ['heavy', 'lite']:
        print(f"\n--- Testing {mode.upper()} mode ---")
        model_paths = get_model_paths_for_mode(script_dir, mode)
        for key, path in model_paths.items():
            print(f"  {key}: {path}")
    print("\n" + "="*60)
    print("Select model mode:")
    print("  1. Heavy (default, better quality)")
    print("  2. Lite (faster, smaller models)")
    choice = input("> ").strip()
    if choice == '2':
        set_model_mode('lite')
    else:
        set_model_mode('heavy')
    print(f"\nSelected mode: {get_model_mode().upper()}")
    model_paths = get_model_paths_for_mode(script_dir, get_model_mode())
    ensure_models(script_dir, model_paths, auto_download=True, prompt=True)
