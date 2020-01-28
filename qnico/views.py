import sys
from pathlib import Path
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow,
                             QFileDialog,
                             QWidget, QPushButton, QCheckBox,
                             QLabel, QLineEdit, QProgressBar,
                             QVBoxLayout,QHBoxLayout
                             )
from PyQt5.QtCore import pyqtSignal, QThread, QObject, Qt
from PyQt5.QtGui import QPixmap

from . import NicoJob, config

logger = logging.getLogger(__name__)

class NicoDownloader(QMainWindow):

    wakeup = pyqtSignal()
    trigger = pyqtSignal(str, bool, bool)  # (videoid, usetitle, changename)
    target = pyqtSignal(str)
    query = pyqtSignal(bool, bool)
    saveas = pyqtSignal(str)
    getready = pyqtSignal()
    # canceled  # button
    # start  # button
    # enter  # LineEdit

    def __init__(self, mainapp, parent=None):
        super().__init__(parent)
        self.wait = mainapp.processEvents

        self.dst = Path(config["USER"]["savepath"]).expanduser()
        self._savename = ""

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
        job.name.connect(self.changename)
        job.video_size.connect(self.infobox.setText)
        job.loginstatus.connect(self.infobox.setText)
        job.thumnail.connect(self.showThumnail)
        self.saveas.connect(job.download_)  # start download
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
    
    def setarg(self, videoid, getname, changename):
        self.setvideoid(videoid)
        self.setgflag(getname)
        self.setcflag(changename)

    def enque(self):
        videoid = self.videoid()
        self.setWindowTitle(videoid)
        self.target.emit(videoid)
        self.wait()

    def detail(self):
        self.query.emit(self.gflag(), self.tflag)
        self.wait()
        if self.cflag():
            self.getname()
        self.getready.emit()  # job will collect detail
    
    def savepath(self):
        if self._savename:
            return str(self._savename)
        else:
            name = self.name()
            p = Path(self.dst, self.name()).with_suffix(".mp4")
            return str(p)

    def getname(self):
        select = QFileDialog.getSaveFileName(
            parent = self.parent(),
            caption="Save as...",
            directory=self.savepath(),
            filter="mp4 (*.mp4);;flv (*.flv);;All files (*.*)",
            initialFilter="mp4"
            )
        logger.debug("save as: %s [%s]", *select)
        if not select[0]:
            logger.info("canceled")
            self.canceled.emit()
        else:
            if not '.' in select[0]:
                logger.warning("savename was %s / %s", *select)
                savepath = str(Path(select[0]).with_suffix(select[1][-5:]))
            else:
                savepath = select[0]
                c = Path(select[0])
                self.dst = c.parent
                self.changename(c)

            self._savename = savepath
##        self.savepath.emit(savepath)

    def standby(self):
        self.worker.start(priority=QThread.LowPriority)  # wake up

    def save(self):
        self.getname()
        self.getready.emit()

    def download(self):
        self.saveas.emit(self.savepath())
    
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
        self.changename = namebox.setText
        self.name = namebox.text
        cflag = QCheckBox("C",parent=base)
        self.setcflag = cflag.setChecked
        self.cflag = cflag.checkState
        self.cue = lambda: (self.videoid(),self.gflag(),self.cflag())

        infobox = QLabel("...waiting for videoid", parent=self)
        self.infobox = infobox
        infobox.setAlignment(Qt.AlignRight)

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

        baseLO.addWidget(infobox)
        baseLO.addWidget(thumnail)
        
        baseLO.addWidget(progressbar)
        
        buttomLO = QHBoxLayout()
        buttomLO.addStretch()
        buttomLO.addWidget(startbutton)
        buttomLO.addWidget(cancelbutton)
        baseLO.addLayout(buttomLO)

if __name__ == "__main__":
    NicoDownloader.openwindow()


