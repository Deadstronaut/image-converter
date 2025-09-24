# scripts/models/BiRefNet_dynamic/BiRefNet_config.py

import torch.nn as nn

class BiRefNetConfig(nn.Module):
    model_type = "SegformerForSemanticSegmentation"

    def __init__(self, bb_pretrained=False, **kwargs):
        super().__init__()
        self.bb_pretrained = bb_pretrained
        for k, v in kwargs.items():
            setattr(self, k, v)

