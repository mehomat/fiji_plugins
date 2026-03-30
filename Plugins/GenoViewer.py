#@ File (label="Directory", style="directory") srcDir
#@ String (label="Position", ) position
#@ String (label="Round1", ) round1
#@ String (label="Round2", ) round2
#@ String (label="Round3", ) round3
#@ String (label="Round4", ) round4
#@ String (label="Red channel", ) channel1
#@ String (label="Green channel", ) channel2
#@ String (label="Blue channel", ) channel3
#@ String (label="Cyan channel", ) channel4
#@ String (label="Magenta channel", ) channel5
#@ Integer (label="Y min (first row)", value=1) ymin
#@ Integer (label="Y max (last row)", value=1) ymax

from ij import IJ, ImagePlus, ImageStack
from ij.gui import GenericDialog
from ij.plugin import ContrastEnhancer
from ij.process import ImageProcessor, FloatProcessor
import os, math

# Set only the foreground color
IJ.setForegroundColor(255, 255, 255)  # white in RGB

def run(srcDir, position, rounds, channels,ylims):
   
	composites = []  # Collect labelled composites for montage
	merge_channels = ["c1","c2","c3","c5","c6"]
	
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
				#imp.flatten()
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
		IJ.run("Make Montage...", "columns=1 rows="+str(len(rounds))+" scale=1 border=2 use")
		montage = IJ.getImage()
		montage.setTitle("Genotyping_" + position)
		
		# Close the intermediate stack
		IJ.selectWindow("MontageStack")
		IJ.run("Close")


# Main function
rounds = []
for r in [round1, round2, round3, round4]:
	if r !="":
		rounds.append(r)
channels = [channel1, channel2, channel3, channel4, channel5]
ymax = max(ymin,ymax)
ylims = [ymin, ymax]
if ymin==ymax:
	ylims = None
else:
	ylims = [max(0,y-1) for y in ylims]
		
run(srcDir.getPath(), position, rounds, channels, ylims)
