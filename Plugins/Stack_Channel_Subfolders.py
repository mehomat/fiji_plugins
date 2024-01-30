#@ File (label="Directory", style="directory") srcDir
#@ String (label="Channel", description="Set channel subfolder name") channelName
#@ String (label="Frame", value="0",description="Set frame index, or leave empty to load all frames") frameIndex
from ij import IJ, ImagePlus, ImageStack
from ij.gui import GenericDialog
import os

def run(srcDir,channelName,frameIndex):
  # Check input arguments
  if not os.path.isdir(srcDir):
    gd=GenericDialog('Error')
    gd.addMessage('Folder '+srcDir+' is not found!')
    gd.hideCancelButton()
    gd.showDialog()
    return
  if not channelName:
    gd=GenericDialog('Error')
    gd.addMessage('Set a correct channel subfolder name')
    gd.hideCancelButton()
    gd.showDialog()
    return
  sId=".tif"
  if not frameIndex:
    fId = None
  else:
    fId = int(frameIndex)
  # Assumes all files have the same size
  paths = []
  stack = None
  for root, directories, filenames in os.walk(srcDir):
    if not (channelName in root):
      continue
    filenames = [filename for filename in filenames if sId in filename]
    if fId is None:
      for filename in filenames:
        paths.append(os.path.join(root,filename))
    else:
      filenames=sorted(filenames)
      paths.append(os.path.join(root, filenames[fId]))
  paths=sorted(paths)
  for path in paths:
      # Upon finding the first image, initialize the VirtualStack
      imp = IJ.openImage(path)
      if stack is None:
        # stack = VirtualStack(imp.width, imp.height, None, srcDir)
        stack = ImageStack(imp.width, imp.height)
      # Add a slice to the virtual stack, relative to the srcDir
      #
      #stack.addSlice(path[len(srcDir):])
      
      # Add a slice to the real stack
      if len(path)>60:
        sliceText = path[-60:]
      else:
        sliceText = path
      stack.addSlice(sliceText, imp.getProcessor())
      
  # Make a ImagePlus from the stack
  ImagePlus("Stack from "+channelName+" subdirectories", stack).show()

run(str(srcDir),channelName,frameIndex)