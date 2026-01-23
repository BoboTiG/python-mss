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
# workloads, and PyTorch's strongest and most mature GPU support today
# is through NVIDIA's CUDA platform.
#
# Screen size has little effect on performance.  The preprocessing
# stage scales the captured image to a fixed size, so the slow part -
# running the neural network - takes roughly the same amount of time
# regardless of the original screen resolution.
#
# With a CUDA-capable GPU, this demo's main loop typically runs in
# around 100 ms per frame (about 10 fps).  When run on the CPU, the
# same work takes roughly 5000 ms per frame (about 0.2 fps).
#
# FIXME Categorize
# ================
#
# The first time you run this demo, Torchvision will download a
# 167 MByte DNN.  This is cached in ~/.cache/torch/hub/checkpoints
# on Unix.  I'm not sure where it's cached on other platforms, but
# it will tell you.


import itertools
import time

# You'll need to "pip install mss pillow".  Additionally, you'll
# need to install PyTorch and TorchVision, and the best way to do that
# can vary depending on your system.  Often, "pip install torch
# torchvision" will be sufficient, but you can get specific
# instructions at <https://pytorch.org/get-started/locally/>.
from PIL import Image
import torch
import torchvision.models.detection
import torchvision.transforms.v2

import mss

# The model will identify objects even if they only vaguely look like
# something.  It also tell us a score of how certain it is, on a scale
# from 0 to 1.  To prevent false positives, we set a threshold and
# ignore any results below it.  The score doesn't have any real
# external meaning: to pick the cutoff, you just try different images
# and get a sense of what seems about right.
SCORE_THRESH = 0.60

# If an image is too small, then it's got a pretty decent chance of
# being a false positive: it's hard to tell if a Discord or Slack
# reaction icon is a cat or something different.  We ignore any
# results that are too small to be reliable.  Here, this cutoff is
# 0.1% of the whole monitor (about 1.5 cm square on a 27" monitor).
MIN_AREA_FRAC = 0.001  # Fraction of image

def top_unique_labels(labels, scores):
    """Return the unique labels, ordered by descending score.

    If you have a person (0.67), dog (0.98), tv (0.88), dog (0.71),
    you'll get back the labels for dog, tv, person, in that order.
    """

    # Find the set of unique labels.
    # `uniq` contains each distinct label once.
    # `inv` maps each original label to its index in `uniq`.
    #
    # Example:
    #   labels = [person, dog, tv, dog]
    #   uniq   = [person, dog, tv]
    #   inv    = [0,      1,   2,  1]
    uniq, inv = torch.unique(labels, return_inverse=True)

    # Create a tensor to hold the maximum score seen for each unique
    # label.  We initialize to -inf so any real score will replace it.
    max_per = torch.full(
        (uniq.numel(),),
        -torch.inf,
        device=scores.device,
        dtype=scores.dtype,
    )

    # For each element in `scores`, reduce it into `max_per` using
    # `inv` as an index map, taking the maximum score per label.
    #
    # After this, max_per[i] is the highest score associated with
    # uniq[i].
    max_per.scatter_reduce_(0, inv, scores, reduce="amax")

    # Sort the unique labels by their maximum score, highest first.
    order = torch.argsort(max_per, descending=True)

    # Return the unique labels in score-ranked order.
    return uniq[order]


# We run the entire program in inference mode.  This is telling
# PyTorch to not bother tracking data that's only useful for training
# a neural net.
@torch.inference_mode()
def main():
    # Prefer CUDA if available.  PyTorch's CUDA backend is the most
    # mature and consistently supported option, and can be tens of
    # times faster than running the same model on the CPU.
    #
    # Other GPU backends (such as Apple's MPS, AMD ROCm, or Intel XPU)
    # exist, but support and configuration vary widely across systems.
    # Since this demo hasn't been tested on those platforms, it
    # conservatively falls back to the CPU when CUDA is not available.
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    # Neural networks, often just called *models*, have two aspects to
    # them: the *architecture*, and the *weights*.  The architecture
    # is the layout of the neural network: what the different units
    # are, how they're connected, and so forth.  The weights are the
    # results of training that neural network; they're numbers saying
    # how much the units in the network influence each other.
    #
    # The same architecture can be trained on different data sets for
    # different purposes.  Different companies might use the exact
    # same object detector architecture for different purposes: a
    # company making a photo editing app might train the model to
    # recognize faces, smiles, or closed eyes for auto-enhancement,
    # while a wildlife research group could train the same
    # architecture to identify animals in wilderness camera photos.
    #
    # The weights are specific to the architecture: you can't plug
    # weights from a training run with the ResNet50 architecture into
    # a Visual Transformers architecture.
    #
    # As described in the comments at the top of the file, we're using
    # the fasterrcnn_resnet50_fpn_v2 architecture, and the weights
    # obtained by training it with the COCO dataset.  Plugging those
    # weights into the architecture produces our model.
    weights = torchvision.models.detection.FasterRCNN_ResNet50_FPN_V2_Weights.COCO_V1
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(weights=weights).to(device).eval()

    # When you train a model, you almost always want to pre-process
    # your input data.  It's important that when you use that model
    # later, you do the same kind of pre-processing.  Otherwise, it'd
    # be like learning a language from slow, carefully-enunciated
    # speech, and then getting dropped right into conversations on a
    # subway.
    #
    # For the model we're using, the preprocessing is to scale the
    # input image to a consistent size, and to normalize its range
    # (kinda similar to the "Auto" filter on your phone).
    # Fortunately, for its pretrained models, Torchvision gives us
    # an easy way to get the correct preprocessing function.
    preprocess = weights.transforms()

    # The labels ("what type of object is this") that the model gives
    # us are just integers; for this model, they're from 0 to 90.  The
    # English words describing them ("cat") are in a list, stored in
    # the weight's metadata.
    model_labels = weights.meta["categories"]
    cat_label = model_labels.index("cat")

    with mss.mss() as sct:
        monitor = sct.monitors[1]

        img_area = monitor["width"] * monitor["height"]
        # FIXME verify whether the ROI boxes are relative to the
        # original or preprocessed image.
        min_box_area = MIN_AREA_FRAC * img_area

        # We start a new line of the log if the cat visibility status
        # changes.  That way, your terminal will show essentially a
        # log of all the times when a cat appeared or vanished.
        cat_has_been_visible = False

        # Track an exponential moving average of how long each frame
        # takes, essentially an FPS counter.
        elapsed_per_frame_moving_avg = None

        # When was the last frame?
        time_last_frame = None

        for frame_number in itertools.count():
            # Do all the work to keep the frame timer.
            time_this_frame = time.monotonic()
            if time_last_frame is not None:  # Skip the first loop
                elapsed_this_frame = time_this_frame - time_last_frame
                if frame_number < 5:
                    # We don't try to keep a moving average until the
                    # pipeline has warmed up for a few frames: the
                    # times are too variable before PyTorch has gotten
                    # a sense of the inputs we're sending it, and we
                    # don't want those initial outlies to affect the
                    # EMA.  Instead, we just show the most recent
                    # frame's number.
                    elapsed_per_frame_moving_avg = elapsed_this_frame
                else:
                    # The exponential moving average we track is based
                    # 90% on the old average, and 10% on the most
                    # recent frame.  If you do the math, each frame's
                    # timing has half as much influence every 7 frames
                    # or so.
                    elapsed_per_frame_moving_avg = elapsed_per_frame_moving_avg * 0.9 + elapsed_this_frame * 0.1
            time_last_frame = time_this_frame

            # Grab the screenshot.
            sct_img = sct.grab(monitor)

            # We transfer the image from MSS to PyTorch by going
            # through a Pillow Image.  There are faster ways to do
            # this transfer, but here, the vast bulk of the time is
            # occupied by the AI work, so we just use the most
            # convenient mechanism.
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            # We explicitly convert it to a tensor here, even though
            # Torchvision can also convert it in the preprocess step.
            # This is so that we send it to the GPU before we do the
            # preprocessing: PIL Images are always on the CPU, and
            # doing the preprocessing on the GPU is much faster.
            #
            # Most image APIs, including MSS, use an array layout of
            # [height, width, channels].  In MSS, the ScreenShot.bgra
            # data follows this convention, even though it's exposed
            # as a flat bytes object.
            #
            # In contrast, most AI frameworks expect images in
            # [channels, height, width] order.  The pil_to_tensor
            # helper performs this rearrangement for us.
            img_tensor = torchvision.transforms.v2.functional.pil_to_tensor(img).to(device)

            # Do the preprocessing stages that the trained model
            # expects; see the comment where we define preprocess.
            # The traditional name for inputs to a neural net is "x",
            # because AI programmers aren't terribly imaginative.
            x = preprocess(img_tensor)
            # In most AI networks, the model expects to take an array
            # of inputs, and will return an array of outputs.  This is
            # because it's _much_ more efficient to operate on batches
            # of inputs than on individual inputs, because of how the
            # matrix math works.  For instance, banks will use batches
            # of transactions in AIs to flag transactions for review
            # as potentially fraudulent.  Because of that design, we
            # need to provide the model our input as a batch of one
            # image, rather than a single image by itself.  That's
            # what the unsqueeze does: it adds a new dimension of
            # length 1 to the beginning of the input.  Also, the
            # output will be in a batch, so we just take the first
            # element, hence the [0].
            pred = model(x.unsqueeze(0))[0]

            # The value of pred is a dict, giving us the labels,
            # scores, and bounding boxes.  See the comments at the top
            # of the file for more information.
            labels = pred["labels"]
            scores = pred["scores"]
            boxes = pred["boxes"]

            # We only want to allow detections that are large enough
            # to be reliable; see the comments on MIN_AREA_FRAC for
            # more information.  Here, we compute the areas of all the
            # boxes we got, using operations that work on all the
            # detected objects in parallel.
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

            # Find the score of the highest-scoring cat that's large
            # enough, even if it's not high enough to register as
            # sufficiently certain for our program.  We always log
            # that, as the "cat score".
            cat_mask = (labels == cat_label) & (areas >= min_box_area)
            if cat_mask.any():
                cat_score = scores[cat_mask].max().item()
            else:
                cat_score = 0.0

            # Is there a cat on the screen?
            cat_in_frame = cat_score >= SCORE_THRESH
            # Did a cat just appear or disappear?  We create a new log
            # line when this happens, so the user gets a log of cat
            # appearances and disappearances.
            cat_status_changed = cat_in_frame != cat_has_been_visible
            if cat_status_changed:
                cat_has_been_visible = cat_in_frame

            if not cat_in_frame:
                # Find all objects that score sufficiently well.
                # We're going to log them if there's no cat to talk
                # about.
                mask = (scores >= SCORE_THRESH) & (areas >= min_box_area)
                if mask.any():
                    show_labels = top_unique_labels(labels[mask], scores[mask])
                else:
                    show_labels = torch.empty((0,), dtype=labels.dtype)

            # Give the user our results.  We only do this if the
            # per-frame durations have been initialized (we're on at
            # least the second frame), just to simplify the layout
            # logic.
            if elapsed_per_frame_moving_avg is not None:
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
                               f"{elapsed_per_frame_moving_avg * 1000:5.0f} ms/frame "
                               f"| {status_line_msg:31s} (cat score={cat_score:.2f})")
                print(f"\r{status_line}", end="\n" if cat_status_changed else "")


if __name__ == "__main__":
    main()
