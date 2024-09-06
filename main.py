
from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import glob
import random

# colors for the bboxes
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 256, 256

class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=False, height=False)

        # initialize global state
        self.imageDir = ''
        self.imageList = []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text="Image Dir:")
        self.label.grid(row=0, column=0, sticky=E)
        self.entry = Entry(self.frame)
        self.entry.grid(row=0, column=1, sticky=W+E)
        self.ldBtn = Button(self.frame, text="Load", command=self.loadDir)
        self.ldBtn.grid(row=0, column=2, sticky=W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Escape> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage)  # press 'a' to go backward
        self.parent.bind("d", self.nextImage)  # press 'd' to go forward
        self.mainPanel.grid(row=1, column=1, rowspan=4, sticky=W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text='Bounding boxes:')
        self.lb1.grid(row=1, column=2, sticky=W+N)
        self.listbox = Listbox(self.frame, width=22, height=12)
        self.listbox.grid(row=2, column=2, sticky=N)
        self.btnDel = Button(self.frame, text='Delete', command=self.delBBox)
        self.btnDel.grid(row=3, column=2, sticky=W+E+N)
        self.btnClear = Button(self.frame, text='ClearAll', command=self.clearBBox)
        self.btnClear.grid(row=4, column=2, sticky=W+E+N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=5, column=1, columnspan=2, sticky=W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # example panel for illustration
        self.egPanel = Frame(self.frame, border=10)
        self.egPanel.grid(row=1, column=0, rowspan=5, sticky=N)
        self.tmpLabel2 = Label(self.egPanel, text="Examples:")
        self.tmpLabel2.pack(side=TOP, pady=5)
        self.egLabels = []
        for i in range(3):
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side=TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(4, weight=1)

    def loadDir(self, dbg=False):
        if not dbg:
            s = self.entry.get()  # Get the directory or image path from the user
            self.parent.focus()
            # Check if input is a file or directory
            if os.path.isfile(s):  # If it's a single image file
                self.imageList = [s]  # Put the single image in a list
            elif os.path.isdir(s):  # If it's a directory
                self.imageDir = s
                self.imageList = glob.glob(os.path.join(self.imageDir, '*.jpg'))  # Change this based on the image format
            else:
                messagebox.showerror("Error", "Invalid file or directory path")
                return
        else:
            # Debugging mode path (modify this if needed)
            s = r'D:\workspace\python\labelGUI'

        if len(self.imageList) == 0:
            print('No images found in the specified dir!')
            return

        self.cur = 1
        self.total = len(self.imageList)

        self.outDir = os.path.join(r'./Labels', '%03d' % (self.category))  # You might want to change how output directory is handled
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        self.loadImage()
        print(f'{self.total} images loaded from {s}')


    def loadImage(self):
        # Load the image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)

        # Resize the image to fit within the bounding box window while maintaining aspect ratio
        window_width = self.mainPanel.winfo_width()  # Get current width of the canvas
        window_height = self.mainPanel.winfo_height()  # Get current height of the canvas

        img_width, img_height = self.img.size  # Get original image size

        scale_factor = max(window_width / img_width, window_height / img_height)

        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)

        # Resize the image
        self.img_resized = self.img.resize((new_width, new_height), Image.LANCZOS)
        self.tkimg = ImageTk.PhotoImage(self.img_resized)

        # Set the resized image to the canvas
        self.mainPanel.config(width=new_width, height=new_height)
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=NW)

        self.progLabel.config(text=f"{self.cur:04d}/{self.total:04d}")

        # Load any existing bounding box information
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)

        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for (i, line) in enumerate(f):
                    if i == 0:
                        continue
                    bbox = [int(x.strip()) for x in line.split()]
                    scaled_bbox = [int(coord * scale_factor) for coord in bbox]  # Scale the bbox to match resized image
                    self.bboxList.append(tuple(scaled_bbox))
                    bbox_id = self.mainPanel.create_rectangle(
                        scaled_bbox[0], scaled_bbox[1], scaled_bbox[2], scaled_bbox[3],
                        width=2,
                        outline=COLORS[len(self.bboxList) % len(COLORS)]
                    )
                    self.bboxIdList.append(bbox_id)
                    self.listbox.insert(END, f"({scaled_bbox[0]}, {scaled_bbox[1]}) -> ({scaled_bbox[2]}, {scaled_bbox[3]})")
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg=COLORS[len(self.bboxIdList) % len(COLORS)])


    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)

            # Calculate scaling factors
            original_width, original_height = self.img.size
            resized_width = self.tkimg.width()
            resized_height = self.tkimg.height()
            scale_x = original_width / resized_width
            scale_y = original_height / resized_height

            # Scale the coordinates to the original image size
            real_x1 = int(x1 * scale_x)
            real_y1 = int(y1 * scale_y)
            real_x2 = int(x2 * scale_x)
            real_y2 = int(y2 * scale_y)

            self.bboxList.append((x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None

            # Display the bounding box coordinates in the listbox (relative to the original image)
            self.listbox.insert(END, f'({real_x1}, {real_y1}) -> ({real_x2}, {real_y2})')
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg=COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])

        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        # Check if an image has been loaded before trying to access its attributes
        if not hasattr(self, 'img') or self.img is None:
            return  # Exit the function if no image is loaded

        original_width, original_height = self.img.size

        resized_width = self.tkimg.width()
        resized_height = self.tkimg.height()

        scale_x = original_width / resized_width
        scale_y = original_height / resized_height

        real_x = int(event.x * scale_x)
        real_y = int(event.y * scale_y)
        self.disp.config(text=f'x: {real_x}, y: {real_y}')

        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, resized_width, event.y, width=2)

            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, resized_height, width=2)

        # Handle drawing a bounding box on the resized image
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)

            # Display the bounding box on the resized image
            self.bboxId = self.mainPanel.create_rectangle(
                self.STATE['x'], self.STATE['y'], event.x, event.y, width=2,
                outline=COLORS[len(self.bboxList) % len(COLORS)]
            )
    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
            self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxIdList))
        self.bboxIdList = []
        self.bboxList = []

    def saveImage(self):
        # Get the original image size
        original_width, original_height = self.img.size

        resized_width = self.tkimg.width()
        resized_height = self.tkimg.height()

        # Calculate the scaling factor
        scale_x = original_width / resized_width
        scale_y = original_height / resized_height

        # Open the label file for writing
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' % len(self.bboxList))

            for bbox in self.bboxList:
                x1, y1, x2, y2 = bbox

                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                f.write(f'{x1} {y1} {x2} {y2}\n')

        print(f'Image No. {self.cur} saved with bounding boxes in original image size')

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

if __name__ == '__main__':
    root = Tk()

    root.geometry("1280x800")  # Set the initial size of the main window

    tool = LabelTool(root)

    # Increase the initial canvas size in the GUI
    tool.mainPanel.config(width=1600, height=900)  # Larger canvas for displaying the image

    # Enable window resizing if necessary
    root.resizable(width=True, height=True)

    root.mainloop()
