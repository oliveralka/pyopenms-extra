import sys
import pyqtgraph as pg
import pyopenms
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QFont, QFontMetricsF, QPainter, QColor, QPen, QBrush, QSpacerItem, QSizePolicy
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout


class peptide_window(QWidget):
    HEIGHT = 0
    WIDTH = 0
    SUFFIX_HEIGHT = 0

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Peptide Viewer')
        self.layout = QHBoxLayout(self)
        # change default setting of 11 px
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.pep = observed_peptide()

        # array starting with 1 and ends with len(seq)
        self.pep.setSequence("PEPTIDE")
        # self.pep.setPrefix({i: ["a%s"% (str(i))] for i in range(1, len(self.pep.sequence))}) #test sequence
        self.pep.setPrefix({1: ["a1", "b1", "c1"], 3: ["a2", "b2", "c2"]})
        self.pep.setSuffix({1: ["x1"], 2: ["x2", "y2"], 4: ["x4", "y4", "z4", "d4", "e4"]})

        # resize window to fit peptide size
        self.__resize()

        self.pep.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.pep.setMinimumSize(peptide_window.WIDTH, peptide_window.HEIGHT)
        self.layout.addItem(QSpacerItem(40, peptide_window.HEIGHT, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))
        self.layout.addWidget(self.pep)
        self.layout.addItem(QSpacerItem(40, peptide_window.HEIGHT, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))

        self.setFixedHeight(peptide_window.HEIGHT)
        self.setStyleSheet("background-color:white;")
        self.show()

    def __resize(self):
        # 8 is the space between the characters, 17 the mean of the monospace chars
        peptide_window.WIDTH = ((len(self.pep.sequence) * 17) + (len(self.pep.sequence) - 1.5) * 8)
        self.__calculateHeight()

    def __calculateHeight(self):
        prefix = self.pep.prefix
        suffix = self.pep.suffix

        # get max ion number
        max_ion_pre = len(prefix[max(prefix, key=lambda key: len(prefix[key]))])
        max_ion_suff = len(suffix[max(suffix, key=lambda key: len(suffix[key]))])

        metrics_pep = QFontMetricsF(self.pep.getFont_Pep())
        height_pep = metrics_pep.height()

        metrics_ion = QFontMetricsF(self.pep.getFont_Ion())
        height_ion = metrics_ion.height()

        # height calculated with the sum of max prefix and suffix height
        height_ion_pre = (height_ion * max_ion_pre + 15)
        peptide_window.SUFFIX_HEIGHT = (height_ion * max_ion_suff + 5)
        peptide_window.HEIGHT = height_pep + height_ion_pre + peptide_window.SUFFIX_HEIGHT


class observed_peptide(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.sequence = ""
        self.suffix = {}
        self.prefix = {}

    def setSequence(self, seq):
        self.sequence = seq

    def setSuffix(self, lst):
        self.suffix = lst

    def setPrefix(self, lst):
        self.prefix = lst

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.fillRect(event.rect(), QBrush(Qt.white))
        self.__drawPeptide(qp)
        qp.end()

    def __drawPeptide(self, qp):
        qp.setWindow(0, 0, peptide_window.WIDTH, peptide_window.HEIGHT)
        qp.setPen(QColor(168, 34, 3))
        qp.setFont(self.getFont_Pep())
        self.__fragmentPeptide(qp)

    def __fragmentPeptide(self, qp):
        SPACE = 8

        if self.sequence != "":
            seq = list(self.sequence)
            dict_seq = {i: seq[i] for i in range(0, len(seq))}

            metrics = QFontMetricsF(self.getFont_Pep())

            blank = 0
            for i, s in dict_seq.items():
                i_rev = self.__getReverseIndex(i, dict_seq)

                width = metrics.boundingRect(s).width()
                height = metrics.boundingRect(s).height()

                start_point = 0

                # position of char
                position = QPointF(start_point + blank, peptide_window.SUFFIX_HEIGHT + height)
                qp.drawText(position, s)

                # position lines
                center = ((peptide_window.SUFFIX_HEIGHT + height) - height / 4) - 1

                if s == "I":
                    pos_start = QPointF(start_point + blank - SPACE / 2 + 2, center - height / 2 - 2.5)
                else:
                    pos_start = QPointF(start_point + blank - SPACE / 2, center - height / 2 - 2.5)

                pos_end = QPointF(pos_start.x(), center + height / 2 + 2.5)

                qp.setPen(self.__getPen())
                qp.setFont(self.getFont_Ion())
                metrics_ion = QFontMetricsF(self.getFont_Ion())

                if i in self.prefix:
                    qp.drawLine(pos_start, pos_end)
                    pos_left = QPointF(pos_end.x() - 2 * SPACE, pos_end.y())
                    qp.drawLine(pos_end, pos_left)

                    prefix_ions = sorted(self.prefix[i])
                    blank_ion = 10

                    # add ions
                    for ion in prefix_ions:
                        height_ion = metrics_ion.boundingRect(ion).height()
                        pos_ion = QPointF(pos_left.x(), pos_left.y() + blank_ion)
                        qp.drawText(pos_ion, ion)
                        blank_ion += height_ion

                # for given line of existing prefix, expand with given suffix
                if i in self.prefix and i_rev in self.suffix:
                    pos_right = QPointF(pos_start.x() + 2 * SPACE, pos_start.y())
                    qp.drawLine(pos_start, pos_right)

                    suffix_ions = sorted(self.suffix[i_rev], reverse=True)
                    blank_ion = 5

                    for ion in suffix_ions:
                        height_ion = metrics_ion.boundingRect(ion).height()
                        pos_ion = QPointF(pos_end.x() + 2.5, pos_right.y() - blank_ion)
                        qp.drawText(pos_ion, ion)
                        blank_ion += height_ion

                elif i_rev in self.suffix and i not in self.prefix:
                    qp.drawLine(pos_start, pos_end)
                    pos_right = QPointF(pos_start.x() + 2 * SPACE, pos_start.y())
                    qp.drawLine(pos_start, pos_right)

                    suffix_ions = sorted(self.suffix[i_rev], reverse=True)
                    blank_ion = 5

                    for ion in suffix_ions:
                        height_ion = metrics_ion.boundingRect(ion).height()
                        pos_ion = QPointF(pos_end.x() + 2.5, pos_right.y() - blank_ion)
                        qp.drawText(pos_ion, ion)
                        blank_ion += height_ion

                blank += width + SPACE
                qp.setFont(self.getFont_Pep())

    def getFont_Pep(self):
        font = QFont("Courier")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(30)
        return font

    def getFont_Ion(self):
        font = QFont("Courier")
        font.setStyleHint(QFont.TypeWriter)
        font.setPixelSize(10)
        return font

    def __getPen(self):
        # style settings for the lines
        pen = QPen(QColor(168, 34, 3), 0.75, Qt.SolidLine)
        pen.setStyle(Qt.DashDotLine)
        return pen

    def __getReverseIndex(self, i, dict_seq):
        i_rev = 0
        if i != 0:
            i_rev = list(dict_seq.keys())[-i]
        return i_rev


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = peptide_window()
    sys.exit(app.exec_())