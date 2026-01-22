#! /usr/bin/env python3

# This demo shows how to use MSS for artificial intelligence.  For
# this demo, we'll be using a simple object detection task: see if
# there's a cat on your monitor.  I mean, displayed on the monitor,
# not sitting on your laptop.
#
# This demo is not meant to be an introduction to AI or computer
# vision.  We assume you have an understanding of the basics of AI,
# and of PyTorch.
#
# Object Detection
# ================
#
# An object detector is a different beast than an object classifier.
# Object classifiers are a common introduction to computer vision.
# These will look at a picture that has a single foreground object,
# front and center, and try to identify what type of object this is: a
# cat, person, bicycle, etc.
#
# An object detector looks at an image and identifies _multiple
# objects_ within it.  Instead of assigning a single label to the
# whole image, saying "this is a picture of a cat", it might say
# "there is a cat here, and a bicycle over there," and provide some
# basic information about each one.  This is, for instance, what a
# self-driving car uses to identify what it's seeing on its cameras.
#
# For this demo, we want to tell if a cat is anywhere on the screen,
# not if the whole screen is a picture of a cat.  That means that we
# want to use an detector, not a classifier.
#
# The detector will find any number of objects.  For each object it
# detects, a typical detector produces three pieces of information:
#
# - A *label*, which identifies _what kind of object_ the detector
#   believes it has found.  Labels are represented internally as
#   integers that map to a fixed list of categories the model was
#   trained on (for example, "cat," "bicycle," or "person").
#
# - A *position*, usually given as a bounding box.  A bounding box
#   describes _where_ the object appears in the image, using a small
#   set of numbers that define a rectangle around it.
#
# - A *score*, which indicates how confident the model is in that
#   detection.  Higher scores mean the model is more confident; lower
#   scores mean it is less confident.  The score is a relative
#   confidence signal, not a calibrated probability, and it should not
#   be interpreted as a percentage or compared across different
#   models.
#
# Most modern object detectors follow this same basic pattern, even if
# their internal architectures differ.  In the Torchvision model used
# in this demo, these results are returned as parallel one-dimensional
# tensors: one tensor of labels, one tensor of bounding boxes, and one
# tensor of scores.  Each index across these tensors refers to the
# same detected object.
#
# The Model We're Using
# =====================
#
# In this demo, we use a pre-trained object-detection model provided
# by PyTorch's Torchvision library: `fasterrcnn_resnet50_fpn_v2`, with
# weights `FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1`.
#
# This name is long, but each part reflects a piece of a larger system
# built up over many years of research and engineering.
#
# *Faster R-CNN* is the overall object-detection architecture.
# Introduced in 2015, it builds on earlier R-CNN variants and
# established the now-common two-stage approach to detection: first
# proposing regions that might contain objects, then classifying and
# refining those regions.  This basic structure is still widely used
# today.
#
# *ResNet-50* refers to the convolutional neural network used as the
# _backbone_.  ResNet itself was originally developed for image
# classification, but its feature-extraction layers proved broadly
# useful and are now reused in many vision systems.  In this model,
# ResNet-50 converts raw pixels into _features_ - numerical
# representations that capture visual patterns such as edges,
# textures, shapes, and object parts - while the original
# classification layers are replaced by the detection-specific
# components of Faster R-CNN.
#
# *FPN*, or Feature Pyramid Network, is a later addition that
# addresses one of the main challenges in object detection: scale.  It
# combines high-level, semantically rich features (good at recognizing
# _what_ is present) with lower-level, higher-resolution features
# (better at preserving _where_ things are).  By layering these ideas
# on top of the backbone, the model can detect both large and small
# objects more reliably.
#
# The *v2* suffix indicates a newer Torchvision implementation that
# incorporates refinements from more recent research and practice.  In
# particular, it follows a standardized training and configuration
# setup described in the 2021 paper "Benchmarking Detection Transfer
# Learning with Vision Transformers".  Despite the paper's title, this
# model does *not* use Transformers; it uses a ResNet-50 backbone, but
# benefits from the same modernized training approach.
#
# Finally, *COCO_V1* indicates that the model was trained on the COCO
# dataset, a widely used community benchmark for object detection.
# COCO contains hundreds of thousands of labeled images covering 80
# common object categories (such as people, animals, and vehicles),
# along with a small number of additional placeholder categories that
# appear as "N/A" in the model metadata.
#
# Performance
# ===========
#
# The biggest determinant of performance is whether the model runs on
# a GPU or on the CPU.  GPUs are extremely well-suited to AI
# workloads, and PyTorch’s strongest and most mature GPU support today
# is through NVIDIA’s CUDA platform.
#
# With a CUDA-capable GPU, this demo’s main loop typically runs in
# around 100 ms per frame (about 10 fps).  When run on the CPU, the
# same work takes roughly 5000 ms per frame (about 0.2 fps).
#
# Screen size has little effect on performance.  The preprocessing
# stage scales the captured image to a fixed size, so the slow part -
# running the neural network - takes roughly the same amount of time
# regardless of the original screen resolution.


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
    """Return the unique labels, ordered by descending score.

    If you have a person (0.67), dog (0.98), tv (0.88), dog (0.71),
    you'll get back the labels for dog, tv, person, in that order.

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
    # Prefer CUDA if available.  PyTorch’s CUDA backend is the most
    # mature and consistently supported option, and can be tens of
    # times faster than running the same model on the CPU.
    #
    # Other GPU backends (such as Apple’s MPS, AMD ROCm, or Intel XPU)
    # exist, but support and configuration vary widely across systems.
    # Since this demo hasn’t been tested on those platforms, it
    # conservatively falls back to the CPU when CUDA is not available.
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

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
