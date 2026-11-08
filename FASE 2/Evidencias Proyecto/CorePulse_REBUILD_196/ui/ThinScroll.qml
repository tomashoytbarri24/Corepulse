import QtQuick

// Barra oscura reutilizable sin ScrollBar nativo de Windows.
// El propio Flickable mantiene desplazamiento con rueda, touchpad y arrastre.
Item {
    id: rail
    required property Flickable target
    width: 9
    visible: target && target.contentHeight > target.height + 1
    readonly property real scrollRange: Math.max(0, target.contentHeight - target.height)
    readonly property real travel: Math.max(0, height - thumb.height)

    Rectangle {
        id: thumb
        x: 2
        width: 5
        height: Math.min(rail.height, Math.max(24, rail.height * Math.min(1, rail.target.height / Math.max(1, rail.target.contentHeight))))
        y: rail.scrollRange > 0 ? Math.max(0, Math.min(rail.travel, rail.target.contentY / rail.scrollRange * rail.travel)) : 0
        radius: 3
        color: grip.pressed ? "#74829B" : grip.containsMouse ? "#596A83" : "#3A465B"
        MouseArea {
            id: grip
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            property real originY: 0
            property real originScroll: 0
            onPressed: function(mouse) {
                originY = mapToItem(rail, mouse.x, mouse.y).y
                originScroll = rail.target.contentY
            }
            onPositionChanged: function(mouse) {
                if (!pressed || rail.travel <= 0) return
                const currentY = mapToItem(rail, mouse.x, mouse.y).y
                rail.target.contentY = Math.max(0, Math.min(rail.scrollRange,
                    originScroll + (currentY - originY) * rail.scrollRange / rail.travel))
            }
        }
    }
}
