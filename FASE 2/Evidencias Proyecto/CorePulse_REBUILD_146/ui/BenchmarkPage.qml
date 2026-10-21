import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: page
    signal goBack()
    property string gpuProfile: "standard"
    readonly property var d: benchmarkController.data || ({})
    readonly property var result: d.result || ({})
    readonly property var gpu: d.gpuResult || ({})
    readonly property var scenes: gpu.scenes || []
    readonly property var session: gpu.session || ({})
    readonly property var sessionWarnings: session.warnings || []
    readonly property var historyRows: d.history || []
    readonly property var visibleHistory: page.filteredHistory()
    readonly property var reportData: reportExporter && reportExporter.data ? reportExporter.data : ({busy:false, status:"", path:"", kind:""})
    property string historyFilter: "all"
    property string historyFirstId: ""
    property string historySecondId: ""
    property var historyComparison: ({ok:false, message:"", metrics:[]})
    readonly property color panel: themeManager.palette.panel
    readonly property color raised: themeManager.palette.panelRaised
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.accent
    readonly property color cyan: themeManager.palette.cyan
    readonly property color purple: themeManager.palette.purple
    readonly property color diskAccent: "#558D82"
    readonly property color warning: "#E9B768"

    function render(value, suffix, decimals) {
        if (typeof value !== "number" || !isFinite(value)) return "N/A"
        return Number(value).toLocaleString(Qt.locale("es-CL"), 'f', decimals === undefined ? 1 : decimals) + (suffix || "")
    }
    function stabilityText(code) {
        if (code === "ESTABLE") return "Estable"
        if (code === "THROTTLING") return "Reducción de relojes"
        if (code === "RELOJ_BAJO") return "Relojes bajo el máximo"
        return "Sin datos"
    }
    function adapterText(code) {
        if (code === "DXGI6_HIGH_PERFORMANCE") return "GPU de alto rendimiento (DXGI 1.6)"
        if (code === "MAX_DEDICATED_VRAM") return "GPU con más VRAM dedicada"
        return "Predeterminada de Windows"
    }
    function sceneTitle(key) {
        if (key === "avenue") return "01 · Avenida de neón"
        if (key === "district") return "02 · Distrito financiero"
        if (key === "skyline") return "03 · Horizonte nocturno"
        if (key === "megacity") return "04 · Megaciudad"
        return key || "Escena"
    }
    function filteredHistory() {
        if (page.historyFilter === "all") return page.historyRows
        return page.historyRows.filter(function(row) {
            return page.historyFilter === "gpu" ? row.kind === "GPU" : row.kind === "CPU_RAM_SSD"
        })
    }
    function historyLabel(row) {
        if (row.kind === "GPU") {
            const profile = row.profile === "quick" ? "Rápido" : row.profile === "extended" ? "Extendido" : row.profile === "standard" ? "Estándar" : "Perfil anterior"
            return "GPU DirectX 11 V29 · " + profile
        }
        return "CPU · RAM · SSD"
    }
    function historyDetails(row) {
        const s = row.summary || ({})
        if (row.kind === "GPU")
            return (row.renderer || "Adaptador N/A") + " · promedio " + page.render(s.gpu_fps, " FPS", 1) + " · 1 % Low " + page.render(s.gpu_low_fps, " FPS", 1)
        return "CPU " + page.render(s.cpu_ops_s, " iter/s", 0) + " · RAM " + page.render(s.ram_mib_s, " MiB/s", 1)
            + " · SSD R/W " + page.render(s.ssd_read_mib_s, " / ", 1) + page.render(s.ssd_write_mib_s, " MiB/s", 1)
    }
    function historyDate(value) {
        const parsed = new Date(String(value || ""))
        return isNaN(parsed.getTime()) ? String(value || "Fecha N/A") : Qt.formatDateTime(parsed, "dd/MM/yyyy HH:mm")
    }
    function setHistorySelection(which, row) {
        if (which === "first") page.historyFirstId = String(row.id || "")
        else page.historySecondId = String(row.id || "")
        if (page.historyFirstId && page.historySecondId)
            page.historyComparison = benchmarkController.compareHistory(page.historyFirstId, page.historySecondId)
        else
            page.historyComparison = ({ok:false, message:"Selecciona una sesión como base y otra como nueva.", metrics:[]})
    }
    function deltaText(value) {
        if (typeof value !== "number" || !isFinite(value)) return "N/A"
        return (value > 0 ? "+" : "") + Number(value).toLocaleString(Qt.locale("es-CL"), "f", 1) + "%"
    }
    component ActionButton: Rectangle {
        id: button
        property string label: ""
        property bool enabledAction: true
        property bool primary: false
        property color tint: page.accent
        signal activated()
        implicitWidth: buttonLabel.implicitWidth + 26
        implicitHeight: 38
        opacity: enabledAction ? 1 : .45
        radius: 11
        color: primary ? Qt.alpha(button.tint, buttonMouse.containsMouse ? .22 : .12) : buttonMouse.containsMouse ? page.raised : page.panel
        border.width: 1
        border.color: primary ? Qt.alpha(button.tint,.62) : page.edge
        Text { id:buttonLabel; anchors.centerIn: parent; text: button.label; color: button.primary ? button.tint : page.ink; font.pixelSize:12; font.bold:true }
        MouseArea { id:buttonMouse; anchors.fill: parent; enabled:button.enabledAction; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; onClicked:button.activated() }
    }
    component ResultCard: GlassPanel {
        id: tile
        property string heading: ""
        property string subhead: ""
        property string value: "N/A"
        property string detail: ""
        property color tint: page.accent
        Layout.fillWidth:true
        Layout.preferredHeight: 160
        radius:16; color:page.panel; border.width:1; border.color:page.edge
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 15; spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Rectangle { Layout.preferredWidth:5; Layout.preferredHeight:25; radius:3; color:tile.tint }
                ColumnLayout { Layout.fillWidth:true; spacing:3
                    Text { text: tile.heading; color:page.ink; font.pixelSize:14; font.bold:true; Layout.fillWidth:true; elide:Text.ElideRight }
                    Text { text: tile.subhead; color:page.muted; font.pixelSize:10; Layout.fillWidth:true; elide:Text.ElideRight }
                }
            }
            Text { id:valueText; text: tile.value; color:tile.tint; font.pixelSize:20; font.bold:true; Layout.fillWidth:true; elide:Text.ElideRight
                ToolTip.visible: valueHover.containsMouse && truncated
                ToolTip.text: tile.value
                MouseArea {id:valueHover; anchors.fill:parent; hoverEnabled:true; acceptedButtons:Qt.NoButton}
            }
            Text { text:tile.detail; color:page.muted; font.pixelSize:11; Layout.fillWidth:true; wrapMode:Text.WordWrap; maximumLineCount:2; elide:Text.ElideRight }
        }
    }

    FileDialog {
        id: historyCsvDialog
        title: "Exportar historial de benchmark"
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV (*.csv)"]
        defaultSuffix: "csv"
        onAccepted: benchmarkController.exportHistory(selectedFile.toString(), page.historyFilter)
    }

    FastFlickable {
        id:scroll
        anchors.fill:parent; anchors.margins:0
        contentWidth:width; contentHeight:body.implicitHeight+24
        clip:true; boundsBehavior:Flickable.StopAtBounds
        ColumnLayout {
            id:body
            width:Math.max(0,scroll.width-10)
            spacing:16
            RowLayout {
                Layout.fillWidth:true; spacing:12
                Rectangle { Layout.preferredWidth:46; Layout.preferredHeight:46; radius:13; color:page.raised
                    Glyph { anchors.centerIn:parent; width:25; height:25; kind:"gauge"; ink:page.cyan }
                }
                ColumnLayout { Layout.fillWidth:true; spacing:4
                    Text { text:"Benchmark"; color:page.ink; font.pixelSize:21; font.bold:true }
                    Text { text:"Pruebas reales del equipo · CPU, RAM, SSD y GPU DirectX 11"; color:page.muted; font.pixelSize:11; Layout.fillWidth:true; elide:Text.ElideRight }
                }
                ActionButton { label:"Volver"; onActivated:page.goBack() }
            }
            GridLayout {
                Layout.fillWidth:true
                columns:body.width < 810 ? 1 : 2
                rowSpacing:11; columnSpacing:11
                GlassPanel {
                    Layout.fillWidth:true; Layout.preferredHeight: runColumn.implicitHeight+30
                    radius:16; color:page.panel; border.width:1; border.color:page.edge
                    ColumnLayout { id:runColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:15; spacing:10
                        Text { text:"CPU · RAM · SSD"; color:page.ink; font.pixelSize:15; font.bold:true }
                        Text { text:"Cálculo entero, copias verificadas y E/S temporal con integridad SHA-256."; color:page.muted; font.pixelSize:11; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                        RowLayout { Layout.fillWidth:true; spacing:8
                            ActionButton { label:"Iniciar benchmark"; tint:page.cyan; primary:true; enabledAction:!d.busy; onActivated:benchmarkController.start() }
                            Item { Layout.fillWidth:true }
                            Text { text:"~5 s"; color:page.muted; font.pixelSize:11 }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth:true; Layout.preferredHeight: gpuColumn.implicitHeight+30
                    radius:16; color:page.panel; border.width:1; border.color:page.edge
                    ColumnLayout { id:gpuColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:15; spacing:10
                        RowLayout { Layout.fillWidth:true
                            Text { text:"GPU · DirectX 11 V29"; color:page.ink; font.pixelSize:15; font.bold:true }
                            Item { Layout.fillWidth:true }
                            Text { text:"Ciudad de neón nocturna"; color:page.muted; font.pixelSize:10 }
                        }
                        RowLayout { Layout.fillWidth:true; spacing:6
                            Repeater {
                                model:[{id:"quick",label:"Rápido"},{id:"standard",label:"Estándar"},{id:"extended",label:"Extendido"}]
                                delegate:Rectangle {
                                    required property var modelData
                                    Layout.preferredHeight:31
                                    Layout.fillWidth:true
                                    radius:9
                                    color:page.gpuProfile === modelData.id ? Qt.alpha(page.purple,.17) : page.panel
                                    border.width:1
                                    border.color:page.gpuProfile === modelData.id ? page.purple : page.edge
                                    Text {anchors.centerIn:parent; text:modelData.label; color:page.ink; font.pixelSize:10; font.bold:page.gpuProfile===modelData.id}
                                    MouseArea { anchors.fill:parent; enabled:!d.busy; cursorShape:Qt.PointingHandCursor; onClicked:page.gpuProfile=modelData.id }
                                }
                            }
                        }
                        RowLayout { Layout.fillWidth:true
                            ActionButton { label:"Iniciar prueba GPU"; tint:page.purple; primary:true; enabledAction:!d.busy; onActivated:benchmarkController.startGpu(page.gpuProfile) }
                            Item { Layout.fillWidth:true }
                            Text { text:page.gpuProfile === "quick" ? "~19 s" : page.gpuProfile === "extended" ? "~91 s" : "~58 s"; color:page.muted; font.pixelSize:11 }
                        }
                    }
                }
            }
            GlassPanel {
                Layout.fillWidth:true; Layout.preferredHeight:122
                radius:16; color:page.panel; border.width:1; border.color:page.edge
                ColumnLayout { anchors.fill:parent; anchors.margins:15; spacing:9
                    RowLayout { Layout.fillWidth:true
                        Text { text:"ESTADO DE LA PRUEBA"; color:page.muted; font.pixelSize:10; font.bold:true; Layout.fillWidth:true }
                        Text { text:d.status || "Sin ejecutar"; color: d.status === "Error" ? "#B16C6C" : page.accent; font.pixelSize:12; font.bold:true }
                        ActionButton { visible:!!d.busy; label:"Cancelar"; onActivated:benchmarkController.cancel() }
                    }
                    Text { text:d.stage || "Listo para iniciar"; color:page.ink; font.pixelSize:11; Layout.fillWidth:true; elide:Text.ElideRight }
                    Rectangle { Layout.fillWidth:true; Layout.preferredHeight:8; radius:4; color:page.edge
                        Rectangle { width:parent.width*Math.max(0,Math.min(100,d.progress||0))/100; height:parent.height; radius:4; color:page.accent
                            Behavior on width { NumberAnimation {duration:120} }
                        }
                    }
                    Text { text:Math.round(d.progress||0)+" % · progreso por mediciones y etapas completadas"; color:page.muted; font.pixelSize:10 }
                }
            }
            RowLayout { Layout.fillWidth:true
                Text { text:"RESULTADOS VERIFICADOS"; color:page.ink; font.pixelSize:13; font.bold:true }
                Item {Layout.fillWidth:true}
                Text { text:"Las cifras solo se muestran después de ejecutar cada prueba"; color:page.muted; font.pixelSize:10 }
            }
            GridLayout { Layout.fillWidth:true; columns:body.width<780?1:2; columnSpacing:11; rowSpacing:11
                ResultCard { heading:"CPU · Cálculo entero"; subhead:"Trabajo medido, no puntuación Cinebench"; tint:page.cyan
                    value:page.render((result.cpu||{}).operationsPerSecond," iter/s",0)
                    detail:(result.cpu||{}).method || (result.cpu||{}).reason || "Aún no ejecutado" }
                ResultCard { heading:"RAM · Copias verificadas"; subhead:"Bloques de 8 MiB · caché incluida"; tint:page.purple
                    value:page.render((result.ram||{}).mibPerSecond," MiB/s",2)
                    detail:(result.ram||{}).method || (result.ram||{}).reason || "Aún no ejecutado" }
                ResultCard { heading:"SSD · Lectura / escritura"; subhead:"E/S de archivo temporal · fsync + SHA-256"; tint:page.diskAccent
                    value:page.render((result.ssd||{}).readMiBPerSecond," / ",1) + page.render((result.ssd||{}).writeMiBPerSecond," MiB/s",1)
                    detail:"Lectura / escritura. Influida por caché del sistema; no equivale a velocidad física directa." }
                ResultCard { heading:"GPU · Escena DirectX 11"; subhead:"Fotogramas realmente presentados · V29"; tint:page.purple
                    value:page.render(gpu.value," FPS",1)
                    detail: gpu.status === "OK" ? "1 % Low: " + page.render(gpu.one_percent_low_fps," FPS",1) + " · " + (gpu.renderer || "GPU verificada") :
                            gpu.reason || "Pendiente de ejecutar el motor gráfico real." }
            }
            GlassPanel { Layout.fillWidth:true; radius:16; color:page.panel; border.width:1; border.color:page.edge
                implicitHeight:scenesColumn.implicitHeight+30
                ColumnLayout {id:scenesColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:15; spacing:11
                    RowLayout {Layout.fillWidth:true
                        Text {text:"ESCENAS GPU DIRECTX 11"; color:page.ink; font.pixelSize:13; font.bold:true}
                        Item {Layout.fillWidth:true}
                        Text {text: page.scenes.length ? page.scenes.length + " escenas medidas" : "Sin resultados GPU"; color:page.muted; font.pixelSize:10}
                    }
                    GridLayout {Layout.fillWidth:true; columns:body.width < 780 ? 1 : 2; columnSpacing:10; rowSpacing:10
                        Repeater {model:["avenue","district","skyline","megacity"]
                            delegate:GlassPanel {id:sceneTile
                                required property string modelData
                                readonly property var reading:(page.scenes || []).find(function(x){return x.key === sceneTile.modelData}) || ({})
                                Layout.fillWidth:true; Layout.preferredHeight:85; radius:12; color:page.panel; border.width:1; border.color:page.edge
                                RowLayout { anchors.fill:parent; anchors.margins:12; spacing:12
                                    Rectangle {Layout.preferredWidth:6; Layout.preferredHeight:39; radius:3; color:page.purple; opacity:sceneTile.reading.status === "OK" ? 1 : .30}
                                    ColumnLayout {Layout.fillWidth:true; spacing:4
                                        Text {text:page.sceneTitle(sceneTile.modelData); color:page.ink; font.pixelSize:12; font.bold:true}
                                        Text {text:sceneTile.reading.status === "OK" ? "Fotogramas medidos: " + (sceneTile.reading.frames || 0) : "Pendiente"; color:page.muted; font.pixelSize:10}
                                        Text {visible:sceneTile.reading.status === "OK"
                                              text:"GPU ocupada " + page.render(typeof sceneTile.reading.gpu_busy_ratio === "number" ? sceneTile.reading.gpu_busy_ratio*100 : NaN," %",0)
                                              color:page.muted; font.pixelSize:10}
                                    }
                                    ColumnLayout {Layout.alignment:Qt.AlignRight; spacing:3
                                        Text {text:page.render(sceneTile.reading.frames_per_s," FPS",1); color:page.purple; font.pixelSize:16; font.bold:true; horizontalAlignment:Text.AlignRight}
                                        Text {text:"1% Low · " + page.render(sceneTile.reading.one_percent_low_fps," FPS",1); color:page.muted; font.pixelSize:10; horizontalAlignment:Text.AlignRight}
                                    }
                                }
                            }
                        }
                    }
                    Text {Layout.fillWidth:true; text:"Método GPU: DirectX 11 V29 · ciudad de neón nocturna con reflejo de calles mojadas, sombras de luna y luz volumétrica, HDR con MSAA 4x, bloom y ACES · render fijo 1920×1080 en cualquier pantalla · GPU de alto rendimiento · FPS = fotogramas presentados ÷ segundos reales · frametime entre Present consecutivos · 3 escenas en Rápido, 4 en Estándar/Extendido. Los resultados V29 no se comparan con V28."; color:page.muted; font.pixelSize:10; wrapMode:Text.WordWrap}
                }
            }
            GlassPanel { Layout.fillWidth:true; radius:16; color:page.panel; border.width:1; border.color:page.edge
                visible: gpu.status === "OK" || gpu.status === "PARTIAL"
                implicitHeight:conditionsColumn.implicitHeight+30
                ColumnLayout {id:conditionsColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:15; spacing:9
                    RowLayout {Layout.fillWidth:true
                        Text {text:"CONDICIONES DE LA PRUEBA GPU"; color:page.ink; font.pixelSize:13; font.bold:true}
                        Item {Layout.fillWidth:true}
                        Text {text:page.stabilityText(page.session.stability); font.pixelSize:12; font.bold:true
                              color: page.session.stability === "ESTABLE" ? "#36D6A0" : page.session.stability ? page.warning : page.muted}
                    }
                    GridLayout {Layout.fillWidth:true; columns:body.width < 780 ? 1 : 2; columnSpacing:18; rowSpacing:5
                        Text {Layout.fillWidth:true; color:page.muted; font.pixelSize:11; elide:Text.ElideRight
                              text:"GPU: " + (gpu.renderer || "N/A") + " · " + page.adapterText(gpu.adapter_selection)}
                        Text {Layout.fillWidth:true; color:page.muted; font.pixelSize:11; elide:Text.ElideRight
                              text:"Render " + (gpu.render_resolution || "N/A") + " · ventana " + (gpu.window_resolution || "N/A")}
                        Text {Layout.fillWidth:true; color:page.muted; font.pixelSize:11; elide:Text.ElideRight
                              text:"Equipo: " + (page.session.device_class === "NOTEBOOK" ? "notebook · " + (page.session.on_battery ? "con batería" : "enchufada") : page.session.device_class === "ESCRITORIO" ? "escritorio" : "N/A") + " · plan " + (page.session.power_plan || "N/A")}
                        Text {Layout.fillWidth:true; color:page.muted; font.pixelSize:11; elide:Text.ElideRight
                              text:"Límite: " + (gpu.bottleneck === "GPU" ? "GPU (resultado representativo)" : gpu.bottleneck === "CPU_O_SISTEMA" ? "CPU o sistema" : "N/A") + " · GPU ocupada " + page.render(typeof gpu.gpu_busy_ratio === "number" ? gpu.gpu_busy_ratio*100 : NaN," %",0)}
                        Text {Layout.fillWidth:true; color:page.muted; font.pixelSize:11; elide:Text.ElideRight
                              text:"Temperatura GPU máx. " + page.render(page.session.gpu_temp_max_c," °C",0) + " · reloj medio " + page.render(page.session.gpu_clock_avg_mhz," MHz",0)}
                        Text {Layout.fillWidth:true; color:page.muted; font.pixelSize:11; elide:Text.ElideRight
                              text:"Consumo medio " + page.render(page.session.gpu_power_avg_w," W",0) + " de " + page.render(page.session.gpu_power_limit_w," W",0) + " · reloj/máx. " + page.render(typeof page.session.gpu_clock_to_max_ratio === "number" ? page.session.gpu_clock_to_max_ratio*100 : NaN," %",0)}
                    }
                    Text {Layout.fillWidth:true; visible:!!page.session.sensor_status && page.session.sensor_status !== "NVIDIA_SMI"
                          text:"Sensores: " + (page.session.sensor_status || ""); color:page.muted; font.pixelSize:10; wrapMode:Text.WordWrap}
                    Repeater {model:page.sessionWarnings
                        delegate:Text {required property string modelData
                            Layout.fillWidth:true; text:"• " + modelData; color:page.warning; font.pixelSize:11; wrapMode:Text.WordWrap}
                    }
                    Text {Layout.fillWidth:true; visible:page.sessionWarnings.length === 0 && !!page.session.stability
                          text:"Sin advertencias: energía, GPU elegida y relojes en condiciones normales."; color:page.accent; font.pixelSize:11; wrapMode:Text.WordWrap}
                }
            }
            GlassPanel {Layout.fillWidth:true; implicitHeight:traceColumn.implicitHeight+28; radius:16; color:page.panel; border.width:1; border.color:page.edge
                ColumnLayout {id:traceColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:14; spacing:7
                    Text {text:"Resultados y trazabilidad"; color:page.ink; font.pixelSize:14; font.bold:true}
                    Text {Layout.fillWidth:true; text:d.resultFile ? "CPU/RAM/SSD: "+d.resultFile : "CPU/RAM/SSD: aún sin resultado guardado"; color:page.muted; font.pixelSize:10; wrapMode:Text.WrapAnywhere}
                    Text {Layout.fillWidth:true; text:d.gpuResultFile ? "GPU V29: "+d.gpuResultFile : "GPU V29: aún sin resultado válido guardado"; color:page.muted; font.pixelSize:10; wrapMode:Text.WrapAnywhere}
                    Text {Layout.fillWidth:true; text:"Las comparaciones solo son válidas para la misma metodología y configuración de prueba."; color:page.muted; font.pixelSize:10; wrapMode:Text.WordWrap}
                }
            }
            GlassPanel {
                Layout.fillWidth:true
                radius:16; color:page.panel; border.width:1; border.color:page.edge
                implicitHeight:historyColumn.implicitHeight+30
                ColumnLayout {
                    id:historyColumn
                    anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top
                    anchors.margins:15; spacing:11
                    RowLayout {
                        Layout.fillWidth:true; spacing:8
                        ColumnLayout {
                            Layout.fillWidth:true; spacing:3
                            Text {text:"HISTORIAL DE SESIONES"; color:page.ink; font.pixelSize:13; font.bold:true}
                            Text {text:page.historyRows.length + " sesiones guardadas localmente · máximo 500"; color:page.muted; font.pixelSize:10}
                        }
                        ActionButton {label:"Actualizar"; enabledAction:!d.busy; onActivated:benchmarkController.refreshHistory()}
                        ActionButton {label:"Informe PDF"; tint:page.cyan; enabledAction:!page.reportData.busy && (page.historyRows.length>0 || page.result.status==="complete" || page.gpu.status==="OK" || page.gpu.status==="PARTIAL"); onActivated:reportExporter.generateBenchmark()}
                        ActionButton {label:"Abrir PDF"; enabledAction:page.reportData.kind==="benchmark" && !!page.reportData.path; visible:page.reportData.kind==="benchmark" && !!page.reportData.path; onActivated:reportExporter.openLast()}
                        ActionButton {label:"Exportar CSV"; tint:page.cyan; primary:true; enabledAction:page.visibleHistory.length>0; onActivated:historyCsvDialog.open()}
                    }
                    RowLayout {
                        Layout.fillWidth:true; spacing:7
                        Repeater {
                            model:[{key:"all",label:"Todas"},{key:"cpu",label:"CPU · RAM · SSD"},{key:"gpu",label:"GPU"}]
                            delegate:Rectangle {
                                required property var modelData
                                Layout.preferredHeight:31
                                Layout.preferredWidth:filterText.implicitWidth+24
                                radius:9
                                color:page.historyFilter===modelData.key ? Qt.alpha(page.cyan,.16) : page.panel
                                border.width:1; border.color:page.historyFilter===modelData.key ? page.cyan : page.edge
                                Text{id:filterText; anchors.centerIn:parent; text:modelData.label; color:page.historyFilter===modelData.key ? page.cyan : page.muted; font.pixelSize:10; font.bold:page.historyFilter===modelData.key}
                                MouseArea{anchors.fill:parent; cursorShape:Qt.PointingHandCursor; onClicked:page.historyFilter=modelData.key}
                            }
                        }
                        ActionButton {label:"Carpeta de reportes"; onActivated:reportExporter.openReportsFolder()}
                        Item {Layout.fillWidth:true}
                        Text {visible:!!d.historyMessage; text:d.historyMessage||""; color:page.muted; font.pixelSize:9; Layout.maximumWidth:280; elide:Text.ElideMiddle}
                    }
                    Text {
                        visible:page.reportData.kind==="benchmark" && !!page.reportData.status
                        Layout.fillWidth:true
                        text:page.reportData.status + (page.reportData.path ? " · " + page.reportData.path : "")
                        color:page.muted; font.pixelSize:9; wrapMode:Text.WrapAnywhere
                    }
                    Text {
                        Layout.fillWidth:true
                        text:"Elige una sesión como Base y otra como Nueva. GPU solo compara mismo método, perfil y adaptador."
                        color:page.muted; font.pixelSize:9; wrapMode:Text.WordWrap
                    }
                    Text {
                        visible:page.visibleHistory.length===0
                        Layout.fillWidth:true; Layout.preferredHeight:40
                        verticalAlignment:Text.AlignVCenter
                        text:page.historyRows.length===0 ? "Aún no hay sesiones. Ejecuta un benchmark para empezar a guardar resultados." : "No hay sesiones para este filtro."
                        color:page.muted; font.pixelSize:11; wrapMode:Text.WordWrap
                    }
                    ListView {
                        id:historyList
                        visible:page.visibleHistory.length>0
                        Layout.fillWidth:true
                        Layout.preferredHeight:Math.min(330,page.visibleHistory.length*87)
                        model:page.visibleHistory
                        clip:true; spacing:7; boundsBehavior:Flickable.StopAtBounds
                        delegate:GlassPanel {
                            id:historyEntry
                            required property var modelData
                            width:historyList.width; height:80
                            radius:11; color:page.panel
                            border.width:1; border.color:page.edge
                            RowLayout {
                                anchors.fill:parent; anchors.margins:10; spacing:10
                                ColumnLayout {
                                    Layout.fillWidth:true; Layout.minimumWidth:0; spacing:4
                                    RowLayout {
                                        Layout.fillWidth:true; spacing:7
                                        Text {text:page.historyLabel(historyEntry.modelData); color:page.ink; font.pixelSize:11; font.bold:true; elide:Text.ElideRight; Layout.fillWidth:true}
                                        Text {text:historyEntry.modelData.status==="PARTIAL" ? "PARCIAL" : "OK"; color:historyEntry.modelData.status==="PARTIAL" ? page.warning : page.accent; font.pixelSize:9; font.bold:true}
                                    }
                                    Text {text:page.historyDate(historyEntry.modelData.timestamp); color:page.muted; font.pixelSize:9}
                                    Text {text:page.historyDetails(historyEntry.modelData); color:page.muted; font.pixelSize:10; elide:Text.ElideRight; Layout.fillWidth:true}
                                }
                                ColumnLayout {
                                    Layout.preferredWidth:106; spacing:5
                                    ActionButton {
                                        Layout.fillWidth:true; Layout.preferredHeight:29; implicitHeight:29; implicitWidth:100
                                        label:page.historyFirstId===historyEntry.modelData.id ? "Base ✓" : "Usar como base"
                                        tint:page.cyan; primary:page.historyFirstId===historyEntry.modelData.id
                                        onActivated:page.setHistorySelection("first",historyEntry.modelData)
                                    }
                                    ActionButton {
                                        Layout.fillWidth:true; Layout.preferredHeight:29; implicitHeight:29; implicitWidth:100
                                        label:page.historySecondId===historyEntry.modelData.id ? "Nueva ✓" : "Comparar con"
                                        tint:page.purple; primary:page.historySecondId===historyEntry.modelData.id
                                        onActivated:page.setHistorySelection("second",historyEntry.modelData)
                                    }
                                }
                            }
                        }
                        FastWheelHandler {scrollTarget:historyList}
                    }
                    GlassPanel {
                        visible:!!page.historyFirstId && !!page.historySecondId
                        Layout.fillWidth:true
                        radius:11; color:page.panel; border.width:1; border.color:page.edge
                        implicitHeight:comparisonColumn.implicitHeight+22
                        ColumnLayout {
                            id:comparisonColumn
                            anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top
                            anchors.margins:11; spacing:8
                            Text {
                                Layout.fillWidth:true
                                text:page.historyComparison.ok
                                    ? "Comparación · " + page.historyDate(page.historyComparison.firstTimestamp) + " → " + page.historyDate(page.historyComparison.secondTimestamp)
                                    : (page.historyComparison.message || "No se pueden comparar estas sesiones.")
                                color:page.historyComparison.ok ? page.ink : page.warning; font.pixelSize:10; font.bold:true; wrapMode:Text.WordWrap
                            }
                            Repeater {
                                model:page.historyComparison.metrics || []
                                delegate:RowLayout {
                                    required property var modelData
                                    Layout.fillWidth:true; spacing:8
                                    Text {Layout.fillWidth:true; text:modelData.label; color:page.muted; font.pixelSize:10}
                                    Text {text:page.render(modelData.before," "+modelData.unit,1)+" → "+page.render(modelData.after," "+modelData.unit,1); color:page.ink; font.pixelSize:10; font.bold:true}
                                    Text {Layout.preferredWidth:58; horizontalAlignment:Text.AlignRight; text:page.deltaText(modelData.deltaPct); color:typeof modelData.deltaPct==="number" ? (modelData.deltaPct>=0 ? "#36D6A0" : "#F36B75") : page.muted; font.pixelSize:10; font.bold:true}
                                }
                            }
                        }
                    }
                }
            }
            Text {Layout.fillWidth:true; text:"Precaución: el Benchmark aumenta temporalmente temperatura y consumo. La prueba GPU abre una ventana DirectX independiente y se puede cancelar. Un fallo gráfico no debe cerrar CorePulse."; color:page.muted; font.pixelSize:11; wrapMode:Text.WordWrap}
            Text {Layout.fillWidth:true; visible:!!d.error; text:d.error || ""; color:"#B16C6C"; font.pixelSize:11; wrapMode:Text.WordWrap}
            Item {Layout.preferredHeight:8}
        }
    }
}
