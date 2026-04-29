# show_cell_outlines.py
# Fiji/ImageJ Jython plugin
#
# PURPOSE:
#   Given an open image stack and a labelled mask stack (each cell has a unique
#   integer label), this script:
#     1. Lets the user pick which open window is the image and which is the mask.
#     2. Thresholds each label in the mask automatically (one ROI per label).
#     3. Adds every cell outline to the ROI Manager.
#     4. Displays a colour-coded overlay on the image stack so outlines are
#        visible on every slice.
#
# HOW TO RUN:
#   Drag-and-drop this file onto Fiji  OR
#   Plugins > Macros > Run...  OR
#   Place in Fiji.app/plugins/ and restart (it will appear in the Plugins menu).
#
# REQUIREMENTS:
#   Fiji with default plugins (no extra update sites needed).

from ij import IJ, ImagePlus, WindowManager
from ij.gui import GenericDialog, Overlay
from ij.plugin.filter import ThresholdToSelection
from ij.plugin.frame import RoiManager
from java.awt import Color


# ---------------------------------------------------------------------------
# Helper: get a consistent, visually distinct colour for each label index
# ---------------------------------------------------------------------------
def label_color(index, total):
    """Return a java.awt.Color using HSB colour wheel spread across all labels."""
    hue = (index / float(max(total, 1))) % 1.0
    return Color.getHSBColor(hue, 0.85, 1.0)


# ---------------------------------------------------------------------------
# Helper: extract a single-label binary mask from one slice of the label image
# ---------------------------------------------------------------------------
def get_label_mask(label_ip, label_value):
    """
    Return a byte ImageProcessor that is 255 where label_ip == label_value,
    0 everywhere else.
    """
    w, h = label_ip.getWidth(), label_ip.getHeight()
    bp = IJ.createImage("tmp", "8-bit black", w, h, 1).getProcessor()
    pixels = label_ip.getPixels()          # short[] or int[] or float[]
    bp_pixels = bp.getPixels()             # byte[]

    for i in range(len(bp_pixels)):
        # getPixelValue works for all pixel types and returns float
        if int(round(label_ip.getf(i % w, i // w))) == label_value:
            bp_pixels[i] = -1  # 0xFF as signed byte = 255 unsigned

    return bp


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------
def run():
    # ---- 1. Ask user to identify the two stacks --------------------------
    open_images = [WindowManager.getImage(id)
                   for id in WindowManager.getIDList() or []]
    titles = [img.getTitle() for img in open_images]

    if len(titles) < 2:
        IJ.error("Show Cell Outlines",
                  "Please open at least two stacks:\n"
                  " • the raw image stack\n"
                  " • the labelled mask stack")
        return

    gd = GenericDialog("Show Cell Outlines")
    gd.addMessage("Select the two open stacks:")
    gd.addChoice("Image stack (raw):", titles, titles[0])
    gd.addChoice("Label mask stack:", titles, titles[1])
    gd.addNumericField("Outline colour opacity (0-255):", 200, 0)
    gd.addCheckbox("Add individual ROIs to ROI Manager", True)
    gd.showDialog()

    if gd.wasCanceled():
        return

    img_title   = gd.getNextChoice()
    mask_title  = gd.getNextChoice()
    opacity     = int(gd.getNextNumber())
    add_to_rm   = gd.getNextBoolean()

    img_stack  = WindowManager.getImage(img_title)
    mask_stack = WindowManager.getImage(mask_title)

    if img_stack is None or mask_stack is None:
        IJ.error("Could not retrieve the selected images.")
        return

    n_slices      = img_stack.getNSlices()
    mask_slices   = mask_stack.getNSlices()

    if n_slices != mask_slices:
        IJ.showMessage(
            "Warning",
            "Image stack has %d slices but mask has %d slices.\n"
            "Outlines will only be drawn for the slices present in the mask."
            % (n_slices, mask_slices))

    # ---- 2. Collect all unique label values across the whole mask stack --
    IJ.showStatus("Scanning mask for unique labels…")
    unique_labels = set()
    for s in range(1, mask_slices + 1):
        mask_stack.setSlice(s)
        ip = mask_stack.getProcessor()
        w, h = ip.getWidth(), ip.getHeight()
        for y in range(h):
            for x in range(w):
                v = int(round(ip.getf(x, y)))
                if v != 0:
                    unique_labels.add(v)

    unique_labels = sorted(unique_labels)
    n_labels = len(unique_labels)
    IJ.showStatus("Found %d unique cell labels." % n_labels)

    if n_labels == 0:
        IJ.error("Show Cell Outlines", "No non-zero labels found in the mask stack.")
        return

    # ---- 3. Set up ROI Manager and Overlay --------------------------------
    rm = RoiManager.getInstance()
    if rm is None:
        rm = RoiManager()
    if add_to_rm:
        rm.reset()

    overlay = Overlay()

    # ---- 4. For each slice × label: threshold → outline → ROI -----------
    total_steps = mask_slices * n_labels
    step = 0

    for s in range(1, mask_slices + 1):
        mask_stack.setSlice(s)
        ip = mask_stack.getProcessor()

        for idx, lv in enumerate(unique_labels):
            step += 1
            IJ.showProgress(step, total_steps)
            IJ.showStatus("Slice %d/%d  |  Label %d/%d" %
                           (s, mask_slices, idx + 1, n_labels))

            # -- Create binary mask for this label on this slice
            binary_ip = get_label_mask(ip, lv)

            # -- Convert threshold directly to a ROI (no ROI Manager involved)
            binary_ip.setThreshold(128, 255, binary_ip.NO_LUT_UPDATE)
            roi = ThresholdToSelection().convert(binary_ip)

            if roi is None:
                continue  # label not present on this slice

            color = label_color(idx, n_labels)
            roi.setStrokeColor(color)
            roi.setFillColor(None)          # outline only, no fill
            roi.setStrokeWidth(1.0)
            roi.setPosition(s)        # pin to this slice (z)
            #roi.setPosition(0, s, 0)        # pin to this slice (z)
            roi.setName("Cell_%04d_s%02d" % (lv, s))

            overlay.add(roi)

            if add_to_rm:
                rm.addRoi(roi)

    # ---- 5. Apply overlay to the image stack ------------------------------
    img_stack.setOverlay(overlay)
    img_stack.show()

    # Make overlay visible
    IJ.run(img_stack, "Show Overlay", "")

    if add_to_rm:
        rm.show()

    IJ.showProgress(1, 1)
    IJ.showStatus("Done — %d outlines drawn across %d slices." %
                   (n_labels, mask_slices))
    IJ.showMessage(
        "Show Cell Outlines",
        "Complete!\n\n"
        "  Cells found : %d\n"
        "  Slices      : %d\n"
        "  Total ROIs  : %d\n\n"
        "Outlines are shown as an overlay on '%s'."
        % (n_labels, mask_slices, overlay.size(), img_title))


# ---------------------------------------------------------------------------
# Entry point — works both as a script and as a Plugins menu item
# ---------------------------------------------------------------------------
run()
