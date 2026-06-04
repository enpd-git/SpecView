# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 23:54:12 2021

@author: enpd
"""
import os, math, time
from PyQt5 import QtGui, QtCore, QtWidgets
from functools import partial

from astropy.io import fits

import numpy as np        
from statsmodels.nonparametric.smoothers_lowess import lowess

from PIL import Image

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import enum


###############################################################################
################################### Globals ###################################

#Require_Serials_For_Build = False
DEBUG_MODE = False # False # True #


class DATA_FILE_TYPE(enum.Enum):
    CONTINUUM = "CONTINUUM"
    ABSORBTION = "ABSORBTION"


################################### Globals ###################################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
###############################################################################


###############################################################################
################################## Formatting #################################

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
        
try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)
       
################################## Formatting #################################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
###############################################################################
       
       
            
###############################################################################
############################### THREADING CLASS ###############################
        
class DataLoader(QtCore.QThread):
    def  __init__(self, App, parent=None):
        super(DataLoader, self).__init__(parent)
        
        self.App = App
        
        self.DataQueue = []
        
        self.__pause = False
        self.__cancel = False
        
    def LoadDataFiles(self, data):
        
        self.App.PauseLoadingButton.show()
        self.App.ContinueLoadingButton.hide()
        self.App.CancelLoadingButton.hide()
        
        self.__pause = False
        self.__cancel = False
        
        self.DataQueue.append(data)
        
    def Pause(self):
        self.__pause = True
        self.__cancel = False
        
        self.App.PauseLoadingButton.hide()
        self.App.ContinueLoadingButton.show()
        self.App.CancelLoadingButton.show()
        
    def Cancel(self):
        self.__pause = False
        self.__cancel = True
        
        self.App.PauseLoadingButton.hide()
        self.App.ContinueLoadingButton.hide()
        self.App.CancelLoadingButton.hide()
        
    def Continue(self):
        self.__pause = False
        self.__cancel = False
        
        self.App.PauseLoadingButton.show()
        self.App.ContinueLoadingButton.hide()
        self.App.CancelLoadingButton.hide()
        
    def start(self):
        
        if self.isRunning():
            return
            
        super().start()
        
    def run(self):
        
        self.__count = 0
        self.__totalFiles = 0
        
        for data in self.DataQueue:
            self.__totalFiles += len(data[0])
        
        self.App.progressSignal.emit(0.0)
        
        while(len(self.DataQueue) > 0):
            
            self.__loadData(self.DataQueue.pop(0))
            
            
        self.App.PauseLoadingButton.hide()
        self.App.ContinueLoadingButton.hide()
        self.App.CancelLoadingButton.hide()
        
        self.App.progressSignal.emit(100.0)
        
        self.App.UpdatePlotButns()
        
        # self.App.PlotNewFile()
        
    def __loadData(self, data):
        
        filePaths, fileType, isNewData = data
        
        if type(fileType) != DATA_FILE_TYPE:
            return
            
        if type(isNewData) != bool:
            return
        
        if len(filePaths) < 1:
            return
            
        self.App.progressSignal.emit(100 * self.__count / self.__totalFiles)
        
        if fileType == DATA_FILE_TYPE.CONTINUUM:
            
            if isNewData:
                self.App.ContinuumFilePaths = []
                
                self.App.ContinuumSpectraImages = []
                self.App.ContinuumLineSpectra = []
                
            for filePath in filePaths:
                
                while self.__pause:
                    time.sleep(0.1)
                    
                if self.__cancel:
                    self.App.progressSignal.emit(100)
                    break
               
                if filePath not in self.App.ContinuumFilePaths:
                    self.App.ContinuumFilePaths.append(filePath)
                
                image = self.GetImageSpecData(filePath)
                
                if len(image) > 0:
                    self.App.ContinuumSpectraImages.append(image)
                    
                    # lineSpec = self.GetLineSpecData(image)
                    # self.App.ContinuumLineSpectra.append(lineSpec)
                    
                self.__count += 1
                
                self.App.progressSignal.emit(100 * self.__count / self.__totalFiles)
                    
            # update gui for available data
            self.App.ContinuumFileComboBox.clear()  
            self.App.ContinuumFileComboBox.addItems(self.GetFileNameFromPaths(self.App.ContinuumFilePaths))

            self.App.SaveFileData(self.App.ContinuumFilesPath, self.App.ContinuumFilePaths)
            
            self.App.LastDirectory = os.path.dirname(filePaths[0])
            self.App.SaveFileData(self.App.LastDirectoryPath, [self.App.LastDirectory])
            
        elif fileType == DATA_FILE_TYPE.ABSORBTION:
            
            if isNewData:
                self.App.AbsorbtionFilePaths = []
                
                self.App.AbsorbtionSpectraImages = []
                self.App.AbsorbtionLineSpectra = []
                
            for filePath in filePaths:
                
                while self.__pause:
                    time.sleep(0.1)
                    
                if self.__cancel:
                    self.App.progressSignal.emit(100)
                    break
                
                if filePath not in self.App.AbsorbtionFilePaths:
                    self.App.AbsorbtionFilePaths.append(filePath)
                    
                image = self.GetImageSpecData(filePath)
                
                if len(image) > 0:
                    self.App.AbsorbtionSpectraImages.append(image)
                    
                    # lineSpec = self.GetLineSpecData(image)
                    # self.App.AbsorbtionLineSpectra.append(lineSpec)
                
                self.__count += 1
                
                self.App.progressSignal.emit(100 * self.__count / self.__totalFiles)
            
             # update gui for available data
            self.App.AbsorbtionFileComboBox.clear()
            self.App.AbsorbtionFileComboBox.addItems(self.GetFileNameFromPaths(self.App.AbsorbtionFilePaths))

            self.App.SaveFileData(self.App.AbsorbtionFilesPath, self.App.AbsorbtionFilePaths)

            self.App.LastDirectory = os.path.dirname(filePaths[0])
            self.App.SaveFileData(self.App.LastDirectoryPath, [self.App.LastDirectory])
        
    def GetFileNameFromPaths(self, filePaths):
        fileNames = []
        for path in filePaths:
           
            fileName = self.GetFileNameFromPath(path)           
            
            if fileName != "":
                fileNames.append(fileName)
            
        return fileNames
        
    def GetFileNameFromPath(self, path):
        
        if not os.path.isfile(path):
            raise FileExistsError(f"File doesn't exist: {path}")
        
        if path[-4:] == ".txt":
            return os.path.basename(path)[:-4]
                
        elif path[-5:] == ".fits":
            return os.path.basename(path)[:-5]
            
        else:
            raise NameError(f'Path extension not allowed: {path}')
        
    def GetImageSpecData(self, filepath):
        
        if filepath[-4:] == ".txt":
            
            data = self. __getData(filepath)
            new_data = []

            for line in data:
                float_line = []
                for value in line:
                    float_line.append(float(value))
                
                new_data.append(float_line)
                
            return np.array(new_data)
                
        elif filepath[-5:] == ".fits":
            with fits.open(filepath) as f:
                data = f[0].data
                # header = f[0].header
            return np.array(data[0], dtype='float64')
        else:
            raise NameError(f'Path extension not allowed: {filepath}')
        
    # def GetLineSpecData(self, image):
            
    #     line_spectra = []
    #     for line in image:
    #         line_spectra.append(sum(line))
            
    #     return np.array(line_spectra)
    
    def __getData(self, path):
        
        data = []
        if not os.path.isfile(path):
            raise FileExistsError(f"File doesn't exist: {path}")
            
        with open(path) as fp:
            for cnt, line in enumerate(fp):
                data.append(line[:-1].split(','))
        return data
        
        

############################### THREADING CLASS ###############################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
###############################################################################

        
###############################################################################
############################## Utility Functions ##############################
        
def test(_string, _num): # update v0.4
    print (_string + ": " + str(_num))
        
def exit_handler(app):
    app.close_app()

    
def add_Button(App, name, objName, layout, minSize, maxSize):
    Button = QtWidgets.QPushButton(App)
    Button.setEnabled(True)
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(Button.sizePolicy().hasHeightForWidth())
    Button.setSizePolicy(sizePolicy)
    Button.setMinimumSize(QtCore.QSize(minSize[0], minSize[1]))
    Button.setMaximumSize(QtCore.QSize(maxSize[0], maxSize[1]))
    Button.setAutoFillBackground(False)
    Button.setObjectName(_fromUtf8(objName)) 
    Button.setText(_translate("MainMenu", name, None))
    if layout != None:
        layout.addWidget(Button)    
        
    return Button
    
def add_ComboBox(App, options, layout, minSize, maxSize):
    ComboBox = QtWidgets.QComboBox(App)
    ComboBox.setEnabled(True)
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
#    sizePolicy.setHeightForWidth(ComboBox.sizePolicy().hasHeightForWidth())
    ComboBox.setSizePolicy(sizePolicy)
    ComboBox.setMinimumSize(QtCore.QSize(minSize[0], minSize[1]))
    ComboBox.setMaximumSize(QtCore.QSize(maxSize[0], maxSize[1]))
#        TextBrowser.setObjectName(_fromUtf8("textBrowser"))
        
    for o in options:
        ComboBox.addItem(str(o))
            
    if layout != None:
        layout.addWidget(ComboBox)
        
    return ComboBox
        
def add_Label(App, name, layout, Max):
    label = QtWidgets.QLabel(App)
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(label.sizePolicy().hasHeightForWidth())
    label.setSizePolicy(sizePolicy)
    label.setMinimumSize(QtCore.QSize(Max[0], 20))
    label.setMaximumSize(QtCore.QSize(Max[0], Max[1]))
    label.setAlignment(QtCore.Qt.AlignCenter)
    label.setText(name)
       
    if layout != None:
        layout.addWidget(label)  
#    layout.addWidget(label)
    
    return label
    
def add_TextEdit(App, name, layout, Max):
    TextEdit = QtGui.QTextEdit(App)
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(TextEdit.sizePolicy().hasHeightForWidth())
    TextEdit.setSizePolicy(sizePolicy)
    TextEdit.setMinimumSize(QtCore.QSize(0, Max[1]))
    TextEdit.setMaximumSize(QtCore.QSize(Max[0], Max[1]))
#    TextEdit.setAlignment(QtCore.Qt.AlignCenter)
    if name != None:
        TextEdit.setText(name) 
         
    if layout != None:
        layout.addWidget(TextEdit)  
        
    return TextEdit
    
def add_SpinBox( value, layout, Max):
    spinBox = QtWidgets.QDoubleSpinBox()
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(spinBox.sizePolicy().hasHeightForWidth())
    spinBox.setSizePolicy(sizePolicy)
    spinBox.setMinimumSize(QtCore.QSize(Max[0], Max[1]))
    spinBox.setMaximumSize(QtCore.QSize(Max[0], Max[1]))
         
    if layout != None:
        layout.addWidget(spinBox)  
        
    spinBox.setRange(-20, 20)
    spinBox.setSingleStep(0.1)
    spinBox.setValue(value)
#    spinBox.setMinimumSize(75,25)
#    spinBox.setMaximumSize(75,25)
        
    return spinBox

    
def prepare_data(args): # *args converts to a tuple 
    data = []
    for arg in args:
        data.append(arg)
    
    data = np.array(data)
    return data

def read_txt_file(path): # , fmt
    
    if not os.path.isfile(path):
        print(f"Path doesn't exist: {path}")
        return
    
    data = []
    with open(path, 'r+') as fp:
        for cnt, line in enumerate(fp):
            data.append(line[:-1].split('\t'))
                
    return np.array(data, dtype=object)

#     data = []
    
#     try:
#         my_file = Path(datafile_path)
#         if my_file.is_file():
#             with open(datafile_path, 'r+') as data_load:
#                 for line in data_load:
#                     fields = line[:-1].split('\t')
#                     data.append(fields)
                
#     except IOError as x: # update v0.54 
#         if x.errno == errno.ENOENT: # update v0.54 
#             print (datafile_path, '- does not exist') # update v0.54 
#         elif x.errno == errno.EACCES: # update v0.54 
#             print (datafile_path, '- cannot be read') # update v0.54 
#         else: # update v0.54 
#             print (datafile_path, '- some other error') # update v0.54 
# #        print ("read_txt_file error")
# #        print (datafile_path) # update v0.53 

#     if data:
#         data = np.array(data)
#         data = format_array(data,fmt) 
        
#     return data
    
def write_txt_file(datafile_path, data, empty=False):
    
    length = 1 # update v0.54 
    if type(data) == np.ndarray or type(data) == list: # update v0.54 
        if len(data) > 0: # update v0.54 
            if type(data[0]) == np.ndarray or type(data[0]) == list: # update v0.54 
                length = len(data[0]) # update v0.54 
    
        
    
    with open(datafile_path, 'w+') as datafile_id:
        
        if not empty:
            np.savetxt(datafile_id, data, fmt=['%s']*length, delimiter='\t') # update v0.54 
        else:
            np.savetxt(datafile_id, [], delimiter='\t')

def format_array(array, array_fmt):
    array = np.array(array)    
    array = array.T

    new_array = []
    
    for col, fmt  in zip(array, array_fmt):
        col_fmt = []
        
        if fmt == "%i":
            for i in col:
                col_fmt.append(int(i))
        elif fmt == "%s":
            for s in col:
                col_fmt.append(str(s))
        else:
            print ("array_fmt error")
            
        new_array.append(col_fmt)
        
        array_transpose = map(list, zip(*new_array))
    
    return array_transpose


def get_file_names(path, extension):
        
    all_files = os.listdir( path )
    file_names = []
    
    for name in all_files:
        name = name
        
        if len(name) > 4:
            if name[-4:] == extension:
                name = name[:-4]
                file_names.append(name)
                
    return file_names
        
        
###############################################################################        
MenuStyleSheet = """
        QMenuBar {
            background-color: rgb(90,90,90);
            color: rgb(220,220,220);
            border: 1px solid #555555;
        }

        QMenuBar::item {
            background-color: rgb(90,90,90);
            color: rgb(240,240,240);
        }

        QMenuBar::item::selected {
            background-color: rgb(30,30,30);
        }

        QMenu {
            background-color: rgb(90,90,90);
            color: rgb(240,240,240);
            border: 1px solid #555555;           
        }

        QMenu::item::selected {
            background-color: rgb(30,30,30);
        }
    """
pass # update v0.4
GroupBoxStyleSheet = """
        QGroupBox#ColoredGroupBox {  
            border: 2px solid #AAAAAA; 
            border-radius: 3px;
            margin-top: 2.5ex;
            font: bold;
            font-size: 10pt; 
            font-family: Courier;
        }
        
        QGroupBox#ColoredGroupBox:title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 7px;
        }
        
    """    
pass # update v0.4   
DragGroupBoxStyleSheet = """
        QGroupBox#ColoredDragGroupBox {  
            background-color: rgb(240,240,240);
            border: 2px solid gray; 
            border-radius: 3px;
            margin-top: 2.5ex;
            font: bold;
            font-size: 10pt; 
            font-family: MS Shell Dlg 2;
        }
        
        QGroupBox#ColoredDragGroupBox:title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 7px;
        }
        
    """ 
    
    
############################## Utility Functions ##############################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
###############################################################################


###############################################################################
################################## GUI CLASS ##################################

class UiMainMenu( QtWidgets.QMainWindow, QtWidgets.QWidget ): 
    
    progressSignal = QtCore.pyqtSignal(float)
    
    def  __init__(self, parent=None):
        super(UiMainMenu, self).__init__(parent=parent)
        
        self.setup_ui()
                                        
        self.set_parameters()  
     
        self.setup_tabs()

        self.showMaximized()

    def get_directory_dialogue(self):
        path_inconfirmed = True
        
        while path_inconfirmed:
        
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")   
            
            if os.path.exists(path):
                # if relevant folders exist
                if os.path.isfile(path + "/Database/File_Saves/config.txt"): 
                    path_inconfirmed = False
                    
        return path
        
    def contains_necessary_files(self, path): # update v0.4
        necessary_files = ["/Database/File_Saves/config.txt"]
        
        for FILE in necessary_files:
            if not os.path.isfile(path + FILE):  
                return False
                
        return True

    def check_current_directory(self): # update v0.4
        
        if self.contains_necessary_files(self.PROJECT_DIRECTORY):  
            return self.PROJECT_DIRECTORY
        else:
            self.get_directory_dialogue()

    def get_project_directory(self):
        
        if os.path.isfile("C:/SpecLab/PROJECT_DIRECTORY.txt"):
            PROJECT_DIRECTORY = read_txt_file("C:/SpecLab/PROJECT_DIRECTORY.txt")
            if PROJECT_DIRECTORY:
                if os.path.exists(PROJECT_DIRECTORY[0][0]):
                    # if SpecLab path mathces the current PROJECT_DIRECTORY
                    if self.PROJECT_DIRECTORY == PROJECT_DIRECTORY[0][0]: # update v0.4
                        # if relevant folders exist
                        if self.contains_necessary_files(PROJECT_DIRECTORY[0][0]):  # update v0.4
                            return PROJECT_DIRECTORY[0][0]

            
        return self.check_current_directory() # update v0.4
        
    def set_parameters(self):     
        
        self.PROJECT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
        
        self.PROJECT_DATABASE = self.PROJECT_DIRECTORY + "/Database"
        
        self.targetDirectory = 'OneDrive'
        self.targetDirectoryOnPC = os.path.abspath('').replace('\\', '/')
        
        self.DATA_LOADER = DataLoader(self) 
        
        self.progressSignal.connect(self.updateProgress)
        
        if self.targetDirectory in self.targetDirectoryOnPC:
            start_index = self.targetDirectoryOnPC.index(self.targetDirectory)

            if start_index <= len(self.targetDirectoryOnPC):
                self.targetDirectoryOnPC = self.targetDirectoryOnPC[:start_index]
                
#        print (self.targetDirectoryOnPC, '\n')
        
        self.Target_Names = []
        
        self.CurrentActiveContinuumFileName = ""
        self.CurrentActiveAbsorbtionFileName = ""
        
        self.minX = 0
        self.maxX = 1024
        
        self.ContinuumFilePaths = []
        self.AbsorbtionFilePaths = []
        
        self.ContinuumSpectraImages = []
        self.AbsorbtionSpectraImages = []
        self.CurrentContinuumImage = []
        self.CurrentAbsorbtionImage = []
        
        
        # self.ContinuumLineSpectra = []
        # self.AbsorbtionLineSpectra = []
        self.ContinuumFilesPath = "config/ContinuumFiles.txt"
        self.AbsorbtionFilesPath = "config/AbsorbtionFiles.txt"
        
        self.Last_X_Axis_Bounds_Path = "config/Last_X_Axis_Bounds.txt"
        self.Last_Y_Axis_Bounds_Path = "config/Last_Y_Axis_Bounds.txt"
        
        self.CalibrationToggledPath = "config/CalibrationToggled.txt"
        self.CalibrationDataPath = "config/CalibrationData.txt"
        
        self.AutoCropConfigPath = "config/AutoCropConfig.txt"
        
        self.forwardIcon = QtGui.QIcon()
        self.forwardIcon.addPixmap(QtGui.QPixmap(_fromUtf8("forward_large.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.backIcon = QtGui.QIcon()
        self.backIcon.addPixmap(QtGui.QPixmap(_fromUtf8("back_large.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
#        self.LastContinuumDirectoryPath = "config/LastContinuumDirectory.txt"
#        self.LastAbsorbtionDirectoryPath = "config/LastAbsorbtionDirectory.txt"
#        self.LastContinuumDirectory = self.LoadFileData(self.LastContinuumDirectoryPath, 1)[0]
#        self.LastAbsorbtionDirectory = self.LoadFileData(self.LastAbsorbtionDirectoryPath, 1)[0]

        self.LastImageDirectoryPath = "config/LastImageDirectory.txt"
        self.LastImageDirectory = ""
        
        LastImageDirectory = self.LoadFileData(self.LastImageDirectoryPath, 1)
        if len(LastImageDirectory) > 0:
            self.LastImageDirectory = LastImageDirectory[0]
        

        self.LastDirectoryPath = "config/LastDirectory.txt"
        self.LastDirectory = self.LoadFileData(self.LastDirectoryPath, 1)[0]
        
        self.CurrentContinuumData = []
        self.CurrentAbsorbtionData = []
        self.X_AxisData = []
        self.CurrentAbsorbtionFeatureData = []
        self.CurrentAbsorbtionFilterData = []
        
        self.CalculateAbsorbtionFeatureData = False
        
    def setup_ui(self):        
        #MainMenu = self.MainMenu
        self.setObjectName(_fromUtf8("MainMenu"))
        self.setEnabled(True)
        #self.resize(500, 500)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        
        self.setSizePolicy(sizePolicy)
        
        self.setMinimumSize(QtCore.QSize(1800, 1000))
        self.setMaximumSize(QtCore.QSize(1800, 1000)) #720
        
        ICON = QtGui.QIcon()
        ICON.addPixmap(QtGui.QPixmap(_fromUtf8("SpeclabIcon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off) # update v0.4
        self.setWindowIcon(ICON)
        
        self.setWindowTitle(_translate("MainMenu", "SpecView: AbsorbtionView", None))
        
        QtCore.QMetaObject.connectSlotsByName(self)
        
    def setup_tabs(self):
        self.ControlTab = QtWidgets.QWidget()

        self.SetMainTab()
       
        self.setCentralWidget(self.ControlTab) 
        
        self.LoadPreviousDataFiles()
        
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#

#     def nicholaButton(self):
#         dataPath = "D:/OneDrive - University College Dublin/College/UCD/PhD/Software/_Python3/CowanCombiner/ExperimentalData/Pt60ns4sec46_LineSpec_eV.txt"
        
#         if not os.path.isfile(dataPath):
#             return
        
#         readData = read_txt_file(dataPath)
        
#         xData = []
#         yData = []
#         for data in readData:
#             xData.append(float(data[0]) - 0.7)
#             yData.append(float(data[1]))
        
#         # dataPath = "D:/OneDrive - University College Dublin/College/UCD/PhD/Software/_Python3/CowanCombiner/ExperimentalData/Pt60ns4sec46_LineSpec_shifted_-0.7eV.txt"
#         # data = np.array([xData, yData]).T
#         # write_txt_file(dataPath, data)
        
        
#         self.AbsorbtionGraph.clf()
        
#         ax = self.AbsorbtionGraph.add_subplot(111)
#         ax.clear()
#         ax.plot(xData, yData, "k-" )
        
#         ax.set_xlim([65.74608629675947, 130.40499151013273]) 
#         ax.set_ylim([0, 1.5])
# #        ax.set_title('Photon Intensity Vs Photon Energy')

#         ax.set_xlabel('Energy [eV]')
#         ax.set_ylabel('Intensity [Arb.]') # 'Cross Section [Mb]'
        
#         x = self.AbsorbtionSpectraToolbar.configure_subplots()
#         x._tight_layout()
#         x.close() 
        
#         self.AbsorbtionCanvas.draw()
    
    def SetMainTab(self):
        
        ControlTabLayout = QtWidgets.QVBoxLayout()
        
        fileInfoLayout = QtWidgets.QHBoxLayout()
        CanvasGroupLayout = QtWidgets.QHBoxLayout()
        
        LoadingLayout = QtWidgets.QVBoxLayout()
        LoadingButtonLayout = QtWidgets.QHBoxLayout()
        
        SpectraCanvasLayout = QtWidgets.QVBoxLayout()
        AbsorbtionCanvasLayout = QtWidgets.QVBoxLayout()
        
        CanvasGroupLayout.addLayout(SpectraCanvasLayout)
        CanvasGroupLayout.addLayout(AbsorbtionCanvasLayout)
        
        ContinuumFileLayout = QtWidgets.QVBoxLayout()
        ContinuumFileButtonLayout = QtWidgets.QHBoxLayout()
        ContinuumFileSelectLayout = QtWidgets.QHBoxLayout()
        
        
        AbsorbtionFileLayout = QtWidgets.QVBoxLayout()
        AbsorbtionFileButtonLayout = QtWidgets.QHBoxLayout()
        AbsorbtionFileSelectLayout = QtWidgets.QHBoxLayout()
        
        PlotButtonLayout = QtWidgets.QHBoxLayout()
        
        ############################ Plot Spectra #############################
        
        PlotSpectra_GroupBox = QtWidgets.QGroupBox("Plot Spectra") 
        PlotSpectra_GroupBox.setObjectName("ColoredDragGroupBox") 
        PlotSpectra_GroupBox.setStyleSheet(DragGroupBoxStyleSheet)       
        
        PlotSpectra_GroupBox.setMaximumWidth(120)

        self.PlotButton = add_Button(self,"Plot","PlotButton", None, [100,69], [100,69])
        self.PlotButton.setMinimumSize(QtCore.QSize(100, 69)) #62
        self.PlotButton.clicked.connect(self.PlotNewFile)
        
        PlotButtonLayout.addWidget(self.PlotButton, alignment = QtCore.Qt.AlignVCenter)
        
        PlotSpectra_GroupBox.setLayout(PlotButtonLayout)
        
        #######################################################################
        
        ########################### Continuum Files ###########################
        
        ContinuumFile_GroupBox = QtWidgets.QGroupBox("Continuum Files") 
        ContinuumFile_GroupBox.setObjectName("ColoredDragGroupBox") 
        ContinuumFile_GroupBox.setStyleSheet(DragGroupBoxStyleSheet)       

        self.ContinuumNewFileButton = add_Button(self,"Load New Files","ContinuumNewFileButton", None, [130,30], [130,30])
        self.ContinuumNewFileButton.clicked.connect(partial(self.LoadDataFilesDialogue, DATA_FILE_TYPE.CONTINUUM, True))
        
        self.ContinuumAddFileButton = add_Button(self,"Add Files","ContinuumAddFileButton", None, [130,30], [130,30])
        self.ContinuumAddFileButton.clicked.connect(partial(self.LoadDataFilesDialogue, DATA_FILE_TYPE.CONTINUUM, False))
        
        
        #################
        
        self.CalibrateWavelengthButton = add_Button(self,"Calibrate Wavelength","CalibrateWavelengthButton", None, [130,30], [130,30])
        self.CalibrateWavelengthButton.clicked.connect(self.ToggleWavelengthCalibration)
        
        A,B,C = (0,0,0)
        
        self.Coefficient_A_SpinBox = add_SpinBox(0, None, [120, 30])
        self.Coefficient_A_SpinBox.setDecimals(10)
        self.Coefficient_A_SpinBox.setSingleStep(0.0000001)
        self.Coefficient_A_SpinBox.setPrefix('A: ')
        
        self.Coefficient_B_SpinBox = add_SpinBox(0, None, [100, 30])
        self.Coefficient_B_SpinBox.setDecimals(7)
        self.Coefficient_B_SpinBox.setSingleStep(0.0001)
        self.Coefficient_B_SpinBox.setPrefix('B: ')
        
        self.Coefficient_C_SpinBox = add_SpinBox(0, None, [93, 30])
        self.Coefficient_C_SpinBox.setDecimals(6)
        self.Coefficient_C_SpinBox.setSingleStep(1)
        self.Coefficient_C_SpinBox.setPrefix('C: ')
        
        self.WavelengthUnitsComboBox = add_ComboBox(self, ['nm', 'eV'], None, [50,20], [50,20])
            
        self.IsWavelengthCalibrated = True
        
        previousData = self.__readTxtFile(self.CalibrationToggledPath)[0]
        
        calibrationData = self.__readTxtFile(self.CalibrationDataPath)
        
        date = previousData[2]
        
        dateExists = False
        saveDataIndex = -1
        
        for i in range(len(calibrationData)):
            if date == calibrationData[i][0]:
                dateExists = True
                saveDataIndex = i
        
        if dateExists:
            
            self.currentDate = date
            
            values = calibrationData[saveDataIndex]
            A = float(values[1])
            B = float(values[2])
            C = float(values[3])
        
        
        self.Coefficient_A_SpinBox.setValue(A)
        self.Coefficient_B_SpinBox.setValue(B)
        self.Coefficient_C_SpinBox.setValue(C)
        
        index = self.WavelengthUnitsComboBox.findText(previousData[1], QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.WavelengthUnitsComboBox.setCurrentIndex(index)
        
        if not bool(previousData[0]):
            self.ToggleWavelengthCalibration()
        
        #######################
        
        self.ContinuumFileComboBox = add_ComboBox(self,[], ContinuumFileSelectLayout, [130,30], [750,30])
        self.ContinuumFileComboBox.currentIndexChanged.connect(self.CheckPlotButtonSelectability)
        
        self.plotPreviousContinuumBtn = add_Button(self, None, "plotPreviousContinuumBtn", ContinuumFileSelectLayout, [32, 32], [32, 32])
        self.plotPreviousContinuumBtn.clicked.connect(partial(self.PlotNextFile, "back", DATA_FILE_TYPE.CONTINUUM))
        self.plotPreviousContinuumBtn.setIcon(self.backIcon)
        self.plotPreviousContinuumBtn.setEnabled(False)
        
        self.plotNextContinuumBtn = add_Button(self, None, "plotNextContinuumBtn", ContinuumFileSelectLayout, [32, 32], [32, 32])
        self.plotNextContinuumBtn.clicked.connect(partial(self.PlotNextFile, "forward", DATA_FILE_TYPE.CONTINUUM))
        self.plotNextContinuumBtn.setIcon(self.forwardIcon)
        self.plotNextContinuumBtn.setEnabled(False)
        
        ContinuumFileButtonLayout.addWidget(self.ContinuumNewFileButton)
        ContinuumFileButtonLayout.addWidget(self.ContinuumAddFileButton)
        
        
        ContinuumFileButtonLayout.addWidget(self.CalibrateWavelengthButton)
        ContinuumFileButtonLayout.addWidget(self.WavelengthUnitsComboBox)
        
        
        ContinuumFileButtonLayout.addItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        
        ContinuumFileLayout.addLayout(ContinuumFileButtonLayout)
        ContinuumFileLayout.addLayout(ContinuumFileSelectLayout) 
        
        ContinuumFile_GroupBox.setLayout(ContinuumFileLayout)
        
        #######################################################################
        
        ########################### Absorbtion Files ##########################
        
        AbsorbtionFile_GroupBox = QtWidgets.QGroupBox("Absorbtion Files") 
        AbsorbtionFile_GroupBox.setObjectName("ColoredDragGroupBox") 
        AbsorbtionFile_GroupBox.setStyleSheet(DragGroupBoxStyleSheet) 
        
        self.AbsorbtionNewFileButton = add_Button(self,"Load New Files","AbsorbtionNewFileButton", None, [130,30], [130,30])
        self.AbsorbtionNewFileButton.clicked.connect(partial(self.LoadDataFilesDialogue, DATA_FILE_TYPE.ABSORBTION, True))
        
        self.AbsorbtionAddFileButton = add_Button(self,"Add Files","AbsorbtionAddFileButton", None, [130,30], [130,30])
        self.AbsorbtionAddFileButton.clicked.connect(partial(self.LoadDataFilesDialogue, DATA_FILE_TYPE.ABSORBTION, False))

        self.AbsorbtionFileComboBox = add_ComboBox(self, [], AbsorbtionFileSelectLayout, [130,30], [750,30]) # [330,30]
        self.AbsorbtionFileComboBox.currentIndexChanged.connect(self.CheckPlotButtonSelectability)
        
        self.plotPreviousAbsorptionBtn = add_Button(self, None, "plotPreviousAbsorptionBtn", AbsorbtionFileSelectLayout, [32, 32], [32, 32])
        self.plotPreviousAbsorptionBtn.clicked.connect(partial(self.PlotNextFile, "back", DATA_FILE_TYPE.ABSORBTION))
        self.plotPreviousAbsorptionBtn.setIcon(self.backIcon)
        self.plotPreviousAbsorptionBtn.setEnabled(False)
        
        self.plotNextAbsorptionBtn = add_Button(self, None, "plotNextAbsorptionBtn", AbsorbtionFileSelectLayout, [32, 32], [32, 32])
        self.plotNextAbsorptionBtn.clicked.connect(partial(self.PlotNextFile, "forward", DATA_FILE_TYPE.ABSORBTION))
        self.plotNextAbsorptionBtn.setIcon(self.forwardIcon)
        self.plotNextAbsorptionBtn.setEnabled(False)
        
        # nicholaButton = add_Button(self,"nicholaButton","ContinuumAddFileButton", None, [130,30], [130,30])
        # nicholaButton.clicked.connect(self.nicholaButton)
        
        AbsorbtionFileButtonLayout.addWidget(self.AbsorbtionNewFileButton)
        AbsorbtionFileButtonLayout.addWidget(self.AbsorbtionAddFileButton)
        # AbsorbtionFileButtonLayout.addWidget(nicholaButton)
        
        AbsorbtionFileButtonLayout.addItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        
        AbsorbtionFileLayout.addLayout(AbsorbtionFileButtonLayout)
        AbsorbtionFileLayout.addLayout(AbsorbtionFileSelectLayout)
        
        
        AbsorbtionFile_GroupBox.setLayout(AbsorbtionFileLayout)
        
#        newfont = QtGui.QFont("MS Shell Dlg 2", 32, QtGui.QFont.Bold)  # update v0.4
#        self.ContinuumFileLabel.setFont(newfont)
#        self.ContinuumFileLabel.setStyleSheet('color: red; border: 2px solid gray; border-radius: 3px;')
        
        #######################################################################
        
        ######################### Loading Progress ############################
        
        Loading_GroupBox = QtWidgets.QGroupBox("Progress") 
        Loading_GroupBox.setObjectName("ColoredDragGroupBox") 
        Loading_GroupBox.setStyleSheet(DragGroupBoxStyleSheet) 
        
        Loading_GroupBox.setMaximumWidth(500)
        
        self.ProgressBar = QtWidgets.QProgressBar(self)
        self.ProgressBar.setValue(100)
        
        self.PauseLoadingButton = add_Button(self,"Pause","PauseLoadingButton", None, [130,30], [130,30])
        self.PauseLoadingButton.clicked.connect(self.DATA_LOADER.Pause)
        
        self.ContinueLoadingButton = add_Button(self,"Continue","ContinueLoadingButton", None, [130,30], [130,30])
        self.ContinueLoadingButton.clicked.connect(self.DATA_LOADER.Continue)
        
        self.CancelLoadingButton = add_Button(self,"Cancel","CancelLoadingButton", None, [130,30], [130,30])
        self.CancelLoadingButton.clicked.connect(self.DATA_LOADER.Cancel)

        LoadingButtonLayout.addItem(QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        LoadingButtonLayout.addWidget(self.PauseLoadingButton)
        LoadingButtonLayout.addWidget(self.ContinueLoadingButton)
        LoadingButtonLayout.addWidget(self.CancelLoadingButton)
        
        self.PauseLoadingButton.hide()
        self.ContinueLoadingButton.hide()
        self.CancelLoadingButton.hide()
        
        # for i in range(LoadingButtonLayout.count()):
        #     print(type(LoadingButtonLayout.itemAt(i)))   # .widget() .hide()
        
        LoadingLayout.addWidget(self.ProgressBar) #needs thread ?
        LoadingLayout.addLayout(LoadingButtonLayout)
        
        Loading_GroupBox.setLayout(LoadingLayout)
        
        #######################################################################
        
        ########################### Spectra Image #############################
        
        xVals = self.__readTxtFile(self.Last_X_Axis_Bounds_Path)#[0]
        yVals = self.__readTxtFile(self.Last_Y_Axis_Bounds_Path)#[0]
        
        minX = int(xVals[0][0])
        maxX = int(xVals[1][0])
        minY = int(yVals[0][0])
        maxY = int(yVals[1][0])
        

        SpectraImage_GroupBox = QtWidgets.QGroupBox("Spectra Image") 
        SpectraImage_GroupBox.setObjectName("ColoredDragGroupBox") 
        SpectraImage_GroupBox.setStyleSheet(DragGroupBoxStyleSheet)         
        
        self.SpectraImageGraph = Figure()
        self.SpectraImageCanvas = FigureCanvas(self.SpectraImageGraph)
        
        toolbar = NavigationToolbar(self.SpectraImageCanvas, self)
        
        
        toolbar.addSeparator()
        
        ##
        
        self.AutoCropCheckBox = QtWidgets.QCheckBox("Auto Crop")
        self.AutoCropCheckBox.setChecked(bool(self.LoadFileData(self.AutoCropConfigPath, 1)[0]))
        self.AutoCropCheckBox.clicked.connect(self.SaveAutoCropConfig)
        
        toolbar.addWidget(self.AutoCropCheckBox)
        
        
        toolbar.addSeparator()
        
        spinBoxSize = QtCore.QSize(86, 30)
        
        
        self.SpectraImageMinX_SpinBox = QtWidgets.QSpinBox() 
        self.SpectraImageMinX_SpinBox.setRange(0, 2048)
        self.SpectraImageMinX_SpinBox.setSingleStep(5)
        self.SpectraImageMinX_SpinBox.setMinimumSize(spinBoxSize)
        self.SpectraImageMinX_SpinBox.setMaximumSize(spinBoxSize)
        self.SpectraImageMinX_SpinBox.setPrefix("min X: ") 
        
        self.SpectraImageMinX_SpinBox.valueChanged.connect(self.UpdateMaxX)
        self.SpectraImageMinX_SpinBox.valueChanged.connect(self.PlotSpectraImage)
        
        toolbar.addWidget(self.SpectraImageMinX_SpinBox)
        
        
        toolbar.addSeparator()
        
        
        self.SpectraImageMaxX_SpinBox = QtWidgets.QSpinBox() 
        self.SpectraImageMaxX_SpinBox.setRange(10, 2048)
        self.SpectraImageMaxX_SpinBox.setSingleStep(5)
        self.SpectraImageMaxX_SpinBox.setMinimumSize(spinBoxSize)
        self.SpectraImageMaxX_SpinBox.setMaximumSize(spinBoxSize)
        self.SpectraImageMaxX_SpinBox.setPrefix("max X: ") 
        
        self.SpectraImageMaxX_SpinBox.valueChanged.connect(self.UpdateMinX)
        self.SpectraImageMaxX_SpinBox.valueChanged.connect(self.PlotSpectraImage)

        toolbar.addWidget(self.SpectraImageMaxX_SpinBox)
        
        
        toolbar.addSeparator()
        
        
        self.SpectraImageMinY_SpinBox = QtWidgets.QSpinBox() 
        self.SpectraImageMinY_SpinBox.setRange(0, 2048)
        self.SpectraImageMinY_SpinBox.setSingleStep(5)
        self.SpectraImageMinY_SpinBox.setMinimumSize(spinBoxSize)
        self.SpectraImageMinY_SpinBox.setMaximumSize(spinBoxSize)
        self.SpectraImageMinY_SpinBox.setPrefix("min Y: ") 
         
        self.SpectraImageMinY_SpinBox.valueChanged.connect(self.UpdateMaxY)
        # self.SpectraImageMinY_SpinBox.valueChanged.connect(self.PlotSpectraImage)
#        self.SpectraImageMinY_SpinBox.valueChanged.connect(self.PlotLineSpectra)
#        self.SpectraImageMinY_SpinBox.valueChanged.connect(self.PlotAbsorbtionSpectra)
#        self.SpectraImageMinY_SpinBox.valueChanged.connect(self.PlotAbsorbtionSpectraBaseline)
        
        toolbar.addWidget(self.SpectraImageMinY_SpinBox)
        
        
        toolbar.addSeparator()
        
        
        self.SpectraImageMaxY_SpinBox = QtWidgets.QSpinBox() 
        self.SpectraImageMaxY_SpinBox.setRange(10, 2048)
        self.SpectraImageMaxY_SpinBox.setSingleStep(5)
        self.SpectraImageMaxY_SpinBox.setValue(1024)
        self.SpectraImageMaxY_SpinBox.setMinimumSize(spinBoxSize)
        self.SpectraImageMaxY_SpinBox.setMaximumSize(spinBoxSize)
        self.SpectraImageMaxY_SpinBox.setPrefix("max Y: ") 

        self.SpectraImageMaxY_SpinBox.valueChanged.connect(self.UpdateMinY)
        # self.SpectraImageMaxY_SpinBox.valueChanged.connect(self.PlotSpectraImage)
#        self.SpectraImageMaxY_SpinBox.valueChanged.connect(self.PlotLineSpectra)
#        self.SpectraImageMaxY_SpinBox.valueChanged.connect(self.PlotAbsorbtionSpectra)
#        self.SpectraImageMaxY_SpinBox.valueChanged.connect(self.PlotAbsorbtionSpectraBaseline)
        
        toolbar.addWidget(self.SpectraImageMaxY_SpinBox)
        
        SpectraImageCanvas_Layout = QtWidgets.QVBoxLayout()
        SpectraImageCanvas_Layout.addWidget(toolbar)
        SpectraImageCanvas_Layout.addWidget(self.SpectraImageCanvas)
        SpectraImage_GroupBox.setLayout(SpectraImageCanvas_Layout)
        
        
        ##
        
        self.SpectraImageMaxY_SpinBox.setValue(maxY)
        self.SpectraImageMinY_SpinBox.setValue(minY)
        self.SpectraImageMaxX_SpinBox.setValue(maxX)
        self.SpectraImageMinX_SpinBox.setValue(minX)
        
        #######################################################################
        
        ############################ Line Spectra #############################
        
        Spectra_GroupBox = QtWidgets.QGroupBox("Line Spectra") 
        Spectra_GroupBox.setObjectName("ColoredDragGroupBox") 
        Spectra_GroupBox.setStyleSheet(DragGroupBoxStyleSheet)         
        
        self.SpectraGraph = Figure()
        self.SpectraCanvas = FigureCanvas(self.SpectraGraph)
        self.LineSpectraToolbar = NavigationToolbar(self.SpectraCanvas, self)

        ####
         
        # self.Saturation_SpinBox = QtWidgets.QSpinBox() 
        # self.Saturation_SpinBox.setRange(0, 1000000)
        # self.Saturation_SpinBox.setSingleStep(10)
        # self.Saturation_SpinBox.setMinimumSize(QtCore.QSize(140, 30))
        # self.Saturation_SpinBox.setMaximumSize(QtCore.QSize(140, 30))
        # self.Saturation_SpinBox.setPrefix("Base Counts: ") 
        
        # self.Saturation_SpinBox.valueChanged.connect(self.UpdateSaturation)

        # self.LineSpectraToolbar.addWidget(self.Saturation_SpinBox)
        
        self.LineSpectraToolbar.addSeparator()
         
        #### 
         
        SpectraCanvas_Layout = QtWidgets.QVBoxLayout()
        SpectraCanvas_Layout.addWidget(self.LineSpectraToolbar)
        SpectraCanvas_Layout.addWidget(self.SpectraCanvas)
        Spectra_GroupBox.setLayout(SpectraCanvas_Layout)
        
        #######################################################################
        
        ######################### Absorbtion Spectra ##########################
        
        Absorbtion_GroupBox = QtWidgets.QGroupBox("Absorbtion Spectra") 
        Absorbtion_GroupBox.setObjectName("ColoredDragGroupBox") 
        Absorbtion_GroupBox.setStyleSheet(DragGroupBoxStyleSheet)        
        
        self.AbsorbtionGraph = Figure()
        self.AbsorbtionCanvas = FigureCanvas(self.AbsorbtionGraph)
        self.AbsorbtionSpectraToolbar = NavigationToolbar(self.AbsorbtionCanvas, self)
        
        self.AbsorbtionSpectraToolbar.addSeparator()
        
        self.SaveAbsorbtionImagesBtn = add_Button(self, "Save Images", "SaveAbsorbtionImagesBtn", self.AbsorbtionSpectraToolbar, [140,30], [140,30])
        self.SaveAbsorbtionImagesBtn.clicked.connect(self.SaveAbsorbtionImages)
        
        self.SaveAbsorbtionDataBtn = add_Button(self, "Save Data", "SaveAbsorbtionDataBtn", self.AbsorbtionSpectraToolbar, [140,30], [140,30])
        self.SaveAbsorbtionDataBtn.clicked.connect(self.SaveAbsorbtionData)
        
        self.AbsorbtionLoess_CheckBox = QtWidgets.QCheckBox()
        self.AbsorbtionLoess_CheckBox.clicked.connect(self.PlotAbsorbtionSpectra)
        self.AbsorbtionLoess_CheckBox.clicked.connect(self.PlotAbsorbtionSpectraBaseline)
        
        self.AbsorbtionLoess_SpinBox = add_SpinBox(0.15, None, [135, 30])
        self.AbsorbtionLoess_SpinBox.setRange(0.00, 1.00)
        self.AbsorbtionLoess_SpinBox.setSingleStep(0.01)
        self.AbsorbtionLoess_SpinBox.valueChanged.connect(self.PlotAbsorbtionSpectra)
        self.AbsorbtionLoess_SpinBox.valueChanged.connect(self.PlotAbsorbtionSpectraBaseline)
        self.AbsorbtionLoess_SpinBox.setPrefix("LOESS FACTOR: ") 
        
        self.AbsorbtionSpectraToolbar.addSeparator()
        self.AbsorbtionSpectraToolbar.addWidget(self.AbsorbtionLoess_CheckBox)
        self.AbsorbtionSpectraToolbar.addSeparator()
        self.AbsorbtionSpectraToolbar.addWidget(self.AbsorbtionLoess_SpinBox)
        
        AbsorbtionCanvas_Layout = QtWidgets.QVBoxLayout()
        AbsorbtionCanvas_Layout.addWidget(self.AbsorbtionSpectraToolbar)
        AbsorbtionCanvas_Layout.addWidget(self.AbsorbtionCanvas)
        Absorbtion_GroupBox.setLayout(AbsorbtionCanvas_Layout)
        
        #######################################################################
        
        ##################### Absorbtion Spectra Baseline #####################
        
        AbsorbtionBaseline_GroupBox = QtWidgets.QGroupBox("Absorbtion Spectra Baseline") 
        AbsorbtionBaseline_GroupBox.setObjectName("ColoredDragGroupBox") 
        AbsorbtionBaseline_GroupBox.setStyleSheet(DragGroupBoxStyleSheet)         
        
        self.AbsorbtionBaselineGraph = Figure()
        self.AbsorbtionBaselineCanvas = FigureCanvas(self.AbsorbtionBaselineGraph)
        toolbar = NavigationToolbar(self.AbsorbtionBaselineCanvas, self)
        
        toolbar.addSeparator()
        
        # self.calibrationDateLabel = add_Label(self, date, None, [75, 30])
        # toolbar.addWidget(self.calibrationDateLabel)
        # toolbar.addSeparator()
        toolbar.addWidget(self.Coefficient_A_SpinBox)
        toolbar.addSeparator()
        toolbar.addWidget(self.Coefficient_B_SpinBox)
        toolbar.addSeparator()
        toolbar.addWidget(self.Coefficient_C_SpinBox)
        toolbar.addSeparator()
        
        saveCalibrationBtn = add_Button(self, "Save Calibration", "saveCalibrationBtn", toolbar, [120,30], [120,30])
        saveCalibrationBtn.clicked.connect(self.saveCalibrationData)
        
        
        AbsorbtionBaselineCanvas_Layout = QtWidgets.QVBoxLayout()
        AbsorbtionBaselineCanvas_Layout.addWidget(toolbar)
        AbsorbtionBaselineCanvas_Layout.addWidget(self.AbsorbtionBaselineCanvas)
        AbsorbtionBaseline_GroupBox.setLayout(AbsorbtionBaselineCanvas_Layout)
        
        #######################################################################
        
        fileInfoLayout.addWidget(ContinuumFile_GroupBox)
        fileInfoLayout.addWidget(AbsorbtionFile_GroupBox)
        fileInfoLayout.addWidget(Loading_GroupBox)
        fileInfoLayout.addWidget(PlotSpectra_GroupBox)
        
        ControlTabLayout.addLayout(fileInfoLayout)
        ControlTabLayout.addLayout(CanvasGroupLayout)
        SpectraCanvasLayout.addWidget(SpectraImage_GroupBox)
        SpectraCanvasLayout.addWidget(Spectra_GroupBox)
        AbsorbtionCanvasLayout.addWidget(Absorbtion_GroupBox)
        AbsorbtionCanvasLayout.addWidget(AbsorbtionBaseline_GroupBox)
        
        
        ControlTabLayout.addItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))
        
        self.ControlTab.setLayout(ControlTabLayout)
        
    # def UpdateSaturation(self):
        
    #     self.PlotNewFile()
    
    def SaveAutoCropConfig(self):
        
        self.SaveFileData(self.AutoCropConfigPath, [self.AutoCropCheckBox.isChecked()])
        
    def CompareCurrentData(self, date, A, B, C):
        if self.currentDate == date and \
            self.Coefficient_A_SpinBox.value() == A and \
            self.Coefficient_B_SpinBox.value() == B and \
            self.Coefficient_C_SpinBox.value() == C:
                return True
        else:
            return False
        
    def loadCalibrationData(self):
        
        data = self.__readTxtFile(self.CalibrationDataPath)
        
        if len(data) < 1:
            self.popupMessage('Load Data', 'No Saved Data!')
            return
            
        self.CurrentActiveContinuumFileName = self.ContinuumFileComboBox.currentText()
        self.CurrentActiveAbsorbtionFileName = self.AbsorbtionFileComboBox.currentText()
        
        date = self.getCurrentFileDate() 
        
        if date == None:
            return
        
        dateExists = False
        saveDataIndex = -1
        
        for i in range(len(data)):
            if date == data[i][0]:
                dateExists = True
                saveDataIndex = i
        
        if dateExists:
            
            self.currentDate = date
            
            values = data[saveDataIndex]
            A = float(values[1])
            B = float(values[2])
            C = float(values[3])
            
            if self.CompareCurrentData(date, A, B, C):
                self.popupMessage('Load Data', 'Data Already Loaded!')
                return
                
            # self.calibrationDateLabel.setText(date)
            self.Coefficient_A_SpinBox.setValue(A)
            self.Coefficient_B_SpinBox.setValue(B)
            self.Coefficient_C_SpinBox.setValue(C)
            
            write_txt_file(self.CalibrationToggledPath, 
                           [[self.IsWavelengthCalibrated, 
                            self.WavelengthUnitsComboBox.currentText(), 
                            self.currentDate]])
            
            self.popupMessage('Load Data', 'Load Successful!')
            
        else:
            self.popupMessage('Load Data', f'No Saved Data for {date}')
    
    def saveCalibrationData(self):
        
        date = self.getCurrentFileDate() 
        
        if date == None:
            return
        
        self.CurrentActiveContinuumFileName = self.ContinuumFileComboBox.currentText()
        self.CurrentActiveAbsorbtionFileName = self.AbsorbtionFileComboBox.currentText()
        
        data = self.__readTxtFile(self.CalibrationDataPath)
        
        A = self.Coefficient_A_SpinBox.value()
        B = self.Coefficient_B_SpinBox.value()
        C = self.Coefficient_C_SpinBox.value()
        
        currentData = [date, str(A), str(B), str(C)]
        
        if len(data) < 1:
            write_txt_file(self.CalibrationDataPath, [currentData])
            
            self.popupMessage('Save Data', 'Save Successful!')
            
        else:
            dateExists = False
            saveData = []
            saveDataIndex = -1
            
            for i in range(len(data)):
                if date == data[i][0]:
                    dateExists = True
                    saveData = data[i]
                    saveDataIndex = i
                    break
                
            if dateExists:
                
                sameData = True
                for i in range(len(saveData)):
                    if saveData[i] != currentData[i]:
                        sameData = False
                        break
                    
                if sameData:
                    self.popupMessage('Save Data', 'Data Already Saved!')
                else:
                    
                    msg = QtWidgets.QMessageBox()
                    response = msg.question(self, 'Save Data', f'Would you like to overwrite {date}?', msg.Yes | msg.No | msg.Cancel)
                    
                    if response == msg.Yes:
                        data[saveDataIndex] = currentData
                        
                        self.__writeCalibrationData(data)
                        
                        self.popupMessage('Save Data', 'Save Successful!')
                    else:
                        return
                    
            else:
                # save new data
                newData = []
                
                for entry in data:
                    newData.append(list(entry))
                
                newData.append([date, A, B, C])
                
                self.__writeCalibrationData(newData)
                
                self.popupMessage('Save Data', 'Save Successful!')
        
        # self.calibrationDateLabel.setText(date)
        self.currentDate = date
        
        write_txt_file(self.CalibrationToggledPath, 
                       [[self.IsWavelengthCalibrated, 
                        self.WavelengthUnitsComboBox.currentText(), 
                        self.currentDate]])
        
    def __writeCalibrationData(self, data):

        data = [ list(x) for _, x in sorted(zip(np.array(data).T[0], data))]
        
        write_txt_file(self.CalibrationDataPath, data)
        
    def popupMessage(self, title, message):
        
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()
        
    def getCurrentFileDate(self):
        
        if self.CurrentActiveContinuumFileName == "":
            self.popupMessage('No active continuum file!', 'Plot to activate continuum file.')
            return
        
        if self.CurrentActiveAbsorbtionFileName == "":
            self.popupMessage('No active absorbtion file!', 'Plot to activate absorbtion file.')
            return
        
        date = self.getDateFromFileName(self.CurrentActiveContinuumFileName)
        
        if date != self.getDateFromFileName(self.CurrentActiveAbsorbtionFileName):
            self.popupMessage('File Name Error!', 'Files are from Different Dates.')
            return
        
        return date
        
    def getDateFromFileName(self, fileName):
        
        if type(fileName) != str:
            return
        if len(fileName) < 13:
            return
        if fileName[4] != "_":
            return
        if fileName[7] != "_":
            return
        if fileName[10] != "_":
            return
        if not fileName[:4].isnumeric():
            return
        if not fileName[5:7].isnumeric():
            return
        if not fileName[8:10].isnumeric():
            return
        
        return fileName[:10]
        
    def __readTxtFile(self, path):

        data = []
        if os.path.isfile(path):
            with open(path) as fp:
                for cnt, line in enumerate(fp):
                    data.append([data for data in line[:-1].split("\t")])
        return np.array(data)
        
    def ToggleWavelengthCalibration(self):
        
        if self.IsWavelengthCalibrated == False:
            self.IsWavelengthCalibrated = True
            self.Coefficient_A_SpinBox.setEnabled(True)
            self.Coefficient_B_SpinBox.setEnabled(True)
            self.Coefficient_C_SpinBox.setEnabled(True)
            self.WavelengthUnitsComboBox.setEnabled(True)
        else:
            self.IsWavelengthCalibrated = False
            self.Coefficient_A_SpinBox.setEnabled(False)
            self.Coefficient_B_SpinBox.setEnabled(False)
            self.Coefficient_C_SpinBox.setEnabled(False)
            self.WavelengthUnitsComboBox.setEnabled(False)
            
        write_txt_file(self.CalibrationToggledPath, 
                       [[self.IsWavelengthCalibrated, 
                        self.WavelengthUnitsComboBox.currentText(), 
                        self.currentDate]])
        
    def LoadPreviousDataFiles(self): 
        
        filePaths = []
        data = self.LoadFileData(self.ContinuumFilesPath, 1)
        
        for path in data:
            if path[-4:] == ".txt" or path[-5:] == ".fits":
                path = self.GetFilePathOnThisPC(path)
                
                if os.path.isfile(path):
                    filePaths.append(path)
                    
        self.DATA_LOADER.LoadDataFiles([filePaths, DATA_FILE_TYPE.CONTINUUM, True])
        
        
        filePaths = []
        data = self.LoadFileData(self.AbsorbtionFilesPath, 1)
        
        for path in data:
            if path[-4:] == ".txt" or path[-5:] == ".fits":
                path = self.GetFilePathOnThisPC(path)
                
                if os.path.isfile(path):
                    filePaths.append(path)
        
        self.DATA_LOADER.LoadDataFiles([filePaths, DATA_FILE_TYPE.ABSORBTION, True])
        
        self.DATA_LOADER.start()
        
    def LoadDataFilesDialogue(self, fileType, isNewData):
        
        if type(fileType) != DATA_FILE_TYPE:
            return
            
        if type(isNewData) != bool:
            return
            
        filePaths = self.GetFilesDialogue(self.LastDirectory)
        
        if len(filePaths) < 1:
            return
        
        self.DATA_LOADER.LoadDataFiles([filePaths, fileType, isNewData])
        self.DATA_LOADER.start()
        
    def GetFilesDialogue(self, directoryPath):
    
        if not os.path.isdir(directoryPath):
            directoryPath = self.PROJECT_DIRECTORY
        
        fileNames = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Choose Spectra Files', directoryPath, 'Spectra files (*.txt *.fits)') #
        
        returnNames = []
        for name in fileNames[0]:
            returnNames.append(name)
        return returnNames
        
    def GetFilePathOnThisPC(self, filePath):
        filePathPC = ''
        
        if self.targetDirectory in filePath:
            start_index = filePath.index(self.targetDirectory)
            
            if start_index < len(filePath):
                filePathPC = self.targetDirectoryOnPC + filePath[start_index:]
                
        return filePathPC
        
    def SaveFileData(self, path, fileNames):
        
        data = prepare_data(fileNames)
        
        write_txt_file(path, data)
        
    def LoadFileData(self, path, num_columns):
        
        if type(num_columns) != int:
            return []
            
        readData = read_txt_file(path)
        loadData = []
        for data in readData:
            loadData.append(data[0])
            
        return loadData
        
    def CheckPlotButtonSelectability(self):
        if self.IsCurrentActiveFileSelected() and self.IsCurrentImageCropped():
            self.PlotButton.setEnabled(False)
        else:
            self.PlotButton.setEnabled(True)
            
    def IsCurrentImageCropped(self):
        # Add functionality
        return False
        
    def IsCurrentActiveFileSelected(self):
        
        if self.CurrentActiveContinuumFileName == self.ContinuumFileComboBox.currentText()\
        and self.CurrentActiveAbsorbtionFileName == self.AbsorbtionFileComboBox.currentText():
            return True
        return False
        
    def UpdateMinY(self):
        self.SpectraImageMinY_SpinBox.setMaximum(self.SpectraImageMaxY_SpinBox.value() - 5)
    
    def UpdateMaxY(self):
        self.SpectraImageMaxY_SpinBox.setMinimum(self.SpectraImageMinY_SpinBox.value() + 5)
        
    def UpdateMinX(self):
        self.SpectraImageMinX_SpinBox.setMaximum(self.SpectraImageMaxX_SpinBox.value() - 5)
    
    def UpdateMaxX(self):
        self.SpectraImageMaxX_SpinBox.setMinimum(self.SpectraImageMinX_SpinBox.value() + 5)
        
    def UpdatePlotButns(self): # , fileType
        
        # if type(fileType) != DATA_FILE_TYPE:
        #     return
        
        for fileType in [DATA_FILE_TYPE.CONTINUUM, DATA_FILE_TYPE.ABSORBTION]:
        
            if fileType == DATA_FILE_TYPE.CONTINUUM:
                index = self.ContinuumFileComboBox.currentIndex()
                amount = len(self.ContinuumSpectraImages)
                previousBtn = self.plotPreviousContinuumBtn
                nextBtn = self.plotNextContinuumBtn
                
            elif fileType == DATA_FILE_TYPE.ABSORBTION:
                index = self.AbsorbtionFileComboBox.currentIndex()
                amount = len(self.AbsorbtionSpectraImages)
                previousBtn = self.plotPreviousAbsorptionBtn
                nextBtn = self.plotNextAbsorptionBtn
            
            if amount == 0:
                previousBtn.setEnabled(False)
                nextBtn.setEnabled(False)
                return
            elif amount == 1:
                previousBtn.setEnabled(False)
                nextBtn.setEnabled(False)
            elif amount == 2:
                if index == 0:
                    previousBtn.setEnabled(False)
                    nextBtn.setEnabled(True)
                else:
                    previousBtn.setEnabled(True)
                    nextBtn.setEnabled(False)
            else:
                if index == 0:
                    previousBtn.setEnabled(False)
                    nextBtn.setEnabled(True)
                elif index == amount-1:
                    previousBtn.setEnabled(True)
                    nextBtn.setEnabled(False)
                else:
                    previousBtn.setEnabled(True)
                    nextBtn.setEnabled(True)
                
    def PlotNextFile(self, direction, fileType):
        
        if direction not in ["forward", "back"]:
            return
        
        if type(fileType) != DATA_FILE_TYPE:
            return
        
        if fileType == DATA_FILE_TYPE.CONTINUUM:
            index = self.ContinuumFileComboBox.currentIndex()
            amount = len(self.ContinuumSpectraImages)
            FileComboBox = self.ContinuumFileComboBox
        elif fileType == DATA_FILE_TYPE.ABSORBTION:
            index = self.AbsorbtionFileComboBox.currentIndex()
            amount = len(self.AbsorbtionSpectraImages)
            FileComboBox = self.AbsorbtionFileComboBox
        
        # select next file
        if direction == "back":
            if index < 1:
                return
            newIndex = index - 1
            if newIndex < 0:
                return
            
            FileComboBox.setCurrentIndex(newIndex)
            
        elif direction == "forward":
            if index >= amount-1:
                return
            newIndex = index + 1
            if newIndex  >= amount:
                return
            
            FileComboBox.setCurrentIndex(newIndex)
            
        self.PlotNewFile()
        
    def PlotNewFile(self):
        
        if self.IsCurrentActiveFileSelected() and self.IsCurrentImageCropped():
            return
        
        self.CurrentActiveContinuumFileName = self.ContinuumFileComboBox.currentText()
        self.CurrentActiveAbsorbtionFileName = self.AbsorbtionFileComboBox.currentText()
        
        self.UpdatePlotButns()

        date = self.getCurrentFileDate() 
        
        if date == None:
            # print("?")
            return
        
        if self.IsWavelengthCalibrated == True:
            
            # check does date exist
            data = self.__readTxtFile(self.CalibrationDataPath)
        
            if len(data) < 1:
                self.popupMessage('Load Data', 'No Saved Data!')
                return
            
            dateExists = False
            saveDataIndex = -1
            
            for i in range(len(data)):
                if date == data[i][0]:
                    dateExists = True
                    saveDataIndex = i
                    
            if dateExists:
                values = data[saveDataIndex]
                A = float(values[1])
                B = float(values[2])
                C = float(values[3])
                
                # change data if it isn't the same as the current calibration data
                if not self.CompareCurrentData(date, A, B, C):
                
                    self.Coefficient_A_SpinBox.setValue(A)
                    self.Coefficient_B_SpinBox.setValue(B)
                    self.Coefficient_C_SpinBox.setValue(C)
                    
                    # self.calibrationDateLabel.setText(date)
                    self.currentDate = date
                    
                    self.popupMessage('Load Data', 'Calibration Data Loaded!')
                    
                    write_txt_file(self.CalibrationToggledPath, 
                                   [[self.IsWavelengthCalibrated, 
                                    self.WavelengthUnitsComboBox.currentText(), 
                                    self.currentDate]])
            else:
                # return if date doesn't exist
                self.popupMessage('Load Data', f'No Saved Data for {date}')
                return

        self.PlotSpectraImage()

        self.PlotLineSpectra()

        self.CalculateAbsorbtionFeatureData = True
        self.PlotAbsorbtionSpectra()

        self.PlotAbsorbtionSpectraBaseline()

        self.CheckPlotButtonSelectability()

    def TruncateImage(self, image):
        
        image_length = len(image)
        
        minY = self.SpectraImageMinY_SpinBox.value()
        maxY = self.SpectraImageMaxY_SpinBox.value()
        
        self.SaveFileData(self.Last_Y_Axis_Bounds_Path, [minY, maxY])
        
        if minY >= maxY:
            return np.array(image)
        
        if minY > image_length - 1:
            return np.array(image)
        
        if maxY > image_length:
            return np.array(image)
            
        return np.array(image)[minY:maxY]
    
    def GetLineSpecData(self, image):
            
        line_spectra = []
        for line in image:
            line_spectra.append(sum(line))
            
        return np.array(line_spectra)
    
    def __gaussianNorm(self, x, area, mu, FWHM): # x = dataset, area = gf, mu = centre, sigma = FWHM/2.3548 = gA /2.3548
    
        sigma = float(FWHM)/2.3548
        gauss = area*(1/(sigma*np.sqrt(2*np.pi)))*np.exp(-0.5*(x-mu)**2/(sigma**2))
        
        return(gauss)
    
    def getNumberOfSpaces(self, min_val, max_val, spacing_val):
        
        retval = 1
        
        if max_val < min_val:
            return retval
        
        return int((max_val - min_val)/spacing_val) + 1
    
    def getNewArray(self, E_range, DataPointSpacing):
        
        NumberOfSpaces = self.getNumberOfSpaces(-E_range, -DataPointSpacing, DataPointSpacing)
        
        if NumberOfSpaces == 1:
            return np.array([-DataPointSpacing, 0, DataPointSpacing])
        
        a = np.linspace(-E_range, -DataPointSpacing, NumberOfSpaces)
        b = np.linspace(0, E_range , NumberOfSpaces + 1)
        
        E_array = np.zeros(len(a) + len(b)) 
        E_array[:len(a)] = a          
        E_array[-len(b):] = b

        return E_array
    
    def PlotSpectraImage(self):
        
        ContinuumIndex = self.ContinuumFileComboBox.currentIndex()
        AbsorbtionIndex = self.AbsorbtionFileComboBox.currentIndex()

        if ContinuumIndex == -1:
            return

        if AbsorbtionIndex == -1:
            return

        ContinuumImage = self.ContinuumSpectraImages[ContinuumIndex]

        if self.AutoCropCheckBox.isChecked():
        
            derivative = np.diff(self.GetLineSpecData(np.copy(ContinuumImage)))
            
            start = np.where(derivative == max(derivative))[0][0]
            end = np.where(derivative == min(derivative))[0][0]
            
            self.SpectraImageMinY_SpinBox.setValue(start)
            self.SpectraImageMaxY_SpinBox.setValue(end+1)
        
        self.CurrentContinuumImage = self.TruncateImage(ContinuumImage)
        self.CurrentAbsorbtionImage = self.TruncateImage(self.AbsorbtionSpectraImages[AbsorbtionIndex])

        continuumImageSize = len(self.CurrentContinuumImage[0])
        absorbtionImageSize = len(self.CurrentAbsorbtionImage[0])
        
        if continuumImageSize < 1:
            return
        if absorbtionImageSize < 1:
            return
        if continuumImageSize != absorbtionImageSize:
            return
        
        self.SpectraImageGraph.clf()
        
        colour_map = plt.get_cmap('jet')
        
        ax = self.SpectraImageGraph.add_subplot(111)
        ax.clear()
        
        minX = self.SpectraImageMinX_SpinBox.value()
        maxX = self.SpectraImageMaxX_SpinBox.value()
        
        self.minX = minX
        self.maxX = maxX
        
        self.SaveFileData(self.Last_X_Axis_Bounds_Path, [self.minX, self.maxX])
        
        # print(np.max(self.CurrentContinuumImage), np.max(self.CurrentAbsorbtionImage))
        
        im_max = np.max(self.CurrentAbsorbtionImage)
        
        ax.imshow(self.CurrentAbsorbtionImage[:, self.minX:self.maxX], colour_map, interpolation='gaussian',
                  vmin=0.05*im_max, vmax=0.75*im_max, aspect='auto')
        
        self.SpectraImageCanvas.draw()
        
        #fig, ax = plt.subplots(nrows=1, ncols=1)
        #
        ##ax[0].imshow(Specs[1].T, colour_map)
        #ax.plot(abs_signal[::-1])
        #ax.set_xlim([0,1000])
        #ax.set_ylim([0, np.max(abs_signal)])
        
        #    colored_image = colour_map(data)
        #    Image.fromarray((colored_image).astype(np.uint8)).show()
        #    Image.fromarray((colored_image[:, :, :3] * 255).astype(np.uint8)).show()
        #    Image.fromarray(colored_image.astype(np.uint8)).show()
            #.save('test.png')
        
        
        #    fig2, ax2 = plt.subplots(nrows=1, ncols=2)
        #    ax2[0].imshow(Specs[0].T, colour_map)
        #    ax2[1].imshow(Specs[1].T, colour_map)
        
    def PlotLineSpectra(self):
        
        ContinuumIndex = self.ContinuumFileComboBox.currentIndex()
        AbsorbtionIndex = self.AbsorbtionFileComboBox.currentIndex()
        
        if ContinuumIndex == -1:
            return
        if AbsorbtionIndex == -1:
            return
        
        continuumImageSize = len(self.CurrentContinuumImage[0])
        absorbtionImageSize = len(self.CurrentAbsorbtionImage[0])
        
        if continuumImageSize < 1:
            return
        if absorbtionImageSize < 1:
            return
        if continuumImageSize != absorbtionImageSize:
            return
        
        self.SpectraGraph.clf()
         
        ax = self.SpectraGraph.add_subplot(111)
        ax.clear()
        
        # .T -> Transpose image
        # [::-1] -> reverse array
        # [:-1] -> dead pixel correction
        self.CurrentContinuumData = self.GetLineSpecData(self.CurrentContinuumImage.T)[::-1][:-1]
        self.CurrentAbsorbtionData = self.GetLineSpecData(self.CurrentAbsorbtionImage.T)[::-1][:-1]
        
        # ########
        # InstrumentalBroadening = 0.05
        # DataPointSpacing = 0.02
        
        # E_range_max = InstrumentalBroadening * 6
        # gauss_x = self.getNewArray(E_range_max, DataPointSpacing) 
        # gaussFilter = self.__gaussianNorm(gauss_x, 1, 0, InstrumentalBroadening)*DataPointSpacing
        # self.CurrentContinuumData = np.convolve(self.CurrentContinuumData, gaussFilter, mode='same')
        # self.CurrentAbsorbtionData = np.convolve(self.CurrentAbsorbtionData, gaussFilter, mode='same')
        # ########
        
        # ax.plot(gauss_x, gaussFilter, 'k')
        # baseCounts = 300
        
        # minValue = np.min([self.CurrentContinuumData, self.CurrentAbsorbtionData]) - baseCounts

        # self.CurrentContinuumData -= minValue
        # self.CurrentAbsorbtionData -= minValue
        
        # self.CurrentContinuumData -= 18000
        # self.CurrentAbsorbtionData -= 18000
        
        # offset = np.min(self.CurrentContinuumData) - np.min(self.CurrentAbsorbtionData)
        
        # baseCounts = self.Saturation_SpinBox.value()
        
        # self.original_data_c = np.copy(self.CurrentContinuumData)
        # self.original_data_a = np.copy(self.CurrentAbsorbtionData)
        
        xLimMin = continuumImageSize - self.maxX - 1
        xLimMax = continuumImageSize - self.minX - 1
        
        
        if self.IsWavelengthCalibrated == True:
            
            A = self.Coefficient_A_SpinBox.value()
            B = self.Coefficient_B_SpinBox.value()
            C = self.Coefficient_C_SpinBox.value()
            
            print(len(self.CurrentAbsorbtionData))

            units = self.WavelengthUnitsComboBox.currentText()
            
            if A != 0 and B != 0 and C != 0:
                self.X_AxisData = []
                for x in range(len(self.CurrentAbsorbtionData)):
                    self.X_AxisData.append(A * x**2 + B * x + C)
                ax.set_xlabel('Wavelength [' + units + ']')
                
                xLimMin = A * xLimMin**2 + B * xLimMin + C
                xLimMax = A * xLimMax**2 + B * xLimMax + C
                
                if units == 'eV':
                    self.X_AxisData = (np.ones(len(self.X_AxisData)) * 1239.8) / np.array(self.X_AxisData)
                    ax.set_xlabel('Energy [eV]')
                    
                    xLimMin_copy = xLimMin
                    
                    xLimMin = 1239.8 / xLimMax
                    xLimMax = 1239.8 / xLimMin_copy
        else:
            
            # self.X_AxisData = np.linspace(69, 126, len(self.CurrentContinuumData))
            self.X_AxisData = range(len(self.CurrentContinuumData))
            ax.set_xlabel('Pixel')
            
            
        # write_txt_file("ExampleThreeColumnFile.txt", np.array([self.X_AxisData, self.CurrentContinuumData, self.CurrentAbsorbtionData]).T)
            
        ax.plot(self.X_AxisData, self.CurrentContinuumData, 'k')
        ax.plot(self.X_AxisData, self.CurrentAbsorbtionData, "r--")
        
        self.xLimMin = xLimMin - 0.2
        self.xLimMax = xLimMax
        
        ax.set_xlim([self.xLimMin, self.xLimMax])
        
#        ax.set_xlim([60, 130]) 
#        ax.set_ylabel('Cross Section [Mb]') #'Photon Intensity [Arb.]'
#        ax.set_xlabel('Photon Energy [eV]')
#        ax.legend(["Cowan Data", "Experimental Data"], loc='best')
        
        x = self.LineSpectraToolbar.configure_subplots()
        
        x._tight_layout()
        x.close()   
        
        self.SpectraCanvas.draw()
        
        
    def PlotAbsorbtionSpectra(self):
        
        if len(self.X_AxisData) < 1:
            return
        if len(self.CurrentContinuumData) < 1:
            return
        if len(self.CurrentAbsorbtionData) < 1:
            return
        
        # baseCounts = 8000 # np.min(self.CurrentAbsorbtionData) - 1
        
        # self.CurrentAbsorbtionData -= baseCounts
        # self.CurrentContinuumData -= baseCounts
        
        if self.CalculateAbsorbtionFeatureData:
            
            self.CurrentAbsorbtionFeatureData = np.log(self.CurrentContinuumData / self.CurrentAbsorbtionData)
            
            # self.CurrentAbsorbtionFeatureData = np.log10(self.CurrentContinuumData / self.CurrentAbsorbtionData)
            
    
            # max_old = max(original_absorbtion_feature_data)
            # max_new = max(self.CurrentAbsorbtionFeatureData)
            # ratio = max_new / max_old
            # baseCounts = self.Saturation_SpinBox.value()
            
            # print(max_old, max_new, ratio, baseCounts)

            self.CalculateAbsorbtionFeatureData = False
            
        self.AbsorbtionGraph.clf()
        
        ax = self.AbsorbtionGraph.add_subplot(111)
        ax.clear()
        
        # ax.plot(self.X_AxisData, original_absorbtion_feature_data, "r-" )
        
#        ax.plot(x_axis, np.array(ContinuumData[::-1]) / np.array(AbsorbtionData[::-1]), "k-" )
        ax.plot(self.X_AxisData, self.CurrentAbsorbtionFeatureData, "k-" )
        
        # print(np.max(self.CurrentContinuumData), np.max(self.CurrentAbsorbtionData))
        
        if self.AbsorbtionLoess_CheckBox.isChecked():
            self.CurrentAbsorbtionFilterData = lowess(self.CurrentAbsorbtionFeatureData, self.X_AxisData, frac=self.AbsorbtionLoess_SpinBox.value()).T[1]
            ax.plot(self.X_AxisData, self.CurrentAbsorbtionFilterData, 'r-')
        
        ############ Limits ############
        
        # a = 0
        # b = len(self.CurrentAbsorbtionFeatureData) - 1
        
        # xLimMin = continuumImageSize - self.maxX - 1
        # xLimMax = continuumImageSize - self.minX - 1
        
        # # x = np.flip(self.X_AxisData)
        # x = self.X_AxisData
        
        # # print(x[:50])
        
        # matches = np.where(x == self.xLimMin)[0]
        # if len(matches) > 0:
        #     a = matches[0]
        
        # print(self.xLimMin, matches, a)
        
        # matches = np.where(x == self.xLimMax)[0]
        # if len(matches) > 0:
        #     b = matches[0]
            
        # print(self.xLimMax, matches, b)
        
        croppedData = self.CurrentAbsorbtionFeatureData[-self.maxX:len(self.CurrentAbsorbtionFeatureData)-self.minX]
        
        yLimMin = math.floor((min(croppedData) - 0.000001) * 11) / 10
        yLimMax = math.ceil ((max(croppedData) + 0.000001) * 11) / 10
        
        
        if yLimMin < 0 :
            pass
        else:
            yLimMin = 0
        
        # print(yLimMin, yLimMax)
        
        self.yLims = [yLimMin, yLimMax]
        self.yLimsActive = True
        
        # print(self.xLimMin, self.xLimMax)
        
        ax.set_xlim([self.xLimMin, self.xLimMax]) 
        if self.yLimsActive:
            ax.set_ylim(self.yLims)
        
#        ax.set_xlim([60, 130]) 
#        ax.set_ylim([0, 0.8])
        # ax.set_ylim(bottom=0)
        
        ############ Limits ############
        
#        ax.plot(x_axis, AbsorbtionData - filtered.T[1], "b-" )
        
        ax.set_title(self.CurrentActiveAbsorbtionFileName)
#        ax.set_title('Photon Intensity Vs Photon Energy')

        if self.IsWavelengthCalibrated == True:
            units = self.WavelengthUnitsComboBox.currentText()
            ax.set_xlabel('Wavelength [' + self.WavelengthUnitsComboBox.currentText() + ']')
            if units == 'eV':
                ax.set_xlabel('Energy [eV]')
        else:
            # ax.set_xlabel('Energy [eV]')
            ax.set_xlabel('Pixel')
    
        ax.set_ylabel(r'Ln($\dfrac{I_0}{I}$) [Arb.]')
        # ax.set_ylabel('Intensity [Arb.]') # 'Cross Section [Mb]'
#        ax.legend(["Cowan Data", "Experimental Data"], loc='best')
        
        x = self.AbsorbtionSpectraToolbar.configure_subplots()
        x._tight_layout()
        x.close() 
        
        self.AbsorbtionCanvas.draw()
        
#        for i in range(3):
#            pass
        #        ax2[i].set_xlim([0,1004])
        #        ax2[i].set_xlim([70,120])
        
    def PlotAbsorbtionSpectraBaseline(self):
        
        if len(self.X_AxisData) < 1:
            return
        if len(self.CurrentAbsorbtionFeatureData) < 1:
            return
            
        Y_Data = self.CurrentAbsorbtionFeatureData
         
        if self.AbsorbtionLoess_CheckBox.isChecked():
            if len(self.CurrentAbsorbtionFilterData) < 1:
                return
            Y_Data = self.CurrentAbsorbtionFeatureData - self.CurrentAbsorbtionFilterData
        
        self.AbsorbtionBaselineGraph.clf()
        
        ax = self.AbsorbtionBaselineGraph.add_subplot(111)
        ax.clear()
        ax.plot(self.X_AxisData, Y_Data, "b-" )
        
        ax.set_xlim([self.xLimMin, self.xLimMax]) 
        if self.yLimsActive:
            ax.set_ylim(self.yLims)
        
        self.AbsorbtionBaselineCanvas.draw()
        
    def rgbToInt(self, rgb):
        
        return rgb[0] + rgb[1] + rgb[2]
        
    def formatImage(self, path):
        
        img = Image.open(path)
        w, h = img.size
        
        pixels = list(img.getdata())

        j = 0
        col = []
        array = []
        for i in range(len(pixels)):
            
            col.append(self.rgbToInt(pixels[i]))
            j += 1
            
            if j == w:
                array.append(col)
                # if sum(col) < 90000:
                #     print(sum(col), i//w)
                col = []
                j = 0
                
        array = np.array(array).T
        
        for i in range(len(array)):
            if sum(array[i]) < 90000:
                break
                # print(i, sum(array[i]))
                
        # return
        # line = pixels[43*w:43*w + 100]
        
        # for i in range(100):
        #     if line[i][0] == 0:
        #         break
        
        startPixel = 96 # value before start black pixel in cs5
        endPixel = 801 # value before end black pixel in cs5
        gap = startPixel - i
        
        # print(i, startPixel + i)
        
        imgA = img.crop((0, 0, i, h))
        imgB = img.transform((endPixel - startPixel, h), Image.Transform.EXTENT, [i, 0, endPixel, h])
        imgC = img.crop((endPixel, 0, w, h))
        
        img = Image.new('RGB', (w, h))
        img.paste((255, 255, 255), box=(0, 0, gap, h))
        img.paste(imgA, box=(gap, 0))
        img.paste(imgB, box=(startPixel, 0))
        img.paste(imgC, box=(endPixel, 0))
        
        return img
        
    def SaveAbsorbtionImages(self):
        
        directoryPath = QtWidgets.QFileDialog().getExistingDirectory(self, "Select Directory", self.LastImageDirectory)
        
        if len(directoryPath) < 1:
            return
        
        self.LastImageDirectory = directoryPath
        
        write_txt_file(self.LastImageDirectoryPath, [self.LastImageDirectory])
        
        fileNames = [self.AbsorbtionFileComboBox.itemText(i) for i in range(self.AbsorbtionFileComboBox.count())]
        
        for i in range(len(fileNames)):
            
            fileName = fileNames[i] + '.png'
            filePath = directoryPath + "/" + fileName
            
            self.AbsorbtionFileComboBox.setCurrentIndex(i)
            self.PlotNewFile()
            
            self.AbsorbtionGraph.savefig(filePath)
            
            self.formatImage(filePath).save(filePath)
            print(filePath, 'saved!\n')
        
    def SaveAbsorbtionData(self):
        
        # if len(self.CurrentActiveAbsorbtionFileName) < 1:
        #     return
        
        # directoryPath = QtWidgets.QFileDialog().getExistingDirectory()
        
        # filePathBase = directoryPath + '/' + self.CurrentActiveAbsorbtionFileName + '_Data'
        
        directoryPath = QtWidgets.QFileDialog().getExistingDirectory(self, "Select Directory", self.LastImageDirectory)
        
        if len(directoryPath) < 1:
            return
        
        if 'Lab Data' in directoryPath:
            QtWidgets.QMessageBox().warning(None, 'Save Aborted!', 'Cannot Save in Lab Data!' )
            return
        
        if directoryPath == self.GetFilePathOnThisPC(self.LastDirectory):
            QtWidgets.QMessageBox().warning(None, 'Save Aborted!', 'Cannot Save in the Same Folder as Original Data!' )
            return
        
        self.LastImageDirectory = directoryPath
        
        write_txt_file(self.LastImageDirectoryPath, [self.LastImageDirectory])
        
        # self.AbsorbtionGraph.savefig(filePathBase + '.png')
        # self.AbsorbtionGraph.savefig(filePathBase + '.svg')
        
        fileNames = [self.AbsorbtionFileComboBox.itemText(i) for i in range(self.AbsorbtionFileComboBox.count())]
        
        for i in range(len(fileNames)):
            
            fileName = fileNames[i] + '_Data.txt'
            filePath = directoryPath + "/" + fileName
            
            self.AbsorbtionFileComboBox.setCurrentIndex(i)
            self.PlotNewFile()
            
            data = np.array([self.X_AxisData, self.CurrentAbsorbtionFeatureData]).T
            write_txt_file(filePath, data)
            
            print(filePath, 'saved!\n')
        
        # data = np.array([self.X_AxisData, self.CurrentAbsorbtionFeatureData]).T
        # write_txt_file(filePathBase + '.txt', data)
        # QtWidgets.QMessageBox().warning(None, 'Save Sucessful!', self.CurrentActiveAbsorbtionFileName )
        
    
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
        
    def updateProgress(self, val):
        if type(val) == float:
            val = int(val)
            
        if type(val) != int:
            return
            
        self.ProgressBar.setValue(val)

    def closeEvent(self, evnt):
        pass
            
            
################################## GUI CLASS ##################################
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX#
###############################################################################


def run():   
    
    # if QtWidgets.QApplication.instance():
    #     app = QtWidgets.QApplication.instance()
    # else:
    #     app = QtWidgets.QApplication(sys.argv)
    
    # app = QtWidgets.QApplication([])
    
    ui = UiMainMenu()
    ui.show()
    
    return ui
        
#    app.aboutToQuit.connect(partial(exit_handler, ui))
#                
    # sys.exit(app.exec_())
    # app.exec_()
    
if __name__ == "__main__":
    app = run()
