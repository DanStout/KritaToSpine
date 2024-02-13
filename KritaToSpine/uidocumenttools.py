# This script is licensed CC 0 1.0, so that you can learn from it.

# ------ CC 0 1.0 ---------------

# The person who associated a work with this deed has dedicated the
# work to the public domain by waiving all of his or her rights to the
# work worldwide under copyright law, including all related and
# neighboring rights, to the extent allowed by law.

# You can copy, modify, distribute and perform the work, even for
# commercial purposes, all without asking permission.

# https://creativecommons.org/publicdomain/zero/1.0/legalcode

import krita
from . import documenttoolsdialog
from . import SpineExport

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (QFormLayout, QListWidget, QAbstractItemView, QLineEdit, QFileDialog, QLabel,
                             QDialogButtonBox, QVBoxLayout, QFrame, QTabWidget, QSpinBox,
                             QPushButton, QAbstractScrollArea, QMessageBox, QHBoxLayout, QCheckBox)
import os
import krita
import importlib
import json


class UIDocumentTools(object):

    def __init__(self):
        self.mainDialog = documenttoolsdialog.DocumentToolsDialog()
        self.spineExport = SpineExport.SpineExport()
        self.mainLayout = QVBoxLayout(self.mainDialog)
        self.formLayout = QFormLayout()
        self.documentLayout = QVBoxLayout()
        self.refreshButton = QPushButton(i18n("Refresh"))
        self.widgetDocuments = QListWidget()
        self.tabTools = QTabWidget()
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.outputField = QLabel()

        # Output directory
        self.directorySelectorLayout = QHBoxLayout()
        self.directoryTextField = QLineEdit()
        self.directoryDialogButton = QPushButton(i18n("..."))
        
        # Bone length
        self.boneLengthField = QSpinBox()
        self.boneLengthField.setRange(0, 100)
        
        self.includeHiddenCheckbox = QCheckBox(i18n("Include Hidden Layers"))

        self.kritaInstance = krita.Krita.instance()
        self.documentsList = []

        self.refreshButton.clicked.connect(self.refreshButtonClicked)
        self.buttonBox.accepted.connect(self.confirmButton)
        self.buttonBox.rejected.connect(self.mainDialog.close)
        self.directoryDialogButton.clicked.connect(self._selectDir)
        self.widgetDocuments.clicked.connect(self._documentSelected)

        self.mainDialog.setWindowModality(Qt.NonModal)
        self.widgetDocuments.setSelectionMode(QAbstractItemView.SingleSelection)
        self.widgetDocuments.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def initialize(self):
        self.loadTools()

        self.documentLayout.addWidget(self.widgetDocuments)
        self.documentLayout.addWidget(self.refreshButton)
        self.directorySelectorLayout.addWidget(self.directoryTextField)
        self.directorySelectorLayout.addWidget(self.directoryDialogButton)

        self.formLayout.addRow(i18n("Documents:"), self.documentLayout)
        self.formLayout.addRow(i18n("Output Directory:"), self.directorySelectorLayout)
        self.formLayout.addRow(i18n("Bone Length:"), self.boneLengthField )
        self.formLayout.addRow(self.includeHiddenCheckbox)
        self.formLayout.addRow(self.tabTools)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.mainLayout.addLayout(self.formLayout)
        self.mainLayout.addWidget(self.line)
        self.mainLayout.addWidget(self.outputField)
        self.mainLayout.addWidget(self.buttonBox)

        self.mainDialog.resize(500, 300)
        self.mainDialog.setWindowTitle(i18n("Export to Spine"))
        self.mainDialog.setSizeGripEnabled(True)
        self.mainDialog.show()
        self.mainDialog.activateWindow()

        userDefaults = os.path.expanduser("~/.kritatospine")
        
        self.loadDocuments()


    def loadTools(self):
        modulePath = 'KritaToSpine.tools'
        toolsModule = importlib.import_module(modulePath)
        modules = []

        for classPath in toolsModule.ToolClasses:
            _module = classPath[:classPath.rfind(".")]
            _klass = classPath[classPath.rfind(".") + 1:]
            modules.append(dict(module='{0}.{1}'.format(modulePath, _module),
                                klass=_klass))

        for module in modules:
            m = importlib.import_module(module['module'])
            toolClass = getattr(m, module['klass'])
            obj = toolClass(self.mainDialog)
            self.tabTools.addTab(obj, obj.objectName())

    def loadDocuments(self):
        self.widgetDocuments.clear()

        self.documentsList = [
            document for document in self.kritaInstance.documents()
            if document.fileName()
        ]

        for document in self.documentsList:
            self.widgetDocuments.addItem(document.fileName())
           
        if self.documentsList:
            self.widgetDocuments.setCurrentItem(self.widgetDocuments.item(0))
            self._documentSelected()

    def refreshButtonClicked(self):
        self.outputField.clear()
        self.loadDocuments()

    def confirmButton(self):
        self.outputField.setText(i18n("Exporting..."))
        
        doc = self._selectedDocuments()[0]

        if doc:
            widget = self.tabTools.currentWidget()
            
            #Krita seems to have a bug where invisible guides in a cloned document get scaled incorrectly
            #Bug: https://bugs.kde.org/show_bug.cgi?id=463713
            oldGuideVis = doc.guidesVisible()
            doc.setGuidesVisible(True)
            cloneDoc = doc.clone()
            doc.setGuidesVisible(oldGuideVis)
            
            widget.adjust(cloneDoc)
            # Save the json from the clone
            self.spineExport.exportDocument(cloneDoc, self.directoryTextField.text(), self.boneLengthField.value(), self.includeHiddenCheckbox.isChecked())
            # Clone no longer needed
            cloneDoc.close()
            
            self.outputField.setText(i18n("Saving settings..."))
            
            jsonVal = {
                "outDir": self.directoryTextField.text(),
                "includeHidden": self.includeHiddenCheckbox.isChecked()
            }
            widget.saveSettings(jsonVal)

            setPath = self._getSettingsPath(doc.fileName())
            
            with open(setPath, "w") as outFile:
                json.dump(jsonVal, outFile, indent=2)
            #os.system("attrib +h \"{0}\"".format(setPath))

            self.outputField.setText(i18n("The selected document has been exported."))
        else:
            self.outputField.setText(i18n("Please select a document."))

    def _getSettingsPath(self, fileName):
        return "{0}.spinesettings.json".format(fileName)

    def _selectDir(self):
        doc = self._selectedDocuments()
        if doc[0]:
            initialDir = os.path.dirname(doc[0].fileName())
        else:
            initialDir = os.path.expanduser("~")

        directory = QFileDialog.getExistingDirectory(self.mainDialog, i18n("Select a Folder"), initialDir, QFileDialog.ShowDirsOnly)
        self.directoryTextField.setText(directory)

    def _documentSelected(self):
        doc = self._selectedDocuments()
        fileName = doc[0].fileName()
        
        setPath = self._getSettingsPath(fileName)
        widget = self.tabTools.currentWidget()
        
        if os.path.exists(setPath):
            with open(setPath, "r") as inFile:
                docData = json.load(inFile)
                self.directoryTextField.setText(docData["outDir"])
                self.includeHiddenCheckbox.setChecked(docData["includeHidden"])
                widget.updateFields(doc[0], docData)
        else: 
            self.directoryTextField.setText(os.path.dirname(fileName))
        # TODO have this loop through the tabs and set them up
        # Tell the widget to update itself to the current settings
        self.outputField.clear()

    def _selectedDocuments(self):
        selectedPaths = [
            item.text() for item in self.widgetDocuments.selectedItems()]
        selectedDocuments = [
            document for document in self.documentsList
            for path in selectedPaths if path == document.fileName()]
        return selectedDocuments

