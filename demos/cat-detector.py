#! /usr/bin/env python3

import itertools
import time

# You'll need to "pip install mss numpy pillow".  Additionally, you'll
# need to install PyTorch and TorchVision, and the best way to do that
# can vary depending on your system.  Often, "pip install torch
# torchvision" will be sufficient, but you can get specific
# instructions at <https://pytorch.org/get-started/locally/>.
import numpy as np
from PIL import Image
import torch
import torchvision.models.detection
import torchvision.transforms.v2

import mss


def top_unique_labels(labels, scores):
    """Return the unique labels, ordered by score descending.

    In other words, if you have a person (0.67), dog (0.98), tv
    (0.88), dog (0.71), you'll get back the labels for dog, tv,
    person, in that order.

    The labels are a 1d tensor of integers, which are identifiers for
    model-specific categories, such as indices into
    weights.meta["categories"].

    The scores are a parallel 1d tensor of the same size of floats: in
    other words, score[0] is the score of label[0].
    """
    uniq, inv = torch.unique(labels, return_inverse=True)
    max_per = torch.full((uniq.numel(),), -torch.inf, device=scores.device, dtype=scores.dtype)
    max_per.scatter_reduce_(0, inv, scores, reduce="amax")
    order = torch.argsort(max_per, descending=True)
    return uniq[order]


# We run the entire program in inference mode.  This is telling
# PyTorch to not bother tracking data that's only useful for training
# a neural net.
@torch.inference_mode()
def main():
    # Use CUDA if it's installed and available.  This is much faster
    # than doing all the work on the CPU.
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # The first time you run this demo, Torchvision will download a
    # 167 MByte DNN.  This is cached in ~/.cache/torch/hub/checkpoints
    # on Unix; not sure where it's cached on other platforms.
    weights = torchvision.models.detection.FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=weights).to(device).eval()
    preprocess = weights.transforms()

    model_labels = weights.meta["categories"]
    cat_label = model_labels.index("cat")

    score_thresh = 0.60
    img_long_side = 960
    min_area_frac = 0.001  # Fraction of image

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor

        img_area = monitor["width"] * monitor["height"]
        min_box_area = min_area_frac * img_area

        cat_has_been_visible = False
        elapsed_per_frame_running_avg = None
        time_last_frame = None

        for frame_number in itertools.count():
            time_this_frame = time.monotonic()
            if time_last_frame is not None:
                elapsed_this_frame = time_this_frame - time_last_frame
                if frame_number < 5:
                    # We don't try to keep a moving average until the
                    # pipeline has warmed up.
                    elapsed_per_frame_running_avg = elapsed_this_frame
                else:
                    elapsed_per_frame_running_avg = elapsed_per_frame_running_avg * 0.9 + elapsed_this_frame * 0.1
            time_last_frame = time_this_frame

            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            # We explicitly convert it to a tensor here, even though
            # Torchvision can also convert it in the preprocess step.
            # This is so that we send it to the GPU to do the
            # preprocessing; PIL images are always on the CPU.
            img_tensor = torchvision.transforms.v2.functional.pil_to_tensor(img).to(device)

            x = preprocess(img_tensor)  # tensor CxHxW
            pred = model([x])[0]

            labels = pred["labels"]
            scores = pred["scores"]
            boxes = pred["boxes"]

            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

            # Find the score of the highest-scoring cat that's large
            # enough, even if it's not high enough to register the
            # detector.  We always log that.
            cat_mask = (labels == cat_label) & (areas >= min_box_area)
            if cat_mask.any():
                cat_score = scores[cat_mask].max().item()
            else:
                cat_score = 0.0

            cat_in_frame = cat_score >= score_thresh
            cat_status_changed = cat_in_frame != cat_has_been_visible
            if cat_status_changed:
                cat_has_been_visible = cat_in_frame

            if not cat_in_frame:
                # Find all objects that score sufficiently well.  We
                # log them if there's no cat to talk about.
                mask = (scores >= score_thresh) & (areas >= min_box_area)
                if mask.any():
                    show_labels = top_unique_labels(labels[mask], scores[mask])
                else:
                    show_labels = torch.empty((0,), dtype=labels.dtype)

            if elapsed_per_frame_running_avg is not None:
                # Record the score of the most cat-like image for
                # logging purposes
                cat_scores = scores[labels == cat_label]
                if cat_scores.any():
                    best = float(cat_scores.max())
                else:
                    best = 0.0

                status_line_time = time.strftime("%H:%M:%S", time.localtime())
                if cat_in_frame:
                    status_line_msg = f"Meow!  Hello kitty-cat!"
                else:
                    status_line_msg = "no cats"
                    if show_labels.shape[0] != 0:
                        label_words = [model_labels[i] for i in show_labels.cpu()]
                        label_words = [w for w in label_words if w != "N/A"]
                        status_line_msg += f":{','.join(label_words)}"
                        if len(status_line_msg) > 31:
                            status_line_msg = status_line_msg[:28] + "..."
                status_line = (f"{status_line_time} {frame_number:4d} "
                               f"{elapsed_per_frame_running_avg * 1000:5.0f} ms/frame "
                               f"| {status_line_msg:31s} (cat score={best:.2f})")
                print(f"\r{status_line}", end="\n" if cat_status_changed else "")


if __name__ == "__main__":
    main()
