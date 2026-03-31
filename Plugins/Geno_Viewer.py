#@ File (label="Directory", style="directory") srcDir
#@ String (label="Position", ) position
#@ Integer (label="Number of rounds", value=4) num_rounds
#@ String (label="Red channel", ) channel1
#@ String (label="Green channel", ) channel2
#@ String (label="Cyan channel", ) channel3
#@ String (label="Magenta channel", ) channel4
#@ Integer (label="Y min (first row)", value=1) ymin
#@ Integer (label="Y max (last row)", value=1) ymax
#@ Boolean (label="Threshold images", value=0) do_thresh

from ij import IJ, ImagePlus, ImageStack
from ij.gui import GenericDialog
from ij.plugin import ContrastEnhancer
from ij.process import ImageProcessor, FloatProcessor
import os, math

# Set only the foreground color
IJ.setForegroundColor(255, 255, 255)  # white in RGB

def reorder_for_column_first(stack, n_cols, n_rows):
    """
    Reorders stack slices from row-first to column-first order.
    E.g. for 2 cols x 4 rows:
      Input order:  1,2,3,4,5,6,7,8  (row-first)
      Output order: 1,3,5,7,2,4,6,8  (column-first)
    """
    new_stack = ImageStack(stack.getWidth(), stack.getHeight())
    for row in range(n_rows):
    	for col in range(n_cols):
    		index = col*n_rows + row+1
    		new_stack.addSlice(stack.getSliceLabel(index), stack.getProcessor(index))
    return new_stack

def get_montage_size(stack):
	N = len(stack)
	n_cols = (N-1) // 4 +1
	n_rows = int(math.ceil(N/n_cols))
	return n_cols, n_rows
	
def flatfield_correction(imp, sigma=50.0):
	"""
	Pseudo-flat-field correction using Gaussian blur estimate.
	sigma: blur radius — should be larger than your largest feature of interest.
	       Typically 50-100 pixels for a 1024x1024 image.
	"""
	ip = imp.getProcessor().convertToFloat()
	
	# Estimate illumination: heavily blurred version of the image
	flat = ip.duplicate()
	flat.blurGaussian(sigma)
	
	# Compute mean of the flat field for rescaling
	flat_pixels = flat.getPixels()
	mean_flat = sum(flat_pixels) / len(flat_pixels)
	
	# Divide original by flat field, rescale by mean
	src  = ip.getPixels()
	corr = flat.getPixels()
	corrected_pixels = [
	    (src[i] / corr[i]) * mean_flat if corr[i] != 0 else 0
	    for i in range(len(src))
	]
	
	result = FloatProcessor(imp.getWidth(), imp.getHeight(), corrected_pixels, None)
	result.setMinAndMax(0, result.getMax())
	result = result.convertToShort(True) # True = scale to full 16-bit range
	return ImagePlus(imp.getTitle() + "_corrected", result)

def run(srcDir, position, rounds, channels, ylims, do_thresh):
   
	composites = []  # Collect labelled composites for montage
	merge_channels = ["c1","c2","c5","c6"]
	
	for r in rounds:
		posfolder = os.path.join(srcDir, r, position)

		if not os.path.isdir(posfolder):
			gd = GenericDialog('Error')
			gd.addMessage('Folder ' + posfolder + ' is not found!')
			gd.hideCancelButton()
			gd.showDialog()
			return

		imps = []

		merge_cmd = ""
		for (mc,c) in zip(merge_channels,channels):
			if c != "":
				chanfolder = os.path.join(posfolder, c)
			   
				imgpath = os.path.join(chanfolder, "img_000000000.tiff")
				imp = IJ.openImage(imgpath)
				if imp is None:
					IJ.log("Failed to open image in: " + imgpath)
					return
				
				if ylims is not None:
					imp.setRoi(0, ylims[0], imp.getWidth(), ylims[1] - ylims[0])
					imp = imp.crop()
				
				# Threshold images if requested
				if do_thresh:
					#imp = flatfield_correction(imp, sigma=5.0)
					IJ.run(imp, "Auto Threshold", "method=Triangle white")
					IJ.run(imp, "Analyze Particles...", "size=10-Infinity show=Masks include")
					imp.close()
					imp = IJ.getImage()
					#IJ.run(imp, "Invert", "")
					
				imp.setTitle(r + "_" + c)
				imp.show()
				IJ.run(imp, "Enhance Contrast", "saturated=0.35 normalize")
				imps.append(imp)
				merge_cmd = merge_cmd +mc+"="+imp.getTitle()+" "
		merge_cmd = merge_cmd+ "create"
		IJ.run("Merge Channels...", merge_cmd)

		# Close the source channel images after merging
		for imp in imps:
			if imp.isVisible():
				imp.close()

		# Get the resulting composite (active image after merge)
		composite = IJ.getImage()
		composite.setTitle("Composite_" + r)

		# Flatten to RGB so text can be drawn on it
		IJ.run(composite, "Flatten", "")
		flat = IJ.getImage()
		flat.setTitle("Flat_" + r)
		composite.close()

		# Burn in the round label (e.g. "R1") at top-left
		IJ.run(flat, "Label...",
			   "format=Text starting=0 interval=1 x=10 y=30 font=28 text=" + r + " range=1-1")

		composites.append(flat)

	# Rename composites so "Images to Stack" can find them by shared title prefix
	for i, c in enumerate(composites):
		c.setTitle("R" + str(i + 1))

	if len(composites)>1:
		# Stack all rounds and make a 1-column x 4-row montage
		IJ.run("Images to Stack", "name=MontageStack title=R use")
		
		# Reorder slices for column-first layout
		stack_imp = IJ.getImage()
		n_cols,n_rows=get_montage_size(composites)
		reordered = reorder_for_column_first(stack_imp.getStack(), n_cols, n_rows)
		stack_imp.setStack(reordered)
		
		IJ.run("Make Montage...", "columns="+str(n_cols)+" rows="+str(n_rows)+" scale=1 border=2 use")
		montage = IJ.getImage()
		montage.setTitle("Genotyping_" + position)
		
		# Close the intermediate stack
		stack_imp.close()


# Main function
rounds = ["R"+str(i+1) for i in range(num_rounds)]
channels = [channel1, channel2, channel3, channel4]
ymax = max(ymin,ymax)
ylims = [ymin, ymax]
if ymin==ymax:
	ylims = None
else:
	ylims = [max(0,y-1) for y in ylims]
		
run(srcDir.getPath(), position, rounds, channels, ylims, do_thresh)
