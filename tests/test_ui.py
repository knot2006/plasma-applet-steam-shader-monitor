import json
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
try:
    from PyQt6.QtCore import QMetaObject, QUrl
    from PyQt6.QtGui import QFont, QGuiApplication
    from PyQt6.QtQml import QQmlComponent, QQmlEngine
    from PyQt6.QtQuick import QQuickItem
except ImportError:
    QGuiApplication = None


ROOT = Path(__file__).resolve().parents[1]
QML = (ROOT / "contents/ui/main.qml").read_text()
IMPORTS = "\n".join(line for line in QML.splitlines() if line.startswith("import ") and "plasmoid" not in line)
PROPERTIES = '''
    property bool isActive: true
    property string gameTitle: "Current Game"
    property string appId: "222"
    property int percent: 100
    property string counts: "100/100"
    property int threads: 8
    property bool expanded: false
'''


@unittest.skipIf(QGuiApplication is None, "PyQt6 required for headless QML tests")
class QmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        self.engine = QQmlEngine()
        version = json.loads((ROOT / "metadata.json").read_text())["KPlugin"]["Version"]
        self.engine.rootContext().setContextProperty("Plasmoid", {"metaData": {"version": version}})
        self.objects = []

    def create(self, source, path):
        component = QQmlComponent(self.engine)
        component.setData(source.encode(), QUrl.fromLocalFile(str(path)))
        obj = component.create()
        self.assertIsNotNone(obj, "\n".join(error.toString() for error in component.errors()))
        self.objects.extend([component, obj])
        return obj

    def settle(self):
        for _ in range(5):
            self.app.processEvents()

    def test_poll_runs_from_path_with_spaces_quotes_and_url_characters(self):
        poll = QML.split("onTriggered: {", 1)[1].split("\n        }", 1)[0]
        source = '''import QtQuick
import org.kde.plasma.plasma5support as Plasma5Support
Item {
    id: root
    property int exitCode: -1
    property string output: ""
    property string errorOutput: ""
    Plasma5Support.DataSource {
        id: shaderSource
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            if (data["exit code"] !== undefined) {
                root.exitCode = data["exit code"]
                root.output = data.stdout
                root.errorOutput = data.stderr
                disconnectSource(sourceName)
            }
        }
    }
    function poll() {''' + poll + '''
    }
}'''
        with tempfile.TemporaryDirectory() as directory:
            contents = Path(directory) / "widget ' $ & ; # % żółć" / "contents"
            script = contents / "scripts/check_shaders.py"
            script.parent.mkdir(parents=True)
            script.write_text('print(\'{"active": true, "percent": 42}\')\n')
            obj = self.create(source, contents / "ui/main.qml")
            QMetaObject.invokeMethod(obj, "poll")
            deadline = time.monotonic() + 5
            while obj.property("exitCode") == -1 and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
            self.assertEqual(obj.property("exitCode"), 0, obj.property("errorOutput"))
            self.assertEqual(json.loads(obj.property("output")), {"active": True, "percent": 42})

    def test_compact_layout_reserves_width_for_idle_and_active_states(self):
        compact = QML.split("compactRepresentation: ", 1)[1].split("\n    fullRepresentation:", 1)[0]
        obj = self.create(IMPORTS + '''
Item {
    id: root
    width: Math.max(32, compactRoot.Layout.minimumWidth)
    height: Math.max(32, compactRoot.Layout.minimumHeight)
    property real requiredWidth: compactRoot.Layout.minimumWidth
    property real contentWidth: compactLayout.width
    property real contentX: compactLayout.x
    property var percentageLabel: compactLayout.children[1]
    property var row: compactLayout
''' + PROPERTIES + compact + "\n}", ROOT / "contents/ui/CompactTest.qml")
        for active, percent in ((False, 0), (True, 0), (True, 9), (True, 42), (True, 100)):
            with self.subTest(active=active, percent=percent):
                obj.setProperty("isActive", active)
                obj.setProperty("percent", percent)
                obj.property("row").ensurePolished()
                self.settle()
                self.assertGreater(obj.property("requiredWidth"), 0)
                self.assertGreaterEqual(obj.property("contentX"), -0.5)
                self.assertLessEqual(obj.property("contentX") + obj.property("contentWidth"), obj.property("width") + 0.5)
        font = QFont()
        font.setPointSize(24)
        obj.property("percentageLabel").setProperty("font", font)
        obj.property("percentageLabel").ensurePolished()
        obj.property("row").ensurePolished()
        self.settle()
        self.assertGreater(obj.property("requiredWidth"), 52)
        self.assertLessEqual(obj.property("contentX") + obj.property("contentWidth"), obj.property("width") + 0.5)

    def test_full_view_loads_in_active_and_idle_states(self):
        full = QML.split("fullRepresentation: ", 1)[1].rsplit("\n}", 1)[0]
        full = full.replace("Item {", "Item {\n    id: root\n" + PROPERTIES, 1)
        obj = self.create(IMPORTS + "\n" + full, ROOT / "contents/ui/FullTest.qml")
        obj.setProperty("width", 360)
        obj.setProperty("height", 240)
        for active in (True, False):
            obj.setProperty("isActive", active)
            self.settle()
            items = [obj]
            visible_text = []
            while items:
                item = items.pop()
                items.extend(child for child in item.childItems() if isinstance(child, QQuickItem))
                if item.isVisible() and item.property("text"):
                    visible_text.append(item.property("text"))
            if active:
                self.assertIn("Current Game", visible_text)
                self.assertIn("8 CPU threads", visible_text)
                self.assertNotIn("✓ All shaders up to date", visible_text)
            else:
                self.assertIn("✓ All shaders up to date", visible_text)
                self.assertNotIn("Current Game", visible_text)


if __name__ == "__main__":
    unittest.main()
