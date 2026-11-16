import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Información secundaria disponible sin ocupar la vista inicial.
Control {
    id: section
    default property alias details: detailBody.data
    property string title: "Detalles"
    property bool expanded: false
    padding: 0
    implicitHeight: sectionContents.implicitHeight
    implicitWidth: 240

    contentItem: ColumnLayout {
        id: sectionContents
        spacing: 8
        AbstractButton {
            id: toggle
            objectName: "detailsToggle"
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            hoverEnabled: true
            Accessible.name: (section.expanded ? "Ocultar " : "Mostrar ") + section.title
            onClicked: section.expanded = !section.expanded
            background: Rectangle {
                radius: 8
                color: toggle.hovered || toggle.activeFocus ? Qt.alpha(themeManager.palette.accent, 0.08) : "transparent"
            }
            contentItem: RowLayout {
                spacing: 12
                Text { Layout.fillWidth: true; text: section.title; color: themeManager.palette.ink; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight }
                Text { text: section.expanded ? "Ocultar −" : "Ver +"; color: themeManager.palette.accent; font.pixelSize: 11 }
            }
        }
        ColumnLayout {
            id: detailBody
            objectName: "detailBody"
            visible: section.expanded
            Layout.fillWidth: true
            spacing: 10
        }
    }
}
