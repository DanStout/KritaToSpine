# This script is licensed CC 0 1.0, so that you can learn from it.

# ------ CC 0 1.0 ---------------

# The person who associated a work with this deed has dedicated the
# work to the public domain by waiving all of his or her rights to the
# work worldwide under copyright law, including all related and
# neighboring rights, to the extent allowed by law.

# You can copy, modify, distribute and perform the work, even for
# commercial purposes, all without asking permission.

# https://creativecommons.org/publicdomain/zero/1.0/legalcode

from PyQt5.QtWidgets import (QWidget, QSpinBox,
                             QVBoxLayout, QFormLayout)


class CanvasSizeTool(QWidget):

    def __init__(self, mainDialog, parent=None):
        super(CanvasSizeTool, self).__init__(parent)

        self.setObjectName(i18n("Canvas Size"))

        self.layout = QFormLayout()
        self.offsetLayout = QVBoxLayout()

        self.widthSpinBox = QSpinBox()
        self.heightSpinBox = QSpinBox()
        self.xOffsetSpinBox = QSpinBox()
        self.yOffsetSpinBox = QSpinBox()

        self.setLayout(self.layout)
        self.initialize()

    def initialize(self):
        self.widthSpinBox.setRange(1, 10000)
        self.heightSpinBox.setRange(1, 10000)
        self.xOffsetSpinBox.setRange(-10000, 10000)
        self.yOffsetSpinBox.setRange(-10000, 10000)

        self.offsetLayout.addWidget(self.xOffsetSpinBox)
        self.offsetLayout.addWidget(self.yOffsetSpinBox)

        self.layout.addRow(i18n("Width:"), self.widthSpinBox)
        self.layout.addRow(i18n("Height:"), self.heightSpinBox)
        self.layout.addRow(i18n("Offset:"), self.offsetLayout)

    def adjust(self, document):
        document.resizeImage(self.xOffsetSpinBox.value(),
                             self.yOffsetSpinBox.value(),
                             self.widthSpinBox.value(),
                             self.heightSpinBox.value())

    def updateFields(self, document, settings):
        self.xOffsetSpinBox.setValue(document.xOffset())
        self.yOffsetSpinBox.setValue(document.yOffset())
        self.widthSpinBox.setValue(settings.get('canvas_width', document.width()))
        self.heightSpinBox.setValue(settings.get('canvas_height', document.height()))

    def saveSettings(self, settings):
        settings['canvas_width'] = self.widthSpinBox.value()
        settings['canvas_height'] = self.heightSpinBox.value()
