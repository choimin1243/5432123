import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QPoint

class TransparentCanvas(QMainWindow):
    def __init__(self):
        super().__init__()
        # 창 설정: 테두리 제거 및 항상 위, 투명 배경
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showMaximized()

        self.drawing = False
        self.last_point = QPoint()
        self.lines = []  # 그린 선들을 저장 (좌표, 펜 설정)
        self.current_color = QColor(0, 0, 0, 255) # 기본 검정

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
        elif event.button() == Qt.RightButton: # 우클릭 시 지우개 모드 (투명색으로 그리기)
            self.drawing = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.drawing:
            painter = QPainter(self)
            # 왼쪽 버튼은 검정색, 오른쪽 버튼은 투명색(지우개)
            color = QColor(0, 0, 0, 255) if event.buttons() & Qt.LeftButton else QColor(0, 0, 0, 0)
            
            # 지우개 구현을 위해 CompositionMode 사용
            pen = QPen(color, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            
            line = (self.last_point, event.pos(), pen, event.buttons())
            self.lines.append(line)
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drawing = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for start, end, pen, button in self.lines:
            if pen.color().alpha() == 0:
                # 지우개 모드: 해당 영역을 투명하게 복구
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
            else:
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
            painter.setPen(pen)
            painter.drawLine(start, end)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: # ESC 누르면 종료
            self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    canvas = TransparentCanvas()
    canvas.show()
    sys.exit(app.exec_())
