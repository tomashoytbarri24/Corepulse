import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    property var pendingItem: null
    property string filterMode: "updates"
    readonly property var theme: themeManager.palette
    readonly property var info: driverUpdates && driverUpdates.data ? driverUpdates.data : ({busy:false,items:[],device_results:[],count:0,checked_devices:0,status:"Sin consulta",actionMessage:"",source:"N/A",note:"",progressCurrent:0,progressTotal:0,progressLabel:"",lastUpdate:"N/A"})
    readonly property string computerName: telemetry && telemetry.metrics ? String(telemetry.metrics.computer || "Equipo no identificado") : "Equipo no identificado"
    readonly property string oemSupportUrl: {
        const name = page.computerName.toLowerCase()
        if (name.indexOf("lenovo") >= 0) return "https://pcsupport.lenovo.com/"
        if (name.indexOf("dell") >= 0 || name.indexOf("alienware") >= 0) return "https://www.dell.com/support/home/en-us?app=drivers"
        if (name.indexOf("acer") >= 0) return "https://www.acer.com/us-en/support/drivers-and-manuals"
        if (name.indexOf("asus") >= 0 || name.indexOf("asustek") >= 0 || name.indexOf("rog") >= 0) return "https://www.asus.com/support/download-center/model/"
        if (name.indexOf("msi") >= 0 || name.indexOf("micro-star") >= 0) return "https://www.msi.com/support/download"
        if (name.indexOf("hp ") >= 0 || name.indexOf("hewlett") >= 0) return "https://support.hp.com/us-en/drivers"
        if (name.indexOf("samsung") >= 0) return "https://www.samsung.com/us/support/downloads/"
        if (name.indexOf("gigabyte") >= 0) return "https://www.gigabyte.com/Support"
        return ""
    }
    readonly property string oemName: {
        const name = page.computerName.toLowerCase()
        if (name.indexOf("lenovo") >= 0) return "Lenovo"
        if (name.indexOf("dell") >= 0 || name.indexOf("alienware") >= 0) return "Dell"
        if (name.indexOf("acer") >= 0) return "Acer"
        if (name.indexOf("asus") >= 0 || name.indexOf("asustek") >= 0 || name.indexOf("rog") >= 0) return "ASUS"
        if (name.indexOf("msi") >= 0 || name.indexOf("micro-star") >= 0) return "MSI"
        if (name.indexOf("hp ") >= 0 || name.indexOf("hewlett") >= 0) return "HP"
        if (name.indexOf("samsung") >= 0) return "Samsung"
        if (name.indexOf("gigabyte") >= 0) return "Gigabyte"
        return "fabricante"
    }
    readonly property int pendingCount: {
        let count = 0
        for (const row of (info.items || [])) if (!row.is_downloaded && !row.installed_by_corepulse && String(row.driver_class || "").toUpperCase() !== "FIRMWARE") ++count
        return count
    }
    readonly property int downloadedCount: {
        let count = 0
        for (const row of (info.items || [])) if (row.is_downloaded && !row.installed_by_corepulse) ++count
        return count
    }
    function pendingDownloadItems() {
        const rows = []
        for (const row of (info.items || [])) if (!row.is_downloaded && !row.installed_by_corepulse && String(row.driver_class || "").toUpperCase() !== "FIRMWARE") rows.push(row)
        return rows
    }
    function openVendor(url) { if (url && String(url).indexOf("https://") === 0) Qt.openUrlExternally(url) }
    function requestScan() { driverUpdates.scan(String(info.lastUpdate || "N/A") !== "N/A") }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Rectangle {
                width: 48; height: 48; radius: 14
                color: page.theme.panelRaised
                Glyph { anchors.centerIn: parent; width: 26; height: 26; kind: "drivers"; ink: page.theme.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text { text: "Controladores"; color: page.theme.ink; font.pixelSize: 22; font.bold: true }
                Text {
                    text: "Compatibilidad por Hardware ID; acceso rápido al soporte OEM del equipo detectado."
                    color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
            }
            Rectangle {
                Layout.preferredWidth: 168; Layout.preferredHeight: 39; radius: 11
                color: scanMouse.containsMouse ? Qt.lighter(page.theme.panelRaised, 1.18) : page.theme.panelRaised
                border.width: 1; border.color: scanMouse.containsMouse ? page.theme.action : page.theme.panelBorder
                Text {
                    anchors.centerIn: parent
                    text: page.info.busy ? "Revisando…" : (String(page.info.lastUpdate || "N/A") === "N/A" ? "Buscar actualizaciones" : "Actualizar ahora")
                    color: page.info.busy ? page.theme.muted : page.theme.action
                    font.pixelSize: 10; font.bold: true
                }
                MouseArea { id: scanMouse; anchors.fill: parent; hoverEnabled: true; enabled: !page.info.busy; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: page.requestScan() }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 12
            color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
            RowLayout {
                anchors.fill: parent; anchors.margins: 11; spacing: 10
                Rectangle { width: 34; height: 34; radius: 10; color: page.theme.panelRaised
                    Glyph { anchors.centerIn: parent; width: 19; height: 19; kind: "laptop"; ink: page.theme.action }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 2
                    Text { text: "Equipo identificado"; color: page.theme.muted; font.pixelSize: 8 }
                    Text { text: page.computerName; color: page.theme.ink; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                Text { text: "Coincidencia por Hardware ID · el portal OEM permite buscar por modelo"; color: page.theme.muted; font.pixelSize: 8; visible: width > 700 }
                Rectangle {
                    visible: page.oemSupportUrl.length > 0
                    Layout.preferredWidth: 134; Layout.preferredHeight: 32; radius: 9
                    color: page.theme.panelRaised; border.width: 1; border.color: page.theme.panelBorder
                    Text { anchors.centerIn: parent; text: "Soporte " + page.oemName; color: page.theme.action; font.pixelSize: 9; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.openVendor(page.oemSupportUrl) }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: [
                    { title: "Dispositivos revisados", value: String(page.info.checked_devices || 0), detail: "Hasta 24 dispositivos prioritarios" },
                    { title: "Actualizaciones", value: String(page.info.count || 0), detail: "Versiones verificadas" },
                    { title: "Paquetes preparados", value: String(page.downloadedCount), detail: "Listos para confirmar instalación" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 13
                    color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 11; spacing: 3
                        Text { text: modelData.title; color: page.theme.muted; font.pixelSize: 9 }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 7
                            Text { text: modelData.value; color: page.theme.ink; font.pixelSize: 17; font.bold: true }
                            Text { text: modelData.detail; color: page.theme.muted; font.pixelSize: 8; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: page.info.busy ? 69 : 54; radius: 12
            color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 6
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Rectangle { width: 7; height: 7; radius: 4; color: page.info.busy ? page.theme.action : (page.info.count > 0 ? "#E9B768" : "#36D6A0") }
                    Text { text: page.info.busy ? (page.info.progressLabel || page.info.status) : (page.info.actionMessage || page.info.status); color: page.theme.ink; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                    Text { text: page.info.source || "Fuente N/A"; color: page.theme.muted; font.pixelSize: 8; horizontalAlignment: Text.AlignRight }
                }
                Rectangle {
                    visible: page.info.busy
                    Layout.fillWidth: true; height: 4; radius: 3; color: page.theme.panelRaised
                    Rectangle {
                        height: parent.height; radius: 3; color: page.theme.action
                        width: page.info.progressTotal > 0 ? parent.width * Math.max(0.04, Math.min(1, page.info.progressCurrent / page.info.progressTotal)) : parent.width * 0.12
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Repeater {
                model: [
                    { id: "updates", label: "Actualizaciones · " + String(page.info.count || 0) },
                    { id: "reviewed", label: "Dispositivos revisados" },
                    { id: "all", label: "Todo" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.preferredWidth: modelData.id === "updates" ? 156 : 135; Layout.preferredHeight: 31; radius: 9
                    color: page.filterMode === modelData.id ? page.theme.panelRaised : "transparent"
                    border.width: 1; border.color: page.filterMode === modelData.id ? page.theme.action : page.theme.panelBorder
                    Text { anchors.centerIn: parent; text: modelData.label; color: page.filterMode === modelData.id ? page.theme.ink : page.theme.muted; font.pixelSize: 9; font.bold: page.filterMode === modelData.id }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.filterMode = modelData.id }
                }
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: page.pendingCount > 0
                Layout.preferredWidth: 161; Layout.preferredHeight: 34; radius: 10
                color: page.info.busy ? page.theme.panel : page.theme.panelRaised
                border.width: 1; border.color: page.theme.accent
                Text { anchors.centerIn: parent; text: "Descargar todas · " + page.pendingCount; color: page.info.busy ? page.theme.muted : page.theme.accent; font.pixelSize: 9; font.bold: true }
                MouseArea { anchors.fill: parent; enabled: !page.info.busy; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: driverUpdates.downloadAll(page.pendingDownloadItems()) }
            }
        }

        FastFlickable {
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: width; contentHeight: resultsColumn.implicitHeight; clip: true
            ColumnLayout {
                id: resultsColumn
                width: parent.width; spacing: 9
                Repeater {
                    model: page.info.items || []
                    delegate: Rectangle {
                        required property var modelData
                        visible: page.filterMode !== "reviewed"
                        Layout.fillWidth: true; implicitHeight: updateCard.implicitHeight + 24; radius: 13
                        color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                        ColumnLayout {
                            id: updateCard
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12; spacing: 7
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                Text { text: modelData.device_name || "Dispositivo"; color: page.theme.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: String(modelData.driver_class || "").toUpperCase() === "FIRMWARE" ? "FIRMWARE · REVISIÓN MANUAL" : modelData.is_downloaded ? "PAQUETE LISTO" : modelData.installed_by_corepulse ? "INSTALADO" : "ACTUALIZACIÓN DISPONIBLE"; color: modelData.installed_by_corepulse ? "#36D6A0" : modelData.is_downloaded ? page.theme.accent : "#E9B768"; font.pixelSize: 8; font.bold: true }
                            }
                            Text { text: (modelData.provider || modelData.official_vendor || "Proveedor N/A") + " · " + (modelData.driver_class || "Controlador") + (modelData.available_date ? " · " + modelData.available_date : ""); color: page.theme.muted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text { text: (modelData.title || "Paquete de controlador") + "\nInstalado: " + (modelData.current_version || "N/A") + "    →    Disponible: " + (modelData.available_version || "N/A"); color: page.theme.ink; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text { text: (modelData.max_download_size ? "Paquete: " + Math.max(1, Math.round(modelData.max_download_size / 1048576)) + " MB · " : "") + (modelData.compatibility_source || modelData.source || "Compatibilidad verificada por Hardware ID"); color: page.theme.muted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text { visible: !!modelData.download_error; text: "No se pudo descargar: " + (modelData.download_error || ""); color: "#ED8A92"; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    visible: !!modelData.official_url; Layout.preferredWidth: 96; Layout.preferredHeight: 30; radius: 9
                                    color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                                    Text { anchors.centerIn: parent; text: "Fabricante"; color: page.theme.ink; font.pixelSize: 9 }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.openVendor(modelData.official_url) }
                                }
                                Rectangle {
                                    visible: !modelData.is_downloaded && !modelData.installed_by_corepulse && String(modelData.driver_class || "").toUpperCase() !== "FIRMWARE"; Layout.preferredWidth: 105; Layout.preferredHeight: 30; radius: 9
                                    color: page.theme.panelRaised; border.width: 1; border.color: page.theme.panelBorder
                                    Text { anchors.centerIn: parent; text: "Descargar"; color: page.theme.action; font.pixelSize: 9; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; enabled: !page.info.busy; onClicked: driverUpdates.download(modelData) }
                                }
                                Rectangle {
                                    visible: modelData.is_downloaded && !modelData.installed_by_corepulse && modelData.bulk_install_allowed !== false; Layout.preferredWidth: 105; Layout.preferredHeight: 30; radius: 9
                                    color: page.theme.panelRaised; border.width: 1; border.color: page.theme.accent
                                    Text { anchors.centerIn: parent; text: "Instalar"; color: page.theme.accent; font.pixelSize: 9; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; enabled: !page.info.busy; onClicked: page.pendingItem = modelData }
                                }
                            }
                            Text {
                                visible: String(modelData.driver_class || "").toUpperCase() === "FIRMWARE"
                                text: "BIOS y firmware pueden afectar el arranque; usa el soporte oficial del modelo para revisarlos."
                                color: "#E9B768"; font.pixelSize: 8; Layout.fillWidth: true; wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
                Repeater {
                    model: page.info.device_results || []
                    delegate: Rectangle {
                        required property var modelData
                        visible: page.filterMode === "reviewed" || (page.filterMode === "all" && modelData.status !== "UPDATE_AVAILABLE")
                        Layout.fillWidth: true; implicitHeight: resultText.implicitHeight + 22; radius: 10
                        color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                        Text {
                            id: resultText; anchors.fill: parent; anchors.margins: 11
                            text: (modelData.device_name || "Dispositivo") + "\n" + (modelData.status === "UPDATE_AVAILABLE" ? "Actualización confirmada · " + (modelData.available_version || "Nueva versión") : modelData.status === "NO_UPDATE" ? "Sin una versión más nueva confirmada" : "Consulta no disponible: " + (modelData.error || "Error de fuente"))
                            color: page.theme.muted; font.pixelSize: 9; wrapMode: Text.WordWrap
                        }
                    }
                }
                Text {
                    visible: !page.info.busy && (page.info.items || []).length === 0 && (page.info.device_results || []).length === 0
                    text: String(page.info.lastUpdate || "N/A") === "N/A" ? "Busca actualizaciones para revisar hasta 24 dispositivos prioritarios. CorePulse confirma compatibilidad por Hardware ID y muestra solo versiones verificables." : "La búsqueda terminó sin actualizaciones confirmadas. Puedes actualizar ahora para consultar de nuevo las fuentes oficiales."
                    color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
                Text {
                    visible: !page.info.busy && page.filterMode === "updates" && (page.info.items || []).length === 0 && (page.info.device_results || []).length > 0
                    text: "No hay actualizaciones confirmadas para estos dispositivos. Cambia a «Dispositivos revisados» para ver qué se comprobó."
                    color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
                Text {
                    visible: !!page.info.note && (page.info.items || []).length > 0
                    text: page.info.note; color: page.theme.muted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
                Item { Layout.preferredHeight: 4 }
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Rectangle {
                Layout.preferredWidth: 108; Layout.preferredHeight: 34; radius: 10
                color: page.theme.panelRaised; border.width: 1; border.color: page.theme.panelBorder
                Text { anchors.centerIn: parent; text: "Volver"; color: page.theme.ink; font.pixelSize: 10 }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.goBack() }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Las instalaciones se confirman una por una. Se comprueba la firma y se respalda el controlador anterior cuando Windows lo permite."
                color: page.theme.muted; font.pixelSize: 9; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight; wrapMode: Text.WordWrap
            }
        }
    }

    Rectangle {
        visible: page.pendingItem !== null; anchors.fill: parent; z: 31; color: "#B5000000"
        Rectangle {
            width: Math.min(parent.width - 24, 470); height: installContents.implicitHeight + 36; anchors.centerIn: parent; radius: 16
            color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
            ColumnLayout {
                id: installContents; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 18; spacing: 12
                Text { text: "Confirmar instalación"; color: page.theme.ink; font.pixelSize: 17; font.bold: true }
                Text {
                    text: page.pendingItem ? (page.pendingItem.device_name || "Dispositivo") + " · " + (page.pendingItem.available_version || "versión N/A") + "\nCorePulse comprobará el paquete y pedirá a Windows que instale este controlador. Puede requerir UAC o reiniciar el equipo." : ""
                    color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
                RowLayout {
                    Layout.fillWidth: true; Item { Layout.fillWidth: true }
                    Rectangle {
                        Layout.preferredWidth: 94; Layout.preferredHeight: 34; radius: 9; color: page.theme.panelRaised; border.width: 1; border.color: page.theme.panelBorder
                        Text { anchors.centerIn: parent; text: "Cancelar"; color: page.theme.ink; font.pixelSize: 10 }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.pendingItem = null }
                    }
                    Rectangle {
                        Layout.preferredWidth: 126; Layout.preferredHeight: 34; radius: 9; color: page.theme.panelRaised; border.width: 1; border.color: "#A95A63"
                        Text { anchors.centerIn: parent; text: "Instalar"; color: "#ED8A92"; font.pixelSize: 10; font.bold: true }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; enabled: !page.info.busy; onClicked: { const item = page.pendingItem; page.pendingItem = null; driverUpdates.install(item) } }
                    }
                }
            }
        }
    }
}
