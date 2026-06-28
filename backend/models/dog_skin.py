import torch
import torch.nn as nn
from torchvision import models
from backend.core.config import DOG_SKIN_MODEL, DEVICE

class_names = [
    "Dermatitis",
    "Fungal_infections",
    "Healthy",
    "Hypersensitivity",
    "demodicosis",
    "ringworm"
]

def load_model():
    model = models.resnet50(pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, len(class_names))

    checkpoint = torch.load(DOG_SKIN_MODEL, map_location=DEVICE)
    model.load_state_dict(checkpoint['model_state_dict'])

    model.to(DEVICE)
    model.eval()

    return model, class_names