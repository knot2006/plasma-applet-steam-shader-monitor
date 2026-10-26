import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    property bool isActive: false
    property string gameTitle: "No Active Shader Job"
    property string appId: ""
    property int percent: 0
    property string counts: ""
    property int threads: 0
    property string statusText: "Idle"

    toolTipMainText: isActive ? gameTitle : "Steam Shaders"
    toolTipSubText: isActive ? ("Compiling shaders: " + percent + "% (" + counts + ")") : "No shaders currently compiling"

    Plasmoid.icon: "steam"

    Plasma5Support.DataSource {
        id: shaderSource
        engine: "executable"
        connectedSources: []

        onNewData: (sourceName, data) => {
            disconnectSource(sourceName)
            if (data["exit code"] === 0 && data.stdout) {
                try {
                    var info = JSON.parse(data.stdout.trim())
                    root.isActive = info.active
                    if (info.active) {
                        root.gameTitle = info.game || "Steam Game"
                        root.appId = info.app_id || ""
                        root.percent = info.percent || 0
                        root.counts = info.counts || ""
                        root.threads = info.threads || 0
                        root.statusText = info.status || (root.percent + "%")
                    } else {
                        root.statusText = "Idle"
                        root.gameTitle = "No Active Shader Job"
                        root.percent = 0
                        root.counts = ""
                        root.appId = ""
                    }
                } catch (e) {
                    print("Error parsing shader json: " + e)
                }
            }
        }
    }

    Timer {
        id: pollTimer
        interval: 1500
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            var scriptPath = decodeURIComponent(Qt.resolvedUrl("../scripts/check_shaders.py").toString().replace("file://", ""))
            shaderSource.connectSource("python3 '" + scriptPath.replace(/'/g, "'\\''") + "'")
        }
    }

    compactRepresentation: MouseArea {
        id: compactRoot
        implicitWidth: compactLayout.implicitWidth
        implicitHeight: compactLayout.implicitHeight
        Layout.minimumWidth: implicitWidth
        Layout.minimumHeight: implicitHeight
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        onClicked: root.expanded = !root.expanded

        RowLayout {
            id: compactLayout
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: "steam"
                Layout.preferredWidth: Kirigami.Units.iconSizes.small
                Layout.preferredHeight: Kirigami.Units.iconSizes.small
                opacity: root.isActive ? 1.0 : 0.4
            }

            PlasmaComponents.Label {
                text: root.isActive ? (root.percent + "%") : ""
                visible: root.isActive
                font.bold: true
                color: Kirigami.Theme.highlightColor
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    fullRepresentation: Item {
        Layout.preferredWidth: Kirigami.Units.gridUnit * 18
        Layout.preferredHeight: Kirigami.Units.gridUnit * 10

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: "steam"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    PlasmaComponents.Label {
                        text: "Steam Shader Pre-caching"
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize + 1
                    }
                    PlasmaComponents.Label {
                        text: root.isActive ? "Background compile in progress" : "Idle (no compilation active)"
                        opacity: 0.7
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillWidth: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                visible: root.isActive

                PlasmaComponents.Label {
                    text: root.gameTitle
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents.Label {
                        text: "App ID: " + root.appId
                        opacity: 0.7
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                    Item { Layout.fillWidth: true }
                    PlasmaComponents.Label {
                        text: root.threads > 0 ? (root.threads + " CPU threads") : ""
                        opacity: 0.7
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                }

                QQC2.ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: root.percent
                }

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents.Label {
                        text: root.percent + "% completed"
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    PlasmaComponents.Label {
                        text: root.counts ? (root.counts + " shaders") : ""
                        opacity: 0.7
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: !root.isActive

                PlasmaComponents.Label {
                    text: "✓ All shaders up to date"
                    opacity: 0.6
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            Item { Layout.fillHeight: true }

            PlasmaComponents.Label {
                text: "v" + Plasmoid.metaData.version
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                opacity: 0.6
                Layout.alignment: Qt.AlignRight
            }
        }
    }
}
