import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Item {
    id: meter
    signal activated()
    property bool interactive: false
    property string title: "CPU"
    property string kind: "cpu"
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
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            radius: 11
            color: meter.interactive && iconMouse.containsMouse ? Qt.alpha(meter.accent, 0.17) : "transparent"
            border.width: meter.interactive && iconMouse.containsMouse ? 1 : 0
            border.color: Qt.alpha(meter.accent, 0.36)
            Behavior on color { ColorAnimation { duration: 130 } }
            Glyph {anchors.centerIn: parent; width:30; height:30; kind:meter.kind; ink:meter.accent}
            MouseArea {
                id:iconMouse
                anchors.fill:parent
                hoverEnabled:true
                enabled:meter.interactive
                cursorShape:Qt.PointingHandCursor
                onClicked:meter.activated()
                ToolTip.visible:containsMouse && meter.interactive
                ToolTip.delay:450
                ToolTip.text:"Abrir especificaciones de " + meter.title
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            RowLayout {
                Layout.fillWidth: true
                spacing: 9
                Text {
                    text: meter.title; color: meter.critical ? "#F36B75" : "#F0F2F8"; font.bold: true
                    font.pixelSize: 14; Layout.preferredWidth: 50
                }
                Rectangle {
                    Layout.fillWidth:true;Layout.preferredHeight:10
                    radius:5;color:"#2B3041";clip:true
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
                    color: meter.critical ? "#F36B75" : "#F2F4FC";font.bold:true;font.pixelSize:14
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
