import sys, glob
import time as tm
import serial
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic

def serial_ports(): 
	if sys.platform.startswith('win'): 
		ports = ['COM%s' % (i + 1) for i in range(256)] 
	elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'): 
		ports = glob.glob('/dev/tty[A-Za-z]*') 
	elif sys.platform.startswith('darwin'): 
		ports = glob.glob('/dev/tty.*') 
	else: 
		raise EnvironmentError('Unsupported platform') 
		
	result = [] 
	for port in ports: 
		try: 
			s = serial.Serial(port) 
			s.close() 
			result.append(port) 
		except (OSError, serial.SerialException): 
			pass 
	
	return result

form_class = uic.loadUiType("main_window.ui")[0]
thisSerial = serial_ports()
ser = serial.Serial()

class MyWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        QMainWindow.setFixedSize(self, 670,625)
        self.statusSerial = QLabel("Fixed size", self)
        self.statusSerial.setFixedWidth(150)
        self.statusbar.addWidget(self.statusSerial)
        self.statusMotor = QLabel()
        self.statusMotor.setFixedWidth(150)
        self.statusbar.addWidget(self.statusMotor)
        self.statusProgram = QLabel()
        self.statusProgram.setFixedWidth(150)
        self.statusbar.addWidget(self.statusProgram)
        self.statusCount = QLabel()
        self.statusCount.setFixedWidth(150)
        self.statusbar.addWidget(self.statusCount)

        self.comboBoxPorts.addItems(thisSerial)
        # self.pushButtonMove.clicked.connect(self.moveStepper)
        self.pushButtonMoveTo.clicked.connect(self.moveToStepper)
        self.pushButtonConnect.clicked.connect(self.connectSerial)
        self.pushButtonSetZero.clicked.connect(self.setZero)
        self.pushButtonStop.clicked.connect(self.stopStepper)
        self.pushButtonInsertProgram.clicked.connect(self.InsertProgram)
        self.pushButtonUpdateProgram.clicked.connect(self.UpdateProgram)
        self.pushButtonDeleteProgram.clicked.connect(self.DeleteProgram)
        self.treeWidgetProgram.currentItemChanged.connect(self.LoadProgram)
        self.pushButtonSaveProgram.clicked.connect(self.SaveProgram)
        self.pushButtonLoadProgram.clicked.connect(self.OpenProgram)
        self.pushButtonRunProgram.clicked.connect(self.StartProgram)
        self.pushButtonStopProgram.clicked.connect(self.StopProgram)
        self.actionexit.triggered.connect(self.close)

        self.timerSerial = QTimer()
        self.timerSerial.setInterval(1000)
        self.timerSerial.timeout.connect(self.checkSerial)
        self.timerSerial.start()

        self.timerMotor = QTimer()
        self.timerMotor.setInterval(100)
        self.timerMotor.timeout.connect(self.checkMotor)
        self.timerMotor.start()

        self.timerProgram = QTimer()
        self.timerProgram.setInterval(100)
        self.timerProgram.timeout.connect(self.checkProgram)
        self.timerProgram.start()

        self.ppr = 200
        self.program = []
        self.runningIndex = 0
        self.runningStatus = 0
        self.runningCount = 0
        self.isProgamRunning = False
        self.waitStart = tm.time()

        self.setProgramRunState(False)
        # self.setReadyState(False)
        # self.setMenuState("no serial")

    def setMenuState(self, MenuState):
        if MenuState == "no serial":
            self.groupBoxSetController.setEnabled(True)
            self.groupBoxOneStep.setEnabled(False)
            self.lineEditProgramRepeat.setEnabled(False)
            self.pushButtonRunProgram.setEnabled(False)
            self.pushButtonStopProgram.setEnabled(False)
            self.pushButtonSaveProgram.setEnabled(True)
            self.pushButtonLoadProgram.setEnabled(True)
        elif MenuState == "step ready":
            self.groupBoxSetController.setEnabled(False)
            self.groupBoxOneStep.setEnabled(True)
            self.lineEditProgramRepeat.setEnabled(False)
            self.pushButtonRunProgram.setEnabled(False)
            self.pushButtonStopProgram.setEnabled(False)
            self.pushButtonSaveProgram.setEnabled(True)
            self.pushButtonLoadProgram.setEnabled(True)
        elif MenuState == "program ready":
            self.groupBoxSetController.setEnabled(False)
            self.groupBoxOneStep.setEnabled(True)
            self.lineEditProgramRepeat.setEnabled(True)
            self.pushButtonRunProgram.setEnabled(True)
            self.pushButtonStopProgram.setEnabled(False)
            self.pushButtonSaveProgram.setEnabled(True)
            self.pushButtonLoadProgram.setEnabled(True)

    def setProgramRunState(self, isRunning):
        self.groupBoxOneStep.setEnabled(not isRunning)
        self.groupBoxSetController.setEnabled(not isRunning)
        self.lineEditProgramRepeat.setEnabled(not isRunning)
        self.pushButtonRunProgram.setEnabled(not isRunning)
        self.pushButtonStopProgram.setEnabled(isRunning)
        self.pushButtonSaveProgram.setEnabled(not isRunning)
        self.pushButtonLoadProgram.setEnabled(not isRunning)

    def setReadyState(self, isSet):
        self.groupBoxOneStep.setEnabled(isSet)
        self.groupBoxSetController.setEnabled(not isSet)
        self.lineEditProgramRepeat.setEnabled(isSet)
        self.pushButtonRunProgram.setEnabled(isSet)
        self.pushButtonStopProgram.setEnabled(isSet)
        self.pushButtonSaveProgram.setEnabled(isSet)
        self.pushButtonLoadProgram.setEnabled(not isSet)

    def StopProgram(self):
        print("stop program")
        if self.isProgamRunning:
            self.stopStepper()
            self.isProgamRunning = False
            self.setProgramRunState(False)
        else:
            QMessageBox.about(self,"프로그램 중단","현재 프로그램 수행중이 아닙니다.")

    def StartProgram(self):
        print("start program...")
        if ser.is_open:
            if len(self.program) > 0:
                self.runningIndex = 0
                self.runningCount = 0
                self.runningStatus = 0
                self.isProgamRunning = True
                self.setProgramRunState(True)
            else:
                QMessageBox.about(self,"프로그램 실행","실행할 프로그램이 없습니다.")
        else:
            QMessageBox.about(self,"프로그램 실행","현재 제어기가 연결되지 않았습니다.")

    def checkProgram(self):
        print("check program...")
        print(self.isProgamRunning, self.runningCount, self.runningIndex, self.runningStatus)
        if self.isProgamRunning:
            self.statusCount.setText(str(self.runningCount+1) + " 번째 실행중")
            if self.runningIndex >= len(self.program):
                self.runningCount += 1
                if self.runningCount >= int(self.lineEditProgramRepeat.text()):
                    self.StopProgram()
                    return
                self.runningIndex = 0
            if self.runningStatus == 0:     # at the beginning of program
                self.treeWidgetProgram.setCurrentItem(self.treeWidgetProgram.topLevelItem(self.runningIndex))
                # tm.sleep(0.5)
                self.moveToStepper()
                self.runningStatus = 1
                return
            elif self.runningStatus == 1:     # motor moving
                self.statusProgram.setText("실행 (모터)...")
                if self.statusMotor.text() == "모터 멈춤.":
                    self.runningStatus = 2
                    self.waitStart = tm.time()
                    return
            elif self.runningStatus == 2:     # waiting
                stText = "실행 (대기)..."
                dt = tm.time() - self.waitStart
                stText += "{:5.2f}".format(dt)
                self.statusProgram.setText(stText)
                if dt > float(self.lineEditWaitTime.text()):
                    self.runningStatus = 0
                    self.runningIndex += 1
                    # self.statusProgram.setText("")
                    return
        else:
            self.statusProgram.setText("프로그램 대기")
            self.statusCount.setText("")

    def OpenProgram(self):
        print("load program...")
        fileName, __ = QFileDialog.getOpenFileName(self, "프로그램 불러오기", "", "프로그램 파일 (*.prg);; program files (*.prg)")
        if fileName:
            f = open(fileName, "r")
            lines = f.readlines()
            f.close()

            self.program.clear()
            for ls in lines:
                cl = ls.split(",")
                self.program.append(cl[:-1])
            self.refreshProgram()
        else:
            print("canceled.")
        

    def SaveProgram(self):
        print("save program...")
        fileName, __ = QFileDialog.getSaveFileName(self, "프로그램 저장", "", "프로그램 파일 (*.prg);; program files (*.prg)")
        if fileName:
            print(fileName)
            f = open(fileName, 'w')
            for item in self.program:
                for L in item:
                    f.write(L)
                    f.write(",")
                f.write("\n")
            f.close()
        else:
            print("canceled.")

    def DeleteProgram(self):
        print("delete program...")
        thisIndex = QModelIndex(self.treeWidgetProgram.currentIndex())
        if thisIndex.row() >= 0:
            del self.program[thisIndex.row()]
            self.refreshProgram()
        else:
            QMessageBox.about(self,"프로그램 삭제","삭제할 프로그램 항목이 선택되지 않았습니다.")

    def UpdateProgram(self):
        print("update program...")
        thisIndex = QModelIndex(self.treeWidgetProgram.currentIndex())
        if thisIndex.row() >= 0:
            self.program[thisIndex.row()] = [self.lineEditMoveTarget.text(),
                                            self.lineEditMaxSpeed.text(),
                                            self.lineEditAcceleration.text(),
                                            self.lineEditWaitTime.text()]
            self.refreshProgram()
            self.treeWidgetProgram.setCurrentItem(self.treeWidgetProgram.topLevelItem(thisIndex.row()))
        else:
            QMessageBox.about(self,"프로그램 변경","변경할 프로그램 항목이 선택되지 않았습니다.")

    def LoadProgram(self):
        print("load program to edit...")
        thisIndex = QModelIndex(self.treeWidgetProgram.currentIndex())
        print("selectec row = " + str(thisIndex.row()))

        if thisIndex.row() >= 0:
            self.lineEditMoveTarget.setText(self.program[thisIndex.row()][0])
            self.lineEditMaxSpeed.setText(self.program[thisIndex.row()][1])
            self.lineEditAcceleration.setText(self.program[thisIndex.row()][2])
            self.lineEditWaitTime.setText(self.program[thisIndex.row()][3])

    def InsertProgram(self):
        print("insert to program...")
        thisIndex = QModelIndex(self.treeWidgetProgram.currentIndex())
        if (thisIndex.row() == -1):
            self.program.append([self.lineEditMoveTarget.text(),
                                 self.lineEditMaxSpeed.text(),
                                 self.lineEditAcceleration.text(),
                                 self.lineEditWaitTime.text()])
            self.refreshProgram()
        else:
            program1 = self.program[0:thisIndex.row()+1]
            program2 = self.program[thisIndex.row()+1:]
            self.program = program1 + [[self.lineEditMoveTarget.text(),
                                       self.lineEditMaxSpeed.text(),
                                       self.lineEditAcceleration.text(),
                                       self.lineEditWaitTime.text()]] + program2
            self.refreshProgram()
            self.treeWidgetProgram.setCurrentItem(self.treeWidgetProgram.topLevelItem(thisIndex.row()))

    def refreshProgram(self):
        self.treeWidgetProgram.clear()
        i=0
        for item in self.program:
            litem = [str(i)] + item
            QTreeWidgetItem(self.treeWidgetProgram, litem)
            i+=1

    def checkSerial(self):
        if ser.is_open:
            self.statusSerial.setText("제어기 연결됨.")
        else:
            self.statusSerial.setText("제어기 연결 끊어짐.")
        pass

    def checkMotor(self):
        if ser.is_open:
            while ser.in_waiting:
                inStr = str(ser.readline().strip())[2:-1]
                ser.flush()
                print(inStr)
                if (inStr.strip() == "00"):
                    self.statusMotor.setText("모터 멈춤.")
        else:
            self.statusMotor.setText(".X.")
        pass


    def connectSerial(self):
        print("connecting serial...")
        if not ser.is_open:
            ser.port = self.comboBoxPorts.currentText()
            ser.baudrate = 9600
            ser.open()
            self.setZero()
        else:
            QMessageBox.about(self,"제어기 연결","이미 제어기가 연결되어 있습니다.")

    def setZero(self):
        print("set current position zero...")
        if ser.is_open:
            cmd = "14\n"
            ser.write(cmd.encode("utf-8"))
        else:
            QMessageBox.about(self,"제어기 상태","현재 제어기가 연결되지 않았습니다.")

    def setMicroStep(self):
        print("set microstep...")
        if ser.is_open:
            cmd = "13"
            if self.radioButtonMS1.isChecked():
                cmd += "1\n"
                self.ppr = 200
            elif self.radioButtonMS2.isChecked():
                cmd += "2\n"
                self.ppr = 200 * 2
            elif self.radioButtonMS4.isChecked():
                cmd += "4\n"
                self.ppr = 200 * 4
            elif self.radioButtonMS8.isChecked():
                cmd += "8\n"
                self.ppr = 200 * 8
            elif self.radioButtonMS16.isChecked():
                cmd += "16\n"
                self.ppr = 200 * 16
            ser.write(cmd.encode("utf-8"))

    def setSpeed(self):
        print("set max speed...")
        if ser.is_open:
            sp = float(self.lineEditMaxSpeed.text().strip())
            dpr = float(self.lineEditProduct.text().strip())
            sp = sp / dpr           # to round
            sp = sp * self.ppr      # to pulse
            cmd = "11" + str(int(sp)) + "\n"
            ser.write(cmd.encode("utf-8"))

    def stopStepper(self):
        print("stop stepper...")
        if ser.is_open:
            cmd = "90\n"
            ser.write(cmd.encode("utf-8"))
        else:
            QMessageBox.about(self,"모터정지","현재 제어기가 연결되지 않았습니다.")

    def setAcceleration(self):
        print("set acceleration...")
        if ser.is_open:
            ac = float(self.lineEditAcceleration.text().strip())
            dpr = float(self.lineEditProduct.text().strip())
            ac = ac / dpr           # to round
            ac = ac * self.ppr      # to pulse
            cmd = "12" + str(int(ac)) + "\n"
            ser.write(cmd.encode("utf-8"))

    def moveStepper(self):
        print("moving stepper...")
        if ser.is_open:
            self.setMicroStep()
            self.setSpeed()
            self.setAcceleration()
            dst = float(self.lineEditMoveTarget.text().strip())
            dpr = float(self.lineEditProduct.text().strip())
            dst = dst / dpr
            dst = dst * self.ppr
            cmd = "02" + str(int(dst)) + "\n"
            ser.write(cmd.encode("utf-8"))

    def moveToStepper(self):
        print("moving to stepper...")
        if ser.is_open:
            self.setMicroStep()
            self.setSpeed()
            self.setAcceleration()
            dst = float(self.lineEditMoveTarget.text().strip())
            dpr = float(self.lineEditProduct.text().strip())
            dst = dst / dpr
            dst = dst * self.ppr
            cmd = "01" + str(int(dst)) + "\n"
            ser.write(cmd.encode("utf-8"))
            self.statusMotor.setText("모터 이동 중...")
        else:
            QMessageBox.about(self,"모터구동","현재 제어기가 연결되지 않았습니다.")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?', 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if ser.is_open:
                ser.close()
            event.accept()
            print('Window closed')
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()