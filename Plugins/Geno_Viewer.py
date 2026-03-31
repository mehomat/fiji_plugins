#@ File (label="Select Main Directory", style="directory") srcDir
#@ Integer (label="Number of rounds", value=4) num_rounds
#@ Integer (label="Y min (first row)", value=1) ymin
#@ Integer (label="Y max (last row)", value=1) ymax
#@ Boolean (label="Threshold images", value=0) do_thresh

from ij import IJ, ImagePlus, ImageStack, WindowManager, Prefs # Added Prefs
from ij.gui import GenericDialog
from ij.process import FloatProcessor
import os, math

# ... [Keep get_subfolders, reorder_for_column_first, and run_logic functions exactly the same] ...

def get_subfolders(path):
    try:
        return sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
    except Exception:
        return []

def reorder_for_column_first(stack, n_cols, n_rows):
    new_stack = ImageStack(stack.getWidth(), stack.getHeight())
    for row in range(n_rows):
        for col in range(n_cols):
            index = col * n_rows + row + 1
            if index <= stack.getSize():
                new_stack.addSlice(stack.getSliceLabel(index), stack.getProcessor(index))
    return new_stack

def run(root, position, rounds, channels, ylims, do_thresh):
    composites = []
    merge_slots = ["c1", "c2", "c5", "c6"]
    
    for r in rounds:
        posfolder = os.path.join(root, r, position)
        if not os.path.isdir(posfolder):
            continue

        imps = []
        merge_cmd = ""
        
        for (slot, c) in zip(merge_slots, channels):
            if c != "None" and c != "":
                imgpath = os.path.join(posfolder, c, "img_000000000.tiff")
                if not os.path.exists(imgpath):
                    continue

                imp = IJ.openImage(imgpath)
                if imp:
                    if ylims:
                        imp.setRoi(0, ylims[0], imp.getWidth(), ylims[1] - ylims[0])
                        imp = imp.crop()
                    if do_thresh:
                        IJ.run(imp, "Auto Threshold", "method=Triangle white")
                        IJ.run(imp, "Analyze Particles...", "size=10-Infinity show=Masks include")
                        imp.close()
                        imp = IJ.getImage()
                    else:
                        IJ.run(imp, "Enhance Contrast", "saturated=0.35 normalize")
                    imp.setTitle(r + "_" + c)
                    imp.show()
                    imps.append(imp)
                    merge_cmd += slot + "=[" + imp.getTitle() + "] "
        
        if len(imps) > 0:
            merge_cmd += "create"
            IJ.run("Merge Channels...", merge_cmd)
            composite = WindowManager.getCurrentImage()
            if composite:
                IJ.run(composite, "Flatten", "")
                flat = WindowManager.getCurrentImage()
                composite.close()
                for imp in imps:
                    if imp.isVisible(): imp.close()
                IJ.run(flat, "Label...", "format=Text starting=0 interval=1 x=10 y=30 font=28 text=" + r + " range=1-1")
                composites.append(flat)

    if len(composites) > 0:
        for i, c in enumerate(composites):
            c.setTitle("R" + str(i + 1))
        if len(composites) == 1:
            composites[0].setTitle("Genotyping_" + position)
            return
        IJ.run("Images to Stack", "name=MontageStack title=R use")
        stack_imp = WindowManager.getCurrentImage()
        n_cols = (len(composites) - 1) // 4 + 1
        n_rows = int(math.ceil(float(len(composites)) / n_cols))
        reordered = reorder_for_column_first(stack_imp.getStack(), n_cols, n_rows)
        stack_imp.setStack(reordered)
        IJ.run("Make Montage...", "columns=" + str(n_cols) + " rows=" + str(n_rows) + " scale=1 border=2 use")
        WindowManager.getCurrentImage().setTitle("Genotyping_" + position)
        stack_imp.close()

# --- Main Logic ---
root = srcDir.getPath()
rounds_list = ["R" + str(i+1) for i in range(num_rounds)]

first_round_path = os.path.join(root, rounds_list[0])
if os.path.isdir(first_round_path):
    available_positions = get_subfolders(first_round_path)
    if available_positions:
        first_pos_path = os.path.join(first_round_path, available_positions[0])
        available_channels = ["None"] + get_subfolders(first_pos_path)

        # 1. LOAD PREVIOUS CHOICES
        # Format: Prefs.get("KeyName", DefaultValue)
        prev_pos = Prefs.get("GenoViewer.lastPos", available_positions[0])
        prev_c1  = Prefs.get("GenoViewer.lastC1", "None")
        prev_c2  = Prefs.get("GenoViewer.lastC2", "None")
        prev_c5  = Prefs.get("GenoViewer.lastC5", "None")
        prev_c6  = Prefs.get("GenoViewer.lastC6", "None")

        # 2. CREATE DIALOG WITH PREVIOUS VALUES
        gd = GenericDialog("GenoViewer: Select Data")
        # Ensure the previous choice still exists in the folder before setting it
        def_pos = prev_pos if prev_pos in available_positions else available_positions[0]
        
        gd.addChoice("Position:", available_positions, def_pos)
        gd.addMessage("--- Assign Channels ---")
        gd.addChoice("Red_Channel:", available_channels, prev_c1 if prev_c1 in available_channels else "None")
        gd.addChoice("Green_Channel:", available_channels, prev_c2 if prev_c2 in available_channels else "None")
        gd.addChoice("Cyan_Channel:", available_channels, prev_c5 if prev_c5 in available_channels else "None")
        gd.addChoice("Magenta_Channel:", available_channels, prev_c6 if prev_c6 in available_channels else "None")
        
        gd.showDialog()
        
        if gd.wasOKed():
            sel_pos = gd.getNextChoice()
            c1 = gd.getNextChoice()
            c2 = gd.getNextChoice()
            c5 = gd.getNextChoice()
            c6 = gd.getNextChoice()
            sel_chans = [c1, c2, c5, c6]
            
            # 3. SAVE CHOICES FOR NEXT TIME
            Prefs.set("GenoViewer.lastPos", sel_pos)
            Prefs.set("GenoViewer.lastC1", c1)
            Prefs.set("GenoViewer.lastC2", c2)
            Prefs.set("GenoViewer.lastC5", c5)
            Prefs.set("GenoViewer.lastC6", c6)
            # This writes the preferences to the IJ_Prefs.txt file
            Prefs.savePreferences()
            
            y_max_val = max(ymin, ymax)
            y_lims = [max(0, ymin-1), y_max_val-1] if ymin != ymax else None
            run(root, sel_pos, rounds_list, sel_chans, y_lims, do_thresh)
else:
    IJ.error("Error", "Could not find folder: " + first_round_path)
