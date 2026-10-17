import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    readonly property var theme: themeManager.palette
    readonly property var info: reportExporter && reportExporter.data ? reportExporter.data : ({busy:false, status:"N/A", path:""})

    Item {
        anchors.fill: parent
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 0; spacing: 16
            RowLayout { Layout.fillWidth: true; spacing: 12
                Rectangle { width: 46; height: 46; radius: 14; color: page.theme.panelRaised
                    Glyph { anchors.centerIn: parent; width: 25; height: 25; kind: "file_chart"; ink: page.theme.accent }
                }
                ColumnLayout { Layout.fillWidth: true; spacing: 4
                    Text { text: "Reportes del equipo"; color: page.theme.ink; font.pixelSize: 22; font.bold: true }
                    Text { text: "Informes PDF con diseño común, paginación y lecturas verificables. Exporta el resumen del equipo o los resultados del benchmark."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 256; radius: 16
                color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                ColumnLayout { anchors.fill: parent; anchors.margins: 18; spacing: 11
                    Text { text: "CONTENIDO DEL INFORME"; color: page.theme.ink; font.pixelSize: 12; font.bold: true }
                    Repeater { model: [
                        "Portada, resumen visual, secciones con jerarquía y pie de página numerado.",
                        "Estado del Centro de salud, cobertura y origen de lecturas verificables.",
                        "Resultados guardados de CPU, RAM, SSD y GPU, incluidos también en el PDF general."
                    ]; delegate: Text { required property string modelData; text: "• " + modelData; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap } }
                    Text { text: "Los informes se guardan localmente. La exportación incluye el benchmark más reciente y sesiones guardadas cuando están disponibles."; color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
            }
            RowLayout { Layout.fillWidth: true; spacing: 10
                Rectangle { Layout.preferredWidth: 190; Layout.preferredHeight: 40; radius: 11
                    color: generateMouse.containsMouse?Qt.lighter(themeManager.palette.panelRaised,1.22):themeManager.palette.panelRaised; border.width: 1; border.color: generateMouse.containsMouse?themeManager.palette.action:themeManager.palette.panelBorder
                    Text { anchors.centerIn: parent; text: info.busy ? "Generando…" : "Generar informe PDF"; color: (info.busy)?"#8993A5":themeManager.palette.action; font.pixelSize: 11; font.bold: true }
                    MouseArea { id: generateMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: info.busy ? Qt.ArrowCursor : Qt.PointingHandCursor; enabled: !info.busy; onClicked: reportExporter.generate() }
                }
                Rectangle { visible: info.path !== ""; Layout.preferredWidth: 130; Layout.preferredHeight: 40; radius: 11
                    color: openMouse.containsMouse ? page.theme.panel : page.theme.panelRaised; border.width: 1; border.color: page.theme.panelBorder
                    Text { anchors.centerIn: parent; text: "Abrir informe"; color: page.theme.ink; font.pixelSize: 11; font.bold: true }
                    MouseArea { id: openMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: reportExporter.openLast() }
                }
                Item { Layout.fillWidth: true }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: statusText.implicitHeight + 28; radius: 12; color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                Text { id: statusText; anchors.fill: parent; anchors.margins: 14; text: info.status + (info.path ? "\n" + info.path : ""); color: page.theme.ink; font.pixelSize: 11; wrapMode: Text.WrapAnywhere; verticalAlignment: Text.AlignVCenter }
            }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true
                Rectangle { Layout.preferredWidth: 110; Layout.preferredHeight: 34; radius: 10; color: page.theme.panelRaised; border.width: 1; border.color: page.theme.panelBorder
                    Text { anchors.centerIn: parent; text: "Volver"; color: page.theme.ink; font.pixelSize: 11; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.goBack() }
                }
                Item { Layout.fillWidth: true }
                Text { text: "El PDF refleja la instantánea disponible en el momento de exportarlo."; color: page.theme.muted; font.pixelSize: 9 }
            }
        }
    }
}
