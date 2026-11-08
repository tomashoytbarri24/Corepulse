import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    readonly property var d: networkHealth.data || ({})
    readonly property color panel: themeManager.palette.panel
    readonly property color raised: themeManager.palette.panelRaised
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.accent
    readonly property color cyan: themeManager.palette.cyan
    readonly property color purple: themeManager.palette.purple
    readonly property var speedInfo: networkSpeedTest && networkSpeedTest.data ? networkSpeedTest.data : ({busy:false,percent:0,status:"N/A",message:"N/A",result:{},ooklaAvailable:false,ooklaDownloading:false})
    property string gaugeSelection: "download"
    readonly property string activeGaugeDirection: speedInfo.busy && speedInfo.phase === "upload" ? "upload"
        : speedInfo.busy && speedInfo.phase === "download" ? "download" : gaugeSelection
    readonly property real displayedSpeed: {
        const value = speedInfo.busy
            ? (activeGaugeDirection === "download" ? speedInfo.live_download_mbps : speedInfo.live_upload_mbps)
            : (activeGaugeDirection === "download" ? speedInfo.result.download_mbps : speedInfo.result.upload_mbps)
        return typeof value === "number" && isFinite(value) && value >= 0 ? value : -1
    }
    readonly property real dialMaximum: displayedSpeed < 0 ? 1000 : displayedSpeed <= 1000 ? 1000 : Math.ceil(displayedSpeed / 1000) * 1000
    readonly property bool phaseHasLiveRate: speedInfo.busy && (speedInfo.phase === "download" || speedInfo.phase === "upload") && displayedSpeed >= 0
    property bool confirmSpeedTest: false
    property bool ooklaTermsAccepted: false
    function beginSpeedtest() {
        page.gaugeSelection = "download"
        if (speedInfo.termsAccepted) {
            networkSpeedTest.start("ookla")
        } else {
            page.ooklaTermsAccepted = false
            page.confirmSpeedTest = true
        }
    }
    function measured(value, suffix, digits) {
        return typeof value === "number" && isFinite(value) && value >= 0
            ? value.toFixed(digits) + suffix : "N/A"
    }

    Component.onCompleted: networkHealth.startWatch()
    Component.onDestruction: networkHealth.stopWatch()

    component MiniButton: Rectangle {
        id: button
        property string label: ""
        property bool enabledAction: true
        property bool selected: false
        property bool actionStyle: false   // ejecuta algo: texto en color de acción (REBUILD 082)
        property bool solidStyle: false    // Aplicar/Actualizar: botón entero de color
        signal activated()
        implicitWidth: Math.max(108, content.implicitWidth + 28)
        implicitHeight: 35
        radius: 10
        color: solidStyle ? (!enabledAction ? themeManager.palette.actionMuted : pointer.containsMouse ? Qt.lighter(themeManager.palette.action, 1.16) : themeManager.palette.action)
                      : selected ? Qt.alpha(themeManager.palette.accent, 0.12) : pointer.containsMouse && enabledAction ? themeManager.palette.panelRaised : themeManager.palette.panel
        opacity: enabledAction || solidStyle ? 1 : 0.5
        border.width: 1; border.color: selected ? themeManager.palette.accent : (solidStyle || (actionStyle && pointer.containsMouse)) && enabledAction ? themeManager.palette.action : themeManager.palette.panelBorder
        Text { id: content; anchors.centerIn: parent; text: button.label; font.pixelSize: 11; font.bold: true
               color: button.solidStyle ? (button.enabledAction ? themeManager.palette.actionText : themeManager.palette.actionMutedText)
                    : button.actionStyle ? themeManager.palette.action : themeManager.palette.ink }
        MouseArea { id: pointer; anchors.fill: parent; enabled: button.enabledAction; hoverEnabled: true
            cursorShape: Qt.PointingHandCursor; onClicked: button.activated() }
    }

    component DataTile: GlassPanel {
        id: tile
        property string title: ""
        property string value: "N/A"
        property string detail: ""
        property string privacyKey: ""   // campo sensible: muestra el ojo
        Layout.fillWidth: true
        Layout.preferredHeight: 122
        radius: 15
        color: themeManager.palette.panel
        border.width: 1; border.color: themeManager.palette.panelBorder
        ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 6
            RowLayout { Layout.fillWidth: true; spacing: 6
                Text { text: tile.title; color: themeManager.palette.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                PrivacyEye { visible: tile.privacyKey !== "" && !!(page.d.hasSensitive || {})[tile.privacyKey]
                    revealed: !!(page.d.revealed || {})[tile.privacyKey]; hint: tile.title
                    onToggled: networkHealth.toggleReveal(tile.privacyKey) }
            }
            Text { Layout.fillWidth: true; text: tile.value; color: themeManager.palette.accent; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight }
            Text { Layout.fillWidth: true; text: tile.detail; color: themeManager.palette.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
        }
    }

    FastFlickable {
        id: scroller
        anchors.fill: parent
        anchors.margins: 0
        contentWidth: width
        contentHeight: content.implicitHeight + 22
        clip: true; boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: content
            width: scroller.width - 12
            spacing: 15
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Glyph { Layout.preferredWidth: 36; Layout.preferredHeight: 36; kind: "network"; ink: page.cyan }
                ColumnLayout { Layout.fillWidth: true; spacing: 3
                    Text { text: "Red avanzada"; color: page.ink; font.pixelSize: 21; font.bold: true }
                    Text { Layout.fillWidth: true; text: "Conexión y velocidad"; color: page.muted; font.pixelSize: 11; elide: Text.ElideRight }
                }
                MiniButton { actionStyle: true; solidStyle: true; label: d.busy ? "Consultando…" : "Actualizar"; enabledAction: !d.busy; onActivated: networkHealth.refresh() }
                MiniButton { label: "Volver"; onActivated: page.goBack() }
            }
            GlassPanel { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 15; color: page.panel; border.width: 1; border.color: page.edge
                ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 6
                    RowLayout { Layout.fillWidth: true
                        Text { text: "CONEXIÓN PRINCIPAL"; color: page.muted; font.pixelSize: 10; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: "Actualizado: " + (d.lastUpdate || "N/A"); color: page.muted; font.pixelSize: 10 }
                    }
                    Text { text: (d.primary || "N/A") + " · " + (d.total === undefined ? "N/A" : d.total) + " adaptadores"; color: page.accent; font.pixelSize: 17; font.bold: true }
                    Text { visible: !!d.busy; text: d.phase || "Consultando…"; color: page.muted; font.pixelSize: 10 }
                }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: content.width < 800 ? 2 : 4
                columnSpacing: 12; rowSpacing: 12
                DataTile { title: "IPV4"; value: d.ipv4 || "N/A"; detail: "Dirección publicada por Windows"; privacyKey: "ipv4" }
                DataTile { title: "VELOCIDAD DE ENLACE"; value: d.linkSpeed || "N/A"; detail: "Enlace local, no velocidad de Internet" }
                DataTile { title: "DESCARGA ACTUAL"; value: d.download || "N/A"; detail: "Tráfico en tiempo real" }
                DataTile { title: "SUBIDA ACTUAL"; value: d.upload || "N/A"; detail: "Tráfico en tiempo real" }
            }

            // REBUILD 188: arco ligado a la aguja y composición Liquid Glass sin discos opacos.
            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: speedContents.implicitHeight + 38
                radius: 16
                // Usa el degradado compartido por GlassPanel, no una capa sólida adicional.
                color: "transparent"
                border.width: 1
                border.color: page.edge

                ColumnLayout {
                    id: speedContents
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 19
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text { text: "Speedtest"; color: page.ink; font.pixelSize: 19; font.bold: true }
                            Text {
                                text: "Motor oficial de Ookla · Prueba integrada, sin abrir el navegador"
                                color: page.muted; font.pixelSize: 11
                                Layout.fillWidth: true; elide: Text.ElideRight
                            }
                        }
                        MiniButton {
                            visible: !speedInfo.ooklaAvailable
                            label: speedInfo.ooklaDownloading ? "Preparando…" : "Preparar Ookla"
                            actionStyle: true
                            enabledAction: !speedInfo.busy && !speedInfo.ooklaDownloading
                            onActivated: networkSpeedTest.checkOokla()
                        }
                    }

                    // Lienzo sin halo circular artificial: solo el cristal del panel principal.
                    Item {
                        id: speedStage
                        Layout.fillWidth: true
                        property real animatedHeight: speedInfo.busy ? 466 : speedInfo.result.ok ? 305 : 352
                        Layout.preferredHeight: animatedHeight
                        Behavior on animatedHeight { NumberAnimation { duration: 420; easing.type: Easing.InOutCubic } }
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 7

                            RowLayout {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: Math.min(speedStage.width - 24, 560)
                                spacing: 36
                                visible: speedInfo.busy
                                ColumnLayout {
                                    spacing: 2
                                    Text { text: "↓  DESCARGA  Mbps"; color: page.cyan; font.pixelSize: 11; font.bold: true }
                                    Text {
                                        text: page.measured(speedInfo.live_download_mbps, "", 2)
                                        color: page.ink; font.pixelSize: 25; font.weight: Font.DemiBold
                                        Behavior on color { ColorAnimation { duration: 300 } }
                                    }
                                }
                                ColumnLayout {
                                    spacing: 2
                                    Text { text: "↑  SUBIDA  Mbps"; color: page.purple; font.pixelSize: 11; font.bold: true }
                                    Text {
                                        text: page.measured(speedInfo.live_upload_mbps, "", 2)
                                        color: page.ink; font.pixelSize: 25; font.weight: Font.DemiBold
                                    }
                                }
                            }
                            RowLayout {
                                Layout.alignment: Qt.AlignHCenter
                                spacing: 18
                                visible: speedInfo.busy
                                Text {
                                    text: "PING  " + page.measured(speedInfo.live_ping_ms, " ms", 1)
                                    color: page.muted; font.pixelSize: 11
                                }
                                Text {
                                    text: "JITTER  " + page.measured(speedInfo.live_jitter_ms, " ms", 1)
                                    color: page.muted; font.pixelSize: 11
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: 180

                                // Estado inicial: botón central independiente, sin placa de fondo.
                                Item {
                                    id: idleView
                                    anchors.fill: parent
                                    opacity: !speedInfo.busy && !speedInfo.result.ok ? 1 : 0
                                    visible: opacity > 0.001
                                    Behavior on opacity { NumberAnimation { duration: 320; easing.type: Easing.InOutCubic } }

                                    Rectangle {
                                        id: startRing
                                        anchors.centerIn: parent
                                        width: 164; height: width; radius: width / 2
                                        color: Qt.alpha(page.cyan, startPointer.containsMouse ? 0.075 : 0.017)
                                        border.width: 1.5
                                        border.color: startPointer.containsMouse ? Qt.lighter(page.cyan, 1.17) : page.cyan
                                        Behavior on color { ColorAnimation { duration: 220 } }
                                        SequentialAnimation on scale {
                                            running: idleView.visible && speedInfo.ooklaAvailable
                                            loops: Animation.Infinite
                                            NumberAnimation { from: 0.985; to: 1.03; duration: 1800; easing.type: Easing.InOutSine }
                                            NumberAnimation { from: 1.03; to: 0.985; duration: 1800; easing.type: Easing.InOutSine }
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: speedInfo.ooklaDownloading ? "PREPARANDO" : speedInfo.ooklaAvailable ? "INICIO" : "OOKLA\nNO DISPONIBLE"
                                            horizontalAlignment: Text.AlignHCenter
                                            color: speedInfo.ooklaAvailable ? page.ink : page.muted
                                            font.pixelSize: speedInfo.ooklaAvailable ? 26 : 12
                                            font.weight: Font.Medium
                                        }
                                        MouseArea {
                                            id: startPointer; anchors.fill: parent; hoverEnabled: true
                                            enabled: speedInfo.ooklaAvailable && !speedInfo.ooklaDownloading && !speedInfo.busy
                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: page.beginSpeedtest()
                                        }
                                    }
                                }

                                // Resultado centrado y repartido: botón de repetición + métricas legibles.
                                Item {
                                    id: finishedView
                                    anchors.fill: parent
                                    opacity: !speedInfo.busy && !!speedInfo.result.ok ? 1 : 0
                                    visible: opacity > 0.001
                                    Behavior on opacity { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
                                    RowLayout {
                                        width: Math.min(parent.width - 24, 825)
                                        height: Math.min(parent.height - 14, 225)
                                        anchors.centerIn: parent
                                        spacing: speedStage.width < 680 ? 22 : 62
                                        Item {
                                            Layout.preferredWidth: speedStage.width < 680 ? 132 : 156
                                            Layout.preferredHeight: 174
                                            Layout.alignment: Qt.AlignVCenter
                                            Rectangle {
                                                id: repeatRing
                                                anchors.centerIn: parent
                                                width: speedStage.width < 680 ? 120 : 145
                                                height: width; radius: width / 2
                                                color: Qt.alpha(page.cyan, repeatPointer.containsMouse ? 0.075 : 0.02)
                                                border.width: 1.5
                                                border.color: repeatPointer.containsMouse ? Qt.lighter(page.cyan, 1.17) : page.cyan
                                                Behavior on color { ColorAnimation { duration: 220 } }
                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "INICIO"; color: page.ink
                                                    font.pixelSize: 21; font.weight: Font.Medium
                                                }
                                                MouseArea {
                                                    id: repeatPointer; anchors.fill: parent; hoverEnabled: true
                                                    enabled: speedInfo.ooklaAvailable && !speedInfo.busy
                                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                    onClicked: page.beginSpeedtest()
                                                }
                                            }
                                        }
                                        ColumnLayout {
                                            id: resultSummary
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 15
                                            Text { text: "RESULTADOS VERIFICADOS"; color: page.muted; font.pixelSize: 11; font.weight: Font.DemiBold }
                                            RowLayout {
                                                Layout.fillWidth: true; spacing: 28
                                                ColumnLayout {
                                                    Layout.fillWidth: true; spacing: 5
                                                    Text { text: "↓  DESCARGA · Mbps"; color: page.cyan; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                    Text { text: page.measured(speedInfo.result.download_mbps, "", 2); color: page.ink
                                                        font.pixelSize: speedStage.width < 680 ? 27 : 39; font.weight: Font.Medium }
                                                }
                                                ColumnLayout {
                                                    Layout.fillWidth: true; spacing: 5
                                                    Text { text: "↑  SUBIDA · Mbps"; color: page.purple; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                    Text { text: page.measured(speedInfo.result.upload_mbps, "", 2); color: page.ink
                                                        font.pixelSize: speedStage.width < 680 ? 27 : 39; font.weight: Font.Medium }
                                                }
                                            }
                                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.alpha(page.edge, 0.85) }
                                            GridLayout {
                                                Layout.fillWidth: true
                                                columns: speedStage.width < 680 ? 2 : 3
                                                columnSpacing: 20; rowSpacing: 8
                                                Text { text: "PING   " + page.measured(speedInfo.result.latency_ms, " ms", 1); color: page.muted; font.pixelSize: 11 }
                                                Text { text: "JITTER   " + page.measured(speedInfo.result.jitter_ms, " ms", 1); color: page.muted; font.pixelSize: 11 }
                                                Text { text: "PÉRDIDA   " + page.measured(speedInfo.result.packet_loss_percent, " %", 2); color: page.muted; font.pixelSize: 11 }
                                            }
                                        }
                                    }
                                }

                                Item {
                                    id: liveDial
                                    opacity: speedInfo.busy ? 1 : 0
                                    visible: opacity > 0.001
                                    Behavior on opacity { NumberAnimation { duration: 360; easing.type: Easing.InOutCubic } }
                                    anchors.fill: parent
                                    Canvas {
                                        id: speedGauge
                                        anchors.centerIn: parent
                                        width: Math.min(parent.width - 14, 445)
                                        height: Math.min(parent.height, 320)
                                        property bool uploading: speedInfo.phase === "upload"
                                        property bool phaseMeasuring: speedInfo.phase === "download" || speedInfo.phase === "upload"
                                        property real currentRate: page.displayedSpeed
                                        property real maxRate: Math.max(1000, page.dialMaximum)
                                        // El objetivo es siempre el valor JSONL de Ookla: interpolación puramente visual.
                                        property real visualRate: phaseMeasuring && currentRate >= 0 ? currentRate : 0
                                        Behavior on visualRate { NumberAnimation { duration: 520; easing.type: Easing.OutCubic } }
                                        // Un único valor interpolado dirige aguja Y arco: nunca se pinta el arco completo antes de tiempo.
                                        readonly property real arcFraction: phaseMeasuring && currentRate >= 0
                                            ? gaugeFraction(visualRate, maxRate) : 0
                                        // La paleta del medidor cambia gradualmente entre descarga y subida.
                                        property color firstColor: uploading ? page.purple : page.cyan
                                        property color lastColor: uploading ? "#F075BB" : "#57E8A6"
                                        Behavior on firstColor { ColorAnimation { duration: 570 } }
                                        Behavior on lastColor { ColorAnimation { duration: 570 } }
                                        // Pulso de conexión: solo indica actividad, no simula Mbps.
                                        property real connectionSweep: 0
                                        NumberAnimation on connectionSweep {
                                            running: speedGauge.visible && speedInfo.busy && (!speedGauge.phaseMeasuring || speedGauge.currentRate < 0)
                                            from: 0; to: 1; duration: 1500; loops: Animation.Infinite
                                        }
                                        onVisualRateChanged: requestPaint()
                                        onArcFractionChanged: requestPaint()
                                        onFirstColorChanged: requestPaint()
                                        onLastColorChanged: requestPaint()
                                        onConnectionSweepChanged: requestPaint()
                                        onCurrentRateChanged: requestPaint()
                                        onMaxRateChanged: requestPaint()
                                        onPhaseMeasuringChanged: requestPaint()
                                        onWidthChanged: requestPaint()
                                        onHeightChanged: requestPaint()
                                        function gaugeFraction(value, maximum) {
                                            const steps = [0, 5, 10, 50, 100, 250, 500, 750, maximum]
                                            if (!isFinite(value) || value <= 0) return 0
                                            for (let i = 1; i < steps.length; ++i) {
                                                if (value <= steps[i])
                                                    return (i - 1 + (value - steps[i - 1]) / (steps[i] - steps[i - 1])) / (steps.length - 1)
                                            }
                                            return 1
                                        }
                                        onPaint: {
                                            const ctx = getContext("2d")
                                            ctx.reset()
                                            const cx = width / 2
                                            const cy = height * 0.53
                                            const r = Math.min(width * 0.405, height * 0.455)
                                            const begin = Math.PI * 0.75
                                            const span = Math.PI * 1.5
                                            const ticks = [0, 5, 10, 50, 100, 250, 500, 750, maxRate]

                                            // Sin anillo de fondo: solo el arco real que corresponde a la lectura actual.
                                            if (arcFraction > 0.001) {
                                                const gradient = ctx.createLinearGradient(cx - r, cy + r * 0.6, cx + r, cy - r * 0.4)
                                                gradient.addColorStop(0, firstColor)
                                                gradient.addColorStop(1, lastColor)
                                                // El final del arco coincide EXACTAMENTE con la posición de la aguja.
                                                const finish = begin + span * arcFraction
                                                ctx.beginPath(); ctx.arc(cx, cy, r, begin, finish)
                                                ctx.lineCap = "round"
                                                ctx.lineWidth = 18
                                                ctx.strokeStyle = gradient
                                                ctx.stroke()
                                            }

                                            ctx.textAlign = "center"
                                            ctx.textBaseline = "middle"
                                            ctx.font = "600 11px sans-serif"
                                            for (let i = 0; i < ticks.length; ++i) {
                                                const angle = begin + span * i / (ticks.length - 1)
                                                const tx = cx + Math.cos(angle) * (r - 32)
                                                const ty = cy + Math.sin(angle) * (r - 32)
                                                ctx.fillStyle = page.ink
                                                ctx.globalAlpha = i === 0 || i === ticks.length - 1 ? 0.62 : 0.87
                                                ctx.fillText(ticks[i].toString(), tx, ty)
                                            }
                                            ctx.globalAlpha = 1

                                            if (phaseMeasuring && currentRate >= 0) {
                                                // Aguja con inercia: los extremos siguen exclusivamente a lecturas reales.
                                                const angle = begin + span * arcFraction
                                                const ux = Math.cos(angle), uy = Math.sin(angle)
                                                const tipX = cx + ux * r * 0.76
                                                const tipY = cy + uy * r * 0.76
                                                const needleGradient = ctx.createLinearGradient(cx, cy, tipX, tipY)
                                                needleGradient.addColorStop(0, Qt.alpha(page.ink, 0.14))
                                                needleGradient.addColorStop(1, Qt.alpha(page.ink, 0.84))
                                                ctx.beginPath()
                                                ctx.moveTo(cx - ux * 14 - uy * 5, cy - uy * 14 + ux * 5)
                                                ctx.lineTo(cx - ux * 14 + uy * 5, cy - uy * 14 - ux * 5)
                                                ctx.lineTo(tipX, tipY)
                                                ctx.closePath()
                                                ctx.fillStyle = needleGradient; ctx.fill()
                                                ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2)
                                                ctx.fillStyle = page.ink; ctx.fill()
                                            } else if (speedInfo.busy) {
                                                // Búsqueda/latencia: pulso de actividad sin inventar velocidad.
                                                const angle = begin + span * connectionSweep
                                                ctx.beginPath()
                                                ctx.arc(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r, 4.5, 0, Math.PI * 2)
                                                ctx.fillStyle = page.cyan; ctx.fill()
                                            }
                                        }
                                    }
                                    Column {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        y: speedGauge.y + speedGauge.height * 0.75
                                        spacing: 3
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: speedInfo.phase === "ping" ? "MIDIENDO PING" : speedInfo.phase === "preparing" ? "CONECTANDO" : speedGauge.phaseMeasuring ? (speedGauge.uploading ? "SUBIDA" : "DESCARGA") : "PREPARANDO"
                                            color: page.muted; font.pixelSize: 11; font.bold: true
                                        }
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: speedGauge.phaseMeasuring && speedGauge.currentRate >= 0 ? speedGauge.visualRate.toFixed(2) : "—"
                                            color: speedGauge.uploading ? page.purple : page.cyan
                                            font.pixelSize: 31; font.weight: Font.DemiBold
                                            Behavior on color { ColorAnimation { duration: 570 } }
                                        }
                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: "Mbps"; color: page.muted; font.pixelSize: 11
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.maximumWidth: speedStage.width - 24
                                spacing: 12
                                Text { text: "SERVIDOR"; color: page.muted; font.pixelSize: 10; font.bold: true }
                                Text {
                                    text: speedInfo.busy ? (speedInfo.live_server_name || "Selección automática")
                                        : (speedInfo.result.ok ? ((speedInfo.result.server || {}).name || "No informado") : "Ookla · selección automática")
                                    color: page.ink; font.pixelSize: 12; font.weight: Font.Medium
                                    Layout.maximumWidth: Math.min(440, speedStage.width - 142)
                                    elide: Text.ElideRight
                                }
                            }
                            Text {
                                visible: !speedInfo.busy && !!speedInfo.result.ok
                                Layout.alignment: Qt.AlignHCenter
                                text: "Ubicación: " + ((speedInfo.result.server || {}).location || "No disponible")
                                color: page.muted; font.pixelSize: 10
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: speedInfo.busy ? 3 : 0
                                visible: speedInfo.busy
                                radius: 2
                                color: Qt.alpha(page.edge, 0.26)
                                Rectangle {
                                    height: parent.height; radius: 2
                                    width: parent.width * (page.phaseHasLiveRate ? Math.max(0, Math.min(1, speedGauge.arcFraction)) : 0)
                                    color: speedGauge.uploading ? page.purple : page.cyan
                                    Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
                                    Behavior on color { ColorAnimation { duration: 480 } }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Rectangle {
                            Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4
                            color: speedInfo.busy ? page.cyan : speedInfo.result.ok ? "#36D6A0" : page.muted
                        }
                        Text {
                            Layout.fillWidth: true
                            text: speedInfo.busy ? (speedInfo.message || "Prueba en curso…")
                                : speedInfo.result.ok ? "Prueba completada con Ookla. Pulsa INICIO para repetir."
                                : speedInfo.result.error ? speedInfo.result.error
                                : speedInfo.ooklaDownloading ? "Preparando el motor oficial de Ookla…"
                                : speedInfo.ooklaAvailable ? "Pulsa INICIO para medir tu conexión."
                                : "No está disponible la CLI de Ookla. Pulsa Preparar Ookla para reintentar."
                            color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Las lecturas en vivo provienen de Ookla; cada prueba comienza solo al pulsar INICIO. El dial responde a Mbps medidos. Ookla recibe datos de conexión durante la medición."
                        color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: speedInfo.termsAccepted
                        textFormat: Text.RichText
                        text: '<a href="https://www.speedtest.net/about/terms">Condiciones de Ookla</a> · <a href="corepulse-reset-ookla">Olvidar aceptación guardada</a>'
                        color: page.muted; linkColor: page.cyan; font.pixelSize: 10
                        onLinkActivated: function(link) {
                            if (link === "corepulse-reset-ookla") networkSpeedTest.forgetOoklaTerms()
                            else if (link.indexOf("https://www.speedtest.net/about/") === 0) Qt.openUrlExternally(link)
                        }
                    }
                }
            }

            Text { text: "Datos de red ocultos · usa el ojo para verlos"; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            DetailsSection {
                objectName: "connectionDetails"
                Layout.fillWidth: true
                title: "Configuración y adaptadores"
                GlassPanel { Layout.fillWidth: true; Layout.preferredHeight: connections.implicitHeight + 28; radius: 16; color: page.panel; border.width: 1; border.color: page.edge
                    ColumnLayout { id: connections; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; spacing: 9
                        Text { text: "Configuración de la conexión"; color: page.ink; font.pixelSize: 15; font.bold: true }
                        Repeater { model: [{t:"Gateway",v:d.gateway || "N/A",k:"gateway"}, {t:"DNS",v:d.dns || "N/A",k:"dns"}, {t:"IPv6",v:d.ipv6 || "N/A",k:"ipv6"}, {t:"Wi-Fi / SSID",v:d.ssid || "N/A",k:"ssid"}, {t:"Señal Wi-Fi",v:d.signal || "N/A",k:""}]
                            delegate: RowLayout { required property var modelData; Layout.fillWidth: true; spacing: 10
                                Text { text: modelData.t; color: page.muted; font.pixelSize: 11; Layout.preferredWidth: 118 }
                                Text { text: modelData.v; color: page.ink; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                                PrivacyEye { visible: modelData.k !== "" && !!(d.hasSensitive || {})[modelData.k]
                                    revealed: !!(d.revealed || {})[modelData.k]; hint: modelData.t
                                    onToggled: networkHealth.toggleReveal(modelData.k) }
                            }
                        }
                        Text { Layout.fillWidth: true; text: "El ojo muestra cada dato durante 30 segundos. Al salir se vuelve a ocultar."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                    }
                }
                Text { text: "Adaptadores detectados"; color: page.ink; font.pixelSize: 15; font.bold: true }
                Repeater { model: d.adapters || []
                    delegate: GlassPanel { required property var modelData; required property int index
                        Layout.fillWidth: true; Layout.preferredHeight: 94; radius: 15; color: page.panel; border.width: 1; border.color: page.edge
                        ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 6
                            RowLayout { Layout.fillWidth: true; spacing: 8
                                Text { text: modelData.name; color: page.ink; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                                Text { text: modelData.status; color: modelData.isUp ? "#36D6A0" : page.muted; font.pixelSize: 11 }
                                PrivacyEye { visible: !!modelData.hasSensitive; revealed: !!modelData.revealed; hint: "direcciones de " + modelData.name
                                    onToggled: networkHealth.toggleReveal("adapter:" + index) }
                            }
                            Text { Layout.fillWidth: true; text: "IPv4: " + modelData.ipv4 + " · Gateway: " + modelData.gateway; color: page.muted; font.pixelSize: 10; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: "DNS: " + modelData.dns + " · Enlace: " + modelData.linkSpeed; color: page.muted; font.pixelSize: 10; elide: Text.ElideRight }
                        }
                    }
                }
                Text { Layout.fillWidth: true; text: "Fuentes: psutil / Get-NetAdapter / Get-NetIPConfiguration / netsh wlan. Esta pantalla no cambia DNS, rutas, IP ni adaptadores."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
            }
            Item { Layout.preferredHeight: 12 }
        }
    }
    Rectangle { visible:page.confirmSpeedTest; anchors.fill:parent; z:40; color:"#B5000000"
        focus: visible
        onVisibleChanged: if (visible) forceActiveFocus()
        Keys.onEscapePressed: { page.confirmSpeedTest=false; page.ooklaTermsAccepted=false }
        MouseArea { anchors.fill:parent; acceptedButtons:Qt.AllButtons; onWheel:function(wheel){wheel.accepted=true} }
        Rectangle { width:Math.min(parent.width-24,460);height:speedConfirmContents.implicitHeight+34;anchors.centerIn:parent;radius:16;color:themeManager.palette.panelOpaque;border.width:1;border.color:page.edge
            ColumnLayout { id:speedConfirmContents;anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top;anchors.margins:17;spacing:12
                Text { text:"Iniciar prueba activa de red";color:page.ink;font.pixelSize:17;font.bold:true }
                Text { text:"Solo la primera vez: confirma las condiciones de Ookla. En las siguientes pruebas bastará pulsar INICIO. La medición utiliza tu conexión y puede consumir cientos de MB.";color:page.muted;font.pixelSize:11;Layout.fillWidth:true;wrapMode:Text.WordWrap }
                Rectangle { objectName:"ooklaConsent"; visible:true;Layout.fillWidth:true;Layout.preferredHeight:50;radius:10;color:page.raised;border.width:1;border.color:page.edge
                    RowLayout { anchors.fill:parent; anchors.margins:10; spacing:10
                        Rectangle { Layout.preferredWidth:20;Layout.preferredHeight:20;radius:5;color:page.ooklaTermsAccepted?page.cyan:page.panel;border.width:1;border.color:page.ooklaTermsAccepted?page.cyan:page.edge
                            Text { anchors.centerIn:parent;text:page.ooklaTermsAccepted?"✓":"";color:"#07121C";font.bold:true;font.pixelSize:14 }
                        }
                        Text { Layout.fillWidth:true;text:"Leí y acepto las condiciones y el aviso de privacidad de Ookla. Recordar en este equipo.";color:page.ink;font.pixelSize:10;wrapMode:Text.WordWrap }
                    }
                    MouseArea { anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:page.ooklaTermsAccepted=!page.ooklaTermsAccepted }
                }
                Text { visible:true;Layout.fillWidth:true;textFormat:Text.RichText;text:"<a href=\"https://www.speedtest.net/about/terms\">Condiciones de uso</a> · <a href=\"https://www.speedtest.net/about/privacy\">Aviso de privacidad</a>";color:page.cyan;font.pixelSize:10;onLinkActivated:function(link){Qt.openUrlExternally(link)} }
                RowLayout { Layout.fillWidth:true;Item{Layout.fillWidth:true}
                    MiniButton { label:"Cancelar";onActivated:{page.confirmSpeedTest=false;page.ooklaTermsAccepted=false} }
                    MiniButton { actionStyle: true; label:"Iniciar prueba";enabledAction:page.ooklaTermsAccepted;onActivated:{const accepted=page.ooklaTermsAccepted;page.confirmSpeedTest=false;page.gaugeSelection="download";networkSpeedTest.startWithConsent("ookla",accepted)} }
                }
            }
        }
    }
}
