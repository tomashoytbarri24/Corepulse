import QtQuick
import QtQuick.Controls

Item {
    id: page
    signal goBack()
    property string section: "sessions"
    property string draftPlan: ""
    property string draftCorner: "inherit"
    property string draftTemps: "inherit"

    readonly property var sessionState: gameSessions.data || ({})
    readonly property var selected: sessionState.detail || ({})
    readonly property var palette: themeManager.palette
    readonly property color ink: palette.ink
    readonly property color muted: palette.muted
    readonly property color edge: palette.panelBorder
    readonly property color accent: palette.cyan
    readonly property color panel: palette.panel
    readonly property color raised: palette.panelRaised

    function value(number, suffix, digits) {
        return typeof number === "number" && isFinite(number) ? Number(number).toFixed(digits || 0) + suffix : "N/A"
    }
    function timeLabel(seconds) {
        if (typeof seconds !== "number" || !isFinite(seconds)) return "N/A"
        return new Date(seconds * 1000).toLocaleString(Qt.locale("es_CL"), "dd/MM/yyyy hh:mm")
    }
    function resetProfile() {
        const profile = sessionState.profile || {}
        draftPlan = profile.plan_guid || ""
        draftCorner = profile.corner || "inherit"
        draftTemps = profile.temperatures || "inherit"
    }
    Component.onCompleted: resetProfile()
    Connections {
        target: gameSessions
        function onChanged() { fpsChart.requestPaint() }
    }

    component ActionButton: Rectangle {
        id: action
        property string label: ""
        property bool selected: false
        property bool enabled: true
        signal clicked()
        implicitWidth: Math.max(98, textItem.implicitWidth + 30)
        implicitHeight: 38
        radius: 10
        color: selected ? Qt.alpha(page.accent, 0.18) : page.raised
        border.color: selected ? page.accent : page.edge
        border.width: 1
        opacity: enabled ? 1 : 0.45
        Text {
            id: textItem
            anchors.centerIn: parent
            text: action.label
            color: action.selected ? page.accent : page.ink
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        MouseArea {
            anchors.fill: parent
            enabled: action.enabled
            cursorShape: Qt.PointingHandCursor
            onClicked: action.clicked()
        }
    }

    Column {
        anchors.fill: parent
        spacing: 15

        Row {
            width: parent.width
            height: 56
            spacing: 14
            Glyph { width: 38; height: 38; y: 7; kind: "game_history"; ink: page.accent }
            Column {
                width: Math.max(200, parent.width - 334)
                spacing: 3
                Text { text: "Sesiones de juego"; color: page.ink; font.pixelSize: 26; font.weight: Font.Bold }
                Text { text: "FPS reales, perfiles e incidencias de cada partida"; color: page.muted; font.pixelSize: 13 }
            }
            ActionButton { width: 120; label: "Actualizar"; onClicked: gameSessions.refresh() }
            ActionButton { width: 100; label: "Volver"; onClicked: page.goBack() }
        }

        GlassPanel {
            width: parent.width; height: 86; radius: 16
            Row {
                anchors.fill: parent; anchors.margins: 18; spacing: 20
                Column {
                    width: Math.max(180, parent.width * 0.35)
                    spacing: 5
                    Text { text: sessionState.active ? "PARTIDA EN CURSO" : "SIN PARTIDA ACTIVA"; color: page.accent; font.pixelSize: 11; font.weight: Font.Bold }
                    Text { text: sessionState.active ? sessionState.activeName : "El historial se guardará al detectar un juego"; color: page.ink; font.pixelSize: 17; font.weight: Font.DemiBold; elide: Text.ElideRight; width: parent.width }
                }
                Rectangle { width: 1; height: 45; color: page.edge }
                Column {
                    width: Math.max(175, parent.width * 0.21); spacing: 5
                    Text { text: "SESIONES GUARDADAS"; color: page.muted; font.pixelSize: 11 }
                    Text { text: (sessionState.sessions || []).length; color: page.ink; font.pixelSize: 22; font.weight: Font.Bold }
                }
                Column {
                    width: Math.max(190, parent.width * 0.26); spacing: 5
                    Text { text: "PLAN AUTOMÁTICO"; color: page.muted; font.pixelSize: 11 }
                    Text { text: sessionState.autoPowerStatus || "ESPERANDO"; color: page.ink; font.pixelSize: 16; font.weight: Font.DemiBold }
                }
            }
        }

        Row {
            height: 41; spacing: 9
            ActionButton { label: "Partidas"; selected: page.section === "sessions"; onClicked: page.section = "sessions" }
            ActionButton { label: "Perfiles por juego"; selected: page.section === "profiles"; onClicked: page.section = "profiles" }
            ActionButton { label: "Registros"; selected: page.section === "records"; onClicked: page.section = "records" }
            ActionButton { label: "Incidencias"; selected: page.section === "events"; onClicked: page.section = "events" }
        }

        Rectangle {
            visible: !!sessionState.message
            width: parent.width; height: visible ? 36 : 0; radius: 9
            color: Qt.alpha(page.accent, 0.10)
            Text { anchors.fill: parent; anchors.margins: 9; verticalAlignment: Text.AlignVCenter; color: page.muted; text: sessionState.message || ""; font.pixelSize: 12; elide: Text.ElideRight }
        }

        Flickable {
            id: scroller
            width: parent.width
            height: parent.height - y
            clip: true
            contentWidth: width
            contentHeight: content.implicitHeight + 18
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            Column {
                id: content
                width: scroller.width - 14
                spacing: 16

                Item {
                    visible: page.section === "sessions"
                    width: parent.width; height: visible ? sessionBody.implicitHeight : 0
                    Column {
                        id: sessionBody
                        width: parent.width; spacing: 14
                        Rectangle {
                            width: parent.width; height: 40; radius: 9; color: page.raised
                            Text { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 14; color: page.ink; text: "Historial de partidas"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Text { anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; anchors.rightMargin: 14; color: page.muted; text: "Guardado local · hasta 100 partidas"; font.pixelSize: 12 }
                        }
                        Text { visible: !(sessionState.sessions || []).length; text: "Abre un juego para comenzar a registrar la primera sesión."; color: page.muted; font.pixelSize: 14 }
                        Repeater {
                            model: sessionState.sessions || []
                            delegate: Rectangle {
                                required property var modelData
                                width: sessionBody.width; height: 69; radius: 12
                                color: page.selected.id === modelData.id ? Qt.alpha(page.accent, 0.14) : page.panel
                                border.color: page.selected.id === modelData.id ? page.accent : page.edge
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: gameSessions.selectSession(modelData.id) }
                                Row {
                                    anchors.fill: parent; anchors.margins: 14; spacing: 17
                                    Column {
                                        width: Math.max(220, parent.width * 0.50); spacing: 5
                                        Row {
                                            width: parent.width
                                            spacing: 10
                                            Image {
                                                id: gameIcon
                                                width: 22; height: 22
                                                source: modelData.iconUrl || ""
                                                fillMode: Image.PreserveAspectFit
                                                asynchronous: true
                                                smooth: true
                                                visible: status === Image.Ready && !!source
                                            }
                                            Rectangle {
                                                width: 22; height: 22; radius: 6
                                                visible: !gameIcon.visible
                                                color: Qt.alpha(page.accent, 0.14)
                                                border.color: Qt.alpha(page.accent, 0.35)
                                                Glyph { anchors.centerIn: parent; width: 14; height: 14; kind: "gamepad"; ink: page.accent }
                                            }
                                            Text {
                                                width: parent.width - x
                                                text: modelData.name
                                                color: page.ink
                                                font.pixelSize: 15
                                                font.weight: Font.DemiBold
                                                elide: Text.ElideRight
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                        Text { text: modelData.startedLabel + "  ·  " + modelData.duration + "  ·  " + modelData.source; color: page.muted; font.pixelSize: 12 }
                                    }
                                    Text { width: 118; text: page.value(modelData.averageFps, " FPS", 1); color: page.accent; font.pixelSize: 17; font.weight: Font.Bold }
                                    Text { width: 125; text: "1 % low  " + page.value(modelData.low_1, "", 1); color: page.ink; font.pixelSize: 13 }
                                }
                                ActionButton {
                                    anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                    width: 105; label: "Comparar"
                                    selected: sessionState.comparisonId === modelData.id
                                    enabled: !!page.selected.id && page.selected.id !== modelData.id && page.selected.game_key === modelData.game_key
                                    onClicked: gameSessions.selectComparison(selected ? 0 : modelData.id)
                                }
                            }
                        }
                        GlassPanel {
                            visible: !!page.selected.id
                            width: parent.width; height: visible ? 275 : 0; radius: 15
                            Column {
                                anchors.fill: parent; anchors.margins: 18; spacing: 12
                                Row {
                                    width: parent.width; height: 39; spacing: 9
                                    Text { width: Math.max(160, parent.width - 270); text: page.selected.name || ""; color: page.ink; font.pixelSize: 18; font.weight: Font.Bold; elide: Text.ElideRight }
                                    ActionButton { width: 120; label: "Informe PDF"; enabled: !!page.selected.id; onClicked: gameSessions.exportPdf(page.selected.id) }
                                    ActionButton { width: 115; label: "Abrir PDF"; enabled: !!sessionState.pdfPath; onClicked: gameSessions.openLastPdf() }
                                }
                                Row {
                                    spacing: 28
                                    Text { text: "FPS medios  " + page.value(page.selected.averageFps, "", 1); color: page.accent; font.pixelSize: 14 }
                                    Text { text: "1 % low  " + page.value(page.selected.low_1, "", 1); color: page.ink; font.pixelSize: 14 }
                                    Text { text: "CPU máx.  " + page.value(page.selected.cpu_peak, " °C", 1); color: page.ink; font.pixelSize: 14 }
                                    Text { text: "GPU máx.  " + page.value(page.selected.gpu_peak, " °C", 1); color: page.ink; font.pixelSize: 14 }
                                }
                                Text { text: "FPS por muestra · N/A si no hubo fotogramas verificables"; color: page.muted; font.pixelSize: 11 }
                                Canvas {
                                    id: fpsChart
                                    width: parent.width; height: 118
                                    onPaint: {
                                        const ctx = getContext("2d")
                                        ctx.clearRect(0, 0, width, height)
                                        const samples = (page.selected.samples || []).filter(s => typeof s.fps === "number" && isFinite(s.fps))
                                        ctx.strokeStyle = Qt.alpha(page.edge, 0.85)
                                        ctx.lineWidth = 1
                                        for (let y of [20, 58, 96]) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(width,y); ctx.stroke() }
                                        if (samples.length < 2) return
                                        let ceiling = 60
                                        for (const sample of samples) ceiling = Math.max(ceiling, sample.fps)
                                        ceiling *= 1.08
                                        ctx.strokeStyle = page.accent
                                        ctx.lineWidth = 2.5
                                        ctx.beginPath()
                                        for (let i = 0; i < samples.length; ++i) {
                                            const x = i * width / (samples.length - 1)
                                            const y = height - 8 - samples[i].fps / ceiling * (height - 18)
                                            if (i) ctx.lineTo(x,y); else ctx.moveTo(x,y)
                                        }
                                        ctx.stroke()
                                    }
                                }
                                Text { text: "" + (page.selected.fps_count || 0) + " lecturas FPS  ·  " + (page.selected.frame_count || 0) + " fotogramas ETW  ·  " + (page.selected.events || []).length + " incidencias"; color: page.muted; font.pixelSize: 12 }
                            }
                        }
                        Rectangle {
                            visible: !!(sessionState.comparison || {}).id
                            width: parent.width; height: visible ? 108 : 0; radius: 13
                            color: Qt.alpha(page.accent, 0.11); border.color: Qt.alpha(page.accent, 0.45)
                            Row {
                                anchors.fill: parent; anchors.margins: 17; spacing: 28
                                Column {
                                    width: Math.max(220, parent.width * 0.30); spacing: 6
                                    Text { text: "COMPARACIÓN · MISMO JUEGO"; color: page.accent; font.pixelSize: 11; font.weight: Font.Bold }
                                    Text { text: "Actual: " + page.selected.startedLabel; color: page.ink; font.pixelSize: 13 }
                                    Text { text: "Referencia: " + (sessionState.comparison || {}).startedLabel; color: page.muted; font.pixelSize: 13 }
                                }
                                Column {
                                    spacing: 6
                                    Text { text: "FPS medios"; color: page.muted; font.pixelSize: 11 }
                                    Text { text: page.value(page.selected.averageFps, "", 1) + " / " + page.value((sessionState.comparison || {}).averageFps, "", 1); color: page.ink; font.pixelSize: 17; font.weight: Font.DemiBold }
                                    Text { text: "Variación " + (typeof page.selected.averageFps === "number" && typeof (sessionState.comparison || {}).averageFps === "number" ? page.value(page.selected.averageFps - sessionState.comparison.averageFps, " FPS", 1) : "N/A"); color: page.accent; font.pixelSize: 12 }
                                }
                                Column {
                                    spacing: 6
                                    Text { text: "1 % low"; color: page.muted; font.pixelSize: 11 }
                                    Text { text: page.value(page.selected.low_1, "", 1) + " / " + page.value((sessionState.comparison || {}).low_1, "", 1); color: page.ink; font.pixelSize: 17; font.weight: Font.DemiBold }
                                }
                            }
                        }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "El 1 % low usa intervalos reales de fotogramas ETW y requiere al menos 300. Una incidencia cercana a una caída es una coincidencia temporal, no una causa confirmada."; color: page.muted; font.pixelSize: 12 }
                    }
                }

                Item {
                    visible: page.section === "profiles"
                    width: parent.width; height: visible ? profileBody.implicitHeight : 0
                    Column {
                        id: profileBody
                        width: parent.width; spacing: 15
                        Text { text: "Perfiles por juego"; color: page.ink; font.pixelSize: 20; font.weight: Font.Bold }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Al entrar al juego se aplican el plan y los ajustes de overlay elegidos. Al salir, CorePulse restaura el plan anterior si Windows sigue usando el plan que activó."; color: page.muted; font.pixelSize: 13 }
                        Text { visible: !(sessionState.gameChoices || []).length; text: "Abre un juego al menos una vez para crear su perfil."; color: page.muted; font.pixelSize: 13 }
                        Flow {
                            width: parent.width; spacing: 8
                            Repeater {
                                model: sessionState.gameChoices || []
                                delegate: ActionButton {
                                    required property var modelData
                                    label: modelData.name
                                    selected: sessionState.profileGameKey === modelData.key
                                    onClicked: { gameSessions.selectProfileGame(modelData.key); page.resetProfile() }
                                }
                            }
                        }
                        GlassPanel {
                            visible: !!sessionState.profileGameKey
                            width: parent.width; height: visible ? settings.implicitHeight + 36 : 0; radius: 15
                            Column {
                                id: settings
                                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 18
                                spacing: 12
                                Text { text: "Plan de energía"; color: page.ink; font.pixelSize: 16; font.weight: Font.DemiBold }
                                Flow {
                                    width: parent.width; spacing: 8
                                    ActionButton { label: "Sin cambio"; selected: page.draftPlan === ""; onClicked: page.draftPlan = "" }
                                    Repeater {
                                        model: sessionState.plans || []
                                        delegate: ActionButton {
                                            required property var modelData
                                            label: modelData.name
                                            selected: page.draftPlan === modelData.guid
                                            onClicked: page.draftPlan = modelData.guid
                                        }
                                    }
                                }
                                Text { text: "Posición del overlay"; color: page.ink; font.pixelSize: 16; font.weight: Font.DemiBold }
                                Flow {
                                    width: parent.width; spacing: 8
                                    Repeater {
                                        model: [{v:"inherit",t:"General"},{v:"top-left",t:"Arriba izquierda"},{v:"top-right",t:"Arriba derecha"},{v:"bottom-left",t:"Abajo izquierda"},{v:"bottom-right",t:"Abajo derecha"}]
                                        delegate: ActionButton { required property var modelData; label: modelData.t; selected: page.draftCorner === modelData.v; onClicked: page.draftCorner = modelData.v }
                                    }
                                }
                                Text { text: "Temperaturas en overlay"; color: page.ink; font.pixelSize: 16; font.weight: Font.DemiBold }
                                Flow {
                                    width: parent.width; spacing: 8
                                    Repeater {
                                        model: [{v:"inherit",t:"General"},{v:"on",t:"Mostrar"},{v:"off",t:"Ocultar"}]
                                        delegate: ActionButton { required property var modelData; label: modelData.t; selected: page.draftTemps === modelData.v; onClicked: page.draftTemps = modelData.v }
                                    }
                                }
                                ActionButton { label: "Guardar perfil"; selected: true; onClicked: gameSessions.saveProfile(sessionState.profileGameKey, page.draftPlan, page.draftCorner, page.draftTemps) }
                            }
                        }
                    }
                }

                ProblemRecords {
                    width:parent.width
                    visible:page.section === "records"
                    height:visible?implicitHeight:0
                }

                Item {
                    visible: page.section === "events"
                    width: parent.width; height: visible ? eventsBody.implicitHeight : 0
                    Column {
                        id: eventsBody
                        width: parent.width; spacing: 13
                        Text { text: "Incidencias de la partida seleccionada"; color: page.ink; font.pixelSize: 20; font.weight: Font.Bold }
                        Text { text: page.selected.name || "Selecciona una partida en la pestaña Partidas"; color: page.muted; font.pixelSize: 13 }
                        Text { visible: !!page.selected.id && !(page.selected.events || []).length; text: "No se registraron incidencias verificables en esta partida."; color: page.muted; font.pixelSize: 13 }
                        Repeater {
                            model: page.selected.events || []
                            delegate: GlassPanel {
                                required property var modelData
                                width: eventsBody.width; height: 82; radius: 12
                                Rectangle { x: 0; y: 12; width: 3; height: 58; radius: 2; color: modelData.kind === "thermal" ? "#E9A34A" : page.accent }
                                Column {
                                    anchors.fill: parent; anchors.margins: 13; anchors.leftMargin: 17; spacing: 5
                                    Row {
                                        spacing: 14
                                        Text { text: modelData.title; color: page.ink; font.pixelSize: 14; font.weight: Font.DemiBold }
                                        Text { text: page.timeLabel(modelData.ts); color: page.muted; font.pixelSize: 11 }
                                    }
                                    Text { width: parent.width; text: modelData.detail; color: page.muted; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                }
                            }
                        }
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Se registran caídas de FPS, fotogramas lentos, temperaturas sostenidas y eventos WHEA o cierres de Windows cercanos a la partida. La proximidad temporal no demuestra causalidad."; color: page.muted; font.pixelSize: 12 }
                    }
                }
            }
        }
    }
}
