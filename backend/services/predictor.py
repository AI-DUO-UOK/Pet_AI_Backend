import torch
from backend.core.config import DEVICE

def predict(model, class_names, tensor):
    tensor = tensor.to(DEVICE)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.nn.functional.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)

    return {
        "class": class_names[pred.item()],
        "confidence": float(conf.item())
    }