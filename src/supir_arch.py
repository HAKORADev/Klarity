import os
import sys
import copy

import numpy as np
import cv2
import torch


SUPIR_ROOT = '/home/z/my-project/SUPIR'

SUPIR_POSITIVE_PROMPT = (
    'Cinematic, High Contrast, highly detailed, taken using a Canon EOS R camera, '
    'hyper detailed photo - realistic maximum detail, 32k, Color Grading, ultra HD, '
    'extreme meticulous detailing, skin pore detailing, hyper sharpness, perfect without deformations.'
)
SUPIR_NEGATIVE_PROMPT = (
    'painting, oil painting, illustration, drawing, art, sketch, oil painting, cartoon, '
    'CG Style, 3D render, unreal engine, blurring, dirty, messy, worst quality, low quality, '
    'frames, watermark, signature, jpeg artifacts, deformed, lowres, over-smooth'
)


class SUPIRProcessor:
    def __init__(self, models_dir):
        self.models_dir = models_dir
        self.enhancer_dir = os.path.join(models_dir, 'enhancer')
        self.model = None
        self._loaded = False

    def load_model(self, device):
        if self._loaded:
            return
        sys.path.insert(0, SUPIR_ROOT)
        os.environ['CKPT_PTH_DIR'] = self.enhancer_dir
        ckpt_pth_path = os.path.join(SUPIR_ROOT, 'CKPT_PTH.py')
        if os.path.exists(ckpt_pth_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("CKPT_PTH", ckpt_pth_path)
            ckpt_pth_mod = importlib.util.module_from_spec(spec)
            clip1_path = os.path.join(self.enhancer_dir, 'clip-vit-large-patch14')
            clip2_path = os.path.join(self.enhancer_dir, 'open_clip_pytorch_model.bin')
            if not os.path.exists(clip1_path):
                clip1_path = None
            if not os.path.exists(clip2_path):
                clip2_path = None
            ckpt_pth_mod.SDXL_CLIP1_PATH = clip1_path
            ckpt_pth_mod.SDXL_CLIP2_CKPT_PTH = clip2_path
            ckpt_pth_mod.LLAVA_CLIP_PATH = None
            ckpt_pth_mod.LLAVA_MODEL_PATH = None
            sys.modules['CKPT_PTH'] = ckpt_pth_mod
            spec.loader.exec_module(ckpt_pth_mod)
        from omegaconf import OmegaConf
        from SUPIR.util import create_SUPIR_model, load_state_dict, HWC3, upscale_image
        self._HWC3 = HWC3
        self._upscale_image = upscale_image
        config_path = os.path.join(SUPIR_ROOT, 'options', 'SUPIR_v0.yaml')
        config = OmegaConf.load(config_path)
        supir_ckpt_path = os.path.join(self.enhancer_dir, 'SUPIR-v0Q.ckpt')
        sdxl_names = ['sd_xl_base_1.0_0.9vae.safetensors', 'sd_xl_base_1.0.safetensors']
        sdxl_ckpt_path = None
        for sdxl_name in sdxl_names:
            candidate = os.path.join(self.enhancer_dir, sdxl_name)
            if os.path.exists(candidate):
                sdxl_ckpt_path = candidate
                break
        if sdxl_ckpt_path is not None:
            config.SDXL_CKPT = sdxl_ckpt_path
        elif config.SDXL_CKPT and not os.path.exists(config.SDXL_CKPT):
            config.SDXL_CKPT = None
        config.SUPIR_CKPT_Q = supir_ckpt_path
        config.SUPIR_CKPT_F = supir_ckpt_path
        config.SUPIR_CKPT = None
        print("Loading SUPIR model (v0Q)...")
        model = create_SUPIR_model(config_path, SUPIR_sign='Q')
        if sdxl_ckpt_path is not None:
            print("Loading SDXL weights...")
            state_dict = load_state_dict(sdxl_ckpt_path, location='cpu')
            model.load_state_dict(state_dict, strict=False)
            del state_dict
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("Loading SUPIR-v0Q weights...")
        state_dict = load_state_dict(supir_ckpt_path, location='cpu')
        model.load_state_dict(state_dict, strict=False)
        del state_dict
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        model.ae_dtype = torch.bfloat16
        model.model.dtype = torch.float16
        model = model.to(device)
        model.first_stage_model.denoise_encoder_s1 = copy.deepcopy(model.first_stage_model.denoise_encoder)
        model.eval()
        self.model = model
        self._loaded = True
        print("SUPIR model loaded successfully.")

    @torch.no_grad()
    def enhance(self, img_bgr, device, step_bar=None):
        if step_bar:
            step_bar.update("SUPIR enhancing...")
        else:
            print("SUPIR enhancing...")
        import einops
        from SUPIR.util import HWC3, upscale_image
        input_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        input_rgb = upscale_image(input_rgb, 1, unit_resolution=32, min_size=1024)
        h, w = input_rgb.shape[:2]
        LQ = (np.array(input_rgb).astype(np.float32) / 255.0) * 2 - 1
        LQ = torch.tensor(LQ, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0).to(device)[:, :3, :, :]
        captions = ['']
        samples = self.model.batchify_sample(
            LQ,
            captions,
            num_steps=50,
            restoration_scale=-1.0,
            s_churn=5,
            s_noise=1.003,
            cfg_scale=7.5,
            control_scale=1.0,
            seed=1234,
            num_samples=1,
            p_p=SUPIR_POSITIVE_PROMPT,
            n_p=SUPIR_NEGATIVE_PROMPT,
            color_fix_type='Wavelet',
            use_linear_CFG=True,
            use_linear_control_scale=False,
            cfg_scale_start=4.0,
            control_scale_start=0.0,
        )
        x_samples = (einops.rearrange(samples, 'b c h w -> b h w c') * 127.5 + 127.5)
        x_samples = x_samples.cpu().numpy().round().clip(0, 255).astype(np.uint8)
        result_rgb = x_samples[0]
        result_rgb = cv2.resize(result_rgb, (1024, 1024), interpolation=cv2.INTER_LANCZOS4)
        result_bgr = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
        return result_bgr
