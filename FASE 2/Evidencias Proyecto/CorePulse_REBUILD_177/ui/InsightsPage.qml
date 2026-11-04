import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    property string section: "alerts"
    readonly property var theme: themeManager.palette
    readonly property var info: monitoringInsights && monitoringInsights.data ? monitoringInsights.data : ({samples:[], events:[], active:[], lastUpdate:"N/A", status:"N/A"})
    readonly property var samples: info.samples || []
    readonly property var comparisonSamples: info.comparisonSamples || []
    readonly property var sessions: info.sessions || []
    readonly property var selectedSession: info.selectedSession || ({})
    readonly property var comparisonSession: info.comparisonSession || ({})
    // Tendencias dibuja exclusivamente muestras verificables persistidas cada 30 s.
    // No se añade un tramo de telemetría por segundo ni se rellenan valores N/A.
    readonly property var active: info.active || []
    readonly property var events: info.events || []
    readonly property string title: section === "trends" ? "Tendencias" : section === "alert_history" ? "Historial de alertas" : "Alertas técnicas"
    property bool confirmClear: false

    function sessionTime(ts) {
        if (typeof ts !== "number" || !isFinite(ts) || ts <= 0) return "N/A"
        const date = new Date(ts * 1000)
        function two(number) { return number < 10 ? "0" + number : String(number) }
        return two(date.getDate()) + "/" + two(date.getMonth()+1) + "/" + date.getFullYear()
               + " · " + two(date.getHours()) + ":" + two(date.getMinutes()) + ":" + two(date.getSeconds())
    }
    function sessionEnd(session) {
        if (session && session.current) return "En curso"
        return session && typeof session.endTs === "number" && isFinite(session.endTs)
            ? sessionTime(session.endTs) : "N/A"
    }

    FastFlickable {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight + 12
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: content
            width: pageScroll.width
            height: page.section === "trends" ? implicitHeight : pageScroll.height
            spacing: 12
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Rectangle { width: 44; height: 44; radius: 13; color: page.theme.panelRaised
                    Glyph { anchors.centerIn: parent; width: 23; height: 23; kind: page.section === "trends" ? "trend_up" : page.section === "alert_history" ? "history" : "bell_alert"; ink: page.theme.accent }
                }
                ColumnLayout { Layout.fillWidth: true; spacing: 3
                    Text { text: page.title; color: page.theme.ink; font.pixelSize: 22; font.bold: true }
                    Text { text: page.section === "trends" ? "Inicio, cierre e historial de uso del computador." : "Cambios de estado derivados de los indicadores verificables del Centro de salud."; color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
                Rectangle {
                    Layout.preferredWidth: 104; Layout.preferredHeight: 36; radius: 11
                    color: backMouse.containsMouse ? page.theme.panel : page.theme.panelRaised
                    border.width: 1; border.color: page.theme.panelBorder
                    Text { anchors.centerIn: parent; text: "Volver"; color: page.theme.ink; font.pixelSize: 11; font.bold: true }
                    MouseArea { id: backMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.goBack() }
                }
                Rectangle {
                    Layout.preferredWidth: 112; Layout.preferredHeight: 36; radius: 11
                    color: refreshMouse.containsMouse?Qt.lighter(themeManager.palette.action,1.16):themeManager.palette.action; border.width: 1; border.color: themeManager.palette.action
                    Text { anchors.centerIn: parent; text: "Actualizar"; color: themeManager.palette.actionText; font.pixelSize: 11; font.bold: true }
                    MouseArea { id: refreshMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: monitoringInsights.refresh() }
                }
                Rectangle {
                    visible: page.section === "alert_history"
                    Layout.preferredWidth: 128; Layout.preferredHeight: 36; radius: 11
                    color: clearMouse.containsMouse ? "#39272D" : page.theme.panelRaised
                    border.width: 1; border.color: clearMouse.containsMouse ? "#A85864" : page.theme.panelBorder
                    Text { anchors.centerIn: parent; text: "Limpiar alertas"; color: "#F0A2A8"; font.pixelSize: 10; font.bold: true }
                    MouseArea { id: clearMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.confirmClear = true }
                }
            }
            Text { visible: page.section !== "trends"; Layout.fillWidth: true; text: "Estado: " + info.status + " · Última muestra guardada: " + info.lastUpdate; color: page.theme.muted; font.pixelSize: 10; elide: Text.ElideRight }
            RowLayout {
                visible: page.section === "trends"
                Layout.fillWidth: true; spacing: 10
                Repeater {
                    model: [{label: "Inicio de Windows", value: page.sessionTime(page.selectedSession.bootTs)},
                            {label: "Cierre de Windows", value: page.sessionEnd(page.selectedSession)}]
                    delegate: GlassPanel {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 76; radius: 13
                        color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                        ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 5
                            Text { text: modelData.label; color: page.theme.muted; font.pixelSize: 11 }
                            Text { text: modelData.value; color: page.theme.ink; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                    }
                }
            }
            Text { visible: page.section === "alert_history" && Boolean(info.alertHistoryStatus); Layout.fillWidth: true; text: info.alertHistoryStatus || ""; color: page.theme.accent; font.pixelSize: 10 }

            GlassPanel {
                visible: page.section === "trends"
                Layout.fillWidth: true; Layout.preferredHeight: Math.max(230, Math.min(340, page.height * 0.46)); radius: 15
                color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder
                Canvas {
                    id: trendCanvas; anchors.fill: parent; anchors.margins: 16
                    onPaint: {
                        const ctx = getContext("2d"); ctx.reset()
                        const w = width, h = height
                        ctx.strokeStyle = page.theme.panelBorder; ctx.lineWidth = 1
                        for (let g = 0; g <= 4; ++g) {
                            const y = 4 + (h - 8) * g / 4
                            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
                        }
                        const series = [{key:"cpu",color:"#4EDDC8"},{key:"gpu",color:"#B48BFA"},{key:"ram",color:"#68A9F5"},{key:"disk",color:"#E9B86B"}]
                        function timeline(rows) {
                            if (!rows || !rows.length)
                                return {positions: [], gapLimit: 95}
                            let gaps = []
                            for (let i = 1; i < rows.length; ++i) {
                                const dt = rows[i].ts - rows[i - 1].ts
                                if (dt > 0)
                                    gaps.push(dt)
                            }
                            gaps.sort(function(a, b) { return a - b })
                            const typical = gaps.length ? gaps[Math.floor(gaps.length / 2)] : 30
                            const gapLimit = Math.max(95, typical * 2.5)
                            // Comprime periodos largos donde CorePulse estuvo cerrado.
                            // La sesión sigue siendo la misma, pero el gráfico prioriza
                            // la lectura continua de las muestras reales disponibles.
                            const displayGap = Math.max(18, Math.min(54, typical * 1.35))
                            let effective = [0]
                            let cursor = 0
                            for (let i = 1; i < rows.length; ++i) {
                                const dt = Math.max(0, rows[i].ts - rows[i - 1].ts)
                                cursor += dt > gapLimit ? displayGap : dt
                                effective.push(cursor)
                            }
                            const span = Math.max(1, effective.length ? effective[effective.length - 1] : 1)
                            let positions = []
                            for (let i = 0; i < effective.length; ++i)
                                positions.push(rows.length === 1 ? w / 2 : w * effective[i] / span)
                            return {positions: positions, gapLimit: gapLimit}
                        }
                        function plot(rows, seriesItem, alpha) {
                            if (!rows || !rows.length) return
                            const map = timeline(rows)
                            ctx.strokeStyle = seriesItem.color
                            ctx.lineWidth = alpha === 1 ? 2 : 1.5
                            ctx.globalAlpha = alpha
                            ctx.setLineDash([])
                            ctx.beginPath()
                            let lastValid = null
                            for (let i = 0; i < rows.length; ++i) {
                                const v = rows[i][seriesItem.key]
                                if (typeof v !== "number" || !isFinite(v) || v < 0 || v > 100) {
                                    // Ausencia del sensor: no se inventa ni conecta un valor.
                                    ctx.stroke(); ctx.beginPath(); lastValid = null
                                    continue
                                }
                                const x = map.positions[i]
                                const y = 4 + (h - 8) * (1 - v / 100)
                                const gap = lastValid !== null && rows[i].ts - rows[lastValid.index].ts > map.gapLimit
                                if (gap) {
                                    // El tramo discontinuo une dos puntos reales separados por un
                                    // intervalo NO monitoreado; no genera lecturas intermedias.
                                    ctx.stroke(); ctx.beginPath()
                                    ctx.globalAlpha = alpha * 0.35
                                    ctx.setLineDash([3, 5])
                                    ctx.moveTo(lastValid.x, lastValid.y)
                                    ctx.lineTo(x, y)
                                    ctx.stroke()
                                    ctx.globalAlpha = alpha
                                    ctx.setLineDash([])
                                    ctx.beginPath(); ctx.moveTo(x, y)
                                } else if (lastValid === null) {
                                    ctx.moveTo(x, y)
                                } else {
                                    ctx.lineTo(x, y)
                                }
                                lastValid = {index: i, x: x, y: y}
                            }
                            ctx.stroke()
                            ctx.setLineDash([])
                            ctx.globalAlpha = 1
                        }
                        for (let s = 0; s < series.length; ++s) {
                            plot(page.samples, series[s], 1)
                            // La comparación es tenue y usa progreso relativo dentro de su sesión.
                            if (page.comparisonSession.id) plot(page.comparisonSamples, series[s], 0.45)
                        }
                    }
                    property string lastPlottedSignature: ""
                    function sampleSignature() {
                        const first = page.samples.length ? Number(page.samples[0].ts) : 0
                        const last = page.samples.length ? Number(page.samples[page.samples.length-1].ts) : 0
                        const other = page.comparisonSamples.length ? Number(page.comparisonSamples[page.comparisonSamples.length-1].ts) : 0
                        return page.info.selectedSessionId + ":" + page.info.comparisonSessionId + ":" + first + ":" + last + ":" + other
                    }
                    Connections {
                        target: monitoringInsights
                        function onChanged() {
                            if (page.section === "trends" && trendCanvas.sampleSignature() !== trendCanvas.lastPlottedSignature) {
                                trendCanvas.lastPlottedSignature = trendCanvas.sampleSignature()
                                trendCanvas.requestPaint()
                            }
                        }
                    }
                    Component.onCompleted: {
                        lastPlottedSignature = sampleSignature()
                        requestPaint()
                    }
                }
            }
            RowLayout {
                visible: page.section === "trends"
                Layout.fillWidth: true; spacing: 13
                Repeater { model: [{text:"CPU", color:"#4EDDC8"},{text:"GPU", color:"#B48BFA"},{text:"RAM", color:"#68A9F5"},{text:"Disco", color:"#E9B86B"}]
                    delegate: Text { required property var modelData; text: "● " + modelData.text; color: modelData.color; font.pixelSize: 10 }
                }
                Item { Layout.fillWidth: true }
                Text { text: "- - Sin lecturas"; color: page.theme.muted; font.pixelSize: 10 }
            }
            Text { visible: page.section === "trends" && page.samples.length === 0; Layout.fillWidth: true; text: "Aún no hay muestras verificadas para esta sesión. CorePulse registra lecturas locales cada 30 segundos mientras está abierto."; color: page.theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            RowLayout {
                visible: page.section === "trends" && Boolean(page.comparisonSession.id)
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: "Comparando sesiones"; color: page.theme.muted; font.pixelSize: 10 }
                Rectangle {
                    Layout.preferredWidth: 125; Layout.preferredHeight: 30; radius: 9
                    color: page.theme.panelRaised
                    Text { anchors.centerIn: parent; text: "Quitar comparación"; color: page.theme.ink; font.pixelSize: 10 }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: monitoringInsights.clearComparison() }
                }
            }
            GlassPanel {
                visible: page.section === "trends" && Boolean(page.selectedSession.id)
                Layout.fillWidth: true
                Layout.preferredHeight: sessionAssessment.implicitHeight + 26
                radius: 13
                color: page.theme.panel
                border.width: 1; border.color: page.theme.panelBorder
                ColumnLayout {
                    id: sessionAssessment
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.margins: 13; spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Text { Layout.fillWidth: true; text: "Estado de esta sesión"; color: page.theme.ink; font.pixelSize: 13; font.bold: true }
                        Text {
                            text: page.selectedSession.healthLabel || "Datos insuficientes"
                            color: page.selectedSession.healthLevel === "attention" ? "#E9B86B" :
                                   page.selectedSession.healthLevel === "ok" ? "#4EDDC8" : page.theme.muted
                            font.bold: true; font.pixelSize: 12
                        }
                    }
                    Repeater {
                        model: page.selectedSession.findings || []
                        delegate: Text {
                            required property var modelData
                            Layout.fillWidth: true
                            text: "• " + modelData
                            color: page.theme.ink; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                    }
                    Text {
                        visible: !(page.selectedSession.findings || []).length
                        Layout.fillWidth: true
                        text: "Sin alertas registradas en las lecturas disponibles. Los datos no medidos no se evalúan."
                        color: page.theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                    }
                }
            }
            Text {
                visible: page.section === "trends"
                text: "HISTORIAL DE SESIONES"
                color: page.theme.ink; font.pixelSize: 15; font.bold: true; Layout.topMargin: 14
            }
            Repeater {
                model: page.section === "trends" ? page.sessions : []
                delegate: GlassPanel {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: sessionCard.implicitHeight + 24
                    radius: 13
                    color: page.theme.panel; border.width: 1
                    border.color: modelData.id === page.info.selectedSessionId ? page.theme.accent : page.theme.panelBorder
                    RowLayout {
                        id: sessionCard
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 12; spacing: 11
                        ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 5
                            Text {
                                Layout.fillWidth: true; elide: Text.ElideRight
                                text: "Inicio:  " + page.sessionTime(modelData.bootTs)
                                color: page.theme.ink; font.pixelSize: 12; font.bold: true
                            }
                            Text {
                                Layout.fillWidth: true; elide: Text.ElideRight
                                text: "Cierre:  " + page.sessionEnd(modelData)
                                color: page.theme.muted; font.pixelSize: 11
                            }
                            Text {
                                Layout.fillWidth: true; elide: Text.ElideRight
                                text: "Estado: " + (modelData.healthLabel || "Datos insuficientes")
                                color: modelData.healthLevel === "attention" ? "#E9B86B" : page.theme.muted
                                font.pixelSize: 11
                            }
                        }
                        Rectangle {
                            Layout.preferredWidth: 76; Layout.preferredHeight: 33; radius: 9
                            color: sessionSelect.containsMouse ? page.theme.panelRaised : page.theme.panel
                            border.width: 1; border.color: page.theme.panelBorder
                            Text { anchors.centerIn: parent; text: modelData.id === page.info.selectedSessionId ? "Viendo" : "Ver"; color: page.theme.ink; font.pixelSize: 10 }
                            MouseArea { id: sessionSelect; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: monitoringInsights.selectSession(modelData.id) }
                        }
                        Rectangle {
                            Layout.preferredWidth: 87; Layout.preferredHeight: 33; radius: 9
                            color: comparisonMouse.containsMouse ? page.theme.panelRaised : page.theme.panel
                            border.width: 1; border.color: page.theme.panelBorder
                            opacity: modelData.id === page.info.selectedSessionId ? 0.45 : 1
                            Text { anchors.centerIn: parent; text: modelData.id === page.info.comparisonSessionId ? "Comparando" : "Comparar"; color: page.theme.ink; font.pixelSize: 10 }
                            MouseArea { id: comparisonMouse; anchors.fill: parent; hoverEnabled: true; enabled: modelData.id !== page.info.selectedSessionId; cursorShape: Qt.PointingHandCursor; onClicked: monitoringInsights.compareSession(modelData.id) }
                        }
                    }
                }
            }
            Text {
                visible: page.section === "trends" && page.sessions.length === 0
                Layout.fillWidth: true
                text: "Aún no hay sesiones para mostrar."
                color: page.theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
            }
            Text { visible: page.section === "alerts"; Layout.fillWidth: true; text: "ACTIVAS · " + page.active.length; color: page.theme.ink; font.pixelSize: 13; font.bold: true }
            Text { visible: page.section === "alert_history"; Layout.fillWidth: true; text: "TRANSICIONES RECIENTES · " + page.events.length; color: page.theme.ink; font.pixelSize: 13; font.bold: true }
            FastFlickable {
                visible: page.section !== "trends"
                Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: width
                contentHeight: rows.implicitHeight; clip: true
                ColumnLayout {
                    id: rows; width: parent.width; spacing: 8
                    Repeater {
                        model: page.section === "alerts" ? page.active : page.events
                        delegate: GlassPanel {
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: rowContents.implicitHeight + 24; radius: 13
                            color: page.theme.panel; border.width: 1; border.color: modelData.state === "critical" ? "#A85864" : modelData.state === "attention" ? "#9B7845" : page.theme.panelBorder
                            ColumnLayout { id: rowContents; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 12; spacing: 5
                                RowLayout { Layout.fillWidth: true
                                    Text { text: modelData.title || modelData.key || "Indicador"; color: page.theme.ink; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: String(modelData.state || "N/A").toUpperCase(); color: modelData.state === "critical" ? "#ED8A92" : modelData.state === "attention" ? "#EBC277" : page.theme.muted; font.pixelSize: 9; font.bold: true }
                                }
                                Text { text: (modelData.value || "N/A") + " · " + (modelData.detail || ""); color: page.theme.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                Text { visible: page.section === "alert_history"; text: (modelData.source || "N/A") + " · " + new Date((modelData.ts || 0) * 1000).toLocaleString(); color: page.theme.muted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            }
                        }
                    }
                    Text {
                        visible: page.section === "alerts" ? page.active.length === 0 : page.events.length === 0
                        text: page.section === "alerts" ? "No hay alertas activas en los indicadores consultados." : "No hay transiciones guardadas todavía."
                        color: page.theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
    Item {
        visible: page.confirmClear
        z: 50
        anchors.fill: parent
        Rectangle { anchors.fill: parent; color: "#B9000000" }
        MouseArea { anchors.fill: parent }
        GlassPanel {
            width: Math.max(1, Math.min(parent.width - 28, 450))
            height: clearDialogColumn.implicitHeight + 34
            anchors.centerIn: parent
            radius: 17
            color: page.theme.panel
            border.width: 1
            border.color: page.theme.panelBorder
            ColumnLayout {
                id: clearDialogColumn
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 17; spacing: 12
                Text { text: "Limpiar historial de alertas"; color: page.theme.ink; font.pixelSize: 16; font.bold: true }
                Text { Layout.fillWidth: true; text: "Se borrarán las transiciones guardadas en este equipo. Las alertas que sigan activas continuarán visibles en Alertas técnicas."; color: page.theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        Layout.preferredWidth: 96; Layout.preferredHeight: 34; radius: 9
                        color: page.theme.panelRaised
                        Text { anchors.centerIn: parent; text: "Cancelar"; color: page.theme.ink; font.pixelSize: 10 }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.confirmClear = false }
                    }
                    Rectangle {
                        Layout.preferredWidth: 124; Layout.preferredHeight: 34; radius: 9
                        color: "#39272D"; border.width: 1; border.color: "#A85864"
                        Text { anchors.centerIn: parent; text: "Limpiar"; color: "#F0A2A8"; font.pixelSize: 10; font.bold: true }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { monitoringInsights.clearAlertHistory(); page.confirmClear = false } }
                    }
                }
            }
        }
    }
}
