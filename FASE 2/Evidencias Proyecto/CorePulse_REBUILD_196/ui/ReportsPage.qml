import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    readonly property var theme: themeManager.palette
    readonly property var info: reportExporter && reportExporter.data ? reportExporter.data : ({busy:false, status:"", path:"", diagnosticStatus:"", diagnosticPath:""})
    readonly property var diagnostic: systemHealth && systemHealth.diagnostic ? systemHealth.diagnostic : ({status:"idle"})
    readonly property bool diagnosticReady: diagnostic.status === "complete" || diagnostic.status === "partial"

    component ReportButton: AbstractButton {
        id: control
        property bool primary: false
        implicitWidth: Math.max(100, label.implicitWidth + 24)
        implicitHeight: 38
        hoverEnabled: true
        background: Rectangle {
            radius: 10
            color: control.hovered && control.enabled ? Qt.lighter(page.theme.panelRaised, 1.12) : page.theme.panelRaised
            border.width: 1
            border.color: control.hovered && control.enabled ? page.theme.action : page.theme.panelBorder
            opacity: control.enabled ? 1 : 0.55
        }
        contentItem: Text {
            id: label
            text: control.text
            color: !control.enabled ? page.theme.muted : control.primary ? page.theme.action : page.theme.ink
            font.pixelSize: 11
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    FastFlickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: contents.implicitHeight + 16
        boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: contents
            width: Math.max(0, scroll.width - 16)
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Glyph { kind: "file_chart"; ink: page.theme.accent; Layout.preferredWidth: 32; Layout.preferredHeight: 32 }
                Text { text: "Informes PDF"; color: page.theme.ink; font.pixelSize: 21; font.bold: true; Layout.fillWidth: true }
                ReportButton { text: "Carpeta de reportes"; onClicked: reportExporter.openReportsFolder() }
                ReportButton { text: "Volver"; onClicked: page.goBack() }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: contents.width < 700 ? 1 : 2
                columnSpacing: 14
                rowSpacing: 14
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 194
                    radius: 16
                    color: page.theme.panel
                    border.color: page.theme.panelBorder
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10
                        Text { text: "Informe del equipo"; color: page.theme.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Sensores, salud y resultados guardados."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Text { text: page.info.status || "Listo para generar."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            spacing: 8
                            ReportButton { objectName: "generateSystemReport"; text: page.info.busy ? "Generando…" : "Crear PDF"; primary: true; enabled: !page.info.busy; onClicked: reportExporter.generate() }
                            ReportButton { objectName: "openSystemReport"; text: "Abrir PDF"; enabled: !!page.info.path; onClicked: reportExporter.openLast() }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 194
                    radius: 16
                    color: page.theme.panel
                    border.color: page.theme.panelBorder
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10
                        Text { text: "Diagnóstico"; color: page.theme.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Comprobaciones de la última ejecución."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Text { text: page.info.diagnosticStatus || (page.diagnosticReady ? "Diagnóstico disponible." : "Ejecuta un diagnóstico para crear su PDF."); color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            spacing: 8
                            ReportButton { objectName: "generateDiagnosticReport"; text: page.info.diagnosticBusy ? "Generando…" : "Crear PDF"; primary: true; enabled: !page.info.busy && page.diagnosticReady; onClicked: reportExporter.generateDiagnostic() }
                            ReportButton { objectName: "openDiagnosticReport"; text: "Abrir PDF"; enabled: !!page.info.diagnosticPath; onClicked: reportExporter.openDiagnostic() }
                        }
                    }
                }
            }
            DetailsSection {
                objectName: "reportDetails"
                Layout.fillWidth: true
                title: "Contenido y ubicación"
                Text { text: "El informe del equipo puede incluir el último benchmark. El PDF de diagnóstico utiliza su propia ejecución y se abre por separado."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { text: "Los archivos se guardan en %LOCALAPPDATA%\\CorePulse\\reportes. Cada PDF refleja la información disponible al crearlo; N/A indica una lectura no disponible."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { visible: !!page.info.path; text: "Equipo: " + (page.info.path || ""); color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                Text { visible: !!page.info.diagnosticPath; text: "Diagnóstico: " + (page.info.diagnosticPath || ""); color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
            }
        }
    }
}
