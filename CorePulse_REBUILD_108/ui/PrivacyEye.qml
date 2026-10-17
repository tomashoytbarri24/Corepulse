import QtQuick
import QtQuick.Controls

// Botón de privacidad reutilizable: muestra u oculta un dato sensible.
// No guarda el valor: sólo pide el cambio. El backend decide qué enviar, así
// el dato real no llega a la pantalla hasta que el usuario lo pide.
Rectangle {
    id: eye
    property bool revealed: false
    property string hint: "dato"
    signal toggled()
    implicitWidth: 26
    implicitHeight: 26
    radius: 8
    color: pointer.containsMouse ? themeManager.palette.panelRaised : "transparent"
    border.width: 1
    border.color: revealed ? themeManager.palette.accent : (pointer.containsMouse ? themeManager.palette.panelBorder : "transparent")
    Glyph {
        anchors.centerIn: parent
        width: 17; height: 17; stroke: 1.6
        kind: eye.revealed ? "eye_off" : "eye"
        ink: eye.revealed ? themeManager.palette.accent : themeManager.palette.muted
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: eye.toggled()
    }
    ToolTip.visible: pointer.containsMouse
    ToolTip.delay: 400
    ToolTip.text: (eye.revealed ? "Ocultar " : "Mostrar ") + eye.hint + " · se oculta solo a los 30 s"
    Accessible.role: Accessible.Button
    Accessible.name: ToolTip.text
}
