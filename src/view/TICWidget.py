import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, \
    QHBoxLayout, QWidget, QDesktopWidget, \
    QAction, QFileDialog, QTableView, QSplitter, \
    QMenu, QAbstractItemView
from PyQt5.QtCore import Qt, QAbstractTableModel, pyqtSignal, QItemSelectionModel, QSortFilterProxyModel, QSignalMapper, \
    QPoint, QRegExp, QRectF

import pyqtgraph as pg
from pyqtgraph import PlotWidget

import numpy as np


import pyopenms

pg.setConfigOption('background', 'w')  # white background
pg.setConfigOption('foreground', 'k')  # black peaks


class TICWidget(PlotWidget):

    def __init__(self, parent=None, dpi=100):
        PlotWidget.__init__(self)
        self.setLimits(yMin=0, xMin=0)
        self.setMouseEnabled(y=False)
        self.setLabel('bottom', 'RT (min)')
        self.setLabel('left', 'relative intensity (%)')
        self._peak_labels = {}
        # numpy arrays for fast look-up
        self._rts = np.array([])
        self._ints = np.array([])
        self._peak_indices = np.array([])
        self.getViewBox().sigXRangeChanged.connect(self._autoscaleYAxis)

    def setTIC(self, chromatogram):
        # delete old labels
        if self._peak_labels != {}:
            self._clear_labels()
            self._peak_labels = {}
        self.chrom = chromatogram
        self._rts, self._ints = self.chrom.get_peaks()
        self._rts_in_min()
        self._relative_ints()
        self._peak_indices = self._find_Peak()
        self._autoscaleYAxis()
        self.redrawPlot()

    def _rts_in_min(self):
        self._rts = np.array([x/60 for x in self._rts])

    def _relative_ints(self):
        maxInt = np.amax(self._ints)
        self._ints = np.array([((x/maxInt)*100) for x in self._ints])

    def redrawPlot(self):
        self.plot(clear=True)
        self._plot_tic()
        self._plot_peak_label()

    def _autoscaleYAxis(self):
        x_range = self.getAxis('bottom').range
        if x_range == [0, 1]:  # workaround for axis sometimes not being set TODO: check if this is resovled
            x_range = [np.amin(self._rts), np.amax(self._rts)]
        self.currMaxY = self._getMaxIntensityInRange(x_range)
        if self.currMaxY:
            self.setYRange(0, self.currMaxY, update=False)
            self._redrawLabels()

    def _getMaxIntensityInRange(self, xrange):
        left = np.searchsorted(self._rts, xrange[0], side='left')
        right = np.searchsorted(self._rts, xrange[1], side='right')
        return np.amax(self._ints[left:right], initial=1)

    def _plot_tic(self):
        plotgraph = pg.PlotDataItem(self._rts, self._ints)
        self.addItem(plotgraph)

    def _currentIntensitiesInRange(self):
        x_range = self.getAxis('bottom').range
        left = np.searchsorted(self._rts, x_range[0], side='left')
        right = np.searchsorted(self._rts, x_range[1], side='right')
        current_ints = self._ints[left:right]
        return current_ints

    def _find_Peak(self):
        data = self._ints
        maxIndex = np.zeros_like(data)
        peakValue = -np.inf
        for i in range(0, len(data), 1):
            if peakValue < data[i]:
                peakValue = data[i]
                for j in range(i, len(data)):
                    if peakValue < data[j]:
                        break
                    elif peakValue == data[j]:
                        continue
                    elif peakValue > data[j]:
                        peakIndex = i + np.floor(abs(i - j) / 2)
                        maxIndex[peakIndex.astype(int)] = 1
                        i = j
                        break
            peakValue = data[i]
        maxIndex = np.where(maxIndex)[0]

        # sort indices of high points from largest intensity to smallest
        maxIndex = sorted(maxIndex, key=lambda x: data[x], reverse=True)

        return maxIndex

    def _add_label(self, label_id, label_text, pos_x, pos_y):
        label = pg.TextItem(anchor=(0.5, 1))
        label.setText(text='{0:.2f}'.format(label_text), color=(100, 100, 100))
        label.setPos(pos_x, pos_y)
        self._peak_labels[label_id] = {'label': label}
        self.addItem(label, ignoreBounds=True)

        if self._label_clashes(label_id):
            self._remove_label(label_id)

    def _remove_label(self, label_id):
        self.removeItem(self._peak_labels[label_id]['label'])
        del self._peak_labels[label_id]


    def _clear_labels(self):
        for label_id in self._peak_labels.keys():
            self.removeItem(self._peak_labels[label_id]['label'])
        self._peak_labels = {}

    def _label_clashes(self, label_id):
        new_label = label_id
        clash = False

        # scaling the distance with the correct pixel size
        pixel_width = self.getViewBox().viewPixelSize()[0]
        limit_distance = 20.0 * pixel_width

        if self._peak_labels == {}:
            return False

        for exist_label in list(self._peak_labels):
            if exist_label != new_label:
                new_label_rect = self._peak_labels[new_label]["label"].mapRectToDevice(
                    self._peak_labels[new_label]["label"].boundingRect())
                exist_label_rect = self._peak_labels[exist_label]["label"].mapRectToDevice(
                    self._peak_labels[exist_label]["label"].boundingRect())

                if not new_label_rect.intersects(exist_label_rect):
                    exist_label_X = self._peak_labels[exist_label]['label'].x()
                    new_label_X = self._peak_labels[new_label]['label'].x()

                    distance = abs(new_label_X - exist_label_X)

                    if distance < limit_distance:
                        clash = True
                        break
                    else:
                        clash = False

                elif new_label_rect.intersects(exist_label_rect):
                    clash = True
                    break
            else:
                if len(self._peak_labels) == 1 and exist_label == new_label:
                    clash = False
        return clash

    def _plot_peak_label(self):
        if self._peak_labels == {}:
            for index in self._peak_indices:
                if self._ints[index] in self._currentIntensitiesInRange():
                    self._add_label(index, self._rts[index], self._rts[index], self._ints[index])

    def _redrawLabels(self):
        self._clear_labels()
        self._plot_peak_label()