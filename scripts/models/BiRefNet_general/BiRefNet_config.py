# scripts/models/BiRefNet_dynamic/BiRefNet_general_config.py

import torch

try:
    from transformers import PretrainedConfig
except ImportError:
    class PretrainedConfig:
        pass

class BiRefNetConfig(PretrainedConfig):
    model_type = "SegformerForSemanticSegmentation"

    def __init__(self, bb_pretrained=False, **kwargs):
        self.bb_pretrained = bb_pretrained
        super().__init__(**kwargs)
        self.bb_pretrained = bb_pretrained
        super().__init__(**kwargs)
