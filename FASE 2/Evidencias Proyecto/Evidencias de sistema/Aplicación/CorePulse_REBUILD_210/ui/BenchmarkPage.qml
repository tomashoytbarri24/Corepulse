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
    property string selectedTest: "system"
    property bool techOpen: false
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

    readonly property bool hasResult: selectedTest === "gpu"
        ? (gpu.status === "OK" || gpu.status === "PARTIAL")
        : typeof (result.cpu || {}).operationsPerSecond === "number"
    // REBUILD 197: calificación sencilla. La GPU se califica por FPS (valen
    // igual en cualquier PC); CPU, RAM y disco se comparan solo contra la
    // medición anterior del mismo equipo hasta tener referencias de varias PC.
    readonly property color good: "#36D6A0"
    readonly property color bad: "#F36B75"
    function rowsOf(kind) {
        const rows = page.historyRows.filter(function(row) { return row.kind === kind })
        if (kind !== "GPU" || rows.length === 0) return rows
        return rows.filter(function(row) { return row.profile === rows[0].profile && row.renderer === rows[0].renderer })
    }
    function nowSummary(kind) { const rows = page.rowsOf(kind); return rows.length ? (rows[0].summary || ({})) : ({}) }
    function beforeSummary(kind) { const rows = page.rowsOf(kind); return rows.length > 1 ? (rows[1].summary || ({})) : ({}) }
    function changePct(now, before) {
        if (typeof now !== "number" || typeof before !== "number" || !isFinite(now) || !isFinite(before) || before <= 0) return NaN
        return (now - before) / before * 100
    }
    // level: -1 sin referencia, 0 bien, 1 atención, 2 problema
    function trend(pct, soft, hard) {
        if (!isFinite(pct)) return {level:-1, label:"Primera medición", color:page.muted,
            text:"Quedó guardada como referencia. La próxima vez te diremos si rinde igual, mejor o peor."}
        if (pct >= 10) return {level:0, label:"Mejor que antes", color:page.good, text:"Rinde " + Math.round(pct) + " % más que tu medición anterior."}
        if (pct > -soft) return {level:0, label:"Igual que antes", color:page.good, text:"Rinde como la última vez: no hay señales de que haya empeorado."}
        if (pct > -hard) return {level:1, label:"Algo más lento", color:page.warning, text:"Rinde " + Math.round(-pct) + " % menos que antes. Puede ser calor, programas abiertos o falta de espacio."}
        return {level:2, label:"Mucho más lento", color:page.bad, text:"Rinde " + Math.round(-pct) + " % menos que antes. Algo cambió en el equipo: revisa temperatura, programas en segundo plano y espacio libre."}
    }
    function fpsGrade(fps) {
        if (typeof fps !== "number" || !isFinite(fps)) return {level:-1, segments:0, label:"Sin datos", color:page.muted, text:"Sin FPS medidos."}
        if (fps < 30) return {level:1, segments:1, label:"Lento", color:page.warning, text:"Los juegos exigentes se verán trabados; baja la calidad gráfica."}
        if (fps < 60) return {level:0, segments:2, label:"Normal", color:page.good, text:"Se puede jugar, con calidad gráfica media."}
        if (fps < 120) return {level:0, segments:3, label:"Bueno", color:page.good, text:"Juegos fluidos en 1080p."}
        return {level:0, segments:4, label:"Muy bueno", color:page.good, text:"Muy fluido, ideal para monitores de alta frecuencia."}
    }
    function lowGrade(fps, low) {
        if (typeof fps !== "number" || typeof low !== "number" || fps <= 0) return {level:-1, label:"Sin datos", color:page.muted, text:"Sin datos de los momentos más lentos."}
        const ratio = low / fps
        if (ratio < .5) return {level:1, label:"Con tirones", color:page.warning, text:"En los peores momentos cae a menos de la mitad: puede haber tirones."}
        if (ratio < .7) return {level:0, label:"Aceptable", color:page.good, text:"Hay algunas caídas, pero no deberían notarse mucho."}
        return {level:0, label:"Estable", color:page.good, text:"Los FPS se mantienen parejos, sin tirones."}
    }
    function worst(items) {
        let pick = items[0]
        for (let i = 1; i < items.length; ++i) if (items[i].level > pick.level) pick = items[i]
        return pick
    }
    function systemVerdict() {
        const n = page.nowSummary("CPU_RAM_SSD"), b = page.beforeSummary("CPU_RAM_SSD")
        const items = [
            Object.assign({part:"procesador"}, page.trend(page.changePct(n.cpu_ops_s, b.cpu_ops_s), 10, 25)),
            Object.assign({part:"memoria RAM"}, page.trend(page.changePct(n.ram_mib_s, b.ram_mib_s), 10, 25)),
            Object.assign({part:"disco"}, page.trend(page.changePct(n.ssd_read_mib_s, b.ssd_read_mib_s), 20, 40))]
        const w = page.worst(items)
        if (w.level < 0) return {level:-1, color:page.muted, title:"Primera medición guardada",
            text:"Todavía no hay con qué comparar. Vuelve a correr la prueba más adelante y te diremos si tu PC sigue rindiendo igual."}
        if (w.level === 0) return {level:0, color:page.good, title:"Tu PC está en buen estado",
            text:"Procesador, memoria y disco rinden igual o mejor que tu medición anterior."}
        return {level:w.level, color:w.color, title:w.level === 2 ? "Hay un problema de rendimiento" : "Rinde menos de lo esperado",
            text:"El " + w.part + ": " + w.text.charAt(0).toLowerCase() + w.text.slice(1)}
    }
    function gpuVerdict() {
        const n = page.nowSummary("GPU"), b = page.beforeSummary("GPU")
        const fps = typeof n.gpu_fps === "number" ? n.gpu_fps : page.gpu.value
        const low = typeof n.gpu_low_fps === "number" ? n.gpu_low_fps : page.gpu.one_percent_low_fps
        const grade = page.fpsGrade(fps)
        const items = [grade, page.lowGrade(fps, low), page.trend(page.changePct(n.gpu_fps, b.gpu_fps), 10, 25)]
        if (page.session.stability === "THROTTLING")
            items.push({level:1, color:page.warning, text:"Tu tarjeta gráfica se calentó y bajó la velocidad. Revisa ventilación y polvo."})
        if (page.session.on_battery)
            items.push({level:1, color:page.warning, text:"La notebook estaba a batería: conéctala y repite la prueba."})
        const w = page.worst(items)
        if (w.level <= 0) return {level:0, color:page.good, title:"Tu tarjeta gráfica rinde bien", text:grade.text}
        return {level:w.level, color:w.color, title:w.level === 2 ? "Hay un problema de rendimiento" : "Rinde menos de lo esperado", text:w.text}
    }
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
    component StepTitle: RowLayout {
        id: step
        property string number: ""
        property string label: ""
        Layout.fillWidth: true
        spacing: 9
        Rectangle {
            Layout.preferredWidth:24; Layout.preferredHeight:24; radius:12
            color:Qt.alpha(page.cyan,.16); border.width:1; border.color:Qt.alpha(page.cyan,.5)
            Text { anchors.centerIn:parent; text:step.number; color:page.cyan; font.pixelSize:12; font.bold:true }
        }
        Text { text:step.label; color:page.ink; font.pixelSize:14; font.bold:true; Layout.fillWidth:true }
    }
    component TestCard: GlassPanel {
        id: card
        property string testId: ""
        property string glyph: "cpu"
        property string heading: ""
        property string description: ""
        property color tint: page.accent
        default property alias extra: cardColumn.data
        readonly property bool chosen: page.selectedTest === testId
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.preferredHeight: cardColumn.implicitHeight + 30
        radius:16; color: chosen ? Qt.alpha(card.tint,.10) : page.panel
        border.width: chosen ? 2 : 1
        border.color: chosen ? card.tint : cardMouse.containsMouse ? Qt.alpha(card.tint,.45) : page.edge
        MouseArea { id:cardMouse; anchors.fill:parent; hoverEnabled:true; enabled:!d.busy; cursorShape:Qt.PointingHandCursor; onClicked:page.selectedTest = card.testId }
        ColumnLayout {
            id:cardColumn
            anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:15; spacing:10
            RowLayout { Layout.fillWidth:true; spacing:11
                Glyph { Layout.preferredWidth:34; Layout.preferredHeight:34; kind:card.glyph; ink:card.tint }
                Text { text:card.heading; color:page.ink; font.pixelSize:16; font.bold:true; Layout.fillWidth:true; elide:Text.ElideRight }
                Rectangle {
                    Layout.preferredWidth:18; Layout.preferredHeight:18; radius:9; color:"transparent"
                    border.width:2; border.color:card.chosen ? card.tint : page.edge
                    Rectangle { anchors.centerIn:parent; width:8; height:8; radius:4; color:card.tint; visible:card.chosen }
                }
            }
            Text { text:card.description; color:page.muted; font.pixelSize:11; Layout.fillWidth:true; wrapMode:Text.WordWrap }
        }
    }
    component RatingCard: GlassPanel {
        id: rating
        property string heading: ""
        property string caption: ""
        property var grade: ({label:"Sin datos", color:page.muted, text:""})
        property int segments: 0
        property string raw: ""
        property var before: undefined
        property var now: undefined
        property string unit: ""
        property int decimals: 1
        readonly property bool compare: typeof before === "number" && typeof now === "number" && before > 0
        readonly property real scaleTop: compare ? Math.max(before, now) : 1
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.preferredHeight: ratingColumn.implicitHeight + 30
        radius:16; color:page.panel; border.width:1; border.color:page.edge
        ColumnLayout {
            id: ratingColumn
            anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:15; spacing:8
            RowLayout { Layout.fillWidth:true; spacing:8
                ColumnLayout { Layout.fillWidth:true; spacing:2
                    Text { text:rating.heading; color:page.ink; font.pixelSize:14; font.bold:true; Layout.fillWidth:true; elide:Text.ElideRight }
                    Text { text:rating.caption; color:page.muted; font.pixelSize:10; Layout.fillWidth:true; elide:Text.ElideRight }
                }
                Rectangle {
                    Layout.preferredHeight:26; Layout.preferredWidth:gradeLabel.implicitWidth + 20; radius:13
                    color:Qt.alpha(rating.grade.color, .14); border.width:1; border.color:Qt.alpha(rating.grade.color, .55)
                    Text { id:gradeLabel; anchors.centerIn:parent; text:rating.grade.label; color:rating.grade.color; font.pixelSize:11; font.bold:true }
                }
            }
            RowLayout { visible:rating.segments > 0; Layout.fillWidth:true; spacing:4
                Repeater { model:4
                    delegate: Rectangle { required property int index
                        Layout.fillWidth:true; Layout.preferredHeight:8; radius:4
                        color: index < rating.segments ? rating.grade.color : page.edge }
                }
            }
            RowLayout { visible:rating.segments > 0; Layout.fillWidth:true
                Repeater { model:["Lento","Normal","Bueno","Muy bueno"]
                    delegate: Text { required property string modelData; Layout.fillWidth:true; text:modelData; color:page.muted; font.pixelSize:9; horizontalAlignment:Text.AlignHCenter }
                }
            }
            Text { text:rating.grade.text; color:page.ink; font.pixelSize:12; Layout.fillWidth:true; wrapMode:Text.WordWrap }
            GridLayout { visible:rating.compare; Layout.fillWidth:true; columns:3; columnSpacing:8; rowSpacing:4
                Text { text:"Antes"; color:page.muted; font.pixelSize:10; Layout.preferredWidth:40 }
                Rectangle { Layout.fillWidth:true; Layout.preferredHeight:7; radius:4; color:page.edge
                    Rectangle { width:parent.width * (rating.compare ? rating.before / rating.scaleTop : 0); height:parent.height; radius:4; color:page.muted } }
                Text { text:page.render(rating.before, "", rating.decimals); color:page.muted; font.pixelSize:10; Layout.preferredWidth:78; horizontalAlignment:Text.AlignRight }
                Text { text:"Ahora"; color:page.ink; font.pixelSize:10; Layout.preferredWidth:40 }
                Rectangle { Layout.fillWidth:true; Layout.preferredHeight:7; radius:4; color:page.edge
                    Rectangle { width:parent.width * (rating.compare ? rating.now / rating.scaleTop : 0); height:parent.height; radius:4; color:rating.grade.color } }
                Text { text:page.render(rating.now, "", rating.decimals); color:page.ink; font.pixelSize:10; font.bold:true; Layout.preferredWidth:78; horizontalAlignment:Text.AlignRight }
            }
            Text { text:rating.raw; color:page.muted; font.pixelSize:10; Layout.fillWidth:true; elide:Text.ElideRight }
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
                Glyph { Layout.preferredWidth:36; Layout.preferredHeight:36; kind:"gauge"; ink:page.cyan }
                ColumnLayout { Layout.fillWidth:true; spacing:4
                    Text { text:"Benchmark"; color:page.ink; font.pixelSize:21; font.bold:true }
                    Text { text:"Elige una prueba, iníciala y mira el resultado de tu equipo"; color:page.muted; font.pixelSize:11; Layout.fillWidth:true; elide:Text.ElideRight }
                }
                HeaderAction { label:"Volver"; onActivated:page.goBack() }
            }

            // REBUILD 197: flujo en tres pasos (elegir, iniciar, ver resultado);
            // lo técnico queda en «Detalles técnicos», plegado por defecto.
            StepTitle { number:"1"; label:"Elige la prueba" }
            GridLayout {
                Layout.fillWidth:true
                columns:body.width < 760 ? 1 : 2
                rowSpacing:11; columnSpacing:11
                TestCard {
                    testId:"system"; glyph:"cpu"; tint:page.cyan
                    heading:"Procesador, RAM y disco"
                    description:"Mide qué tan rápido calcula tu CPU, copia datos tu memoria y lee y escribe tu disco."
                }
                TestCard {
                    testId:"gpu"; glyph:"gpu"; tint:page.purple
                    heading:"Tarjeta gráfica"
                    description:"Dibuja una ciudad 3D (GPU · DirectX 11 V29) y cuenta cuántos FPS logra tu GPU."
                    RowLayout { Layout.fillWidth:true; spacing:6; visible:page.selectedTest === "gpu"
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
                }
            }

            StepTitle { number:"2"; label:d.busy ? "Prueba en curso" : "Inicia la prueba" }
            Rectangle {
                id:startButton
                visible:!d.busy
                Layout.fillWidth:true; Layout.preferredHeight:54
                radius:14
                readonly property color tint:page.selectedTest === "gpu" ? page.purple : page.cyan
                color:Qt.alpha(startButton.tint, startMouse.containsMouse ? .30 : .20)
                border.width:1; border.color:Qt.alpha(startButton.tint,.75)
                Text {
                    anchors.centerIn:parent
                    text:page.selectedTest === "gpu" ? "Iniciar prueba de tarjeta gráfica" : "Iniciar prueba de procesador, RAM y disco"
                    color:page.ink; font.pixelSize:15; font.bold:true
                }
                MouseArea {
                    id:startMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor
                    onClicked: page.selectedTest === "gpu" ? benchmarkController.startGpu(page.gpuProfile) : benchmarkController.start()
                }
            }
            GlassPanel {
                visible:!!d.busy
                Layout.fillWidth:true; Layout.preferredHeight:112
                radius:16; color:page.panel; border.width:1; border.color:page.edge
                ColumnLayout { anchors.fill:parent; anchors.margins:15; spacing:9
                    RowLayout { Layout.fillWidth:true
                        Text { text:d.stage || "Preparando la prueba…"; color:page.ink; font.pixelSize:13; font.bold:true; Layout.fillWidth:true; elide:Text.ElideRight }
                        Text { text:Math.round(d.progress||0)+" %"; color:page.accent; font.pixelSize:16; font.bold:true }
                        ActionButton { label:"Cancelar"; onActivated:benchmarkController.cancel() }
                    }
                    Rectangle { Layout.fillWidth:true; Layout.preferredHeight:10; radius:5; color:page.edge
                        Rectangle { width:parent.width*Math.max(0,Math.min(100,d.progress||0))/100; height:parent.height; radius:5; color:page.accent
                            Behavior on width { NumberAnimation {duration:120} }
                        }
                    }
                    Text { text:"No uses el equipo mientras mide para que el resultado sea fiel. Puedes cancelar cuando quieras."; color:page.muted; font.pixelSize:10; Layout.fillWidth:true; elide:Text.ElideRight }
                }
            }
            Text {Layout.fillWidth:true; visible:!!d.error; text:d.error || ""; color:"#B16C6C"; font.pixelSize:11; wrapMode:Text.WordWrap}

            StepTitle { number:"3"; label:"Resultado" }
            Text {
                visible:!page.hasResult
                Layout.fillWidth:true
                text:"Todavía no hay resultado de esta prueba. Iníciala y aquí verás si tu PC anda bien."
                color:page.muted; font.pixelSize:12; wrapMode:Text.WordWrap
            }
            GlassPanel {
                id: verdictPanel
                visible:page.hasResult
                readonly property var verdict: page.selectedTest === "gpu" ? page.gpuVerdict() : page.systemVerdict()
                Layout.fillWidth:true; Layout.preferredHeight:verdictColumn.implicitHeight + 32
                radius:16; color:Qt.alpha(verdictPanel.verdict.color, .09); border.width:1; border.color:Qt.alpha(verdictPanel.verdict.color, .55)
                RowLayout { anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:16; spacing:14
                    Rectangle { Layout.preferredWidth:44; Layout.preferredHeight:44; Layout.alignment:Qt.AlignTop; radius:22
                        color:Qt.alpha(verdictPanel.verdict.color, .18); border.width:2; border.color:verdictPanel.verdict.color
                        Text { anchors.centerIn:parent; color:verdictPanel.verdict.color; font.pixelSize:21; font.bold:true
                            text:verdictPanel.verdict.level === 0 ? "✓" : verdictPanel.verdict.level < 0 ? "i" : "!" } }
                    ColumnLayout { id:verdictColumn; Layout.fillWidth:true; spacing:5
                        Text { text:verdictPanel.verdict.title; color:page.ink; font.pixelSize:18; font.bold:true; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                        Text { text:verdictPanel.verdict.text; color:page.muted; font.pixelSize:12; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                        Repeater { model:page.selectedTest === "gpu" ? page.sessionWarnings.slice(0, 3) : []
                            delegate: Text { required property string modelData; Layout.fillWidth:true; text:"• " + modelData; color:page.warning; font.pixelSize:11; wrapMode:Text.WordWrap }
                        }
                    }
                }
            }
            GridLayout { Layout.fillWidth:true; columns:body.width<780?1:3; columnSpacing:11; rowSpacing:11
                visible:page.hasResult && page.selectedTest === "system"
                readonly property var n: page.nowSummary("CPU_RAM_SSD")
                readonly property var b: page.beforeSummary("CPU_RAM_SSD")
                RatingCard { heading:"Procesador"; caption:"Velocidad de cálculo en un núcleo"
                    grade:page.trend(page.changePct(parent.n.cpu_ops_s, parent.b.cpu_ops_s), 10, 25)
                    before:parent.b.cpu_ops_s; now:parent.n.cpu_ops_s; decimals:0
                    raw:"Medido: " + page.render((result.cpu||{}).operationsPerSecond," iter/s",0) }
                RatingCard { heading:"Memoria RAM"; caption:"Velocidad para mover datos"
                    grade:page.trend(page.changePct(parent.n.ram_mib_s, parent.b.ram_mib_s), 10, 25)
                    before:parent.b.ram_mib_s; now:parent.n.ram_mib_s; decimals:0
                    raw:"Medido: " + page.render((result.ram||{}).mibPerSecond," MiB/s",0) }
                RatingCard { heading:"Disco"; caption:"Velocidad para abrir y guardar archivos"
                    grade:page.trend(page.changePct(parent.n.ssd_read_mib_s, parent.b.ssd_read_mib_s), 20, 40)
                    before:parent.b.ssd_read_mib_s; now:parent.n.ssd_read_mib_s; decimals:0
                    raw:"Medido: lectura " + page.render((result.ssd||{}).readMiBPerSecond," · escritura ",0) + page.render((result.ssd||{}).writeMiBPerSecond," MiB/s",0) }
            }
            GridLayout { Layout.fillWidth:true; columns:body.width<780?1:3; columnSpacing:11; rowSpacing:11
                visible:page.hasResult && page.selectedTest === "gpu"
                readonly property var n: page.nowSummary("GPU")
                readonly property var b: page.beforeSummary("GPU")
                readonly property real fps: typeof n.gpu_fps === "number" ? n.gpu_fps : gpu.value
                RatingCard { heading:"Fluidez en juegos"; caption:"GPU · Escena DirectX 11 a 1080p"
                    grade:page.fpsGrade(parent.fps); segments:Math.max(1, page.fpsGrade(parent.fps).segments)
                    raw:"Promedio medido: " + page.render(gpu.value," FPS",1) }
                RatingCard { heading:"Tirones"; caption:"Qué pasa en los momentos más exigentes"
                    grade:page.lowGrade(parent.fps, typeof parent.n.gpu_low_fps === "number" ? parent.n.gpu_low_fps : gpu.one_percent_low_fps)
                    raw:"1 % Low: " + page.render(gpu.one_percent_low_fps," FPS",1) }
                RatingCard { heading:"Comparado con antes"; caption:"Misma prueba, perfil y tarjeta gráfica"
                    grade:page.trend(page.changePct(parent.n.gpu_fps, parent.b.gpu_fps), 10, 25)
                    before:parent.b.gpu_fps; now:parent.n.gpu_fps; decimals:1
                    raw:gpu.renderer || "" }
            }

            Rectangle {
                Layout.fillWidth:true; Layout.preferredHeight:44
                radius:12; color:techMouse.containsMouse ? page.raised : page.panel
                border.width:1; border.color:page.edge
                RowLayout { anchors.fill:parent; anchors.leftMargin:15; anchors.rightMargin:15
                    Text { text:"Detalles técnicos"; color:page.ink; font.pixelSize:13; font.bold:true; Layout.fillWidth:true }
                    Text { text:"Escenas, condiciones, método y archivos"; color:page.muted; font.pixelSize:10 }
                    Text { text:page.techOpen ? "−" : "+"; color:page.muted; font.pixelSize:18; font.bold:true }
                }
                MouseArea { id:techMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; onClicked:page.techOpen = !page.techOpen }
            }
            ColumnLayout {
                visible:page.techOpen
                Layout.fillWidth:true; spacing:16
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
                        clip:true; spacing:7; boundsBehavior:Flickable.StopAtBounds; interactive:false
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 7 }
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
            Item {Layout.preferredHeight:8}
        }
    }
}
