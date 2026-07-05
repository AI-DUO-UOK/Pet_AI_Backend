import torch
import torch.nn as nn
from torchvision import models
from core.config import CAT_SKIN_MODEL, DEVICE

class_names = ["Flea_Allergy", "Health", "Ringworm", "Scabies"]

def load_model():
    model = models.resnet50(pretrained=False)
    model.fc = nn.Linear(model.fc.in_features, len(class_names))

    checkpoint = torch.load(CAT_SKIN_MODEL, map_location=DEVICE)
    model.load_state_dict(checkpoint['model_state_dict'])

    model.to(DEVICE)
    model.eval()

    return model, class_names