import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Item {
    id: meter
    signal activated()
    property bool interactive: false
    property string title: "CPU"
    property string kind: "cpu"
    property string brandVendor: "unknown"
    readonly property bool brandedCpu: kind === "cpu" && (brandVendor === "intel" || brandVendor === "amd")
    readonly property bool brandedGpu: kind === "gpu" && (brandVendor === "nvidia" || brandVendor === "amd" || brandVendor === "intel")
    readonly property bool hasBrandMark: brandedCpu || brandedGpu
    readonly property color brandFill: brandVendor === "nvidia" ? "#76B900" : brandVendor === "amd" ? "#B11F25" : brandVendor === "intel" ? "#1AA0F2" : "transparent"
    readonly property color brandInk: hasBrandMark ? "#FFFFFF" : accent
    property string hardwareName: ""
    property string secondary: "N/A"
    property string secondaryPrefix: ""
    property var temperature: null
    property real hotThreshold: 90
    property bool critical: false
    readonly property bool hasTemperature: typeof temperature === "number" && isFinite(temperature) && temperature >= 5 && temperature <= 125
    readonly property bool tooHot: hasTemperature && temperature >= hotThreshold
    property string sourceHint: ""  // Se presenta solo al pasar el mouse, no ocupa espacio.
    property var value: null
    property color accent: "#1AB9F7"
    readonly property bool measured: typeof value === "number" && isFinite(value) && value >= 0 && value <= 100
    implicitHeight: 78
    HoverHandler { id: detailsHover }
    ToolTip.visible: detailsHover.hovered && meter.sourceHint.length > 0
    ToolTip.delay: 650
    ToolTip.text: meter.sourceHint

    RowLayout {
        anchors.fill: parent
        spacing: 12
        Rectangle {
            Layout.preferredWidth: 40
            Layout.preferredHeight: 40
            radius: 12
            color: meter.hasBrandMark
                ? meter.brandFill
                : meter.interactive && iconMouse.containsMouse ? Qt.alpha(meter.accent, 0.17) : "transparent"
            border.width: meter.hasBrandMark ? 0 : (meter.interactive && iconMouse.containsMouse ? 1 : 0)
            border.color: Qt.alpha(meter.accent, 0.36)
            Behavior on color { ColorAnimation { duration: 130 } }

            // El icono original solo aparece cuando no hay fabricante conocido.
            Glyph {
                anchors.centerIn: parent
                width: 32; height: 32
                visible: !meter.hasBrandMark
                kind: meter.kind
                ink: meter.accent
            }
            Glyph {
                anchors.centerIn: parent
                width: 29; height: 29
                visible: meter.brandedGpu && meter.brandVendor === "nvidia"
                kind: "gpu_nvidia"
                ink: meter.brandInk
            }
            Glyph {
                anchors.centerIn: parent
                width: 32; height: 10
                visible: meter.hasBrandMark && meter.brandVendor === "amd"
                kind: "gpu_amd"
                ink: meter.brandInk
            }
            Text {
                visible: meter.hasBrandMark && meter.brandVendor === "intel"
                anchors.centerIn: parent
                text: "intel"
                color: meter.brandInk
                font.family: "Segoe UI"
                font.pixelSize: 10
                font.weight: Font.DemiBold
            }
            MouseArea {
                id:iconMouse
                anchors.fill:parent
                hoverEnabled:true
                enabled:meter.interactive
                cursorShape:Qt.PointingHandCursor
                onClicked:meter.activated()
                ToolTip.visible:containsMouse && meter.interactive
                ToolTip.delay:450
                ToolTip.text:meter.kind.indexOf("storage") === 0 ? "Seleccionar unidad y abrir detalles del almacenamiento" : "Abrir especificaciones de " + meter.title
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            RowLayout {
                Layout.fillWidth: true
                spacing: 9
                Text {
                    text: meter.title; color: meter.critical ? "#F36B75" : themeManager.palette.ink; font.bold: true
                    font.pixelSize: 14; Layout.preferredWidth: 50
                }
                Rectangle {
                    Layout.fillWidth:true;Layout.preferredHeight:10
                    radius:5;color:themeManager.palette.panelBorder;clip:true
                    Rectangle {
                        width: meter.measured ? parent.width*Number(meter.value)/100 : 0
                        height: parent.height;radius:5;color:meter.accent
                        Behavior on width { NumberAnimation { duration: 240 } }
                    }
                }
                Text {
                    Layout.preferredWidth:43
                    horizontalAlignment: Text.AlignRight
                    text: meter.measured ? Math.round(meter.value)+"%" : "N/A"
                    color: meter.critical ? "#F36B75" : themeManager.palette.ink;font.bold:true;font.pixelSize:14
                }
            }
            Text {
                Layout.fillWidth:true
                visible: hardwareName.length>0 && hardwareName!=="N/A"
                text: meter.hardwareName
                color:"#E8EAF3";font.pixelSize:11;font.bold:true
                elide: Text.ElideRight
            }
            Text {
                visible: meter.secondaryPrefix.length === 0
                Layout.fillWidth:true; text:meter.secondary
                color:meter.critical ? "#F36B75" : meter.tooHot ? "#F36B75" : "#A7B0C1"
                font.pixelSize:11;elide:Text.ElideRight
            }
            RowLayout {
                visible: meter.secondaryPrefix.length > 0
                Layout.fillWidth:true; spacing:3
                Text {
                    text:meter.secondaryPrefix
                    color:"#A7B0C1";font.pixelSize:10
                    Layout.preferredWidth: Math.min(implicitWidth, 105)
                    elide:Text.ElideRight
                }
                Text {
                    Layout.fillWidth:true
                    text:"Temp. " + (meter.hasTemperature ? meter.temperature.toFixed(1)+" °C" : "N/A")
                    color:meter.tooHot ? "#F36B75" : "#A7B0C1"
                    font.pixelSize:10; font.bold:meter.tooHot; elide:Text.ElideRight
                }
            }
        }
    }
}
