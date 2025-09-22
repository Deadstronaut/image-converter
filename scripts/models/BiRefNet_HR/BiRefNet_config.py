# scripts/models/BiRefNet_HR/BiRefNet_config.py

from transformers import PretrainedConfig

class BiRefNetConfig(PretrainedConfig):
    model_type = "SegformerForSemanticSegmentation"

    def __init__(self, bb_pretrained=False, **kwargs):
        self.bb_pretrained = bb_pretrained
        super().__init__(**kwargs)

