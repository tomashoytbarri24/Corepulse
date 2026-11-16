import QtQuick

Rectangle {
    radius: 19
    color: "transparent"
    Rectangle {
        anchors.fill: parent
        z: -1
        radius: parent.radius
        color: themeManager.palette.panelOpaque
    }
    gradient: Gradient {
        GradientStop { position: 0.00; color: Qt.alpha(themeManager.palette.bgStart, 0.93) }
        GradientStop { position: 0.52; color: Qt.alpha(themeManager.palette.bgMid, 0.90) }
        GradientStop { position: 1.00; color: Qt.alpha(themeManager.palette.bgEnd, 0.91) }
    }
    border.width: 1
    border.color: Qt.alpha(themeManager.palette.ink, 0.10)
}
