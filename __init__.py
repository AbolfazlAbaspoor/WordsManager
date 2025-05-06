import addonHandler
import api
import config
from globalCommands import SCRCAT_SPEECH
import globalPluginHandler
from queueHandler import eventQueue, queueFunction
import speech
import speechViewer
import tones
import versionInfo

BUILD_YEAR = getattr(versionInfo, 'version_year', 2021)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._patch()

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
		text = self.getSequenceText(sequence)
		if  "thunder" in text.strip():
			tones.beep(300, 250)
			tones.beep(400, 250)
			tones.beep(500, 250)

	def getSequenceText(self, sequence):
		return speechViewer.SPEECH_ITEM_SEPARATOR.join([x for x in sequence if isinstance(x, str)])
