import os
import re
import krita
import json
import pathlib

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMessageBox)

class SpineExport(object):

    def __init__(self, parent=None):
        self.msgBox = None
        self.fileFormat = 'png'

        self.bonePattern = re.compile("\(bone\)|\[bone\]", re.IGNORECASE)
        self.mergePattern = re.compile("\(merge\)|\[merge\]", re.IGNORECASE)
        self.slotPattern = re.compile("\(slot\)|\[slot\]", re.IGNORECASE)
        self.skinPattern = re.compile("\(skin(:.+)?\)|\[skin(:.+)?\]", re.IGNORECASE)

    def exportDocument(self, document, directory, boneLength, includeHidden):
        if document is not None:
            self.json = {
                "skeleton": {"images": directory},
                "bones": [{"name": "root"}],
                "slots": [],
                "skins": {"default": {}},
                "animations": {}
            }
            self.spineBones = self.json['bones']
            self.spineSlots = self.json['slots']
            self.spineSkins = self.json['skins']
            self.boneLength = boneLength
            self.includeHidden = includeHidden

            horGuides = document.horizontalGuides()
            verGuides = document.verticalGuides()

            xOrigin = 0
            yOrigin = 0
                        
            if len(horGuides) == 1 and len(verGuides) == 1:
                xOrigin = verGuides[0]
                yOrigin = -horGuides[0] + 1
            else:
                self._alert(f"Not exactly 1 each of {horGuides} horizontal and {verGuides} vertical guides; not using origin")

            krita.Krita.instance().setBatchmode(True)
            self.document = document
            self._export(document.rootNode(), directory, "root", xOrigin, yOrigin)
            krita.Krita.instance().setBatchmode(False)
            with open('{0}/{1}'.format(directory, 'spine.json'), 'w') as outfile:
                json.dump(self.json, outfile, indent=2)
        else:
            self._alert("Please select a Document")

    @staticmethod
    def quote(value):
        return '"' + value + '"'
        
    @staticmethod
    # Returns None if the name doesn't contain the tag. Empty string if the tag is present but has no value, otherwise returns the tag's value
    def getTagValue(name, tag):
        regex = "\[{0}:?([^\]]+)?\]".format(tag)
        matches = re.findall(regex, name, flags=re.IGNORECASE)
        if len(matches) > 0:
            return matches[0].strip()
        else:
            return None

    def _alert(self, message):
        print(f"Showing alert: {message}")
        self.msgBox = self.msgBox if self.msgBox else QMessageBox()
        self.msgBox.setText(message)
        self.msgBox.exec()
        
    def _getSlot(self, name):
        return next((x for x in self.spineSlots if x['name'] == name), None)

    def _export(self, node, directory, bone="root", xOffset=0, yOffset=0, slot=None, currentSkinName="default"):
        for child in node.childNodes():
            if "selectionmask" in child.type():
                continue

            if not self.includeHidden and not child.visible():
                continue

            if '[ignore]' in child.name():
                continue
                
            # Special "fake" Krita layer - maybe used for showing guides?
            if child.name() == "decorations-wrapper-layer":
                continue;
                
            # Save a copy so other children don't affect us
            skinName = currentSkinName
            
            childDir = directory

            if "grouplayer" in child.type():
                child.setPassThroughMode(False)

            if child.childNodes() and not self.mergePattern.search(child.name()):
                newBone = bone
                newSlot = slot
                newX = xOffset
                newY = yOffset

                # Found a bone
                if self.bonePattern.search(child.name()):
                    newBone = self.bonePattern.sub('', child.name()).strip()
                    rect = child.bounds()
                    newX = rect.left() + rect.width() / 2 - xOffset
                    newY = (- rect.bottom() + rect.height() / 2) - yOffset
                    self.spineBones.append({
                        'name': newBone,
                        'parent': bone,
                        'length': self.boneLength,
                        'x': newX,
                        'y': newY
                    })
                    newX = xOffset + newX
                    newY = yOffset + newY

                # Found a slot
                if self.slotPattern.search(child.name()):
                    newSlotName = self.slotPattern.sub('', child.name()).strip()

                    newSlot = self._getSlot(newSlotName)
                    if (newSlot == None):
                        newSlot = {
                            'name': newSlotName,
                            'bone': bone,
                            'attachment': None,
                            'blend': 'normal',
                        }
                        self.spineSlots.append(newSlot)

                # Found a skin
                newSkinName = self.getTagValue(child.name(), "skin")

                if newSkinName is not None:
                    skinName = newSkinName
                    childDir = childDir + "/" + skinName
                    pathlib.Path(childDir).mkdir(parents=True, exist_ok=True)
                
                self._export(child, directory, newBone, newX, newY, newSlot, skinName)
                continue
                
            newSkinName = self.getTagValue(child.name(), "skin")
            if newSkinName is not None:
                skinName = newSkinName
                childDir = directory + "/" + skinName
                pathlib.Path(childDir).mkdir(parents=True, exist_ok=True)

            name = self.mergePattern.sub('', child.name()).strip()
            name = self.skinPattern.sub('', name).strip()
            fileName = name if skinName == "default" else "{0}/{1}".format(skinName, name)
            outPath = '{0}/{1}.{2}'.format(directory, fileName, self.fileFormat)
            print("outpath: " + outPath)
            ## Note there is an optional bounds setting here
            child.save(outPath, 96, 96, krita.InfoObject()) 

            newSlot = slot

            if not newSlot:
                newSlot = self._getSlot(name)
                if newSlot == None:
                    newSlot = {
                        'name': name,
                        'bone': bone,
                        'attachment': name,
                        'blend': 'normal',
                    }
                    self.spineSlots.append(newSlot)
            else:
                if not newSlot['attachment']:
                    newSlot['attachment'] = name

            # Found a blend mode
            if child.blendingMode() == 'multiply':
                newSlot['blend'] = 'multiply'
            if child.blendingMode() == 'add':
                newSlot['blend'] = 'additive'
            if child.blendingMode() == 'screen':
                newSlot['blend'] = 'screen'

            rect = child.bounds()
            slotName = newSlot['name']
            
            if skinName not in self.spineSkins:
                self.spineSkins[skinName] = {}
                
            skinDict = self.spineSkins[skinName]
            
            if slotName not in skinDict:
                skinDict[slotName] = {}
            
            slotDict = skinDict[slotName]
            
            slotDict[name] = {
                'x': round(rect.left() + rect.width() / 2 - xOffset, 2),
                'y': round((- rect.bottom() + rect.height() / 2) - yOffset, 2),
                'width': rect.width(),
                'height': rect.height(),
            }
            
            if name != fileName:
                slotDict[name]["name"] = fileName



