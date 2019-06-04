from PIL import Image   

# Use the wxPython backend of matplotlib
import matplotlib       
matplotlib.use('WXAgg')

# Matplotlib elements used to draw the bounding rectangle
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# Wxpython
import wx
import os

# OpenCV
import cv2
import numpy as np


class MyDialog(wx.Panel):
    def __init__(self, parent, pathToImage=None):
        
        # Use English dialog
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
        
        # Initialise the parent
        wx.Panel.__init__(self, parent)

        # Intitialise the matplotlib figure
        #self.figure = plt.figure(facecolor='gray')
        self.figure = Figure(facecolor='gray')

        # 显示当前图片原图
        self.axes = plt.Axes(self.figure,[0,0.1,1,1])  #left, bottom,   
        #self.axes_h = plt.Axes(self.figure,[0,0,1,1]) 
        self.axes.set_axis_off()
        self.figure.add_axes(self.axes)
        
        
        # Add the figure to the wxFigureCanvas
        self.canvas = FigureCanvas(self, -1, self.figure)

        
        # Add Button and Progress Bar
        self.openBtn=wx.Button(self,-1,"Open",pos=(680,50),size=(70,40))
        self.maskBtn=wx.Button(self,-1,"mask",pos=(680,150),size=(70,40))
        self.frontBtn=wx.Button(self,-1,"Front",pos=(680,200),size=(70,40))
        self.nextBtn=wx.Button(self,-1,"Next",pos=(790,200),size=(70,40))
        self.gauge=wx.Gauge(self,-1,100,(0,520),(640,50))   

        self.Btn_cvt2HSV =wx.Button(self, -1, 'HSV', pos=(790, 150), size=(70, 40))
        
        # Attach button with function
        self.Bind(wx.EVT_BUTTON,self.load,self.openBtn)
        self.Bind(wx.EVT_BUTTON,self.get_mask,self.maskBtn)
        self.Bind(wx.EVT_BUTTON,self.front,self.frontBtn)
        self.Bind(wx.EVT_BUTTON,self.next,self.nextBtn)
        self.Bind(wx.EVT_BUTTON,self.cvt2HSV,self.Btn_cvt2HSV)

        # Show dialog path
        self.pathText=wx.TextCtrl(self,-1,"",pos=(680,120),size=(175,30))

        # Show HSV text
        self.h_text = wx.TextCtrl(self, -1, ":", pos=(790,50), size=(70,20), style=wx.TE_PROCESS_ENTER)
        self.s_text = wx.TextCtrl(self, -1, ":", pos=(790,75), size=(70,20), style=wx.TE_PROCESS_ENTER)
        self.v_text = wx.TextCtrl(self, -1, ":", pos=(790,100), size=(70,20), style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.hsv_filter,self.h_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.hsv_filter,self.s_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.hsv_filter,self.v_text)

        self.area_text = wx.TextCtrl(self, -1, u'记录',pos=(680,255),size=(200,200),style=(wx.TE_MULTILINE))
        #self.area_text.SetInsertionPoint(0) 

        # Initialise the rectangle
        self.rect = Rectangle((0,0), 0, 0, facecolor='None', edgecolor='red')
        self.x0 = None
        self.y0 = None
        self.x1 = None
        self.y1 = None
        self.axes.add_patch(self.rect)


        # The list of the picture(absolute path)
        self.fileList=[]

        # Picture name
        self.picNameList=[]

        # Picture index in list
        self.count=0 
    
        # Cut from the picture of the rectangle
        self.cut_img=None

        
        # Connect the mouse events to their relevant callbacks
        self.canvas.mpl_connect('button_press_event', self._onPress)
        self.canvas.mpl_connect('button_release_event', self._onRelease)
        self.canvas.mpl_connect('motion_notify_event', self._onMotion)
        
        
        # Lock to stop the motion event from behaving badly when the mouse isn't pressed
        self.pressed = False

        # If there is an initial image, display it on the figure
        if pathToImage is not None:
            self.setImage(pathToImage)



    # 使得允许读中文路径 
    def cv2_imread(self, path):
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), -1)
        return img
    
    # 校正斜杠
    def rected_path(self, path):
        return path.replace("\\", "/")
    
    # 显示img的分量直方图
    def show_hist(self, img, show=True):
        plt.clf()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        #hist_s = cv2.calcHist([hsv], [1], None, [255], [0, 255])
        if show:
            plt.plot(hist_h, 'b')
            #plt.plot(hist_s, 'y')
            plt.show()
        return hist_h
    
    # 对直方图均值滤波，滤波器大小为2*win
    def avg_hist(self, hist, win, show=True):
        h_size = hist.shape[0]
        hist_avg = np.zeros(hist.shape)
        for cur in range(h_size):
            left = (cur - win) % h_size
            right = (cur + win) % h_size
            if left < right:
                hist_avg[cur] = np.sum(hist[left:right+1])# // (right+1-left)
            else:
                hist_avg[cur] = (np.sum(hist[0:right+1]) + np.sum(hist[left:h_size+1]))# // (h_size+1-left+right)
        if show:
            plt.plot(hist_avg, 'r')
            plt.show()
        return hist_avg
    
    def get_histpeaks(self, img, hist):
        hue = img[:,:,0]
        h_size = hist.shape[0]  #180
        hist_rshift = np.zeros(hist.shape)
        hist_lshift = np.zeros(hist.shape)

        hist_rshift[1:h_size] = hist[0:h_size-1]
        hist_rshift[0] = hist[h_size-1]
        hist_lshift[0:h_size-1] = hist[1:h_size]
        hist_lshift[h_size-1] = hist[0]

        height = hue.shape[0]
        width = hue.shape[1]
        area = width * height
        thresh_up = (3.0/4.0) * area
        thresh_dn = (1.0/16.0) * area

        peaks_flags = (hist > hist_lshift) & (hist > hist_rshift) & (hist > thresh_dn) & (hist <thresh_up)
        return peaks_flags
    
    def mask_bypeaks_hue(self, img, peaks_flags, win):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hue,_,_ = cv2.split(hsv)
        h_size = peaks_flags.shape[0]   #180
        mask = np.zeros(hue.shape)


        for flag in range(h_size):
            if peaks_flags[flag]:
                print('Peak->', flag)
                left = (flag - win) % h_size
                right = (flag + win) % h_size
                print(left, right)
                if left < right:
                    mask = (hue > left) & (hue < right)
                else:
                    mask = (hue < right) | (hue > left)
        mask = mask * 255
        mask = np.array(mask, dtype=np.uint8)
        return mask


    # GetFilesPath with the end with .jpg or .png
    def getFilesPath(self,path):
        filesname=[]
        dirs = os.listdir(path)
        for i in dirs:
            if os.path.splitext(i)[1] == ".jpg" or os.path.splitext(i)[1] == ".png":
                r_path = self.rected_path(path)    #替换斜杠
                filesname+=[r_path+"/"+i]
                self.picNameList+=[i[:-4]]
        return filesname


    # Load Picture button function
    def load(self,event):
        dlg = wx.DirDialog(self,"Choose File",style=wx.DD_DEFAULT_STYLE)  
        if dlg.ShowModal() == wx.ID_OK:
            self.count=0           
            self.fileList=self.getFilesPath(dlg.GetPath())
            if self.fileList:
                self.setImage(self.fileList[0])
                #打印hue、avg直方图
                first_img_path = self.rected_path(self.fileList[0])  
                print(first_img_path)
                img = self.cv2_imread(first_img_path)
                hist = self.show_hist(img)
                self.avg_hist(hist, 10)
                
                self.gauge.SetValue((self.count+1)/len(self.fileList)*100)
                self.pathText.Clear()
                self.pathText.AppendText(dlg.GetPath())
            else:
                print("List Null")
        dlg.Destroy()


    # 显示hue阈值mask后的图片
    def get_mask(self,event):
        img_path = self.rected_path(self.fileList[self.count])
        img = self.cv2_imread(img_path)
        hist = self.show_hist(img, show=False)
        hist_avg = self.avg_hist(hist, 10, show=False)
        peaks_flags = self.get_histpeaks(img, hist_avg)
        
        size = peaks_flags.shape[0]
        for pos in range(size):
            if peaks_flags[pos]:
                one_flag = np.zeros(peaks_flags.shape)
                one_flag[pos, 0] = 1
                mask = self.mask_bypeaks_hue(img, one_flag, 10)
                cv2.namedWindow('mask', cv2.WINDOW_NORMAL)
                cv2.imshow("mask", mask)
                cv2.waitKey(0)
        cv2.destroyAllWindows()
        '''
                if self.cut_img is None:
            print("Please Draw Area")
            return
        else:
            cv2.imwrite(self.picNameList[self.count]+'_rect.jpg',self.cut_img)
            print("Save Successful")
        '''

            


    # The front picture button function
    def front(self,event):
        self.count-=1
        self.cut_img=None
        if self.fileList:
            if self.count<0:
                self.count+=1
                print("Null Pic")
            else:
                self.setImage(self.fileList[self.count])
                self.gauge.SetValue((self.count+1)/len(self.fileList)*100)
                #打印hue直方图
                first_img_path = self.rected_path(self.fileList[self.count])     
                img = self.cv2_imread(first_img_path)
                hist = self.show_hist(img)
                self.avg_hist(hist, 10)
                #print(self.count,self.fileList[self.count])
            
        else:
            print("Please Choose File")
            return 
        
       
    # The next picture button function        
    def next(self,event):
        self.count+=1
        self.cut_img=None
        if self.fileList:
            if self.count>(len(self.fileList) - 1):
                self.count-=1
                print("Null Pic")
            else:
                self.setImage(self.fileList[self.count])
                self.gauge.SetValue((self.count+1)/len(self.fileList)*100)
                #打印hue直方图
                first_img_path = self.rected_path(self.fileList[self.count])   
                print(first_img_path)
                img = self.cv2_imread(first_img_path)
                hist = self.show_hist(img)
                self.avg_hist(hist, 10)
                #print(self.count,self.fileList[self.count])

        else:
            print("Please Choose File")
            return 
        

        
    # 相应HSV按钮，并返回当前图片的HSV  
    def cvt2HSV(self, event):
        if self.fileList:
            bgr = self.cv2_imread(self.fileList[self.count])
            print(self.fileList[self.count])
            hsv = cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
            cv2.namedWindow('HSV', cv2.WINDOW_NORMAL)
            cv2.imshow('HSV', hsv)
            return hsv
        else:
            wx.MessageBox("List is None")
            return
        
    # 响应hsv_textctrl
    def hsv_filter(self, event):
        h, s, v = self.h_text.GetLineText(0), self.s_text.GetLineText(0), self.v_text.GetLineText(0)
        hl,hh = h.split(':')
        sl,sh = s.split(':')
        vl,vh = v.split(':')
        hsv = self.cvt2HSV(event)
        hl = float(hl)
        hh = float(hh)
        if hl < 0.0:
            hl = (hl + 180) % 180
            low = np.array([float(hl), float(sl), float(vl)])
            high = np.array([180.0, float(sh), float(vh)])
            mask1 = cv2.inRange(hsv, low, high)
            low = np.array([0.0, float(sl), float(vl)])
            high = np.array([hh, float(sh), float(vh)])
            mask2 = cv2.inRange(hsv, low, high)
            mask = cv2.bitwise_or(mask1, mask2)
        elif hh > 180.0:
            hh = hh % 180
            low = np.array([0.0, float(sl), float(vl)])
            high = np.array([hh, float(sh), float(vh)])
            mask1 = cv2.inRange(hsv, low, high)
            low = np.array([hl, float(sl), float(vl)])
            high = np.array([180.0, float(sh), float(vh)])
            mask2 = cv2.inRange(hsv, low, high)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            low = np.array([float(hl), float(sl), float(vl)])
            high = np.array([float(hh), float(sh), float(vh)])
            mask = cv2.inRange(hsv, low, high)
   
        cv2.namedWindow('filter', cv2.WINDOW_NORMAL)
        cv2.imshow('filter', mask)
    

    def _onPress(self, event):
        ''' Callback to handle the mouse being clicked and held over the canvas'''
        # Check the mouse press was actually on the canvas
        if event.xdata is not None and event.ydata is not None:

            # Upon initial press of the mouse record the origin and record the mouse as pressed
            self.pressed = True
            self.rect.set_linestyle('dashed')
            self.x0 = event.xdata
            self.y0 = event.ydata

    def cpt_hsvrange(self, rect):
        '''
        计算所选区域hsv取值mean，选一个范围并填充在hsv_TextCtrl里
        '''
        rect_hsv = cv2.cvtColor(rect, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(rect_hsv)
        
        h_mean, h_std = cv2.meanStdDev(h)
        s_mean, s_std = cv2.meanStdDev(s)
        v_mean, v_std = cv2.meanStdDev(v)
        h_mean = h_mean.squeeze()          # 删除冗余维度，成常数
        s_mean = s_mean.squeeze()
        v_mean = v_mean.squeeze()
        h_std = h_std.squeeze()
        s_std = s_std.squeeze()
        v_std = v_std.squeeze()
        h_mean = np.around(h_mean, decimals=1)      # 只保留一位小数
        s_mean = np.around(s_mean, decimals=1)
        v_mean = np.around(v_mean, decimals=1)
        
        h_std = (10 if h_std<10 else np.around(h_std, decimals=1))
        s_std = (10 if s_std<10 else np.around(s_std, decimals=1))
        v_std = (10 if v_std<10 else np.around(v_std, decimals=1))
        
        hsv_str = "%s, %s, %s\nstd--->%s, %s, %s" % (h_mean, s_mean, v_mean, h_std, s_std, v_std)
        wx.MessageBox(hsv_str)
        
        
        str_h = str(h_mean-h_std) + ':' +str(h_mean+h_std)
        str_s = str(s_mean-10) + ':' +str(s_mean+10)
        str_v = str(v_mean-10) + ':' +str(v_mean+10)

        self.h_text.SetValue(str_h)
        self.s_text.SetValue(str_s)
        self.v_text.SetValue(str_v)
    
    def _onRelease(self, event):
        '''Callback to handle the mouse being released over the canvas'''
        # Check that the mouse was actually pressed on the canvas to begin with and this isn't a rouge mouse 
        # release event that started somewhere else
        if self.pressed:

            # Upon release draw the rectangle as a solid rectangle
            self.pressed = False
            self.rect.set_linestyle('solid')

            # Check the mouse was released on the canvas, and if it wasn't then just leave the width and 
            # height as the last values set by the motion event
            if event.xdata is not None and event.ydata is not None:
                self.x1 = event.xdata
                self.y1 = event.ydata

            # Set the width and height and origin of the bounding rectangle
            self.boundingRectWidth =  self.x1 - self.x0
            self.boundingRectHeight =  self.y1 - self.y0
            self.bouningRectOrigin = (self.x0, self.y0)

            # Draw the bounding rectangle
            self.rect.set_width(self.boundingRectWidth)
            self.rect.set_height(self.boundingRectHeight)
            self.rect.set_xy((self.x0, self.y0))
            self.canvas.draw()

            
            # OpenCV cut picture(all number shoudle be integer)
            x=int(self.x0)
            y=int(self.y0)
            width=int(self.boundingRectWidth)
            height=int(self.boundingRectHeight)
            if  self.fileList and width:
                org = self.cv2_imread(self.fileList[self.count])
                self.cut_img = org[y:y+height, x:x+width]
                self.cpt_hsvrange(self.cut_img)                                 
                cv2.imshow('cut_image', self.cut_img)
            else:
                print("Draw Null Rectangle")
                return
            
            
            

    def _onMotion(self, event):
        '''Callback to handle the motion event created by the mouse moving over the canvas'''
        # If the mouse has been pressed draw an updated rectangle when the mouse is moved so 
        # the user can see what the current selection is
        if self.pressed:
            # Check the mouse was released on the canvas, and if it wasn't then just leave the width and 
            # height as the last values set by the motion event
            if event.xdata is not None and event.ydata is not None:
                self.x1 = event.xdata
                self.y1 = event.ydata
            
            # Set the width and height and draw the rectangle
            self.rect.set_width(self.x1 - self.x0)
            self.rect.set_height(self.y1 - self.y0)
            self.rect.set_xy((self.x0, self.y0))
            self.canvas.draw()

        # Show Picture
    def setImage(self, pathToImage):
        '''Sets the background image of the canvas'''
        # Clear the rectangle in front picture
        self.axes.text(100,100,'',None)
        self.rect.set_width(0)
        self.rect.set_height(0)
        self.rect.set_xy((0, 0))
        self.canvas.draw()
        #plt.cla()
        #self.initCanvas()
        # Load pic by OpenCV
        #image=cv2.imread(pathToImage,1)
        
        # Load the image into matplotlib and PIL
        image = matplotlib.image.imread(pathToImage)
        
        imPIL = Image.open(pathToImage) 

        # Save the image's dimensions from PIL
        self.imageSize = imPIL.size

        '''
        self.imageSize = image.shape
        print(pathToImage)
        print("It's width and height:")
        print(self.imageSize)
        
        print("------------------------")

        # OpenCV add text on pic
        str1='(%s,%s)' % (str(self.imageSize[0]),str(self.imageSize[1]))
        rev=wx.StaticText(self,-1,str1,(670,400))
        #rev.SetForegroundColour('white')
        #rev.SetBackgroundColour('black')
        #rev.SetFont(wx.Font(15,wx.DECORATIVE,wx.ITALIC,wx.NORMAL))
        cv2.putText(image,str1,(10,200), cv2.FONT_HERSHEY_SIMPLEX, 1,(255,0,0),2)
        '''

        str1='%s,%s' % (str(self.imageSize[0]),str(self.imageSize[1]))
        rev=wx.StaticText(self,-1,str1,(680,550))
        
        # Add the image to the figure and redraw the canvas. Also ensure the aspect ratio of the image is retained.
        self.axes.imshow(image,aspect='equal')
  
        self.canvas.draw()


       

