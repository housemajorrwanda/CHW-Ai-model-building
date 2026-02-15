import torch

MODEL_NAME = "microsoft/trocr-base-handwritten"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
ENABLE_PREPROCESSING = True
DENOISE = True
ENHANCE_CONTRAST = True
DESKEW = True
OUTPUT_DIR = "./output"
SAVE_JSON = True
SAVE_CSV = True
