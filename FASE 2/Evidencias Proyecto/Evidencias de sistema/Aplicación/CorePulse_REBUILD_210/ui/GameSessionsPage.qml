import QtQuick
import QtQuick.Controls

Item {
    id: page
    signal goBack()
    property string section: "sessions"
    onSectionChanged: scroller.contentY = 0
    property string draftPlan: ""
    property string draftCorner: "inherit"
    property string draftTemps: "inherit"

    readonly property var sessionState: gameSessions.data || ({})
    readonly property var selected: sessionState.detail || ({})
    readonly property var activeGame: sessionState.activeGame || ({active:false, name:"", source:"", artUrl:"", artKind:"", session:"N/A", state:"N/A"})
    readonly property var colors: themeManager.palette
    readonly property color ink: colors.ink
    readonly property color muted: colors.muted
    readonly property color edge: colors.panelBorder
    readonly property color accent: colors.cyan
    readonly property color panel: colors.panel
    readonly property color raised: colors.panelRaised

    function value(number, suffix, digits) {
        return typeof number === "number" && isFinite(number) ? Number(number).toFixed(digits || 0) + suffix : "N/A"
    }
    function hasUnavailableFps(sessions) {
        for (let i = 0; i < sessions.length; ++i) {
            const row = sessions[i]
            if (typeof row.averageFps !== "number" || !isFinite(row.averageFps) ||
                    typeof row.low_1 !== "number" || !isFinite(row.low_1)) return true
        }
        return false
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

    FastFlickable {
        anchors.fill: parent
        id: scroller
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: content.implicitHeight + 18

        Column {
            id: content
            width: scroller.width - 12
            spacing: 15

        Row {
            width: parent.width
            height: 56
            spacing: 14
            Glyph { width: 38; height: 38; y: 7; kind: "game_history"; ink: page.accent }
            Column {
                width: Math.max(0, parent.width - 38 - 14 - 14 - 87 - 87)
                spacing: 3
                Text { width: parent.width; text: "Sesiones de juego"; color: page.ink; font.pixelSize: 26; font.weight: Font.Bold; elide: Text.ElideRight }
                Text { width: parent.width; text: "FPS reales, perfiles e incidencias de cada partida"; color: page.muted; font.pixelSize: 13; elide: Text.ElideRight }
            }
            HeaderAction { label: "Actualizar"; onActivated: gameSessions.refresh() }
            HeaderAction { label: "Volver"; onActivated: page.goBack() }
        }

        GlassPanel {
            id: activeSessionCard
            width: parent.width; height: 224; radius: 16; clip: true
            Column {
                anchors.fill: parent; anchors.margins: 12; spacing: 9
                Row {
                    width: parent.width; height: 49; spacing: 6
                    Column {
                        width: parent.width * 0.52; spacing: 3
                        Text { text: page.activeGame.active ? "PARTIDA EN CURSO" : "SIN PARTIDA ACTIVA"; color: page.accent; font.pixelSize: 10; font.weight: Font.Bold }
                        Text { text: page.activeGame.active ? (page.activeGame.name || sessionState.activeName) : "El historial se guarda automáticamente"; color: page.ink; font.pixelSize: 15; font.weight: Font.DemiBold; elide: Text.ElideRight; width: parent.width }
                    }
                    Rectangle { width: 1; height: 38; color: page.edge }
                    Column {
                        width: parent.width * 0.18; spacing: 3
                        Text { text: "PARTIDAS"; color: page.muted; font.pixelSize: 9; font.weight: Font.Bold }
                        Text { text: (sessionState.sessions || []).length; color: page.ink; font.pixelSize: 18; font.weight: Font.Bold }
                    }
                    Column {
                        width: parent.width * 0.22; spacing: 3
                        Text { text: "PLAN"; color: page.muted; font.pixelSize: 9; font.weight: Font.Bold }
                        Text { text: sessionState.autoPowerStatus || "ESPERANDO"; color: page.ink; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight; width: parent.width }
                    }
                }
                Rectangle {
                    id: activeGameArtwork
                    width: parent.width; height: 142; radius: 12
                    color: page.raised; border.width: 1; border.color: page.edge; clip: true
                    Image {
                        id: activeGameCover
                        anchors.fill: parent
                        source: page.activeGame.active && page.activeGame.artKind === "cover" ? (page.activeGame.artUrl || "") : ""
                        fillMode: Image.PreserveAspectCrop; asynchronous: true; cache: true
                        visible: status === Image.Ready && page.activeGame.artKind === "cover"
                    }
                    Rectangle {
                        anchors.fill: parent; visible: !activeGameCover.visible
                        gradient: Gradient {
                            GradientStop { position: 0; color: Qt.alpha(page.accent, 0.22) }
                            GradientStop { position: 1; color: page.raised }
                        }
                    }
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0; color: "#00000000" }
                            GradientStop { position: 1; color: "#D9000000" }
                        }
                    }
                    Image {
                        visible: page.activeGame.active && page.activeGame.artKind === "icon" && !activeGameCover.visible
                        source: page.activeGame.artUrl || ""
                        width: 66; height: 66; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 16
                        fillMode: Image.PreserveAspectFit; asynchronous: true
                    }
                    Glyph {
                        visible: !page.activeGame.active || (!activeGameCover.visible && page.activeGame.artKind !== "icon")
                        width: 34; height: 34; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 19
                        kind: "game_history"; ink: Qt.alpha(page.ink, 0.70)
                    }
                    Column {
                        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                        anchors.margins: 14; spacing: 3
                        Text { text: page.activeGame.active ? (page.activeGame.name || sessionState.activeName) : "Esperando un juego"; color: "white"; font.pixelSize: 18; font.bold: true; width: parent.width; elide: Text.ElideRight }
                        Text { text: page.activeGame.active ? ((page.activeGame.state || "En ejecución") + " · " + (page.activeGame.source || "Origen local") + " · " + (page.activeGame.session || "N/A")) : "La portada y las métricas aparecerán al iniciar una partida"; color: "#E0E7EF"; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight }
                    }
                }
            }
        }

        GlassPanel {
            width: parent.width
            height: 126
            radius: 16
            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8
                Text { text: "Opciones de juego"; color: page.ink; font.pixelSize: 16; font.bold: true }
                Row {
                    spacing: 9
                    ActionButton {
                        label: gameBoost.enabled ? "Desactivar optimización" : "Activar optimización"
                        onClicked: gameBoost.setEnabled(!gameBoost.enabled)
                    }
                    ActionButton {
                        label: "Liberar memoria en espera " + (gameBoost.purgeStandby ? "Sí" : "No")
                        selected: gameBoost.purgeStandby
                        onClicked: gameBoost.setPurgeStandby(!gameBoost.purgeStandby)
                    }
                    ActionButton {
                        label: "Energía de procesos " + (gameBoost.powerThrottling ? "Sí" : "No")
                        selected: gameBoost.powerThrottling
                        onClicked: gameBoost.setPowerThrottling(!gameBoost.powerThrottling)
                    }
                }
                Text { text: (gameBoost.message || gameBoost.status) + " · Puede modificar consumo y autonomía."; color: page.muted; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
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
                        Text {
                            visible: page.hasUnavailableFps(sessionState.sessions || [])
                            width: parent.width
                            wrapMode: Text.WordWrap
                            text: "N/A significa que faltaron fotogramas verificables; no indica 0 FPS. El 1 % low necesita al menos 300 fotogramas."
                            color: page.muted
                            font.pixelSize: 12
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
                        Text { width: parent.width; wrapMode: Text.WordWrap; text: "Una incidencia cercana a una caída coincide en el tiempo, pero no confirma la causa."; color: page.muted; font.pixelSize: 12 }
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
        ThinScroll {
            target: scroller
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
        }
    }
}


