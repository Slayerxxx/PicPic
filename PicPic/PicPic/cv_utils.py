import numpy as np
import cv2

def cv2_imread(path):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), -1)
    return img
    
def rected_path(path):
    return path.replace("\\", "/")

def show_hist(self, img):
	plt.clf()
	hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
	hist_h = cv2.calcHist([hsv], [0], None, [180], [0, 180])
	hist_s = cv2.calcHist([hsv], [1], None, [255], [0, 255])
	plt.plot(hist_h, 'b')
	plt.plot(hist_s, 'y')
	plt.show()
    
def avg_hist(hist, win, loop=True):
    '''
    对直方图均值滤波
    inputs
    hist: 需要滤波的直方图
    win: 窗口大小
    loop: 通道是否是循环的  i.e hue
    
    return
    hist_avg: 滤波后的直方图
    '''
    print('开始均值滤波...')
    h_size = hist.shape[0]
    hist_avg = np.zeros(hist.shape)
    for cur in range(h_size):
        if loop:                        
            left = (cur - win) % h_size
            right = (cur + win) % h_size
        else:
            left = (cur - win) if (cur - win)>=0 else 0
            right = (cur + win) if (cur + win)<=255 else 255
        if left < right:
            hist_avg[cur] = np.sum(hist[left:right+1]) #// (right+1-left)
        else:
            hist_avg[cur] = (np.sum(hist[0:right+1]) + np.sum(hist[left:h_size+1])) #// (h_size+1-left+right)
            
    return hist_avg

def get_histpeaks(hue, hist):
    '''
    计算直方图的波峰
    inputs
    hue: 为了计算图像大小传入
    hist: 
    
    return
    peaks_flags: 和hist大小一样的直方图。波峰为True，其他为False
    '''
    print('开始找峰值点...')
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
    
    peaks_flags = (hist > hist_lshift) & (hist > hist_rshift) #& (hist > thresh_dn)# & (hist <thresh_up)
    return peaks_flags

def mask_bypeaks(src, peaks_flags, win, loop=True):
    '''
    以每个flag位置左右win大小的范围为阈值，得到一个mask
    win: flag有效范围
    loop: 通道是否是循环的  i.e hue
    
    return
    masks: mask的列表
    '''
    print('开始获得mask')
    h_size = peaks_flags.shape[0]   #180
    mask = np.zeros(src.shape)
    masks = []
    for flag in range(h_size):
        if peaks_flags[flag]:
            print('Peak->', flag)
            if loop:
                left = (flag - win) % h_size
                right = (flag + win) % h_size
                print(left, right)           
            else:
                left = (flag - win) if (flag - win)>=0 else 0
                right = (flag + win) if (flag + win)<=255 else 255
                print(left, right)  
            if left < right:
                mask = (src > left) & (src < right)
            else:
                mask = (src < right) | (src > left)
            mask = mask * 255
            mask = np.array(mask, dtype=np.uint8)
            masks.append(mask)
    return masks


def pipline_pvm(src, hist, win_filter, win_effarea, loop=True):  # 主要值mask
    hist_avg = avg_hist(hist, win_filter, loop=loop)
    peaks_flags = get_histpeaks(src, hist_avg)
    masks = mask_bypeaks(src, peaks_flags, win_effarea, loop=loop)
    return masks