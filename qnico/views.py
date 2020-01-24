import sys
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow,
                             QFileDialog,
                             QWidget, QPushButton, QCheckBox,
                             QLabel, QLineEdit, QProgressBar,
                             QVBoxLayout,QHBoxLayout
                             )
from PyQt5.QtCore import pyqtSignal, QThread, QObject
from PyQt5.QtGui import QPixmap

from . import NicoJob, default_path

class NicoDownloader(QMainWindow):

    wakeup = pyqtSignal()
    trigger = pyqtSignal(str, bool, bool)  # (videoid, usetitle, changename)
    target = pyqtSignal(str)
    query = pyqtSignal(bool, bool)
    savepath = pyqtSignal(str)
    getready = pyqtSignal()
    # canceled  # button
    # start  # button
    # enter  # LineEdit

    def __init__(self, mainapp, parent=None):
        super().__init__(parent)
        self.wait = mainapp.processEvents

        self.initUI()
        self.initConnection()
        
##        self.show()
        self.setAutoClose(True)  # default
        self.tflag = True
        
        # get ready
        worker = QThread()
        self.worker = worker
        job = NicoJob(mainapp=mainapp)
        self.job = job  # save from GC
        job.moveToThread(worker)
        # trigger
        self.wakeup.connect(job.setup)
        self.start.connect(self.download)
        self.trigger.connect(job.do)
        self.getready.connect(job.prepare)
        # messaging
        job.status.connect(self.setValue)
        job.filesize.connect(self.setMaximum)
        job.readySig.connect(self.waitingbar)
        job.name.connect(self.setsavename)
        job.thumnail.connect(self.showThumnail)
        self.savepath.connect(job.download_)  # start download
        # exit
        self.canceled.connect(self.reject)
        job.doneSig.connect(worker.quit)  # sleep it self
        job.doneSig.connect(self.accept)

        self.standby()
        self.wakeup.emit()

    def boost(self):
        job = self.job
        # boost
        job.readySig.connect(self.activate)
        self.enter.connect(self.enque)
        self.target.connect(job.settarget)
        job.infoOK.connect(self.detail)
        self.query.connect(job.detail)

    def shortcut(self):
        job = self.job
        # boost
        job.confirm.connect(self.save)
        job.readySig.connect(self.download)
        

    def initConnection(self):
        pass

    def setAutoClose(self, flag=True):
        self.autoclose = flag
    
    def accept(self):
        if self.autoclose:
            self.close()

    def reject(self):
        self.worker.exit(-1)
        if self.autoclose:
            self.close()
    
    def setarg(self, videoid, getname, savename):
        self.setvideoid(videoid)
        self.setgflag(getname)
        self.setcflag(savename)

    def enque(self):
        videoid = self.videoid()
        self.target.emit(videoid)
        self.wait()

    def detail(self):
        self.query.emit(self.gflag(), self.tflag)
        self.wait()
        if self.cflag():
            self.getname()
        self.getready.emit()

    def getname(self):
        p = Path(default_path, self.name()).with_suffix(".mp4")
        select = QFileDialog.getSaveFileName(
            parent = self.parent(),
            caption="Save as...",
            directory=str(p),
            filter="mp4 (*.mp4);;flv (*.flv);;All files (*.*)",
            initialFilter="mp4"
            )
        print(select)
        if not select[0]:
            print("canceled")
            self.canceled.emit()
        else:
            if not '.' in select[0]:
                print("oh")
                savepath = str(Path(select[0]).with_suffix(select[1][-5:]))
            else:
                savepath = select[0]
            self.setsavename(savepath)
##        self.savepath.emit(savepath)

    def standby(self):
        self.worker.start(priority=QThread.LowPriority)  # wake up

    def save(self):
        self.getname()
        self.getready.emit()

    def download(self):
        self.savepath.emit(self.name())
    
    def showThumnail(self, thbytes, fmt):
        label = self.thumnail
        pxmap = QPixmap()
        pxmap.loadFromData(thbytes, format=fmt)
        label.setPixmap(pxmap)
        

    @staticmethod
    def go(videoid,g,s):
        app=QApplication(sys.argv)
        me = NicoDownloader(mainapp=app)
        me.shortcut()
        me.show()
        me.setarg(videoid,g,s)
        me.trigger.emit(videoid,g,s)
        app.exec_()

    @staticmethod
    def openwindow():
        app = QApplication(sys.argv)
        me = NicoDownloader(mainapp=app)
        me.boost()
        me.show()
        app.exec_()

    def initUI(self):
        ## const
        base = QWidget(self)

        idbox = QLineEdit(parent=base)
        self.setvideoid = idbox.setText
        self.videoid = idbox.text
        self.enter = idbox.returnPressed
        gflag = QCheckBox("G",parent=base)
        self.setgflag = gflag.setChecked
        self.gflag = gflag.checkState
        namebox = QLineEdit(parent=base)
        self.setsavename = namebox.setText
        self.name = namebox.text
        cflag = QCheckBox("C",parent=base)
        self.setcflag = cflag.setChecked
        self.cflag = cflag.checkState
        self.cue = lambda: (self.videoid(),self.gflag(),self.cflag())

        thumnail = QLabel(self)
        self.thumnail = thumnail
        
        progressbar = QProgressBar(self)
        self.setValue = progressbar.setValue
        self.setMaximum = progressbar.setMaximum
        self.waitingbar = lambda: progressbar.setMaximum(0)
        progressbar.setMinimum(0)
        
        cancelbutton = QPushButton("Cancel",parent=base)
        startbutton = QPushButton("start", parent=base)
        startbutton.setEnabled(False)
        self.cancelbutton = cancelbutton
        self.canceled = cancelbutton.clicked
        self.start = startbutton.clicked
        self.activate = lambda: startbutton.setEnabled(True)

        ## arrange
        self.setCentralWidget(base)
        baseLO = QVBoxLayout(base)

        topLO = QVBoxLayout()
        topLO1 = QHBoxLayout()
        topLO2 = QHBoxLayout()
        
        topLO1.addWidget(idbox)
        topLO1.addWidget(gflag)
        topLO.addLayout(topLO1)
        
        topLO2.addWidget(namebox)
        topLO2.addWidget(cflag)
        topLO.addLayout(topLO2)
        
        baseLO.addLayout(topLO)

        baseLO.addWidget(thumnail)
        
        baseLO.addWidget(progressbar)
        
        buttomLO = QHBoxLayout()
        buttomLO.addStretch()
        buttomLO.addWidget(startbutton)
        buttomLO.addWidget(cancelbutton)
        baseLO.addLayout(buttomLO)

if __name__ == "__main__":
    NicoDownloader.openwindow()


