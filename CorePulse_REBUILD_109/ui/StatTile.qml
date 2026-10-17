import QtQuick
import QtQuick.Layouts

Rectangle {
    id: tile
    property string title: "Estado"
    property string content: "N/A"
    property string detail: "Pendiente"
    property string kind: "health"
    property color accent: "#1AB9F7"
    property bool interactive: false
    property bool restartVisible: false
    signal restartRequested()
    signal activated()
    radius: 20
    color: tile.interactive && tileMouse.containsMouse ? themeManager.palette.panelRaised : themeManager.palette.panel
    border.width: 1
    border.color: tile.interactive && tileMouse.containsMouse ? Qt.alpha(tile.accent, 0.56) : themeManager.palette.panelBorder
    Behavior on color { ColorAnimation { duration: 160 } }
    Behavior on border.color { ColorAnimation { duration: 160 } }
    clip: true
    ColumnLayout {
        anchors.fill:parent
        anchors.margins:15
        spacing:8
        RowLayout {
            Layout.fillWidth:true
            spacing:10
            Rectangle {
                Layout.preferredWidth:42;Layout.preferredHeight:42
                radius:13;color:Qt.alpha(tile.accent,0.13)
                Glyph { anchors.centerIn:parent;width:28;height:28;kind:tile.kind;ink:tile.accent }
            }
            Text {
                Layout.fillWidth:true
                text:tile.title;color:themeManager.palette.ink;font.bold:true;font.pixelSize:13
                elide:Text.ElideRight
            }
        }
        Item { Layout.fillHeight:true; Layout.minimumHeight:0 }
        Text {
            Layout.fillWidth:true
            text:tile.content;color:tile.accent
            font.pixelSize:tile.restartVisible ? 23 : tile.content.length > 10 ? 23 : 29
            font.bold:true;horizontalAlignment:Text.AlignHCenter
            elide:Text.ElideRight
        }
        Text {
            visible: !tile.restartVisible
            Layout.fillWidth:true
            text:tile.detail;color:themeManager.palette.muted;font.pixelSize:11
            horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight
        }
        Rectangle {
            id: rebootButton
            visible: tile.restartVisible
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 102; Layout.preferredHeight: 29
            radius:9
            color: rebootArea.containsMouse ? "#542831" : "#38232D"
            border.width:1; border.color: rebootArea.containsMouse ? "#F36B75" : "#8D4852"
            Text {
                anchors.centerIn: parent
                text:"Reiniciar";font.pixelSize:11;font.bold:true;color:"#FFAFB5"
            }
            MouseArea {
                id: rebootArea; anchors.fill:parent;hoverEnabled:true
                cursorShape:Qt.PointingHandCursor
                onClicked:tile.restartRequested()
            }
        }
    }
    MouseArea {
        id: tileMouse
        anchors.fill: parent
        enabled: tile.interactive
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: tile.activated()
    }
}
