import QtQuick
import QtQuick.Layouts

// Resumen independiente, sin módulos históricos. Solo telemetría de telemetry.py.
Item {
    id: page
    readonly property var m: telemetry && telemetry.metrics ? telemetry.metrics : ({
        cpuPercent: null, gpuPercent: null, ramPercent: null, diskPercent: null,
        cpuName: "N/A", gpuName: "N/A", diskName: "N/A", diskLabel: "N/A",
        health: "N/A", alerts: "N/A", uptime: "N/A", coverage: "N/A"
    })
    signal openReadings()
    signal openComponent(string componentKind)
    signal openHealth()
    signal openAlerts()
    signal restartRequested()
    readonly property color alertRed: "#F36B75"
    readonly property color ramAccent: "#28B8C7"
    readonly property color storageAccent: "#A66BD6"
    readonly property color cpuBrandColor: page.brandAccent(page.m.cpuName, "cpu")
    readonly property color gpuBrandColor: page.brandAccent(page.m.gpuName, "gpu")
    readonly property bool longSession: page.validNumber(page.m.uptimeSeconds) && page.m.uptimeSeconds >= 10 * 3600
    readonly property bool ramCritical: page.validNumber(page.m.ramPercent) && page.m.ramPercent >= 90
    function validNumber(v) { return typeof v === "number" && isFinite(v) }
    function isAmd(name) {
        const brand = String(name || "").toLowerCase()
        return brand.indexOf("amd") >= 0 || brand.indexOf("ryzen") >= 0 || brand.indexOf("radeon") >= 0
    }
    function cpuVendor(name, manufacturer) {
        const brand = (String(manufacturer || "") + " " + String(name || "")).toLowerCase()
        if (brand.indexOf("intel") >= 0 || brand.indexOf("xeon") >= 0 || brand.indexOf("core(tm)") >= 0 || brand.indexOf("pentium") >= 0 || brand.indexOf("celeron") >= 0) return "intel"
        if (brand.indexOf("amd") >= 0 || brand.indexOf("ryzen") >= 0 || brand.indexOf("threadripper") >= 0 || brand.indexOf("epyc") >= 0 || brand.indexOf("athlon") >= 0) return "amd"
        return "unknown"
    }
    function gpuVendor(name) {
        const brand = String(name || "").toLowerCase()
        if (/nvidia|geforce|quadro|tesla|\brtx\b|\bgtx\b/.test(brand)) return "nvidia"
        if (/amd|radeon|\bati\b|firepro/.test(brand)) return "amd"
        if (/intel|iris|uhd graphics|\barc\b/.test(brand)) return "intel"
        return "unknown"
    }
    function brandAccent(name, kind) {
        const brand = String(name || "").toLowerCase()
        if (brand.indexOf("intel") >= 0 || brand.indexOf("arc") >= 0) return "#1688F3"
        if (brand.indexOf("nvidia") >= 0 || brand.indexOf("geforce") >= 0) return "#76B900"
        if (isAmd(name)) return kind === "gpu" && isAmd(page.m.cpuName) ? "#F28C28" : "#E34245"
        return kind === "gpu" ? "#BB57EF" : "#1AB9F7"
    }
    function storageGlyphKind(disk) {
        const media = String((disk && disk.media) || "").toLowerCase()
        const bus = String((disk && disk.bus) || "").trim().toLowerCase()
        if (media.indexOf("hdd") >= 0 || media.indexOf("hard") >= 0 || media.indexOf("magnetic") >= 0) return "storage_hdd"
        if (bus.indexOf("nvme") >= 0 || bus === "17") return "storage_nvme"
        if (media.indexOf("ssd") >= 0 && (bus.indexOf("sata") >= 0 || bus === "11")) return "storage_sata"
        return "storage"
    }
    function storageTitle(disk) {
        const media = String((disk && disk.media) || "").toLowerCase()
        const bus = String((disk && disk.bus) || "").trim().toLowerCase()
        if (media.indexOf("hdd") >= 0 || media.indexOf("hard") >= 0 || media.indexOf("magnetic") >= 0) return "HDD"
        if (bus.indexOf("nvme") >= 0 || bus === "17") return "NVMe"
        if (media.indexOf("ssd") >= 0 && (bus.indexOf("sata") >= 0 || bus === "11")) return "SATA"
        if (media.indexOf("ssd") >= 0) return "SSD"
        return "Disco"
    }
    function chooseVolume(mount, openDetails) {
        if (storageHealth) storageHealth.selectVolume(mount)
        page.storageSelectorOpen = false
        if (openDetails) page.openComponent("storage")
    }
    readonly property bool horizontal: width >= 810
    readonly property var healthSummary: systemHealth && systemHealth.data ? systemHealth.data : ({headline:"Información insuficiente", state:"partial", coverage:"N/A", critical:0, attention:0, unknown:0})
    readonly property var storageData: storageHealth && storageHealth.data ? storageHealth.data : ({volumes:[],physical:[],selectedVolume:{},selectedPhysical:{},busy:false,physicalBusy:false})
    readonly property var selectedVolume: storageData.selectedVolume || ({})
    readonly property var selectedPhysical: storageData.selectedPhysical || ({})
    property bool storageSelectorOpen: false
    onStorageSelectorOpenChanged: if (storageHealth) storageHealth.setPickerOpen(storageSelectorOpen)
    readonly property string healthTileContent: healthSummary.state === "critical" ? "Crítico" : healthSummary.state === "attention" ? "Revisar" : healthSummary.state === "ok" ? "OK" : "Parcial"
    readonly property string alertsTileContent: String((healthSummary.critical || 0) + (healthSummary.attention || 0))
    readonly property string alertsTileDetail: (healthSummary.critical || 0) + " críticas · " + (healthSummary.attention || 0) + " por revisar"
    readonly property int tilesHeight: 152
    readonly property int panelsHeight: horizontal
        ? Math.max(335, height - tilesHeight - 18)
        : 690

    // Todas las pestañas comparten ahora el MISMO vidrio de Resumen.
    component GlassCard: GlassPanel {
        radius: 22
        clip: true
    }

    // Mismo fabricante que las fichas de Procesador y Tarjeta gráfica.
    // El distintivo identifica la serie; el trazado conserva las muestras reales.
    component ChartBrandIcon: Item {
        id: mark
        property string vendor: "unknown"
        property color accent: "#1AB9F7"
        readonly property bool recognized: vendor === "intel" || vendor === "amd" || vendor === "nvidia"
        implicitWidth: recognized ? 24 : 8
        implicitHeight: 24
        Rectangle {
            anchors.centerIn: parent
            width: mark.recognized ? 24 : 8
            height: width
            radius: mark.recognized ? 7 : 4
            color: mark.accent
        }
        Glyph {
            anchors.centerIn: parent
            width: 19; height: 19
            kind: "gpu_nvidia"
            ink: "#FFFFFF"
            visible: mark.vendor === "nvidia"
        }
        Glyph {
            anchors.centerIn: parent
            width: 19; height: 8
            kind: "gpu_amd"
            ink: "#FFFFFF"
            visible: mark.vendor === "amd"
        }
        Text {
            anchors.centerIn: parent
            visible: mark.vendor === "intel"
            text: "intel"
            color: "#FFFFFF"
            font.family: "Segoe UI"
            font.pixelSize: 9
            font.weight: Font.DemiBold
        }
    }

    FastFlickable {
        id: scroll
        anchors.fill:parent
        contentWidth:width
        contentHeight: dashboard.implicitHeight
        boundsBehavior:Flickable.StopAtBounds
        clip:true

        ColumnLayout {
            id: dashboard
            width: scroll.width
            spacing:16

            GridLayout {
                id: primary
                Layout.fillWidth:true
                columns: page.horizontal ? 2 : 1
                columnSpacing:14
                rowSpacing:14

                GlassCard {
                    Layout.fillWidth:true;Layout.minimumWidth:0
                    Layout.preferredWidth: page.horizontal ? Math.max(1, (page.width - 14) * .70) : Math.max(1, page.width)
                    Layout.preferredHeight: page.horizontal ? page.panelsHeight : 385
                    Layout.row:0;Layout.column:0
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:19;spacing:15
                        RowLayout {
                            Layout.fillWidth:true;spacing:12
                            Rectangle {
                                Layout.preferredHeight:52;Layout.preferredWidth:52
                                radius:15;color:Qt.alpha(themeManager.palette.cyan, 0.105)
                                Glyph{anchors.centerIn:parent;width:32;height:32;kind:"chart";ink:"#1AB9F7"}
                            }
                            ColumnLayout {
                                Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                                Text {
                                    text:"Rendimiento en tiempo real";color:themeManager.palette.ink;font.bold:true
                                    font.pixelSize:17;elide:Text.ElideRight;Layout.fillWidth:true
                                }
                                Text {
                                    text:"Muestras reales de CPU y GPU";color:themeManager.palette.muted;font.pixelSize:11
                                    elide:Text.ElideRight;Layout.fillWidth:true
                                }
                            }
                            RowLayout {
                                spacing: 5
                                Rectangle {
                                    Layout.preferredWidth: 10
                                    Layout.preferredHeight: 10
                                    radius: 5
                                    color: page.cpuBrandColor
                                }
                                Text { text:"CPU"; color:themeManager.palette.muted; font.pixelSize:11 }
                            }
                            RowLayout {
                                spacing: 5
                                Rectangle {
                                    Layout.preferredWidth: 10
                                    Layout.preferredHeight: 10
                                    radius: 5
                                    color: page.gpuBrandColor
                                }
                                Text { text:"GPU"; color:themeManager.palette.muted; font.pixelSize:11 }
                            }
                            Rectangle {
                                Layout.preferredWidth:94;Layout.preferredHeight:34
                                radius:12;color:Qt.alpha(themeManager.palette.ink, 0.055)
                                Text { anchors.centerIn:parent;text:"Últimas 60";font.pixelSize:11;color:themeManager.palette.muted }
                            }
                        }
                        HistoryChart {
                            Layout.fillWidth:true
                            Layout.fillHeight:true
                            cpuValues:telemetry ? telemetry.cpuHistory : []
                            gpuValues:telemetry ? telemetry.gpuHistory : []
                            cpuColor:page.cpuBrandColor
                            gpuColor:page.gpuBrandColor
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth:true;Layout.minimumWidth:0
                    Layout.preferredWidth:page.horizontal ? Math.max(1,(page.width - 14) * .30) :Math.max(1,page.width)
                    Layout.preferredHeight:page.horizontal ? page.panelsHeight : 300
                    Layout.row:page.horizontal?0:1;Layout.column:page.horizontal?1:0
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:18;spacing:13
                        RowLayout {
                            Layout.fillWidth:true;spacing:12
                            Rectangle {
                                Layout.preferredWidth:46;Layout.preferredHeight:46
                                radius:14;color:Qt.alpha(themeManager.palette.cyan, 0.105)
                                Glyph{anchors.centerIn:parent;width:30;height:30;kind:"chart";ink:"#1AB9F7"}
                            }
                            ColumnLayout {
                                Layout.fillWidth:true;spacing:5
                                Text{text:"Estado del sistema";font.pixelSize:15;font.bold:true;color:themeManager.palette.ink}
                                Text{text:"Uso actual de los componentes";font.pixelSize:10;color:themeManager.palette.muted}
                            }
                        }
                        Item { Layout.preferredHeight:1 }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"CPU";kind:"cpu";interactive:true
                            onActivated:page.openComponent("cpu")
                            value:page.m.cpuPercent;accent:page.brandAccent(page.m.cpuName, "cpu")
                            brandVendor: page.cpuVendor(page.m.cpuName, page.m.cpuManufacturer)
                            hardwareName:page.m.cpuName
                            sourceHint:"Frecuencia: " + (page.m.cpuClockSource || "N/A")
                                + "\nTemperatura: " + (page.m.cpuTempSource || "N/A")
                            secondaryPrefix:page.validNumber(page.m.cpuGHz)
                                ? page.m.cpuGHz.toFixed(2)+" GHz"
                                    + (page.m.cpuClockSource && page.m.cpuClockSource.indexOf("Estimación")===0 ? " (est.)" : "")
                                : "Frecuencia N/A"
                            temperature: page.m.cpuTemp
                            hotThreshold: 90
                        }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"GPU";kind:"gpu";interactive:true
                            onActivated:page.openComponent("gpu")
                            value:page.m.gpuPercent;accent:page.gpuBrandColor
                            brandVendor: page.gpuVendor(page.m.gpuName)
                            hardwareName:page.m.gpuName
                            sourceHint:page.m.gpuUtilSource !== "N/A" ? page.m.gpuUtilSource
                                : "Porcentaje de GPU no disponible"
                            temperature: page.m.gpuTemp
                            hotThreshold: 85
                            secondary:page.validNumber(page.m.gpuTemp) ? page.m.gpuTemp.toFixed(1)+" °C" : "Temperatura N/A"
                        }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"RAM";kind:"ram";interactive:true
                            onActivated:page.openComponent("ram")
                            value:page.m.ramPercent;accent:page.ramCritical ? page.alertRed : page.ramAccent
                            critical:page.ramCritical
                            secondary:page.validNumber(page.m.ramUsed)&&page.validNumber(page.m.ramTotal)
                                ? page.m.ramUsed.toFixed(1)+" GB / "+page.m.ramTotal.toFixed(1)+" GB" : "N/A"
                        }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:page.storageTitle(page.selectedPhysical);kind:page.storageGlyphKind(page.selectedPhysical);interactive:true
                            onActivated:{page.storageSelectorOpen=true;storageHealth.refresh()}
                            value:page.validNumber(page.selectedVolume.usedPct) ? page.selectedVolume.usedPct : page.m.diskPercent
                            accent:page.storageAccent
                            hardwareName:page.selectedVolume.mount ? (page.selectedPhysical.name || "Modelo físico N/A · "+page.selectedVolume.mount) : (page.m.diskName && page.m.diskName!=="N/A" ? page.m.diskName : "Selecciona una unidad")
                            secondary:page.selectedVolume.used && page.selectedVolume.total
                                ? page.selectedVolume.used+" / "+page.selectedVolume.total
                                : page.validNumber(page.m.diskUsed)&&page.validNumber(page.m.diskTotal) ? page.m.diskUsed.toFixed(1)+" GB / "+page.m.diskTotal.toFixed(1)+" GB" : "N/A"
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth:true
                columns:page.width >= 810 ? 4 : 2
                columnSpacing:14;rowSpacing:14
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Salud del sistema";content:page.healthTileContent;detail:page.healthSummary.headline
                    kind:"health";interactive:true;accent:page.healthSummary.state === "attention" ? "#E9B768" : page.healthSummary.state === "critical" ? "#F36B75" : page.healthSummary.state === "ok" ? "#36D6A0" : "#8592A6"
                    onActivated:page.openHealth()
                }
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Alertas";content:page.alertsTileContent;detail:page.alertsTileDetail
                    kind:"alerts";accent:"#BB57EF";interactive:true
                    onActivated:page.openAlerts()
                }
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Tiempo de sesión";content:page.m.uptime;detail:"Tiempo activo del sistema"
                    kind:"clock";accent:page.longSession ? page.alertRed : "#1AB9F7"
                    restartVisible:page.longSession
                    onRestartRequested:page.restartRequested()
                }
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Lecturas disponibles";content:page.m.coverage;detail:page.m.coverageDetail || "Ver las 7 lecturas"
                    kind:"trace";accent:"#BB57EF";interactive:true
                    onActivated:page.openReadings()
                }
            }
        }
    }

    Item {
        visible: page.storageSelectorOpen
        z: 50
        anchors.fill: parent
        Rectangle { anchors.fill: parent; color: "#B9000000" }
        MouseArea { anchors.fill: parent; onClicked: page.storageSelectorOpen = false }
        Rectangle {
            id: storageDialog
            width: Math.max(1, Math.min(parent.width - 28, 650))
            height: Math.max(1, Math.min(parent.height - 24, 520))
            anchors.centerIn: parent
            radius: 18
            color: themeManager.palette.panelOpaque
            border.width: 1
            border.color: themeManager.palette.panelBorder
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: "Seleccionar unidad de almacenamiento"; color: themeManager.palette.ink; font.pixelSize: 16; font.bold: true; wrapMode: Text.WordWrap }
                    Rectangle {
                        Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 10
                        color: closeStorageMouse.containsMouse ? themeManager.palette.panel : "transparent"
                        Text { anchors.centerIn: parent; text: "×"; color: themeManager.palette.muted; font.pixelSize: 21 }
                        MouseArea { id: closeStorageMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.storageSelectorOpen = false }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: page.storageData.busy ? "Buscando volúmenes…" : page.storageData.physicalBusy ? "Unidades listas; consultando detalles físicos…" : "Elige un volumen. La lista detecta conexiones y retiros automáticamente mientras está abierta."
                    color: themeManager.palette.muted; font.pixelSize: 10; wrapMode: Text.WordWrap
                }
                FastFlickable {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    contentWidth: width; contentHeight: driveList.implicitHeight
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    ColumnLayout {
                        id: driveList
                        width: parent.width
                        spacing: 8
                        Repeater {
                            model: page.storageData.volumes || []
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 98
                                radius: 13
                                color: themeManager.palette.panelRaised
                                border.width: 1
                                border.color: String(page.storageData.selectedMount || "").toUpperCase() === String(modelData.mount || "").toUpperCase() ? themeManager.palette.cyan : themeManager.palette.panelBorder
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 12
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        spacing: 4
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Unidad " + (modelData.mount || "N/A"); color: themeManager.palette.ink; font.pixelSize: 12; font.bold: true }
                                            Text { Layout.fillWidth: true; text: modelData.volumeLabel && modelData.volumeLabel !== "Sin etiqueta" ? modelData.volumeLabel : (modelData.physicalName || "Sin etiqueta"); color: themeManager.palette.muted; font.pixelSize: 10; elide: Text.ElideRight }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 6; radius: 3
                                            color: themeManager.palette.panelBorder; clip: true
                                            Rectangle { width: typeof modelData.usedPct === "number" ? parent.width * Math.max(0, Math.min(100, modelData.usedPct)) / 100 : 0; height: parent.height; radius: 3; color: typeof modelData.usedPct === "number" && modelData.usedPct >= 90 ? "#E9B86B" : "#BB57EF" }
                                        }
                                        Text { text: (modelData.used || "N/A") + " usados · " + (modelData.free || "N/A") + " libres · " + (modelData.total || "N/A") + " total"; color: themeManager.palette.muted; font.pixelSize: 9; elide: Text.ElideRight }
                                        Text { text: (modelData.deviceType || "Unidad local") + " · " + (modelData.filesystem || "Sistema de archivos N/A") + (modelData.physicalName ? " · " + modelData.physicalName : ""); color: themeManager.palette.muted; font.pixelSize: 8; elide: Text.ElideRight }
                                    }
                                    ColumnLayout {
                                        Layout.preferredWidth: 104
                                        spacing: 5
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 30; radius: 9
                                            color: String(page.storageData.selectedMount || "").toUpperCase() === String(modelData.mount || "").toUpperCase() ? Qt.alpha(themeManager.palette.cyan, 0.16) : themeManager.palette.panel
                                            border.width: 1; border.color: themeManager.palette.panelBorder
                                            Text { anchors.centerIn: parent; text: String(page.storageData.selectedMount || "").toUpperCase() === String(modelData.mount || "").toUpperCase() ? "Seleccionada" : "Seleccionar"; color: themeManager.palette.ink; font.pixelSize: 9; font.bold: true }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.chooseVolume(modelData.mount, false) }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 30; radius: 9
                                            color: detailsStorageMouse.containsMouse ? themeManager.palette.panel : themeManager.palette.panel
                                            border.width: 1; border.color: themeManager.palette.panelBorder
                                            Text { anchors.centerIn: parent; text: "Ver detalles"; color: themeManager.palette.ink; font.pixelSize: 9; font.bold: true }
                                            MouseArea { id: detailsStorageMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.chooseVolume(modelData.mount, true) }
                                        }
                                    }
                                }
                            }
                        }
                        Text {
                            visible: !page.storageData.busy && (!page.storageData.volumes || page.storageData.volumes.length === 0)
                            Layout.fillWidth: true
                            text: "No se encontraron volúmenes locales o USB listos para mostrar. Conecta una unidad con volumen montado para agregarla aquí."
                            color: themeManager.palette.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                    }
                }
                Text { Layout.fillWidth: true; text: "Se revisa la lista cada segundo mientras este selector está abierto. Ver detalles abre el estado físico y los contadores que Windows pueda comprobar."; color: themeManager.palette.muted; font.pixelSize: 9; wrapMode: Text.WordWrap }
            }
        }
    }
}
