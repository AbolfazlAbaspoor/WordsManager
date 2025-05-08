import addonHandler
import config
import globalPluginHandler
import speech
import speechViewer
import tones
import versionInfo
import gui
import wx
import time

BUILD_YEAR = getattr(versionInfo, 'version_year', 2021)
CONFIG_SECTION = "monitoredWordsAddon"
TOGGLE_INTERVAL = 0.7

def getMonitoredWords():
	if CONFIG_SECTION not in config.conf:
		config.conf[CONFIG_SECTION] = {}
	return config.conf[CONFIG_SECTION].get("words", [])

def setMonitoredWords(words):
	if CONFIG_SECTION not in config.conf:
		config.conf[CONFIG_SECTION] = {}
	config.conf[CONFIG_SECTION]["words"] = words
	config.conf.save()

def getEnabled():
	if CONFIG_SECTION not in config.conf:
		config.conf[CONFIG_SECTION] = {}
	return config.conf[CONFIG_SECTION].get("enabled", True)

def setEnabled(enabled):
	if CONFIG_SECTION not in config.conf:
		config.conf[CONFIG_SECTION] = {}
	config.conf[CONFIG_SECTION]["enabled"] = enabled
	config.conf.save()

class WordListDialog(wx.Dialog):
	def __init__(self, parent, words):
		super().__init__(parent, title="Manage Monitored Words", size=(350, 350))
		self.words = list(words)
		self._initUI()
		self.CenterOnScreen()

	def _initUI(self):
		pnl = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)
		self.listbox = wx.ListBox(pnl, choices=self.words, style=wx.LB_SINGLE)
		vbox.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 10)
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		self.addBtn = wx.Button(pnl, label="Add")
		self.editBtn = wx.Button(pnl, label="Edit")
		self.removeBtn = wx.Button(pnl, label="Remove")
		hbox.Add(self.addBtn, 0, wx.RIGHT, 5)
		hbox.Add(self.editBtn, 0, wx.RIGHT, 5)
		hbox.Add(self.removeBtn, 0)
		vbox.Add(hbox, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
		btnBox = wx.BoxSizer(wx.HORIZONTAL)
		self.okBtn = wx.Button(pnl, wx.ID_OK, "OK")
		self.cancelBtn = wx.Button(pnl, wx.ID_CANCEL, "Cancel")
		btnBox.Add(self.okBtn, 0, wx.RIGHT, 5)
		btnBox.Add(self.cancelBtn, 0)
		vbox.Add(btnBox, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
		pnl.SetSizer(vbox)
		self.addBtn.Bind(wx.EVT_BUTTON, self.onAdd)
		self.editBtn.Bind(wx.EVT_BUTTON, self.onEdit)
		self.removeBtn.Bind(wx.EVT_BUTTON, self.onRemove)

	def onAdd(self, event):
		dlg = wx.TextEntryDialog(self, "Enter a word to monitor:", "Add Word")
		if dlg.ShowModal() == wx.ID_OK:
			word = dlg.GetValue().strip()
			if word and word.lower() not in [w.lower() for w in self.words]:
				self.words.append(word)
				self.listbox.Append(word)
		dlg.Destroy()

	def onEdit(self, event):
		sel = self.listbox.GetSelection()
		if sel != wx.NOT_FOUND:
			oldWord = self.words[sel]
			dlg = wx.TextEntryDialog(self, "Edit the selected word:", "Edit Word", value=oldWord)
			if dlg.ShowModal() == wx.ID_OK:
				newWord = dlg.GetValue().strip()
				if newWord and newWord.lower() not in [w.lower() for i, w in enumerate(self.words) if i != sel]:
					self.words[sel] = newWord
					self.listbox.SetString(sel, newWord)
			dlg.Destroy()

	def onRemove(self, event):
		sel = self.listbox.GetSelection()
		if sel != wx.NOT_FOUND:
			self.words.pop(sel)
			self.listbox.Delete(sel)

	def getWords(self):
		return self.words

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	__gestures = {
		"kb:windows+NVDA+w": "showWordDialog"
	}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._patch()
		self._lastActivation = 0
		self._dialogOpen = False  # Track if dialog is open

	def _patch(self):
		if BUILD_YEAR >= 2021:
			self.oldSpeak = speech.speech.speak
			speech.speech.speak = self.mySpeak
		else:
			self.oldSpeak = speech.speak
			speech.speak = self.mySpeak

	def terminate(self, *args, **kwargs):
		super().terminate(*args, **kwargs)
		if BUILD_YEAR >= 2021:
			speech.speech.speak = self.oldSpeak
		else:
			speech.speak = self.oldSpeak

	def mySpeak(self, sequence, *args, **kwargs):
		self.oldSpeak(sequence, *args, **kwargs)
		if not getEnabled():
			return
		text = self.getSequenceText(sequence).lower()
		for word in getMonitoredWords():
			if word.lower() in text:
				tones.beep(300, 250)
				tones.beep(400, 250)
				tones.beep(500, 250)
				break

	def getSequenceText(self, sequence):
		return speechViewer.SPEECH_ITEM_SEPARATOR.join([x for x in sequence if isinstance(x, str)])

	def script_showWordDialog(self, gesture):
		now = time.time()
		if now - getattr(self, "_lastActivation", 0) < TOGGLE_INTERVAL:
			# Toggle the add-on enabled state when double-tapped
			enabled = not getEnabled()
			setEnabled(enabled)
			if enabled:
				tones.beep(2000, 150)
			else:
				tones.beep(100, 200)

			if self._dialogOpen:  # If the dialog is open, close it
				wx.CallAfter(self.closeWordDialog)
			self._lastActivation = 0
		else:
			self._lastActivation = now
			if not self._dialogOpen:  # If dialog is not open, open it
				wx.CallAfter(self.showWordDialog)
	script_showWordDialog.__doc__ = "Manage monitored words or double-press to toggle add-on"

	def showWordDialog(self):
		if self._dialogOpen:
			return
		self._dialogOpen = True
		self.dialog = WordListDialog(gui.mainFrame, getMonitoredWords())
		if self.dialog.ShowModal() == wx.ID_OK:
			setMonitoredWords(self.dialog.getWords())
		self.dialog.Destroy()
		self._dialogOpen = False  # Reset dialog status

	def closeWordDialog(self):
		if self._dialogOpen and self.dialog:  # If the dialog is open, close it
			self.dialog.EndModal(wx.ID_CANCEL)
			self.dialog.Destroy()
			self._dialogOpen = False
