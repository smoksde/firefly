import os
import random
import time
import datetime
import numpy as np
import pandas as pd
import albumentations as A
import cv2
from PIL import Image
from glob import glob
from tqdm import tqdm
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from utils import (
    seeding,
    create_dir,
    shuffling,
    epoch_time,
    EarlyStopping,
    save_checkpoint,
    load_checkpoint,
)
from metrics import DiceLoss, DiceCELoss
from model import build_unet


def load_data(dataset_path, split=0.2, subset=0.2):
    images = sorted(glob(os.path.join(dataset_path, "images", "*.jpg")))
    masks = sorted(glob(os.path.join(dataset_path, "masks", "*.png")))
    assert len(images) == len(masks)

    train_x, valid_x, train_y, valid_y = train_test_split(
        images, masks, test_size=split, random_state=42
    )
    train_x, test_x, train_y, test_y = train_test_split(
        train_x, train_y, test_size=split, random_state=42
    )

    if subset < 1.0:
        n_train = max(1, int(len(train_x) * subset))
        n_valid = max(1, int(len(valid_x) * subset))
        n_test = max(1, int(len(test_x) * subset))
        train_x, train_y = train_x[:n_train], train_y[:n_train]
        valid_x, valid_y = valid_x[:n_valid], valid_y[:n_valid]
        test_x, test_y = test_x[:n_test], test_y[:n_test]

    return (train_x, train_y), (valid_x, valid_y), (test_x, test_y)


class DATASET(Dataset):
    def __init__(self, images_path, masks_path, size, colormap, transform=None):
        super().__init__()

        self.images_path = images_path
        self.masks_path = masks_path
        self.size = size
        self.colormap = colormap
        self.transform = transform
        self.n_samples = len(images_path)

    def __getitem__(self, index):
        image = cv2.imread(self.images_path[index], cv2.IMREAD_COLOR)
        mask = cv2.imread(self.masks_path[index], cv2.IMREAD_COLOR)

        if self.transform is not None:
            augmentations = self.transform(image=image, mask=mask)
            image = augmentations["image"]
            mask = augmentations["mask"]

        image = cv2.resize(image, self.size)
        image = np.transpose(image, (2, 0, 1))
        image = image / 255.0

        mask = cv2.resize(mask, self.size)
        mask = np.array(mask, dtype=np.uint8)

        mask_class = np.zeros(mask.shape[:2], dtype=np.uint8)
        for idx, color in enumerate(self.colormap):
            mask_class[np.all(mask == color, axis=-1)] = idx

        return image, mask_class

    def __len__(self):
        return self.n_samples


def train(model, loader, optimizer, loss_fn, device):
    model.train()
    epoch_loss = 0.0

    use_amp = device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    for i, (x, y) in enumerate(loader):
        x = x.to(device, dtype=torch.float32)
        y = y.to(device, dtype=torch.long)

        with torch.autocast(device_type=device.type, enabled=use_amp):
            y_pred = model(x)
            loss = loss_fn(y_pred, y)

        optimizer.zero_grad()
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        epoch_loss += loss.item()

    epoch_loss = epoch_loss / len(loader)
    return epoch_loss


def evaluate(model, loader, loss_fn, device):
    model.eval()
    epoch_loss = 0.0

    with torch.no_grad():
        for i, (x, y) in enumerate(loader):
            x = x.to(device, dtype=torch.float32)
            y = y.to(device, dtype=torch.long)

            y_pred = model(x)
            loss = loss_fn(y_pred, y)
            epoch_loss += loss.item()

        epoch_loss = epoch_loss / len(loader)
        return epoch_loss


if __name__ == "__main__":
    """Seeding"""
    seeding(42)

    """ Directories """
    path = "files"
    create_dir(path)

    """ Hyperparameters """
    image_w = 128  # 256
    image_h = 128  # 256
    size = (image_w, image_h)
    batch_size = 16  # 16
    start_epoch = 0
    num_epochs = 30
    lr = 1e-2
    early_stopping_patience = 50
    checkpoint_path = f"{path}/checkpoint.pth"
    dataset_path = "dataset/weed_augmented"
    colormap = [
        [0, 0, 0],  # Background
        [0, 0, 128],  # Class 1
        [0, 128, 0],  # Class 2
    ]
    num_classes = len(colormap)

    """ Device """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print("GPU device name:", torch.cuda.get_device_name(0))
    else:
        print(
            "No GPU found, running on CPU. Consider reducing batch size or dataset size."
        )

    """ Dataset """
    (train_x, train_y), (valid_x, valid_y), (test_x, test_y) = load_data(dataset_path)
    data_str = f"Dataset Size: Train: {len(train_x)} - Valid: {len(valid_x)} - Test: {len(test_x)}"
    print(data_str)

    """ Data augmentation: Transforms """
    transform = A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.Affine(translate_percent=0.05, scale=(0.9, 1.1), rotate=(-10, 10), p=0.5),
            A.RandomBrightnessContrast(p=0.2),
            A.GaussianBlur(p=0.2),
            A.CoarseDropout(
                p=0.2,
                num_holes_range=(1, 8),
                hole_height_range=(1, 24),
                hole_width_range=(1, 24),
            ),
        ],
        is_check_shapes=False,
    )

    """ Dataset and loader """
    # On CPU, reduce num_workers to 0 to avoid multiprocessing overhead
    num_workers = 4 if device.type == "cuda" else 0
    pin_memory = device.type == "cuda"

    train_dataset = DATASET(train_x, train_y, size, colormap, transform=transform)
    valid_dataset = DATASET(valid_x, valid_y, size, colormap, transform=None)

    train_loader = DataLoader(
        dataset=train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )

    valid_loader = DataLoader(
        dataset=valid_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )

    """ Model """
    model = build_unet(num_classes=num_classes)
    model = model.to(device)

    optimizer = torch.optim.SGD(
        model.parameters(), lr=lr, momentum=0.9, weight_decay=0.0005
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, "min", patience=5)
    early_stopping = EarlyStopping(patience=early_stopping_patience, verbose=True)

    """ Load checkpoint if exists """
    model, optimizer, start_epoch = load_checkpoint(model, optimizer, checkpoint_path)

    loss_fn = DiceCELoss(
        num_classes=num_classes, dice_weight=1.0, ce_weight=1.0, ignore_index=-1
    )
    loss_name = "Dice + Cross Entropy Loss"
    print(f"Optimizer: SGD - Loss: {loss_name}")

    """ Training the model """
    for epoch in range(start_epoch + 1, num_epochs, 1):
        start_time = time.time()

        train_loss = train(model, train_loader, optimizer, loss_fn, device)
        valid_loss = evaluate(model, valid_loader, loss_fn, device)

        end_time = time.time()
        epoch_mins, epoch_secs = epoch_time(start_time, end_time)

        current_lr = optimizer.param_groups[0]["lr"]
        data_str = (
            f"[{epoch:02}/{num_epochs:02}] | "
            f"Epoch Time: {epoch_mins}m {epoch_secs}s | "
            f"LR: {current_lr:.2e} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val. Loss: {valid_loss:.4f}"
        )
        print(data_str)

        scheduler.step(valid_loss)
        early_stopping(valid_loss, model, optimizer, epoch, checkpoint_path)

        if early_stopping.early_stop:
            print("Early stopping triggered. Training will stop.")
            break
