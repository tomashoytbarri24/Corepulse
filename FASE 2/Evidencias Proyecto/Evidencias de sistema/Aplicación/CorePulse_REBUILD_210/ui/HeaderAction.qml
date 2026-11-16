import QtQuick

// Acciones de encabezado compartidas: misma forma, altura, relleno y tipografía
// que las acciones del encabezado de Tweaks.
Rectangle {
    id: control
    property string label: ""
    property bool emphasized: false
    property bool available: true
    signal activated()

    implicitWidth: Math.max(75, labelText.implicitWidth + 25)
    implicitHeight: 35
    radius: 10
    color: emphasized
        ? (available ? themeManager.palette.action : themeManager.palette.panelRaised)
        : mouse.containsMouse && available
            ? Qt.alpha(themeManager.palette.accent, 0.14)
            : themeManager.palette.panel
    opacity: available ? 1 : 0.50
    border.width: 1
    border.color: emphasized ? themeManager.palette.action : themeManager.palette.panelBorder

    Text {
        id: labelText
        anchors.centerIn: parent
        text: control.label
        color: control.emphasized && control.available
            ? themeManager.palette.actionText : themeManager.palette.ink
        font.pixelSize: 11
        font.weight: Font.DemiBold
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: control.available
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: control.activated()
    }
}
