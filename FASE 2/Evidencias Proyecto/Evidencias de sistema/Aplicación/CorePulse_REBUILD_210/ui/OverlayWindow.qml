import QtQuick
import QtQuick.Window

// REBUILD 201: overlay de CorePulse dibujado con Qt, sin CorePulseOverlayHost.exe.
// Tres modos según overlay.py (data.osd.mode): «line» (minimalista), «osd»
// (panel avanzado) y «panel» (panel rápido con mouse). Ventana sin bordes,
// siempre encima, sin foco; deja pasar los clics salvo sobre el botón con rayo
// y en el panel rápido.
Window {
    id: win
    readonly property var info: (overlayController && overlayController.data && overlayController.data.osd) || ({})
    readonly property var design: (overlayController && overlayController.data && overlayController.data.design) || ({})
    readonly property string mode: info.mode || "hidden"
    readonly property var screenRect: info.screen || [0, 0, 1920, 1080]
    readonly property var theme: info.theme || ["#0F1828", "#1B1025", "#28B6EA"]
    readonly property real base: Math.max(0.8, Math.min(2.2, screenRect[2] * 0.25 / 382))
    readonly property real factor: base * (design.scale || 70) / 100
    readonly property real panelScale: Math.max(0.6, Math.min(2.2, Math.min(screenRect[2] * 0.82, screenRect[2] - 24) / 1440))
    readonly property real margin: 22 * factor
    readonly property bool showButton: overlayController.data.quickButton !== false
    readonly property var metrics: design.metrics || ["fps", "cpu", "gpu", "ram"]
    readonly property bool hover: !!overlayController.data.lineButtonHover
    readonly property Item activeSurface: mode === "line" ? lineSurface : mode === "osd" ? osdSurface : panelSurface
    // Centro del botón en coordenadas de la ventana (overlay.py deja pasar los clics fuera de él).
    property real buttonX: mode === "line" && showButton ? lineButton.mapToItem(win.contentItem, lineButton.width / 2, 0).x
                         : mode === "osd" && showButton ? 357 * factor : -1000
    property real buttonY: mode === "line" ? height / 2 : 20 * factor
    property real buttonRadius: showButton && (mode === "line" || mode === "osd") ? 11 * factor : 0

    transientParent: null
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
           | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
    color: "transparent"
    visible: mode !== "hidden"
    width: Math.max(1, Math.ceil(activeSurface.width))
    height: Math.max(1, Math.ceil(activeSurface.height))
    x: mode === "panel" ? screenRect[0] + (screenRect[2] - width) / 2
       : screenRect[0] + margin + Math.max(0, screenRect[2] - width - 2 * margin) * (design.x === undefined ? 1000 : design.x) / 1000
    y: mode === "panel" ? screenRect[1] + 16 * panelScale
       : screenRect[1] + margin + Math.max(0, screenRect[3] - height - 2 * margin) * (design.y === undefined ? 0 : design.y) / 1000
    Component.onCompleted: overlayController.registerLineWindow(win)

    function tint(key) {
        return key === "fps" ? "#27B6F0" : key === "cpu" ? (info.cpuColor || "#29B7F0")
             : key === "gpu" ? (info.gpuColor || "#A66BD6") : key === "ram" ? "#37CBB8" : "#A66BD6"
    }
    function value(key) {
        return key === "fps" ? (info.fpsFull || "N/A") : key === "cpu" ? (info.cpu || "N/A")
             : key === "gpu" ? (info.gpu || "N/A") : key === "ram" ? (info.ramPercent || "N/A") : (info.disk || "N/A")
    }

    component Bolt: Rectangle {
        id: bolt
        property real unit: 1
        width: 22 * unit; height: width; radius: width / 2
        color: win.hover ? "#1C5678" : "#16344E"
        border.width: 1.2; border.color: "#27B6F0"
        Canvas {
            id: boltCanvas
            anchors.fill: parent
            onPaint: {
                const g = getContext("2d"); g.reset()
                g.fillStyle = win.hover ? "#A0ECFF" : "#27B6F0"
                const c = width / 2, s = width / 22
                g.beginPath(); g.moveTo(c + 2.6 * s, c - 7.5 * s); g.lineTo(c - 4.2 * s, c + 1.2 * s); g.lineTo(c + 1 * s, c + 1.2 * s); g.closePath(); g.fill()
                g.beginPath(); g.moveTo(c - 1 * s, c - 1.2 * s); g.lineTo(c + 4.2 * s, c - 1.2 * s); g.lineTo(c - 2.6 * s, c + 7.5 * s); g.closePath(); g.fill()
            }
        }
        Connections { target: win; function onHoverChanged() { boltCanvas.requestPaint() } }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.openQuickPanel() }
    }
    component Label: Text { color: "#AABCCF"; font.pixelSize: 9 * win.factor; font.bold: true; font.family: "Segoe UI"; anchors.verticalCenter: parent.verticalCenter }
    component Value: Text { color: "#F1F8FF"; font.pixelSize: 12 * win.factor; font.weight: Font.DemiBold; font.family: "Segoe UI"; anchors.verticalCenter: parent.verticalCenter }
    component Dot: Text { text: "•"; color: "#5A6B82"; font.pixelSize: 12 * win.factor; anchors.verticalCenter: parent.verticalCenter }

    // ---------------------------------------------------------------- Minimalista
    Rectangle {
        id: lineSurface
        visible: win.mode === "line"
        width: lineRow.implicitWidth + 30 * win.factor
        height: 34 * win.factor
        radius: height / 2
        color: Qt.rgba(0.06, 0.09, 0.15, (win.design.opacity || 94) / 100)
        border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.08)
        Row {
            id: lineRow
            anchors.verticalCenter: parent.verticalCenter
            x: 16 * win.factor
            spacing: 6 * win.factor
            Label { text: "FPS" }
            Text { text: win.info.fps || "N/A"; color: win.info.fpsColor || "#AABCCF"; font.pixelSize: 15 * win.factor; font.bold: true; font.family: "Segoe UI"; anchors.verticalCenter: parent.verticalCenter }
            Dot { visible: win.design.frametime !== false }
            Label { text: "FT"; visible: win.design.frametime !== false }
            Value { text: win.info.ft || "N/A"; visible: win.design.frametime !== false }
            Repeater {
                model: win.metrics.filter(function(k) { return k !== "fps" })
                delegate: Row {
                    required property string modelData
                    spacing: 6 * win.factor
                    anchors.verticalCenter: parent.verticalCenter
                    Dot {}
                    Label { text: modelData === "disk" ? "DISCO" : modelData.toUpperCase() }
                    Value { text: modelData === "cpu" ? (win.info.cpu || "N/A") : modelData === "gpu" ? (win.info.gpu || "N/A")
                                : modelData === "ram" ? (win.info.ram || "N/A") : (win.info.disk || "N/A") }
                    Text {
                        visible: (modelData === "cpu" ? win.info.cpuTemp : modelData === "gpu" ? win.info.gpuTemp : "") ? true : false
                        text: modelData === "cpu" ? (win.info.cpuTemp || "") : (win.info.gpuTemp || "")
                        color: "#AABCCF"; font.pixelSize: 10 * win.factor; font.family: "Segoe UI"; anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        visible: modelData === "ram"
                        width: 32 * win.factor; height: 5 * win.factor; radius: height / 2; color: "#26334A"
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: parent.width * Math.max(0, Math.min(1, (win.info.ramPct || 0) / 100)); height: parent.height; radius: parent.radius; color: "#36D6A0" }
                    }
                }
            }
            Item { width: win.showButton ? 4 * win.factor : 0; height: 1 }
            Bolt { id: lineButton; unit: win.factor; visible: win.showButton; anchors.verticalCenter: parent.verticalCenter }
        }
    }

    // ---------------------------------------------------------------- Avanzado
    Rectangle {
        id: osdSurface
        visible: win.mode === "osd"
        readonly property real tileH: win.info.compact ? 52 : 70
        readonly property real logicalH: 40 + tileH + 12 + (win.design.frametime !== false ? 76 : 0)
        width: 382 * win.factor; height: logicalH * win.factor
        radius: 18 * win.factor
        opacity: (win.design.opacity || 94) / 100
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.tint(win.theme[0], Qt.alpha(win.theme[2], 0.12)) }
            GradientStop { position: 1; color: Qt.tint(win.theme[1], Qt.alpha(win.theme[0], 0.65)) }
        }
        Item {
            width: 382; height: osdSurface.logicalH
            scale: win.factor; transformOrigin: Item.TopLeft
            Text { x: 14; y: 9; text: "Core"; color: "#F1F8FF"; font.pixelSize: 17; font.bold: true; font.family: "Segoe UI" }
            Text { x: 53; y: 9; text: "Pulse"; color: "#27B6F0"; font.pixelSize: 17; font.bold: true; font.family: "Segoe UI" }
            Bolt { x: 346; y: 9; unit: 1; visible: win.showButton }
            Repeater {
                model: win.metrics
                delegate: Rectangle {
                    required property string modelData
                    required property int index
                    readonly property real tileW: (354 - (win.metrics.length - 1) * (win.design.gap || 8)) / win.metrics.length
                    x: 14 + index * (tileW + (win.design.gap || 8)); y: 40
                    width: tileW; height: osdSurface.tileH; radius: 10
                    color: Qt.alpha(win.tint(modelData), 0.14)
                    Text { x: 8; y: 7; text: modelData === "disk" ? "DISCO" : modelData.toUpperCase(); color: win.tint(modelData); font.pixelSize: 10; font.family: "Segoe UI" }
                    Text { x: 8; y: 22; width: parent.width - 12; text: win.value(modelData); color: "#F1F8FF"; font.pixelSize: modelData === "fps" ? 22 : 16; font.bold: true; elide: Text.ElideRight; font.family: "Segoe UI" }
                    Text {
                        x: 8; y: 50
                        visible: !win.info.compact && !!win.info.temps && (modelData === "cpu" || modelData === "gpu")
                        text: (modelData === "cpu" ? win.info.cpuTempFull : win.info.gpuTempFull) || "N/A"
                        color: "#AABCCF"; font.pixelSize: 10; font.family: "Segoe UI"
                    }
                }
            }
            Text {
                x: 14; y: 40 + osdSurface.tileH + 12
                visible: win.design.frametime !== false
                text: "Frametime  " + (win.info.ft || "N/A")
                color: "#AABCCF"; font.pixelSize: 10; font.family: "Segoe UI"
            }
            FrametimeChart {
                x: 14; y: 40 + osdSurface.tileH + 31; width: 354; height: 44
                visible: win.design.frametime !== false
                samples: overlayController.data.frameTimes || []
                grid: Qt.rgba(1, 1, 1, 0.08); muted: "#AABCCF"
            }
        }
    }

    // ---------------------------------------------------------------- Panel rápido
    Item {
        id: panelSurface
        visible: win.mode === "panel"
        width: 1440 * win.panelScale; height: 116 * win.panelScale
        Item {
            width: 1440; height: 116
            scale: win.panelScale; transformOrigin: Item.TopLeft
            Repeater {
                model: [
                    {x: 12, w: 276, label: "CPU", value: win.info.cpu, name: win.info.cpuName, detail: win.info.cpuTempFull, color: win.info.cpuColor || "#29B7F0"},
                    {x: 296, w: 276, label: "GPU", value: win.info.gpu, name: win.info.gpuName, detail: win.info.gpuTempFull, color: win.info.gpuColor || "#A66BD6"},
                    {x: 580, w: 190, label: "RAM", value: win.info.ramPercent, name: win.info.ramInfo, detail: "Memoria física", color: "#37CBB8"},
                    {x: 778, w: 270, label: "DISCO", value: win.info.disk, name: win.info.diskName, detail: win.info.diskInfo, color: "#A66BD6"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    x: modelData.x; y: 8; width: modelData.w; height: 100; radius: 16
                    color: Qt.tint(win.theme[0], Qt.alpha(modelData.color, 0.14))
                    border.width: 1; border.color: Qt.alpha(modelData.color, 0.35)
                    Text { x: 16; y: 13; text: modelData.label; color: modelData.color; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    Text { anchors.right: parent.right; anchors.rightMargin: 13; y: 6; text: modelData.value || "N/A"; color: modelData.color; font.pixelSize: 22; font.bold: true; font.family: "Segoe UI" }
                    Text { x: 16; y: 40; width: parent.width - 30; text: modelData.name || ""; color: "#F1F8FF"; font.pixelSize: 12; elide: Text.ElideRight; font.family: "Segoe UI" }
                    Text { x: 16; y: 71; width: parent.width - 30; text: modelData.detail || ""; color: "#AABCCF"; font.pixelSize: 12; elide: Text.ElideRight; font.family: "Segoe UI" }
                }
            }
            Rectangle {
                x: 1052; y: 0; width: 384; height: 25; radius: 8
                color: Qt.alpha(win.theme[0], 0.92)
                Text { x: 4; anchors.verticalCenter: parent.verticalCenter; width: 340; text: win.info.capture || win.info.status || "Perfiles de energía"; color: "#AABCCF"; font.pixelSize: 11; elide: Text.ElideRight; font.family: "Segoe UI" }
                Rectangle {
                    x: 352; y: 2; width: 28; height: 21; radius: 6
                    color: closeMouse.containsMouse ? Qt.alpha("#F36B75", 0.25) : "transparent"
                    Text { anchors.centerIn: parent; text: "×"; color: "#AABCCF"; font.pixelSize: 16 }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.panelAction("CLOSE", "") }
                }
            }
            Repeater {
                model: (win.info.plans || []).slice(0, 4)
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    x: 1056 + (index % 2) * 184; y: 29 + Math.floor(index / 2) * 26; width: 176; height: 23; radius: 9
                    color: modelData.active || planMouse.containsMouse ? Qt.tint(win.theme[0], Qt.alpha(win.theme[2], 0.27)) : Qt.tint(win.theme[0], Qt.alpha("#AABCCF", 0.10))
                    border.width: 1; border.color: modelData.active ? win.theme[2] : Qt.alpha("#FFFFFF", 0.08)
                    Text { anchors.centerIn: parent; width: parent.width - 12; horizontalAlignment: Text.AlignHCenter; text: modelData.name; color: modelData.active ? "#F1F8FF" : "#AABCCF"; font.pixelSize: 11; elide: Text.ElideRight; font.family: "Segoe UI" }
                    MouseArea { id: planMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.panelAction("APPLY", modelData.guid) }
                }
            }
            Rectangle {
                visible: (win.info.plans || []).length === 0
                x: 1056; y: 29; width: 176; height: 23; radius: 9; color: Qt.tint(win.theme[0], Qt.alpha("#AABCCF", 0.10))
                Text { anchors.centerIn: parent; text: "Sin planes de energía"; color: "#AABCCF"; font.pixelSize: 11; font.family: "Segoe UI" }
            }
            Repeater {
                model: [{action: "RAM", label: "RAM A FONDO", color: "#37CBB8"}, {action: "OPEN", label: "COREPULSE", color: "#27B6F0"}]
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    x: 1056 + index * 190; y: 84; width: 182; height: 24; radius: 9
                    color: actionMouse.containsMouse ? Qt.tint(win.theme[0], Qt.alpha(modelData.color, 0.32)) : Qt.tint(win.theme[0], Qt.alpha(modelData.color, 0.18))
                    border.width: 1; border.color: Qt.alpha(modelData.color, 0.6)
                    Text { anchors.centerIn: parent; text: modelData.label; color: modelData.color; font.pixelSize: 11; font.bold: true; font.family: "Segoe UI" }
                    MouseArea { id: actionMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.panelAction(modelData.action, "") }
                }
            }
        }
    }
}
