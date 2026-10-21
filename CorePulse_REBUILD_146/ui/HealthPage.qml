import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    signal navigateTo(string route)
    property string requestedModule: "auto"
    property string requestedWindowsSection: ""
    property string currentModule: requestedModule === "windows" ? "windows" :
        requestedModule === "repair" ? "repair" :
        requestedModule === "restore" ? "recovery" :
        requestedModule === "history" ? "history" :
        requestedModule === "storage" ? "storage" :
        requestedModule === "audio" ? "audio" :
        requestedModule === "performance" ? "performance" :
        requestedModule === "battery" ? "battery" : "hub"
    property string expandedWindowsSection: ""
    onRequestedWindowsSectionChanged: if (currentModule === "windows" && requestedWindowsSection !== "") expandedWindowsSection = requestedWindowsSection
    property bool overviewRequested: false
    property bool showDetailedReadings: false
    readonly property var audioInfo: audioTest && audioTest.data ? audioTest.data :
        ({busy:false, message:"Preparado", summary:"NO EVALUADO", outputDevice:"No consultado", inputDevice:"No consultado", outputAvailable:false, inputAvailable:false, stereo:null, pending:"", pendingLabel:"", answers:{}, hasRecording:false, captureSignal:"N/A", capturePeak:"N/A", inputLevel:0})
    onCurrentModuleChanged: {
        if (currentModule === "hub" && !overviewRequested) {
            overviewRequested = true
            systemHealth.refresh()
        } else if (currentModule === "windows" && !windowsInfo.busy && windowsInfo.lastUpdate === "N/A") windowsHealth.refresh()
        else if (currentModule === "storage" && !storageInfo.busy && storageInfo.lastUpdate === "N/A") storageHealth.refresh()
        else if (currentModule === "recovery" && !recoveryInfo.busy && recoveryInfo.lastUpdate === "N/A") recoveryHealth.refresh()
        else if (currentModule === "history" && !historyInfo.busy && historyInfo.lastUpdate === "N/A") changeHistory.refresh()
        else if (currentModule === "audio" && !audioInfo.busy && !audioInfo.outputAvailable) audioTest.refresh()
        if (currentModule === "performance") {
            performanceHealth.startGameWatch()
            if (!performanceInfo.busy && performanceInfo.lastUpdate === "N/A") performanceHealth.refresh()
        } else performanceHealth.stopGameWatch()
    }

    Component.onCompleted: {
        if (currentModule === "hub" && !overviewRequested) {
            overviewRequested = true
            systemHealth.refresh()
        } else if (currentModule === "windows") windowsHealth.refresh()
        else if (currentModule === "storage") storageHealth.refresh()
        else if (currentModule === "recovery") recoveryHealth.refresh()
        else if (currentModule === "history") changeHistory.refresh()
        else if (currentModule === "audio") audioTest.refresh()
        else if (currentModule === "performance") {
            performanceHealth.startGameWatch()
            performanceHealth.refresh()
        }
    }
    readonly property var windowsInfo: windowsHealth && windowsHealth.data ? windowsHealth.data :
        ({busy: false, lastUpdate: "N/A", progress: 0, stage: "Sin comprobaciones ejecutadas.", startup:{available:false,metric:"N/A",caption:"No disponible",items:[]},
         services:{available:false,metric:"N/A",caption:"No disponible",items:[]},
         events:{available:false,metric:"N/A",caption:"No disponible",items:[]},
         drivers:{available:false,metric:"N/A",caption:"No disponible",items:[]}})
    readonly property var repairInfo: repairHealth && repairHealth.data ? repairHealth.data :
        ({busy:false, status:"N/A", summary:"No disponible", stage:"", steps:[], kind:"", logPath:"N/A", isAdmin:false, progress:0})
    readonly property var recoveryInfo: recoveryHealth && recoveryHealth.data ? recoveryHealth.data :
        ({busy:false, status:"N/A", summary:"Sin consultas ejecutadas.", progress:0, stage:"Sin consultas ejecutadas.", isAdmin:false, systemDrive:"N/A", protectionText:"N/A", protectionEnabled:null, recoveryEnv:"N/A", pointCount:"N/A", latestDescription:"N/A", latestCreated:"N/A", points:[], lastUpdate:"N/A", logPath:"N/A", details:"N/A"})
    readonly property var performanceInfo: performanceHealth && performanceHealth.data ? performanceHealth.data :
        ({busy:false, available:false, plans:[], activeGuid:"", activeName:"N/A", backupAvailable:false, originalName:"N/A", probableGames:[], gameCaption:"Sin consulta", status:"N/A", message:"Sin consulta", lastUpdate:"N/A"})
    readonly property var activeGame: performanceInfo.activeGame || ({active:false, name:'', source:'', artUrl:'', session:'N/A', pid:0, executable:''})
    readonly property var generalInfo: systemHealth && systemHealth.data ? systemHealth.data :
        ({headline:"Información insuficiente", state:"partial", verified:0, total:0,
          attention:0, critical:0, unknown:0, coverage:"0/0", checks:[], note:"No hay datos confirmados."})
    readonly property var historyInfo: changeHistory && changeHistory.data ? changeHistory.data :
        ({busy:false, progress:0, stage:"Sin consultas ejecutadas.", status:"N/A", sourceCount:"N/A", sections:[], events:[], shownCount:0, lastUpdate:"N/A"})
    property string historyFilter: "all"
    readonly property var historyFiltered: historyFilter === "all" ? (historyInfo.events || []) :
        (historyInfo.events || []).filter(function(entry) { return entry.source === historyFilter })
    readonly property var historyFilters: [
        {key:"all", title:"Todos"}, {key:"tweaks", title:"Tweaks"},
        {key:"repair", title:"DISM / SFC"}, {key:"updates", title:"Windows Update"},
        {key:"restore", title:"Restauración"}
    ]
    property string confirmRepair: ""
    property string confirmRecovery: ""
    property string pendingPowerGuid: ""
    property string pendingPowerName: ""
    property bool confirmPowerRestore: false
    property bool confirmGameBoost: false
    Component.onDestruction: performanceHealth.stopGameWatch()
    readonly property var windowsSections: [
        {key:"startup", title:"INICIO DE WINDOWS", icon:"power", description:"Entradas registradas"},
        {key:"services", title:"SERVICIOS", icon:"services", description:"Automáticos detenidos"},
        {key:"events", title:"ESTABILIDAD", icon:"activity", description:"Eventos recientes"},
        {key:"drivers", title:"CONTROLADORES", icon:"drivers", description:"Dispositivos con códigos PnP"}
    ]
    readonly property var storageInfo: storageHealth && storageHealth.data ? storageHealth.data :
        ({volumes: [], physical: [], selectedVolume:{}, selectedPhysical:{}, busy: false, physicalBusy:false, lastUpdate: "N/A"})
    readonly property var selectedStorageVolume: storageInfo.selectedVolume || (storageInfo.volumes && storageInfo.volumes.length ? storageInfo.volumes[0] : ({}))
    readonly property var selectedStorageDisk: storageInfo.selectedPhysical || ({})
    function storageGlyphKind(disk) {
        const media = String((disk && disk.media) || "").toLowerCase()
        const bus = String((disk && disk.bus) || "").trim().toLowerCase()
        if (media.indexOf("hdd") >= 0 || media.indexOf("hard") >= 0 || media.indexOf("magnetic") >= 0) return "storage_hdd"
        if (bus.indexOf("nvme") >= 0 || bus === "17") return "storage_nvme"
        if (media.indexOf("ssd") >= 0 && (bus.indexOf("sata") >= 0 || bus === "11")) return "storage_sata"
        return "storage"
    }
    function storageMetric(value, suffix) {
        return typeof value === "number" && isFinite(value) ? String(Math.round(value)) + suffix : "N/A"
    }
    function nvmeDataUnits(value) {
        const units = Number(value)
        if (!isFinite(units) || units < 0) return "N/A"
        const bytes = units * 512000
        if (bytes >= 1e12) return "≈ " + (bytes / 1e12).toFixed(2) + " TB"
        if (bytes >= 1e9) return "≈ " + (bytes / 1e9).toFixed(1) + " GB"
        return "≈ " + (bytes / 1e6).toFixed(1) + " MB"
    }
    function nvmeWarning(value) {
        if (typeof value !== "number" || !isFinite(value)) return "N/A"
        return value === 0 ? "Sin alertas" : "0x" + ("0" + Number(value).toString(16).toUpperCase()).slice(-2)
    }
    function storageWearState(value) {
        if (typeof value !== "number" || !isFinite(value) || value < 0) return "Sin lectura SMART"
        if (value >= 100) return "Resistencia estimada superada"
        if (value >= 80) return "Muy alto"
        if (value >= 50) return "Alto"
        if (value >= 20) return "Moderado"
        return "Bajo"
    }
    function storageWearColor(value) {
        if (typeof value !== "number" || !isFinite(value) || value < 0) return page.muted
        if (value >= 80) return "#F36B75"
        if (value >= 50) return "#E98B55"
        if (value >= 20) return "#E9B768"
        return "#36D6A0"
    }
    function selectedDiskIsNvme() {
        const bus = String(page.selectedStorageDisk.bus || "").toLowerCase()
        const source = String(page.selectedStorageDisk.smartSource || "").toLowerCase()
        return bus.indexOf("nvme") >= 0 || source.indexOf("nvme") >= 0
    }
    readonly property var storageReadings: [
        {label:"Temperatura actual", value:page.storageMetric(page.selectedStorageDisk.temperatureC, " °C")},
        {label:"Temperatura máxima", value:page.storageMetric(page.selectedStorageDisk.temperatureMaxC, " °C")},
        {label:"Desgaste estimado", value:page.storageMetric(page.selectedStorageDisk.wearPercent, " %")},
        {label:"Horas encendido", value:page.storageMetric(page.selectedStorageDisk.powerOnHours, " h")},
        {label:"Ciclos de encendido", value:page.storageMetric(page.selectedStorageDisk.powerOnCount, "")},
        {label:"Reserva disponible NVMe", value:page.storageMetric(page.selectedStorageDisk.nvmeAvailableSparePercent, " %"), nvmeOnly:true},
        {label:"Advertencia crítica NVMe", value:page.nvmeWarning(page.selectedStorageDisk.nvmeCriticalWarning), nvmeOnly:true},
        {label:"Apagados inseguros NVMe", value:page.storageMetric(page.selectedStorageDisk.nvmeUnsafeShutdowns, ""), nvmeOnly:true},
        {label:"Errores de medio NVMe", value:page.storageMetric(page.selectedStorageDisk.nvmeMediaErrors, ""), nvmeOnly:true},
        {label:"Lectura del host NVMe", value:page.nvmeDataUnits(page.selectedStorageDisk.nvmeDataUnitsRead), nvmeOnly:true},
        {label:"Escritura del host NVMe", value:page.nvmeDataUnits(page.selectedStorageDisk.nvmeDataUnitsWritten), nvmeOnly:true},
        {label:"Comandos de lectura NVMe", value:page.storageMetric(page.selectedStorageDisk.nvmeHostReadCommands, ""), nvmeOnly:true},
        {label:"Comandos de escritura NVMe", value:page.storageMetric(page.selectedStorageDisk.nvmeHostWriteCommands, ""), nvmeOnly:true},
        {label:"Entradas del registro de errores NVMe", value:page.storageMetric(page.selectedStorageDisk.nvmeErrorLogEntries, ""), nvmeOnly:true},
        {label:"Errores de lectura", value:page.storageMetric(page.selectedStorageDisk.readErrorsTotal, ""), sataOnly:true},
        {label:"Lecturas no corregibles", value:page.storageMetric(page.selectedStorageDisk.readErrorsUncorrected, ""), sataOnly:true},
        {label:"Errores de escritura", value:page.storageMetric(page.selectedStorageDisk.writeErrorsTotal, ""), sataOnly:true},
        {label:"Escrituras no corregibles", value:page.storageMetric(page.selectedStorageDisk.writeErrorsUncorrected, ""), sataOnly:true}
    ]

    readonly property color surface: themeManager.palette.panel
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.accent
    readonly property color statusOk: "#36D6A0"
    readonly property color statusWarning: "#E9B768"
    readonly property color statusCritical: "#F36B75"
    readonly property var info: batteryHealth && batteryHealth.data ? batteryHealth.data : ({
        hasBattery: false, chargePct: null, chargeText: "N/A",
        powerState: "Sin lecturas", remaining: "N/A", remainingSource: "", healthPct: null,
        healthText: "N/A", healthLabel: "No disponible", wearText: "N/A",
        designText: "N/A", fullText: "N/A", cyclesText: "N/A",
        model: "N/A", manufacturer: "N/A", count: 0,
        details: "N/A", busy: false, lastUpdate: "N/A"
    })
    readonly property color healthAccent: typeof info.healthPct !== "number" ? muted :
        (info.healthPct >= 85 ? "#4EDDC8" : (info.healthPct >= 70 ? "#E5B768" : "#E17D82"))

    component OutlineButton: AbstractButton {
        id: button
        property color accentColor: page.accent
        property bool selected: false
        property bool actionStyle: false   // ejecuta algo: texto en color de acción (REBUILD 082)
        property bool solidStyle: false    // Aplicar/Actualizar: botón entero de color
        readonly property color actionFill: themeManager.palette.action
        implicitWidth: Math.max(88, textLabel.implicitWidth + 27)
        implicitHeight: 38
        hoverEnabled: true
        background: Rectangle {
            radius: 10
            color: button.solidStyle ? (!button.enabled ? themeManager.palette.actionMuted : button.down ? Qt.darker(button.actionFill, 1.12) : button.hovered ? Qt.lighter(button.actionFill, 1.16) : button.actionFill)
                 : !button.enabled ? "#232530" : button.down ? "#252936" : button.selected ? "#193A35" : button.hovered ? "#313340" : themeManager.palette.panelRaised
            border.width: 1
            border.color: button.solidStyle ? (button.enabled ? button.actionFill : themeManager.palette.actionMuted)
                          : button.enabled && (button.hovered || button.selected) ? (button.actionStyle ? button.actionFill : button.accentColor) : page.edge
        }
        contentItem: Text {
            id: textLabel
            text: button.text
            color: button.solidStyle ? (button.enabled ? themeManager.palette.actionText : themeManager.palette.actionMutedText)
                 : button.actionStyle ? (button.enabled ? button.actionFill : "#8993A5")
                 : !button.enabled ? "#8993A5" : button.selected ? page.accent : page.ink
            font.pixelSize: 12
            font.weight: button.solidStyle ? Font.Bold : Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }


    function openHealthModule(route) {
        const normalized = route === "windows_health" ? "windows" : route === "restore" ? "recovery" : route === "change_history" ? "history" : route
        if (normalized === "cpu" || normalized === "gpu" || normalized === "ram" || normalized === "storage") {
            page.navigateTo(normalized)
        } else if (["battery", "windows", "repair", "recovery", "history", "audio", "performance"].indexOf(normalized) >= 0) {
            page.currentModule = normalized
        }
    }
    component HeaderIconButton: AbstractButton {
        id: iconButton
        property color inkColor: page.accent
        implicitWidth: 34
        implicitHeight: 34
        hoverEnabled: true
        background: Rectangle {
            radius: 9
            color: !iconButton.enabled ? "transparent" : iconButton.down ? "#1A2433" : iconButton.hovered ? "#141C2A" : "transparent"
            border.width: 0
        }
        contentItem: Item {
            anchors.fill: parent
            Glyph {
                anchors.centerIn: parent
                width: 18; height: 18
                kind: "refresh"
                ink: iconButton.enabled ? iconButton.inkColor : page.muted
            }
        }
    }


    function moduleTitle(moduleKey) {
        switch (moduleKey) {
        case "battery": return "Batería"
        case "windows": return "Windows"
        case "repair": return "Reparación"
        case "recovery": return "Recuperación"
        case "history": return "Historial y cambios"
        case "storage": return "Almacenamiento"
        case "performance": return "Rendimiento"
        case "audio": return "Test de audio"
        default: return "Centro de salud"
        }
    }

    function moduleAccent(moduleKey) {
        switch (moduleKey) {
        case "battery": return "#4EDDC8"
        case "windows": return "#58C8FF"
        case "repair": return "#7EE08A"
        case "history": return "#F2B661"
        case "recovery": return "#5EE1D5"
        case "performance": return "#B879FF"
        case "audio": return "#FF82CF"
        case "storage": return "#A66BD6"
        case "hub": return page.accent
        default: return page.accent
        }
    }

    component InfoCell: GlassPanel {
        property string title: ""
        property string value: "N/A"
        property color tint: page.accent
        property string hint: ""
        Layout.fillWidth: true
        Layout.preferredHeight: 95
        radius: 14
        color: page.surface
        border.width: 1
        border.color: page.edge
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 6
            Text { text: title; color: page.muted; font.pixelSize: 11 }
            Text { text: value; color: tint; font.pixelSize: 19; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
            Text { visible: hint.length > 0; text: hint; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
        }
    }

    FastFlickable {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight + 15
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: content
            width: Math.max(0, pageScroll.width - 17)
            spacing: 15

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Glyph { Layout.preferredWidth: 38; Layout.preferredHeight: 38; width: 32; height: 32; kind: page.currentModule === "performance" ? "gauge" : page.currentModule === "hub" ? "health_shield" : page.currentModule === "storage" ? page.storageGlyphKind(page.selectedStorageDisk) : page.currentModule === "windows" ? "services" : page.currentModule === "repair" ? "wrench" : page.currentModule === "recovery" ? "restore" : page.currentModule === "history" ? "history" : page.currentModule === "audio" ? "headphones" : "battery"; ink: page.moduleAccent(page.currentModule) }
                ColumnLayout {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 4
                    Text { text: page.moduleTitle(page.currentModule); color: page.ink; font.pixelSize: 21; font.bold: true }
                    Text { text: page.currentModule === "performance" ? "Rendimiento · energía, estabilidad y Gaming" : page.currentModule === "hub" ? "Panel principal · accesos y lecturas verificadas" : page.currentModule === "battery" ? "Batería · diagnóstico de Windows" : page.currentModule === "storage" ? "Almacenamiento · diagnóstico de la unidad" : (page.currentModule === "repair" ? "Reparación de Windows · DISM y SFC" : (page.currentModule === "recovery" ? "Recuperación del sistema · restauración y WinRE" : page.currentModule === "history" ? "Historial de cambios · fuentes reales" : page.currentModule === "audio" ? "Test de audio · salida y herramientas" : "Análisis de Windows · solo lectura")); color: page.muted; font.pixelSize: 11 }
                }
                Item { Layout.fillWidth: true }
                HeaderIconButton {
                    visible: currentModule === "hub"
                    enabled: true
                    inkColor: page.accent
                    onClicked: systemHealth.refresh()
                }
                OutlineButton { solidStyle: true; actionStyle: true;
                    text: currentModule === "battery" && info.busy ? "Consultando…" :
                          currentModule === "storage" && storageInfo.busy ? "Consultando…" :
                          currentModule === "windows" && windowsInfo.busy ? "Consultando…" :
                          currentModule === "recovery" && recoveryInfo.busy ? "Consultando…" :
                          currentModule === "history" && historyInfo.busy ? "Consultando…" : "Actualizar"
                    visible: currentModule !== "hub" && currentModule !== "repair" && currentModule !== "audio"
                    enabled: currentModule === "performance" ? !performanceInfo.busy : currentModule === "battery" ? !info.busy : currentModule === "storage" ? !storageInfo.busy : currentModule === "windows" ? !windowsInfo.busy : currentModule === "recovery" ? !recoveryInfo.busy : currentModule === "history" ? !historyInfo.busy : true
                    onClicked: {
                        if (currentModule === "performance") performanceHealth.refresh()
                        else if (currentModule === "battery") batteryHealth.refresh()
                        else if (currentModule === "storage") storageHealth.refresh()
                        else if (currentModule === "windows") windowsHealth.refresh()
                        else if (currentModule === "recovery") recoveryHealth.refresh()
                        else if (currentModule === "history") changeHistory.refresh()
                        else if (currentModule === "performance") performanceHealth.refresh()
                    }
                }
                OutlineButton { visible: currentModule !== "hub"; text: "Volver"; onClicked: page.currentModule = "hub" }
            }

            // Portada de Centro de Salud alineada con la estructura de CorePulse V485:
            // estado general explicable y accesos a módulos. La matriz de la V045
            // queda disponible bajo demanda como evidencia adicional, no como portada.
            ColumnLayout {
                visible: page.currentModule === "hub"
                Layout.fillWidth: true
                spacing: 13
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: healthHeadlineColumn.implicitHeight + 38
                    radius: 17; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: healthHeadlineColumn
                        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                        anchors.margins: 17; spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ESTADO GENERAL"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text { text: page.generalInfo.coverage + " lecturas"; color: page.muted; font.pixelSize: 11 }
                        }
                        Text {
                            text: page.generalInfo.headlineDisplay || page.generalInfo.headline || "Centro de salud"
                            color: page.generalInfo.state === "critical" ? page.statusCritical : page.generalInfo.state === "attention" ? page.statusWarning : page.generalInfo.state === "ok" ? page.statusOk : page.muted
                            font.pixelSize: 19
                            font.bold: true
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                        Text {
                            visible: (page.generalInfo.headlineDetail || "").length > 0
                            text: page.generalInfo.headlineDetail || ""
                            color: page.muted
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
                Text { text: "Áreas de mantenimiento y diagnóstico"; font.pixelSize: 16; color: page.ink; font.bold: true; Layout.topMargin: 6 }
                Text { text: "Revisa el estado de cada área y abre solo la herramienta que necesites."; font.pixelSize: 11; color: page.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 790 ? 1 : (content.width < 1090 ? 2 : 3)
                    columnSpacing: 12; rowSpacing: 12
                    Repeater {
                        model: [
                            {key:"battery", title:"Batería", desc:"Capacidad, desgaste, ciclos y autonomía.", icon:"battery", target:"battery", iconColor:"#4EDDC8"},
                            {key:"windows", title:"Windows", desc:"Inicio, servicios, estabilidad y controladores.", icon:"services", target:"windows", iconColor:"#58C8FF"},
                            {key:"repair", title:"Reparación", desc:"Diagnóstico y reparación con DISM/SFC.", icon:"wrench", target:"repair", iconColor:"#7EE08A"},
                            {key:"history", title:"Historial y cambios", desc:"Registros disponibles de mantenimiento y cambios.", icon:"history", target:"history", iconColor:"#F2B661"},
                            {key:"recovery", title:"Recuperación", desc:"Puntos de restauración y herramientas de Windows.", icon:"restore", target:"recovery", iconColor:"#5EE1D5"},
                            {key:"performance", title:"Rendimiento", desc:"Throttling, energía y herramientas Gaming.", icon:"gauge", target:"performance", iconColor:"#B879FF"},
                            {key:"audio", title:"Test de Audio", desc:"Canales izquierdo/derecho y herramientas de sonido.", icon:"headphones", target:"audio", iconColor:"#FF82CF"}
                        ].filter(function(item) { return item.key !== "battery" || page.info.hasBattery })
                        delegate: GlassPanel {
                            id: hubCard
                            required property var modelData
                            readonly property bool available: modelData.target !== ""
                            Layout.fillWidth: true; Layout.preferredHeight: 156
                            radius: 15; color: page.surface; border.width: 1; border.color: page.edge
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 14; spacing: 7
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    Glyph { kind: hubCard.modelData.icon; ink: hubCard.available ? hubCard.modelData.iconColor : page.muted; Layout.preferredWidth: 30; Layout.preferredHeight: 30 }
                                    Text { text: hubCard.modelData.title; color: page.ink; font.bold: true; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                Text { text: hubCard.modelData.desc; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2 }
                                Item { Layout.fillHeight: true }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        Layout.fillWidth: true; color: hubCard.available ? page.accent : "#E5B768"; font.pixelSize: 10
                                        text: !hubCard.available ? "Pendiente de migrar" :
                                              hubCard.modelData.key === "battery" ? page.info.healthText + " salud" :
                                              hubCard.modelData.key === "windows" ? (page.windowsInfo.lastUpdate === "N/A" ? "Sin analizar" : "Consulta disponible") :
                                              hubCard.modelData.key === "repair" ? page.repairInfo.status :
                                              hubCard.modelData.key === "history" ? (page.historyInfo.lastUpdate === "N/A" ? "Sin consultar" : "Registros consultados") :
                                              hubCard.modelData.key === "recovery" ? page.recoveryInfo.status :
                                              hubCard.modelData.key === "audio" ? "Listo para probar" :
                                              hubCard.modelData.key === "performance" ? (page.performanceInfo.lastUpdate === "N/A" ? "Sin consultar" : page.performanceInfo.activeName) : "N/A"
                                        elide: Text.ElideRight
                                    }
                                    OutlineButton {
                                        text: "Abrir"; enabled: hubCard.available; Layout.preferredHeight: 29
                                        onClicked: page.currentModule = hubCard.modelData.target
                                    }
                                }
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.topMargin: 3
                    Text { text: "Lecturas técnicas verificables"; font.pixelSize: 14; font.bold: true; color: page.ink; Layout.fillWidth: true }
                    OutlineButton { text: page.showDetailedReadings ? "Ocultar lecturas" : "Ver lecturas"; onClicked: page.showDetailedReadings = !page.showDetailedReadings }
                }
                GridLayout {
                    visible: page.showDetailedReadings
                    Layout.fillWidth: true
                    columns: content.width < 730 ? 1 : 2
                    columnSpacing: 12; rowSpacing: 12
                    Repeater {
                        model: page.generalInfo.checks || []
                        delegate: GlassPanel {
                            id: generalEntry
                            required property var modelData
                            readonly property color statusColor: modelData.state === "critical" ? page.statusCritical : modelData.state === "attention" ? page.statusWarning : modelData.state === "ok" ? page.statusOk : page.muted
                            Layout.fillWidth: true; Layout.preferredHeight: 148
                            radius: 15; color: page.surface; border.width: 1; border.color: page.edge
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 14; spacing: 6
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: generalEntry.modelData.title; color: page.ink; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: generalEntry.modelData.state === "critical" ? "PRIORITARIO" : generalEntry.modelData.state === "attention" ? "REVISAR" : generalEntry.modelData.state === "ok" ? "DISPONIBLE" : "N/A"; color: generalEntry.statusColor; font.pixelSize: 10; font.bold: true }
                                }
                                Text { text: generalEntry.modelData.value; color: generalEntry.statusColor; font.pixelSize: 20; font.bold: true }
                                Text { text: generalEntry.modelData.detail; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                                Item { Layout.fillHeight: true }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: "Fuente: " + generalEntry.modelData.source; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                    OutlineButton { text: "Ver módulo"; Layout.preferredHeight: 29; onClicked: page.openHealthModule(generalEntry.modelData.route) }
                                }
                            }
                        }
                    }
                }
                Text { text: page.generalInfo.note; visible: page.showDetailedReadings; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }

            GridLayout {
                visible: page.currentModule === "battery" && info.hasBattery
                Layout.fillWidth: true
                columns: content.width < 680 ? 1 : 2
                columnSpacing: 15
                rowSpacing: 15

                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 249
                    radius: 18; color: page.surface
                    border.width: 1; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 19; spacing: 9
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "CARGA ACTUAL"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Glyph {kind: "battery"; ink: page.accent; Layout.preferredWidth: 20; Layout.preferredHeight: 20}
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
                            Item {
                                Layout.preferredWidth: 134; Layout.preferredHeight: 134
                                Canvas {
                                    id: chargeRing
                                    anchors.fill: parent
                                    renderTarget: Canvas.Image
                                    antialiasing: true
                                    onPaint: {
                                        const ctx = getContext("2d")
                                        ctx.clearRect(0, 0, width, height)
                                        const pct = typeof info.chargePct === "number" ? Math.max(0, Math.min(100, info.chargePct)) : 0
                                        const x=width/2, y=height/2, r=Math.min(width,height)/2-11
                                        ctx.lineWidth=11
                                        ctx.lineCap="round"
                                        ctx.beginPath(); ctx.strokeStyle=themeManager.palette.panelBorder; ctx.arc(x,y,r,-Math.PI/2,3*Math.PI/2);ctx.stroke()
                                        if (typeof info.chargePct === "number" && pct > 0) {
                                            ctx.beginPath();ctx.strokeStyle="#4EDDC8";
                                            ctx.arc(x,y,r,-Math.PI/2,-Math.PI/2+2*Math.PI*pct/100);ctx.stroke()
                                        }
                                    }
                                }
                                Text {
                                    anchors.centerIn: parent
                                    text: info.chargeText
                                    color: page.ink; font.pixelSize: 24; font.bold: true
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 9
                                Text {text: "ESTADO"; color: page.muted; font.pixelSize: 10; font.bold: true}
                                Text {
                                    text: info.powerState
                                    color: page.accent; font.pixelSize: 15; font.bold: true
                                    Layout.fillWidth: true; wrapMode: Text.WordWrap
                                }
                                Text {
                                    text: info.hasBattery ? "Lectura actual de Windows" : "Sin lectura disponible"
                                    color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }

                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 249
                    radius: 18; color: page.surface
                    border.width: 1; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 19; spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "SALUD DE BATERÍA"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Glyph {kind: "health_shield"; ink: page.healthAccent; Layout.preferredWidth: 20; Layout.preferredHeight: 20}
                        }
                        Text {text: info.healthText; font.pixelSize: 43; font.bold: true; color: page.healthAccent}
                        Text {text: info.healthLabel; color: page.ink; font.pixelSize: 15; font.bold: true}
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 8; radius: 4; color: themeManager.palette.panelBorder
                            Rectangle {
                                width: typeof info.healthPct === "number" ? parent.width * Math.max(0,Math.min(100, info.healthPct))/100 : 0
                                height: parent.height; radius: 4; color: page.healthAccent
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text {text: "Desgaste estimado"; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true}
                            Text {text: info.wearText; color: page.ink; font.pixelSize: 12; font.bold: true}
                        }
                        Text {text: "Medida mediante Windows (CIM / informe nativo)"; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap}
                    }
                }
            }

            GridLayout {
                visible: page.currentModule === "battery" && info.hasBattery
                Layout.fillWidth: true
                columns: content.width < 610 ? 1 : 3
                columnSpacing: 12
                rowSpacing: 12
                InfoCell { title: "Capacidad de diseño"; value: info.designText }
                InfoCell { title: "Capacidad máxima actual"; value: info.fullText }
                InfoCell { title: "Ciclos de carga"; value: info.cyclesText }
                InfoCell { title: "Autonomía restante"; value: info.remaining; hint: info.remainingSource }
                InfoCell { title: "Baterías detectadas"; value: info.count > 0 ? String(info.count) : "N/A" }
                InfoCell { title: "Última actualización"; value: info.lastUpdate; tint: page.ink }
            }

            GlassPanel {
                visible: page.currentModule === "battery" && info.hasBattery
                Layout.fillWidth: true
                Layout.preferredHeight: detailsColumn.implicitHeight + 32
                radius: 14; color: page.surface
                border.width: 1; border.color: page.edge
                ColumnLayout {
                    id: detailsColumn
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.top: parent.top; anchors.margins: 16
                    spacing: 7
                    Text {text: "INFORMACIÓN TÉCNICA"; color: page.accent; font.pixelSize: 10; font.bold: true}
                    Text {text: "Modelo: " + info.model; color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight}
                    Text {text: "Fabricante: " + info.manufacturer; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight}
                    Text {text: info.details || "Consulta de Windows en curso."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap}
                }
            }

            // Almacenamiento: salud física reportada por Windows separada del espacio usado.
            ColumnLayout {
                visible: page.currentModule === "storage"
                Layout.fillWidth: true
                spacing: 13
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "UNIDAD SELECCIONADA"; color: page.muted; font.pixelSize: 11; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: page.selectedStorageVolume.mount || "N/A"
                        color: page.accent
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 154
                    radius: 17
                    color: page.surface
                    border.width: 1
                    border.color: page.edge
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 17
                        spacing: 18
                        ColumnLayout {
                            Layout.preferredWidth: 142
                            spacing: 6
                            Text { text: "ESTADO DE SALUD"; color: page.muted; font.pixelSize: 9; font.bold: true }
                            Text {
                                text: page.selectedStorageDisk.healthKnown ? page.selectedStorageDisk.health : "N/A"
                                color: page.selectedStorageDisk.health === "Correcto" ? "#36D6A0" : page.selectedStorageDisk.health === "Crítico" ? "#F36B75" : page.selectedStorageDisk.health === "Advertencia" ? "#E9B86B" : page.muted
                                font.pixelSize: 22
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                            Text { text: page.selectedStorageDisk.smartSource || (page.selectedStorageDisk.healthKnown ? "Windows Storage" : "Sin lectura confirmada"); color: page.muted; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: page.edge }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 5
                            Text {
                                Layout.fillWidth: true
                                text: page.selectedStorageDisk.name || "Disco físico no asociado"
                                color: page.ink
                                font.pixelSize: 16
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: (page.selectedStorageDisk.media || "Unidad") + " · " + (page.selectedStorageDisk.capacity || "N/A") + " · " + (page.selectedStorageDisk.bus || "Bus N/A")
                                color: page.muted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "Firmware: " + (page.selectedStorageDisk.firmware || "N/A") + " · Serie: " + (page.selectedStorageDisk.serial || "N/A")
                                color: page.muted
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: page.selectedStorageDisk.name ? ("Estado operativo: " + (page.selectedStorageDisk.operationalStatus || "N/A")) : "Windows no pudo relacionar esta partición con un disco físico."
                                color: page.muted
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }
                        ColumnLayout {
                            Layout.preferredWidth: 150
                            Layout.minimumWidth: 120
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 3
                            Text { text: "TEMPERATURA"; color: page.muted; font.pixelSize: 9; font.bold: true }
                            Text {
                                text: page.storageMetric(page.selectedStorageDisk.temperatureC, " °C")
                                color: typeof page.selectedStorageDisk.temperatureC === "number" ? "#36D6A0" : page.muted
                                font.pixelSize: 25
                                font.bold: true
                            }
                            Text { text: "ESTADO DE DESGASTE"; color: page.muted; font.pixelSize: 9; font.bold: true; wrapMode: Text.WordWrap }
                            Text {
                                text: page.storageWearState(page.selectedStorageDisk.wearPercent)
                                color: page.storageWearColor(page.selectedStorageDisk.wearPercent)
                                font.pixelSize: 12
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: typeof page.selectedStorageDisk.wearPercent === "number" && isFinite(page.selectedStorageDisk.wearPercent)
                                      ? page.storageMetric(page.selectedStorageDisk.wearPercent, "%") + " de resistencia estimada consumida"
                                      : "El controlador no reporta el desgaste"
                                color: page.muted
                                font.pixelSize: 9
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 112
                    radius: 15
                    color: page.surface
                    border.width: 1
                    border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "USO DEL VOLUMEN " + (page.selectedStorageVolume.mount || ""); color: page.ink; font.pixelSize: 12; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: typeof page.selectedStorageVolume.usedPct === "number" ? Number(page.selectedStorageVolume.usedPct).toFixed(1) + "% ocupado" : "N/A"
                                color: typeof page.selectedStorageVolume.usedPct === "number" && page.selectedStorageVolume.usedPct >= 90 ? "#E9B86B" : page.accent
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 9
                            radius: 5
                            color: page.edge
                            clip: true
                            Rectangle {
                                width: typeof page.selectedStorageVolume.usedPct === "number" ? parent.width * Math.max(0, Math.min(100, page.selectedStorageVolume.usedPct)) / 100 : 0
                                height: parent.height
                                radius: 5
                                color: typeof page.selectedStorageVolume.usedPct === "number" && page.selectedStorageVolume.usedPct >= 90 ? "#E9B86B" : "#26B8F2"
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Usado: " + (page.selectedStorageVolume.used || "N/A"); color: page.accent; font.pixelSize: 10; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: "Libre: " + (page.selectedStorageVolume.free || "N/A") + " · Total: " + (page.selectedStorageVolume.total || "N/A"); color: page.muted; font.pixelSize: 10 }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    implicitHeight: smartColumn.implicitHeight + 24
                    radius: 15
                    color: page.surface
                    border.width: 1
                    border.color: page.edge
                    ColumnLayout {
                        id: smartColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ATRIBUTOS DE CONFIABILIDAD"; color: page.ink; font.pixelSize: 12; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: "VALOR"; color: page.muted; font.pixelSize: 9; font.bold: true }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.edge }
                        Repeater {
                            model: page.storageReadings
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                visible: (!modelData.nvmeOnly || page.selectedDiskIsNvme()) &&
                                         (!modelData.sataOnly || !page.selectedDiskIsNvme() || modelData.value !== "N/A")
                                Layout.preferredHeight: visible ? 29 : 0
                                spacing: 8
                                Text { text: modelData.label; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true }
                                Text { text: modelData.value; color: modelData.value === "N/A" ? page.muted : page.ink; font.pixelSize: 10; font.bold: true; horizontalAlignment: Text.AlignRight }
                                Rectangle { Layout.fillWidth: true; Layout.preferredWidth: 12; Layout.preferredHeight: 1; color: page.edge; opacity: 0.65 }
                            }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Estado SMART y desgaste son lecturas distintas. El desgaste es resistencia estimada consumida: menos de 20 % bajo, 20–49 % moderado, 50–79 % alto y desde 80 % muy alto; son bandas orientativas, no un diagnóstico de fallo. En NVMe se muestran datos leídos/escritos del host, comandos y errores de medio; no se inventan contadores separados de error de lectura/escritura. Si Windows o el controlador no expone una lectura, permanece como N/A."
                    color: page.muted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Text {
                    visible: page.storageInfo.busy || page.storageInfo.physicalBusy
                    Layout.fillWidth: true
                    text: page.storageInfo.physicalBusy ? "Consultando información física del almacenamiento…" : "Consultando volúmenes…"
                    color: page.muted
                    font.pixelSize: 10
                }
            }

            // Módulo histórico recuperado de V485, en modo diagnóstico de solo lectura.
            ColumnLayout {
                visible: page.currentModule === "windows"
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    radius: 10; color: themeManager.palette.panelRaised; border.width: 1; border.color: page.edge
                    Row {
                        anchors.left: parent.left; anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter; spacing: 9
                        Glyph { kind: "services"; ink: page.accent; width: 19; height: 19 }
                        Text { text: "Análisis de Windows"; color: page.accent; font.bold: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
                Text {
                    Layout.fillWidth: true; wrapMode: Text.WordWrap
                    text: "Diagnóstico real de inicio, servicios, eventos y dispositivos. Sin cambios automáticos en Windows."
                    color: page.muted; font.pixelSize: 11
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: windowsProgressColumn.implicitHeight + 28
                    radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: windowsProgressColumn
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 15; spacing: 9
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ESTADO DEL ANÁLISIS"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text { text: page.windowsInfo.busy ? "EN CURSO" : "LISTO"; color: page.windowsInfo.busy ? page.accent : page.statusOk; font.pixelSize: 12; font.bold: true }
                        }
                        Text { text: page.windowsInfo.stage || "Sin comprobaciones ejecutadas."; color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: themeManager.palette.panelBorder
                            Rectangle {
                                height: parent.height; radius: 5; color: page.accent
                                width: parent.width * Math.max(0, Math.min(100, Number(page.windowsInfo.progress || 0))) / 100
                                Behavior on width { NumberAnimation { duration: 180 } }
                            }
                        }
                        Text { text: Math.round(Number(page.windowsInfo.progress || 0)) + " %"; color: page.muted; font.pixelSize: 11 }
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 740 ? 1 : 2
                    columnSpacing: 13; rowSpacing: 13
                    Repeater {
                        model: page.windowsSections
                        delegate: GlassPanel {
                            required property var modelData
                            readonly property var section: page.windowsInfo[modelData.key] || ({available:false,metric:"N/A",caption:"No disponible",items:[]})
                            Layout.fillWidth: true; Layout.preferredHeight: 152
                            color: page.surface; border.width: 1; border.color: page.edge; radius: 16
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 14; spacing: 5
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: modelData.title; font.pixelSize: 11; font.bold: true; color: page.muted; Layout.fillWidth: true }
                                    Glyph { kind: modelData.icon; ink: page.accent; width: 19; height: 19 }
                                }
                                Text { text: section.metric; font.pixelSize: 32; font.bold: true; color: section.available ? page.accent : page.muted }
                                Text {
                                    text: section.caption; Layout.fillWidth: true
                                    wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 11
                                }
                                OutlineButton {
                                    text: page.expandedWindowsSection === modelData.key ? "Ocultar detalles" : "Ver detalles"
                                    enabled: section.available
                                    Layout.preferredHeight: 33
                                    Layout.alignment: Qt.AlignLeft
                                    onClicked: page.expandedWindowsSection = page.expandedWindowsSection === modelData.key ? "" : modelData.key
                                }
                            }
                        }
                    }
                }
                GlassPanel {
                    visible: page.expandedWindowsSection !== ""
                    Layout.fillWidth: true
                    Layout.preferredHeight: detailsWindowColumn.implicitHeight + 28
                    color: page.surface; border.width: 1; border.color: page.edge; radius: 15
                    ColumnLayout {
                        id: detailsWindowColumn
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: parent.top; anchors.margins: 14
                        spacing: 10
                        Text { text: "DETALLES · " + page.expandedWindowsSection.toUpperCase(); color: page.accent; font.pixelSize: 11; font.bold: true }
                        Repeater {
                            model: page.expandedWindowsSection && page.windowsInfo[page.expandedWindowsSection] ?
                                (page.windowsInfo[page.expandedWindowsSection].items || []) : []
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 3
                                Text { text: modelData.primary; color: page.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.secondary; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.edge }
                            }
                        }
                        Text {
                            visible: page.expandedWindowsSection !== "" && page.windowsInfo[page.expandedWindowsSection] &&
                                page.windowsInfo[page.expandedWindowsSection].items.length === 0
                            text: "Sin elementos que mostrar en esta consulta."
                            color: page.muted; font.pixelSize: 12
                        }
                    }
                }
                Text {
                    text: "Actualizado: " + page.windowsInfo.lastUpdate + "  ·  Fuente: CIM / Visor de eventos / PnP de Windows"
                    color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
                Text {
                    text: "Una entrada de inicio o un servicio automático detenido no significa necesariamente un problema. " +
                          "Los eventos muestran hasta 80 registros recientes; los drivers se evalúan por código PnP, no por actualizaciones pendientes."
                    color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
            }

            // Recuperación del sistema: lectura real + accesos controlados.
            ColumnLayout {
                visible: page.currentModule === "recovery"
                Layout.fillWidth: true
                spacing: 13
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    radius: 10; color: themeManager.palette.panelRaised; border.width: 1; border.color: page.edge
                    Row {
                        anchors.left: parent.left; anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter; spacing: 9
                        Glyph { kind: "restore"; ink: page.accent; width: 19; height: 19 }
                        Text { text: "Recuperación del sistema"; color: page.accent; font.bold: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
                Text {
                    text: "Consulta Restaurar sistema, puntos de restauración y el estado de Windows RE. No ejecuta cambios hasta que tú lo confirmes."
                    color: page.muted; wrapMode: Text.WordWrap; font.pixelSize: 12; Layout.fillWidth: true
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 740 ? 1 : 2
                    columnSpacing: 13; rowSpacing: 13
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 176
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 8
                            Text { text: "PROTECCIÓN DEL SISTEMA"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: page.recoveryInfo.protectionText || "N/A"; color: page.recoveryInfo.protectionText === "Activa" ? page.statusOk : page.muted; font.pixelSize: 24; font.bold: true }
                            Text { text: "Unidad del sistema: " + (page.recoveryInfo.systemDrive || "N/A"); color: page.ink; font.pixelSize: 12 }
                            Text { text: "Windows RE: " + (page.recoveryInfo.recoveryEnv || "N/A"); color: page.muted; font.pixelSize: 11 }
                            Text { text: page.recoveryInfo.isAdmin ? "Administrador detectado" : "Para crear puntos debes abrir CorePulse como administrador"; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        }
                    }
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 176
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 8
                            Text { text: "PUNTOS DE RESTAURACIÓN"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: page.recoveryInfo.pointCount || "N/A"; color: page.accent; font.pixelSize: 24; font.bold: true }
                            Text { text: "Último punto:"; color: page.muted; font.pixelSize: 11 }
                            Text { text: page.recoveryInfo.latestDescription || "N/A"; color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text { text: page.recoveryInfo.latestCreated || "N/A"; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: recoveryStatusColumn.implicitHeight + 30
                    color: page.surface; radius: 16; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: recoveryStatusColumn
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 15; spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ESTADO DE RECUPERACIÓN"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text { text: page.recoveryInfo.busy ? "EN CURSO" : (page.recoveryInfo.status || "N/A"); color: (page.recoveryInfo.status === "ERROR" || page.recoveryInfo.status === "PARCIAL" || page.recoveryInfo.status === "ADMIN") ? page.statusWarning : page.recoveryInfo.status === "OK" ? page.statusOk : page.muted; font.pixelSize: 12; font.bold: true }
                        }
                        Text { text: page.recoveryInfo.busy ? page.recoveryInfo.stage : page.recoveryInfo.summary; color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: themeManager.palette.panelBorder
                            Rectangle {
                                height: parent.height; radius: 5; color: page.recoveryInfo.status === "ERROR" || page.recoveryInfo.status === "PARCIAL" ? page.statusWarning : page.statusOk
                                width: parent.width * Math.max(0, Math.min(100, Number(page.recoveryInfo.progress || 0))) / 100
                                Behavior on width { NumberAnimation { duration: 180 } }
                            }
                        }
                        Text { text: Math.round(Number(page.recoveryInfo.progress || 0)) + " %"; color: page.muted; font.pixelSize: 11 }
                        Text { visible: page.recoveryInfo.logPath !== "N/A"; text: "Registro local: " + page.recoveryInfo.logPath; font.pixelSize: 10; color: page.muted; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 740 ? 1 : 2
                    columnSpacing: 13; rowSpacing: 13
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 178
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 9
                            Text { text: "CREAR PUNTO"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: "Punto de restauración"; color: page.accent; font.pixelSize: 22; font.bold: true }
                            Text { text: "Crea un punto manual usando la función nativa de Windows. Requiere protección del sistema y privilegios de administrador."; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            OutlineButton { actionStyle: true; text: "Crear punto"; enabled: !page.recoveryInfo.busy; onClicked: page.confirmRecovery = "create" }
                        }
                    }
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 178
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 9
                            Text { text: "HERRAMIENTAS DE WINDOWS"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: "Restaurar y recuperación"; color: page.accent; font.pixelSize: 22; font.bold: true }
                            Text { text: "Abre las herramientas nativas para restaurar el sistema o entrar a la configuración de recuperación."; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            RowLayout {
                                spacing: 10
                                OutlineButton { text: "Abrir Restaurar sistema"; enabled: !page.recoveryInfo.busy; onClicked: recoveryHealth.openSystemRestore() }
                                OutlineButton { text: "Configuración"; enabled: !page.recoveryInfo.busy; onClicked: recoveryHealth.openRecoverySettings() }
                            }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: recoveryPointsColumn.implicitHeight + 28
                    visible: (page.recoveryInfo.points || []).length > 0
                    color: page.surface; border.width: 1; border.color: page.edge; radius: 15
                    ColumnLayout {
                        id: recoveryPointsColumn
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 14; spacing: 10
                        Text { text: "DETALLES · PUNTOS DE RESTAURACIÓN"; color: page.accent; font.pixelSize: 11; font.bold: true }
                        Repeater {
                            model: page.recoveryInfo.points || []
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 3
                                Text { text: modelData.primary; color: page.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.secondary; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.edge }
                            }
                        }
                    }
                }
                Text {
                    visible: !page.recoveryInfo.busy && (page.recoveryInfo.points || []).length === 0
                    text: page.recoveryInfo.pointCount === "0" ? "No hay puntos de restauración registrados." : "No se pudo confirmar el inventario de puntos. Revisa el estado de la consulta."
                    color: page.muted; font.pixelSize: 12
                }
                Text {
                    text: "Actualizado: " + page.recoveryInfo.lastUpdate + "  ·  Fuente: Windows / Restaurar sistema / reagentc"
                    color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap
                }
            }

            // Historial de cambios: fuentes independientes de solo lectura.
            ColumnLayout {
                visible: page.currentModule === "history"
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    radius: 10; color: themeManager.palette.panelRaised; border.width: 1; border.color: page.edge
                    Row {
                        anchors.left: parent.left; anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter; spacing: 9
                        Glyph { kind: "history"; ink: page.accent; width: 19; height: 19 }
                        Text { text: "Historial de cambios"; color: page.accent; font.bold: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
                Text {
                    Layout.fillWidth: true; wrapMode: Text.WordWrap
                    text: "Registros de Tweaks, DISM/SFC, Windows Update y puntos de restauración. Consultas de solo lectura; no es un registro de toda la actividad de Windows."
                    color: page.muted; font.pixelSize: 11
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: historyStatusColumn.implicitHeight + 28
                    radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: historyStatusColumn
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 14; spacing: 9
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "CONSULTA DE HISTORIAL"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text { text: page.historyInfo.busy ? "EN CURSO" : page.historyInfo.status; color: page.historyInfo.status === "PARCIAL" || page.historyInfo.status === "ERROR" ? "#E5B768" : page.accent; font.pixelSize: 12; font.bold: true }
                        }
                        Text { text: page.historyInfo.stage; color: page.ink; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 9; radius: 5; color: themeManager.palette.panelBorder
                            Rectangle {
                                height: parent.height; radius: 5; color: page.accent
                                width: parent.width * Math.max(0, Math.min(100, Number(page.historyInfo.progress || 0))) / 100
                                Behavior on width { NumberAnimation { duration: 190 } }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: Math.round(Number(page.historyInfo.progress || 0)) + " %"; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: "Fuentes disponibles: " + page.historyInfo.sourceCount; color: page.muted; font.pixelSize: 11 }
                        }
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 760 ? 2 : 4
                    columnSpacing: 11; rowSpacing: 11
                    Repeater {
                        model: page.historyInfo.sections || []
                        delegate: GlassPanel {
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 127
                            radius: 14; color: page.surface; border.width: 1; border.color: page.edge
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 7
                                Text { text: modelData.title; color: page.muted; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.metric; color: modelData.available ? page.accent : page.muted; font.pixelSize: 25; font.bold: true }
                                Text { text: modelData.available ? "Registros mostrados" : "Fuente no disponible"; color: page.ink; font.pixelSize: 11 }
                                Text { text: modelData.caption; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 7
                    Repeater {
                        model: page.historyFilters
                        delegate: OutlineButton {
                            required property var modelData
                            text: modelData.title
                            selected: page.historyFilter === modelData.key
                            onClicked: page.historyFilter = modelData.key
                            Layout.preferredHeight: 33
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: historyList.implicitHeight + 28
                    radius: 15; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: historyList
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 14; spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "CAMBIOS RECIENTES"; color: page.accent; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text { text: "Mostrando " + page.historyFiltered.length; color: page.muted; font.pixelSize: 10 }
                        }
                        Repeater {
                            model: page.historyFiltered
                            delegate: ColumnLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 4
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    Text { text: modelData.title; color: page.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: modelData.state; color: modelData.state === "Falló" || modelData.state === "ERROR" ? "#E17D82" : page.accent; font.pixelSize: 10; font.bold: true }
                                }
                                Text { text: modelData.sourceTitle + " · " + modelData.date; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: modelData.details; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.edge }
                            }
                        }
                        Text {
                            visible: !page.historyInfo.busy && page.historyFiltered.length === 0
                            text: page.historyInfo.lastUpdate === "N/A" ? "Presiona Actualizar para consultar los cambios." : "No hay registros disponibles para el filtro seleccionado."
                            color: page.muted; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap
                        }
                    }
                }
                Text { text: "Actualizado: " + page.historyInfo.lastUpdate + " · Las fuentes inaccesibles figuran como N/A; ninguna acción se realiza desde aquí."
                    color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }

            // Rendimiento V485: planes existentes, observación térmica y Gaming verificable.
            ColumnLayout {
                visible: page.currentModule === "performance"
                Layout.fillWidth: true
                spacing: 12
                // Tarjeta viva al estilo biblioteca Steam: proceso real, portada automática verificada
                // por manifiesto local de Steam, estado y tiempo observados.
                GlassPanel {
                    id: currentGameCard
                    Layout.fillWidth: true
                    Layout.preferredHeight: content.width < 790 ? 460 : 390
                    radius: 17; color: page.surface; border.width: 1; border.color: page.edge
                    clip: true
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "JUEGO EN EJECUCIÓN"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text {
                                text: page.activeGame.active ? (page.activeGame.state === "Cliente abierto" ? "CLIENTE ABIERTO" : "EN EJECUCIÓN") : "SIN JUEGO ACTIVO"
                                color: page.activeGame.active ? page.accent : page.muted
                                font.pixelSize: 11; font.bold: true
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            spacing: 10
                            Rectangle {
                                id: steamCover
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: 210
                                color: "#20232E"
                                radius: 12; border.width: 1; border.color: page.edge; clip: true
                                // La portada verificada ocupa toda la tarjeta. Si falta,
                                // mostramos un banner informativo completo, NUNCA ampliamos el icono.
                                Image {
                                    id: gameArtwork
                                    anchors.fill: parent
                                    source: page.activeGame.active && page.activeGame.artKind === "cover" ? (page.activeGame.artUrl || "") : ""
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true; cache: true
                                    visible: status === Image.Ready && page.activeGame.artKind === "cover"
                                }
                                Rectangle {
                                    anchors.fill: parent; visible: !gameArtwork.visible
                                    gradient: Gradient {
                                        GradientStop { position: 0; color: "#223B43" }
                                        GradientStop { position: 0.52; color: "#222C3B" }
                                        GradientStop { position: 1; color: "#1A1E2B" }
                                    }
                                }
                                Rectangle {
                                    visible: !gameArtwork.visible
                                    width: parent.width * 0.55; height: parent.height * 0.80
                                    x: parent.width * 0.53; y: -parent.height * 0.23
                                    rotation: -24; radius: 30; color: "#1B77B6B4"
                                }
                                Text {
                                    visible: !gameArtwork.visible && page.activeGame.active
                                    anchors.left: parent.left; anchors.top: parent.top
                                    anchors.leftMargin: 18; anchors.topMargin: 21
                                    color: "#90E1E0"; font.pixelSize: 11; font.bold: true
                                    text: "COREPULSE · JUEGO DETECTADO"
                                }
                                Rectangle {
                                    visible: !gameArtwork.visible && page.activeGame.active && page.activeGame.artKind === "icon"
                                    width: 90; height: 90; radius: 20
                                    anchors.right: parent.right; anchors.top: parent.top
                                    anchors.margins: 24
                                    color: "#3A131B25"; border.width: 1; border.color: "#527D95"
                                    Image {
                                        anchors.fill: parent; anchors.margins: 12
                                        source: page.activeGame.artUrl || ""
                                        fillMode: Image.PreserveAspectFit; asynchronous: true
                                    }
                                }
                                Glyph {
                                    visible: !gameArtwork.visible && (!page.activeGame.active || page.activeGame.artKind !== "icon")
                                    anchors.right: parent.right; anchors.top: parent.top
                                    anchors.rightMargin: 46; anchors.topMargin: 45
                                    width: 43; height: 43; kind: "gamepad"; ink: "#7F9CAA"
                                }
                                Rectangle {
                                    anchors.fill: parent
                                    gradient: Gradient {
                                        GradientStop { position: 0; color: "#00000000" }
                                        GradientStop { position: 0.52; color: "#430B1019" }
                                        GradientStop { position: 1; color: "#EB10121B" }
                                    }
                                }
                                Column {
                                    anchors.left: parent.left; anchors.right: parent.right
                                    anchors.bottom: parent.bottom; anchors.margins: 13; spacing: 6
                                    Text {
                                        text: page.activeGame.active ? page.activeGame.name : "Aún no hay juego activo"
                                        color: "#FFFFFF"; font.pixelSize: page.activeGame.active ? 21 : 18
                                        font.bold: true; width: parent.width; elide: Text.ElideRight
                                    }
                                    Text {
                                        text: page.activeGame.active ? "Detectado desde " + page.activeGame.source + (page.activeGame.artKind === "icon" ? " · Portada oficial no disponible" : "") : "Abre un juego de Steam, Epic, Riot, EA app o Microsoft Store/Xbox para verlo aquí"
                                        color: "#BACAD6"; font.pixelSize: 11; width: parent.width
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: content.width < 790 ? 1 : 3
                                columnSpacing: 9; rowSpacing: 9
                                Repeater {
                                    model: [
                                        {title:"ESTADO", value:page.activeGame.active ? (page.activeGame.state || "En ejecución") : "Esperando juego", icon:"gamepad"},
                                        {title:"TIEMPO ACTIVO", value:page.activeGame.active ? page.activeGame.session : "N/A", icon:"history"},
                                        {title:"ORIGEN", value:page.activeGame.active ? page.activeGame.source : "N/A", icon:"storage"}
                                    ]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 96
                                        radius: 10; color: themeManager.palette.panelRaised; border.width: 1; border.color: page.edge
                                        ColumnLayout {
                                            anchors.fill: parent; anchors.margins: 12; spacing: 5
                                            Text { text: modelData.title; color: page.muted; font.pixelSize: 9; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            Text { text: modelData.value; color: page.activeGame.active ? page.accent : page.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    visible: !!(page.performanceInfo.artworkMessage || "")
                    Layout.fillWidth: true; font.pixelSize: 11; color: page.accent; wrapMode: Text.WordWrap
                    text: page.performanceInfo.artworkMessage || ""
                }
                Text {
                    Layout.fillWidth: true; font.pixelSize: 10; color: page.muted; wrapMode: Text.WordWrap
                    text: "La tarjeta muestra el título y el estado reales del juego. Cuando existe, usa una portada verificada; si no está disponible, conserva un banner completo con el icono como referencia. FPS: N/A sin una fuente real."
                }
                GlassPanel {
                    Layout.fillWidth: true; implicitHeight: autoEnergyColumn.implicitHeight + 26
                    radius: 14; color: page.surface; border.width: 1
                    border.color: page.performanceInfo.autoPowerStatus === "ACTIVO" ? page.accent : page.edge
                    ColumnLayout {
                        id: autoEnergyColumn
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 13; spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 3
                                Text { text: "ENERGÍA AUTOMÁTICA PARA JUEGOS"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text {
                                    text: page.performanceInfo.autoPowerStatus || "ESPERANDO"
                                    color: page.performanceInfo.autoPowerStatus === "ERROR" ? "#E17D82" : page.accent
                                    font.pixelSize: 11; font.bold: true
                                }
                            }
                            OutlineButton {
                                text: page.performanceInfo.autoPowerEnabled ? "Desactivar" : "Activar"
                                selected: page.performanceInfo.autoPowerEnabled === true
                                onClicked: performanceHealth.setAutoPowerEnabled(!page.performanceInfo.autoPowerEnabled)
                            }
                        }
                        Text {
                            Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 11
                            text: page.performanceInfo.autoPowerMessage || "Esperando un juego."
                        }
                        Text {
                            Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 10
                            text: "Utiliza Máximo rendimiento si ya existe; en su defecto, Alto rendimiento. No crea planes, no solicita administrador y restaura el anterior al cerrar el último juego. Puede aumentar el consumo y reducir la autonomía."
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true; Layout.preferredHeight: gameBoostContent.implicitHeight + 30
                    radius: 16; color: page.surface; border.width: 1; border.color: gameBoost.enabled ? page.accent : page.edge
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 16; spacing: 14
                        ColumnLayout {
                            id: gameBoostContent
                            Layout.fillWidth: true; spacing: 6
                            Text { text: "GAME BOOST · " + (gameBoost.status || "DESACTIVADO"); color: gameBoost.enabled ? page.accent : page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: gameBoost.activeGame !== "N/A" ? "Juego detectado: " + gameBoost.activeGame : "Esperando un juego compatible"; color: page.ink; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text { text: gameBoost.message || "Sin cambios en Windows."; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text { text: "La prioridad, HighQoS y Game Mode se restauran al cerrar el juego o la app. La purga standby es opcional y se solicita una vez por sesión; Windows puede denegar estas acciones. No usa prioridad Realtime ni hace overclock."; color: page.muted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: content.width < 650 ? 1 : 2
                                columnSpacing: 8; rowSpacing: 6
                                OutlineButton { Layout.fillWidth: true; text: "Purgar standby: " + (gameBoost.purgeStandby ? "Sí" : "No"); selected: gameBoost.purgeStandby; onClicked: gameBoost.setPurgeStandby(!gameBoost.purgeStandby) }
                                OutlineButton { Layout.fillWidth: true; text: "Desactivar Power Throttling: " + (gameBoost.powerThrottling ? "Sí" : "No"); selected: gameBoost.powerThrottling; onClicked: gameBoost.setPowerThrottling(!gameBoost.powerThrottling) }
                            }
                        }
                        OutlineButton { actionStyle: true;
                            text: gameBoost.enabled ? "Desactivar" : "Activar Game Boost"
                            Layout.preferredWidth: 150; Layout.preferredHeight: 38
                            onClicked: gameBoost.enabled ? gameBoost.setEnabled(false) : page.confirmGameBoost = true
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: energyHead.implicitHeight + 32
                    radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: energyHead
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16; spacing: 9
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "PLANES DE ENERGÍA DE WINDOWS"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text { text: page.performanceInfo.busy ? "CONSULTANDO…" : page.performanceInfo.status; color: page.performanceInfo.status === "ERROR" ? "#E17D82" : page.accent; font.pixelSize: 11; font.bold: true }
                        }
                        Text { text: "Actual: " + (page.performanceInfo.activeName || "N/A"); color: page.accent; font.pixelSize: 17; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Text { text: page.performanceInfo.message || "Sin consulta"; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        RowLayout {
                            visible: page.performanceInfo.backupAvailable
                            Layout.fillWidth: true; spacing: 12
                            Text { text: "Plan original: " + page.performanceInfo.originalName; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            OutlineButton { actionStyle: true; text: "Restaurar plan anterior"; enabled: !page.performanceInfo.busy && page.performanceInfo.autoPowerStatus !== "ACTIVO"; onClicked: page.confirmPowerRestore = true }
                        }
                        Text { text: "Solo se ofrecen planes existentes y confirmados por powercfg. Cambiar de plan puede afectar consumo y autonomía."; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 790 ? 1 : (content.width < 1120 ? 2 : 3)
                    columnSpacing: 12; rowSpacing: 12
                    Repeater {
                        model: page.performanceInfo.plans || []
                        delegate: GlassPanel {
                            id: powerChoice
                            required property var modelData
                            readonly property bool isActive: modelData.guid === page.performanceInfo.activeGuid
                            Layout.fillWidth: true; Layout.preferredHeight: 126
                            radius: 15; color: page.surface; border.width: 1; border.color: isActive ? page.accent : page.edge
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 13; spacing: 7
                                RowLayout {
                                    Layout.fillWidth: true
                                    Glyph { kind: "power"; ink: powerChoice.isActive ? page.accent : page.muted; Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
                                    Text { text: powerChoice.modelData.name; color: page.ink; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                Text { text: powerChoice.isActive ? "Activo y verificado" : "Plan existente de Windows"; color: powerChoice.isActive ? page.accent : page.muted; font.pixelSize: 11 }
                                Item { Layout.fillHeight: true }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: powerChoice.modelData.guid.slice(0, 8) + "…"; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true }
                                    OutlineButton { solidStyle: true; actionStyle: !powerChoice.isActive;
                                        text: powerChoice.isActive ? "Activo" : "Aplicar"
                                        enabled: !page.performanceInfo.busy && !powerChoice.isActive && page.performanceInfo.autoPowerStatus !== "ACTIVO"
                                        Layout.preferredHeight: 30
                                        onClicked: {
                                            page.pendingPowerGuid = powerChoice.modelData.guid
                                            page.pendingPowerName = powerChoice.modelData.name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                Text { visible: !page.performanceInfo.busy && (page.performanceInfo.plans || []).length === 0; text: "Windows no proporcionó planes de energía verificables (N/A)."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { text: "ESTABILIDAD TÉRMICA"; color: page.ink; font.pixelSize: 15; font.bold: true; Layout.topMargin: 4 }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 740 ? 1 : 2
                    columnSpacing: 12; rowSpacing: 12
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 146
                        radius: 15; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 15; spacing: 7
                            Text { text: "CPU · Temperatura y riesgo térmico"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text {
                                text: typeof page.performanceMetrics.cpuTemp === "number" ? page.performanceMetrics.cpuTemp.toFixed(1) + " °C" : "N/A"
                                color: typeof page.performanceMetrics.cpuTemp === "number" && page.performanceMetrics.cpuTemp >= 90 ? "#E17D82" : page.accent
                                font.pixelSize: 24; font.bold: true
                            }
                            Text { text: typeof page.performanceMetrics.cpuTemp === "number" ? (page.performanceMetrics.cpuTemp >= 90 ? "Temperatura elevada; revisar refrigeración." : "Temperatura disponible; el throttling no está confirmado.") : "Sensor no disponible, sin diagnóstico térmico."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text { text: "Origen: " + (page.performanceMetrics.cpuTempSource || "N/A"); color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 146
                        radius: 15; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 15; spacing: 7
                            Text { text: "GPU · Temperatura y riesgo térmico"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text {
                                text: typeof page.performanceMetrics.gpuTemp === "number" ? page.performanceMetrics.gpuTemp.toFixed(1) + " °C" : "N/A"
                                color: typeof page.performanceMetrics.gpuTemp === "number" && page.performanceMetrics.gpuTemp >= 85 ? "#E17D82" : page.accent
                                font.pixelSize: 24; font.bold: true
                            }
                            Text { text: typeof page.performanceMetrics.gpuTemp === "number" ? (page.performanceMetrics.gpuTemp >= 85 ? "Temperatura elevada; revisar refrigeración." : "Temperatura disponible; throttling no confirmado.") : "Sensor no disponible, sin diagnóstico térmico."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text { text: "Origen: " + (page.performanceMetrics.gpuSource || "Telemetría GPU de CorePulse"); color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true; Layout.preferredHeight: 94
                    radius: 14; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 15; spacing: 7
                        Text { text: "THROTTLING REAL"; color: page.muted; font.pixelSize: 11; font.bold: true }
                        Text { text: "N/A — No hay sensor de limitación térmica confirmado"; color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Text { text: "Temperatura alta o frecuencias estimadas no prueban throttling por sí solas."; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
                Text { text: "Game Boost está desactivado por defecto. Puede ajustar prioridad, HighQoS, Game Mode y purga standby opcional; restaura los cambios reversibles que aún controla al terminar la sesión.";
                    font.pixelSize: 11; color: page.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { text: "Fuente: powercfg de Windows · psutil (procesos) · sensores de CorePulse · Actualizado: " + page.performanceInfo.lastUpdate; font.pixelSize: 10; color: page.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }

            // Diagnóstico guiado de salida y entrada con dispositivos WASAPI reales.
            ColumnLayout {
                visible: page.currentModule === "audio"
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 42
                    radius: 10; color: themeManager.palette.panelRaised; border.width: 1; border.color: page.edge
                    RowLayout {
                        anchors.left: parent.left; anchors.leftMargin: 14
                        anchors.right: parent.right; anchors.rightMargin: 14
                        anchors.verticalCenter: parent.verticalCenter; spacing: 9
                        Glyph { kind: "headphones"; ink: page.accent; width: 19; height: 19 }
                        Text { text: "Test guiado de audio"; color: page.accent; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true; verticalAlignment: Text.AlignVCenter }
                        OutlineButton { solidStyle: true; actionStyle: true; text: "Actualizar dispositivos"; enabled: !page.audioInfo.busy; onClicked: audioTest.refresh() }
                    }
                }
                Text {
                    Layout.fillWidth: true; wrapMode: Text.WordWrap
                    text: "Prueba la salida y el micrófono de forma local. El audio capturado solo permanece en memoria durante esta sesión y no se envía."
                    color: page.muted; font.pixelSize: 11
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 760 ? 1 : 2
                    columnSpacing: 13; rowSpacing: 13
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 220
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 10
                            Text { text: "SALIDA · CANALES"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: page.audioInfo.outputDevice; color: page.accent; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text { text: page.audioInfo.stereo === true ? "Salida estéreo detectada." : page.audioInfo.stereo === false ? "La salida informa un formato mono." : "Formato: N/A hasta consultar el dispositivo."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                OutlineButton { actionStyle: true; text: "Izquierdo"; Layout.fillWidth: true; enabled: !page.audioInfo.busy && page.audioInfo.outputAvailable; onClicked: audioTest.play("left") }
                                OutlineButton { actionStyle: true; text: "Ambos"; Layout.fillWidth: true; enabled: !page.audioInfo.busy && page.audioInfo.outputAvailable; onClicked: audioTest.play("both") }
                                OutlineButton { actionStyle: true; text: "Derecho"; Layout.fillWidth: true; enabled: !page.audioInfo.busy && page.audioInfo.outputAvailable; onClicked: audioTest.play("right") }
                            }
                            Text { text: "Resultados: " + ((page.audioInfo.answers || {}).left || "Sin confirmar") + " · " + ((page.audioInfo.answers || {}).right || "Sin confirmar") + " · " + ((page.audioInfo.answers || {}).both || "Sin confirmar"); color: page.ink; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        }
                    }
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 220
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 10
                            Text { text: "ENTRADA · MICRÓFONO"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: page.audioInfo.inputDevice; color: page.accent; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text { text: "Graba 5 segundos, revisa el nivel y reproduce la muestra antes de confirmar."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Rectangle {
                                Layout.fillWidth: true; height: 8; radius: 4; color: themeManager.palette.panelRaised
                                Rectangle { width: parent.width * page.audioInfo.inputLevel; height: parent.height; radius: 4; color: "#4EDDC8" }
                            }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                OutlineButton { actionStyle: !page.audioInfo.busy; text: page.audioInfo.busy ? "Cancelar" : "Grabar 5 s"; Layout.fillWidth: true; enabled: !page.audioInfo.busy && page.audioInfo.inputAvailable; onClicked: page.audioInfo.busy ? audioTest.cancel() : audioTest.record() }
                                OutlineButton { actionStyle: true; text: "Reproducir muestra"; Layout.fillWidth: true; enabled: !page.audioInfo.busy && page.audioInfo.hasRecording; onClicked: audioTest.replay() }
                            }
                            Text { text: page.audioInfo.captureCompleted ? page.audioInfo.captureSignal + " · pico " + page.audioInfo.capturePeak : "Señal capturada: N/A"; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true; Layout.preferredHeight: pendingAudio.implicitHeight + 28
                    visible: page.audioInfo.pending !== ""
                    radius: 14; color: page.surface; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: pendingAudio
                        anchors.fill: parent; anchors.margins: 14; spacing: 9
                        Text { text: "¿Escuchaste correctamente " + (page.audioInfo.pendingLabel || "la prueba") + "?"; color: page.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            OutlineButton { text: "Sí"; Layout.fillWidth: true; enabled: !page.audioInfo.busy; onClicked: audioTest.confirm("Sí") }
                            OutlineButton { text: "No estoy seguro"; Layout.fillWidth: true; enabled: !page.audioInfo.busy; onClicked: audioTest.confirm("No estoy seguro") }
                            OutlineButton { text: "No"; Layout.fillWidth: true; enabled: !page.audioInfo.busy; onClicked: audioTest.confirm("No") }
                        }
                    }
                }
                Text { Layout.fillWidth: true; text: page.audioInfo.summary + " · " + page.audioInfo.message; color: page.audioInfo.summary === "PROBLEMA REPORTADO" ? "#E17D82" : page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }

            // Reparación Windows: no ejecuta comandos hasta confirmación explícita.
            ColumnLayout {
                visible: page.currentModule === "repair"
                Layout.fillWidth: true
                spacing: 13
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    color: themeManager.palette.panelRaised; radius: 10; border.width: 1; border.color: page.edge
                    Row {
                        anchors.left: parent.left; anchors.leftMargin: 14
                        anchors.verticalCenter: parent.verticalCenter; spacing: 9
                        Glyph { kind: "wrench"; ink: page.accent; width: 19; height: 19 }
                        Text { text: "Reparación de Windows"; color: page.accent; font.bold: true; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
                Text {
                    text: "Analiza la integridad de Windows o inicia una reparación manual. DISM y SFC pueden tardar bastante tiempo."
                    color: page.muted; wrapMode: Text.WordWrap; font.pixelSize: 12; Layout.fillWidth: true
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: content.width < 740 ? 1 : 2
                    columnSpacing: 13; rowSpacing: 13
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 176
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 9
                            Text { text: "COMPROBAR INTEGRIDAD"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: "DISM + SFC"; color: page.accent; font.pixelSize: 23; font.bold: true }
                            Text { text: "CheckHealth · ScanHealth · VerifyOnly"; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            OutlineButton { actionStyle: true;
                                text: "Analizar Windows"
                                enabled: !page.repairInfo.busy
                                onClicked: page.confirmRepair = "diagnostic"
                            }
                        }
                    }
                    GlassPanel {
                        Layout.fillWidth: true; Layout.preferredHeight: 176
                        radius: 16; color: page.surface; border.width: 1; border.color: page.edge
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 17; spacing: 9
                            Text { text: "REPARAR WINDOWS"; color: page.muted; font.pixelSize: 11; font.bold: true }
                            Text { text: "DISM + SFC"; color: page.accent; font.pixelSize: 23; font.bold: true }
                            Text { text: "RestoreHealth · ScanNow · comprobar"; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            OutlineButton { actionStyle: true;
                                text: "Iniciar reparación"
                                enabled: !page.repairInfo.busy
                                onClicked: page.confirmRepair = "repair"
                            }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: repairStatusColumn.implicitHeight + 30
                    color: page.surface; radius: 16; border.width: 1; border.color: page.edge
                    ColumnLayout {
                        id: repairStatusColumn
                        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                        anchors.margins: 15; spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ESTADO DE REPARACIÓN"; color: page.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                            Text {
                                text: page.repairInfo.busy ? "EN CURSO" : page.repairInfo.status
                                color: page.repairInfo.status === "ERROR" || page.repairInfo.status === "ATENCION" ? "#E5B768" : page.accent
                                font.pixelSize: 12; font.bold: true
                            }
                        }
                        Text { text: page.repairInfo.busy ? page.repairInfo.stage : page.repairInfo.summary
                            color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 10; radius: 5; color: themeManager.palette.panelBorder
                            Rectangle {
                                height: parent.height; radius: 5; color: page.accent
                                width: parent.width * Math.max(0, Math.min(100, Number(page.repairInfo.progress || 0))) / 100
                                Behavior on width { NumberAnimation { duration: 180 } }
                            }
                        }
                        Text { text: Math.round(Number(page.repairInfo.progress || 0)) + " %"; color: page.muted; font.pixelSize: 11 }
                        Text { text: page.repairInfo.isAdmin ? "Administrador detectado" : "Requiere iniciar CorePulse como administrador"
                            color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Repeater {
                            model: page.repairInfo.steps || []
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true; spacing: 8
                                Text { text: modelData.title; Layout.fillWidth: true; color: page.ink; font.pixelSize: 11; elide: Text.ElideRight }
                                Text { text: modelData.state; color: modelData.state === "ERROR" ? "#E17D82" : page.accent; font.pixelSize: 11; font.bold: true }
                            }
                        }
                        Text {
                            visible: page.repairInfo.logPath !== "N/A"
                            text: "Registro local: " + page.repairInfo.logPath
                            font.pixelSize: 10; color: page.muted; Layout.fillWidth: true
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
                Text {
                    text: "Las reparaciones modifican archivos de Windows y no equivalen a revertir Tweaks. " +
                          "No se ejecuta nada automáticamente. Puede requerirse reiniciar; guarda tu trabajo antes."
                    Layout.fillWidth: true; font.pixelSize: 11; color: page.muted; wrapMode: Text.WordWrap
                }
            }
        }
    }
    ThinScroll {
        target: pageScroll
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
    }
    Rectangle {
        id: gameBoostConfirmOverlay
        anchors.fill: parent; z: 103
        visible: page.confirmGameBoost
        color: "#B5000000"
        Rectangle {
            width: Math.min(parent.width - 24, 460)
            height: gameBoostConfirmContents.implicitHeight + 38
            radius: 17; color: page.surface; border.width: 1; border.color: page.edge
            anchors.centerIn: parent
            ColumnLayout {
                id: gameBoostConfirmContents
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 19; spacing: 14
                Text { text: "Activar Game Boost"; font.pixelSize: 18; color: page.ink; font.bold: true }
                Text { text: "CorePulse cambiará temporalmente la prioridad del juego, desactivará HighQoS si está habilitado y, si hace falta, activará Game Mode de tu usuario. Si la purga está activa, solicitará liberar la lista standby una vez al comenzar la sesión. Guardará y restaurará los cambios reversibles. ¿Continuar?"; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 12 }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Item { Layout.fillWidth: true }
                    OutlineButton { text: "Cancelar"; onClicked: page.confirmGameBoost = false }
                    OutlineButton { actionStyle: true; text: "Activar"; onClicked: { page.confirmGameBoost = false; gameBoost.setEnabled(true) } }
                }
            }
        }
    }
    Rectangle {
        id: powerConfirmOverlay
        anchors.fill: parent; z: 102
        visible: page.pendingPowerGuid !== "" || page.confirmPowerRestore
        color: "#B5000000"
        Rectangle {
            width: Math.min(parent.width - 24, 440)
            height: powerConfirmContents.implicitHeight + 38
            radius: 17; color: page.surface; border.width: 1; border.color: page.edge
            anchors.centerIn: parent
            ColumnLayout {
                id: powerConfirmContents
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 19; spacing: 15
                Text { text: page.confirmPowerRestore ? "Restaurar plan anterior" : "Confirmar plan de energía"; font.pixelSize: 18; color: page.ink; font.bold: true }
                Text {
                    text: page.confirmPowerRestore ? "Windows activará el plan registrado antes de los cambios de CorePulse. ¿Continuar?" : "Se activará «" + page.pendingPowerName + "», plan existente de Windows. Puede cambiar el consumo y la autonomía. CorePulse guardará el plan anterior para restaurarlo. ¿Continuar?"
                    Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 12
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Item { Layout.fillWidth: true }
                    OutlineButton { text: "Cancelar"; onClicked: { page.pendingPowerGuid = ""; page.confirmPowerRestore = false } }
                    OutlineButton { actionStyle: true;
                        text: "Confirmar"
                        onClicked: {
                            const selected = page.pendingPowerGuid
                            const restore = page.confirmPowerRestore
                            page.pendingPowerGuid = ""
                            page.confirmPowerRestore = false
                            if (restore) performanceHealth.restorePrevious()
                            else if (selected !== "") performanceHealth.applyPlan(selected)
                        }
                    }
                }
            }
        }
    }
    Rectangle {
        id: repairConfirmOverlay
        visible: page.confirmRepair !== ""
        z: 100
        anchors.fill: parent
        color: "#B5000000"
        Rectangle {
            width: Math.min(parent.width - 24, 440)
            height: confirmPanel.implicitHeight + 38
            radius: 17; color: page.surface; border.width: 1; border.color: page.edge
            anchors.centerIn: parent
            ColumnLayout {
                id: confirmPanel
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 19; spacing: 15
                Text { text: page.confirmRepair === "repair" ? "Confirmar reparación" : "Confirmar diagnóstico"
                    font.pixelSize: 18; color: page.ink; font.bold: true }
                Text {
                    text: page.confirmRepair === "repair" ?
                        "Se ejecutarán DISM RestoreHealth y SFC ScanNow. Pueden modificar archivos del sistema y tardar varios minutos. ¿Continuar?" :
                        "Se ejecutarán DISM CheckHealth, ScanHealth y SFC VerifyOnly. No se reparará nada. ¿Continuar?"
                    Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 12
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Item { Layout.fillWidth: true }
                    OutlineButton { text: "Cancelar"; onClicked: page.confirmRepair = "" }
                    OutlineButton { actionStyle: true;
                        text: "Confirmar"
                        onClicked: {
                            const selected = page.confirmRepair
                            page.confirmRepair = ""
                            if (selected === "diagnostic" || selected === "repair") repairHealth.start(selected)
                        }
                    }
                }
            }
        }
    }
    Rectangle {
        id: recoveryConfirmOverlay
        visible: page.confirmRecovery !== ""
        z: 101
        anchors.fill: parent
        color: "#B5000000"
        Rectangle {
            width: Math.min(parent.width - 24, 440)
            height: recoveryConfirmPanel.implicitHeight + 38
            radius: 17; color: page.surface; border.width: 1; border.color: page.edge
            anchors.centerIn: parent
            ColumnLayout {
                id: recoveryConfirmPanel
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 19; spacing: 15
                Text { text: "Confirmar creación"; font.pixelSize: 18; color: page.ink; font.bold: true }
                Text {
                    text: "Windows intentará crear un punto de restauración manual. Esto requiere permisos de administrador y puede fallar si la protección del sistema está desactivada o si Windows limita la frecuencia de creación. ¿Continuar?"
                    Layout.fillWidth: true; wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 12
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Item { Layout.fillWidth: true }
                    OutlineButton { text: "Cancelar"; onClicked: page.confirmRecovery = "" }
                    OutlineButton { actionStyle: true;
                        text: "Confirmar"
                        onClicked: {
                            const selected = page.confirmRecovery
                            page.confirmRecovery = ""
                            if (selected === "create") recoveryHealth.createPoint()
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: batteryHealth
        function onChanged() {
            chargeRing.requestPaint()
            if (!page.info.hasBattery && !page.info.busy && page.currentModule === "battery")
                page.currentModule = "hub"
        }
    }
}
