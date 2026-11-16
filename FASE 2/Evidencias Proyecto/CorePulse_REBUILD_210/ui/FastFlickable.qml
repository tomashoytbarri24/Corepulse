import QtQuick

Flickable {
    id: view
    // Las páginas se desplazan con rueda/touchpad o con la barra visible;
    // arrastrar el contenido con el botón izquierdo no debe mover la vista.
    interactive: false
    flickableDirection: Flickable.VerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    FastWheelHandler { scrollTarget: view }

    onHeightChanged: contentY = Math.max(0, Math.min(contentY, Math.max(0, contentHeight - height)))
    onContentHeightChanged: contentY = Math.max(0, Math.min(contentY, Math.max(0, contentHeight - height)))
}
