import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    readonly property var info: corepulseAI.state
    readonly property color panel: themeManager.palette.panel
    readonly property color raised: themeManager.palette.panelRaised
    readonly property color borderTone: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.cyan
    // V064: la configuracion solo ocupa altura mientras se necesita conectar
    // o cuando el usuario decide mostrarla. Al conectar, priorizar el chat.
    property bool settingsExpanded: false
    readonly property bool usingCloud: page.info.provider === "cloud"
    readonly property bool showSettings: page.info.enabled && page.settingsExpanded
    property int chatFontSize: 16
    clip: true

    // Basic permite personalizar background/contentItem/indicator en Windows.
    // Botones de medidas estables: el hover cambia solo el color, no tamaño ni borde.
    component ActionButton: Button {
        id: btn
        property bool secondary: false
        property bool compact: false
        implicitWidth: compact ? 38 : Math.max(94, buttonLabel.implicitWidth + 28)
        implicitHeight: 36
        topPadding: 0; bottomPadding: 0; leftPadding: 0; rightPadding: 0
        hoverEnabled: true
        focusPolicy: Qt.StrongFocus
        background: Rectangle {
            radius: 9
            border.width: 1
            border.color: !btn.enabled ? "#343A48" : btn.secondary ? page.borderTone : page.accent
            color: !btn.enabled ? "#252A35" : btn.down ? "#1D343D"
                 : btn.hovered ? (btn.secondary ? "#303848" : "#21414B")
                 : btn.secondary ? page.raised : "#19343C"
            Behavior on color { ColorAnimation { duration: 100 } }
        }
        contentItem: Text {
            id: buttonLabel
            text: btn.text
            color: !btn.enabled ? "#8591A2" : btn.secondary ? page.ink : "#69DDED"
            font.pixelSize: btn.compact ? 15 : 12
            font.bold: true
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    component ConsentCheck: CheckBox {
        id: cb
        implicitHeight: 34
        spacing: 8
        hoverEnabled: true
        indicator: Rectangle {
            x: 1
            y: (cb.height - height) / 2
            width: 17; height: 17; radius: 5
            color: cb.checked ? page.accent : "#242B38"
            border.color: cb.checked ? page.accent : "#586174"
            border.width: 1
            Text { anchors.centerIn: parent; text: "✓"; visible: cb.checked; color: "#10242B"; font.bold: true; font.pixelSize: 13 }
        }
        contentItem: Text {
            text: cb.text
            color: cb.enabled ? page.ink : page.muted
            font.pixelSize: 12
            leftPadding: cb.indicator.width + cb.spacing
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            spacing: 11
            Rectangle {
                Layout.preferredWidth: 46; Layout.preferredHeight: 46
                radius: 12; color: page.raised
                Glyph { anchors.centerIn: parent; width: 25; height: 25; kind: "spark_ai"; ink: page.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text { text: "CorePulse AI"; color: page.ink; font.bold: true; font.pixelSize: 19 }
                Text {
                    text: "CorePulse AI Cloud · Conexión automática"
                    color: page.muted; font.pixelSize: 11; elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
            ActionButton { text: "Volver"; secondary: true; Layout.preferredWidth: 88; onClicked: page.goBack() }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 49
            radius: 11; color: page.panel; border.width: 1; border.color: page.borderTone
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 12; spacing: 10
                Rectangle {
                    Layout.preferredWidth: 9; Layout.preferredHeight: 9; radius: 5
                    color: !page.info.enabled ? "#8693A7" : page.info.ready ? "#42D7B3" : "#E9B963"
                }
                Text {
                    Layout.fillWidth: true
                    text: page.info.status
                    color: page.ink; font.pixelSize: 12
                    maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignVCenter
                }
                // Tras conectar, los permisos se mantienen accesibles aqui, sin
                // desperdiciar el espacio vertical de la conversacion.
                ActionButton {
                    visible: page.info.enabled && !cuenta.conectado
                    text: "Iniciar sesión"
                    secondary: true; Layout.preferredWidth: 115
                    enabled: !cuenta.ocupado
                    onClicked: cuenta.iniciarSesion()
                }
                ActionButton {
                    visible: page.info.enabled && cuenta.conectado && !page.info.ready && !page.info.busy && page.info.consent
                    text: "Reintentar"
                    secondary: true; Layout.preferredWidth: 91
                    onClicked: corepulseAI.connectCloud()
                }
                ActionButton {
                    visible: page.info.enabled
                    text: page.showSettings ? "Ocultar ajustes" : "Ajustes"
                    secondary: true
                    Layout.preferredWidth: page.showSettings ? 117 : 88
                    onClicked: {
                        page.settingsExpanded = !page.settingsExpanded
                    }
                }
                ActionButton {
                    text: page.info.enabled ? "Apagar IA" : "Activar IA"
                    Layout.preferredWidth: 118
                    onClicked: {
                        page.settingsExpanded = false
                        corepulseAI.enable(!page.info.enabled)
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: page.showSettings ? 152 : 0
            visible: page.showSettings
            radius: 11; color: page.panel; border.width: 1; border.color: page.borderTone
            clip: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 5
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 35
                    ConsentCheck {
                        Layout.fillWidth: true
                        checked: page.info.consent
                        text: "Permitir enviar mis preguntas al pulsar Enviar"
                        onToggled: corepulseAI.allowQuestions(checked)
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 35
                    ConsentCheck {
                        Layout.fillWidth: true
                        enabled: page.info.consent
                        checked: page.info.hardware
                        text: "Compartir lecturas técnicas del equipo (opcional)"
                        onToggled: corepulseAI.allowHardware(checked)
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 35
                    ConsentCheck {
                        Layout.fillWidth: true
                        enabled: page.info.consent && page.info.hardware
                        checked: Boolean(page.info.historyConsent)
                        text: "Compartir resumen de sesión de Tendencias (y comparación entre sesiones si lo pregunto)"
                        onToggled: corepulseAI.allowHistory(checked)
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Abrir CorePulse no envía preguntas ni lecturas. Solo se envía lo que autorices expresamente."
                    color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.minimumHeight: page.height >= 620 ? 220 : (page.height >= 510 ? 170 : 115)
            radius: 12; color: page.panel; border.width: 1; border.color: page.borderTone
            clip: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    Text { text: "Conversación"; color: page.ink; font.bold: true; font.pixelSize: 16 }
                    Item { Layout.fillWidth: true }
                    Text { text: "Texto"; color: page.muted; font.pixelSize: 12 }
                    ActionButton {
                        text: "A−"; compact: true; secondary: true
                        Layout.preferredWidth: 36
                        enabled: page.chatFontSize > 14
                        onClicked: page.chatFontSize = Math.max(14, page.chatFontSize - 1)
                    }
                    ActionButton {
                        text: "A+"; compact: true; secondary: true
                        Layout.preferredWidth: 36
                        enabled: page.chatFontSize < 19
                        onClicked: page.chatFontSize = Math.min(19, page.chatFontSize + 1)
                    }
                    ActionButton { text: "Borrar chat"; secondary: true; Layout.preferredWidth: 104; onClicked: corepulseAI.clearChat() }
                }
                ListView {
                    id: transcript
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true; spacing: 13
                    model: page.info.messages
                    boundsBehavior: Flickable.StopAtBounds
                    FastWheelHandler { scrollTarget: transcript }
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 7 }
                    delegate: Rectangle {
                        id: bubble
                        required property var modelData
                        required property int index
                        readonly property bool fromUser: bubble.modelData.role === "user"
                        readonly property bool hasDetails: !fromUser && Boolean(bubble.modelData.details)
                        readonly property bool hasSources: !fromUser && bubble.modelData.sources && bubble.modelData.sources.length > 0
                        width: fromUser ? Math.min(transcript.width - 10, 730) : Math.min(transcript.width - 9, 1000)
                        x: fromUser ? Math.max(0, transcript.width - width - 5) : 4
                        height: bubbleContents.implicitHeight + 28
                        radius: 10
                        color: fromUser ? page.raised : "#172A32"
                        border.width: 1
                        border.color: fromUser ? page.borderTone : "#28444D"
                        ColumnLayout {
                            id: bubbleContents
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.leftMargin: 17; anchors.rightMargin: 17; anchors.topMargin: 12
                            spacing: 8
                            Text {
                                id: speaker
                                Layout.fillWidth: true
                                text: bubble.fromUser ? "Tú" : bubble.modelData.verified ? "CorePulse AI · Dictamen verificado" : "CorePulse AI"
                                color: bubble.fromUser ? page.muted : page.accent
                                font.pixelSize: 12; font.bold: true
                                elide: Text.ElideRight
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 27
                                visible: bubble.modelData.verified
                                radius: 7; color: "#20373F"
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left; anchors.leftMargin: 10
                                    text: bubble.modelData.assessmentStatus === "recurrence_observed"
                                          ? "Requiere revisión · Se repitió una incidencia"
                                          : bubble.modelData.assessmentStatus === "no_recurrence_in_recorded_events"
                                          ? "Sin recurrencia detectada en las lecturas disponibles"
                                          : "Cobertura insuficiente para concluir"
                                    color: page.muted; font.pixelSize: 11; font.bold: true
                                }
                            }
                            Text {
                                id: messageText
                                Layout.fillWidth: true
                                text: bubble.modelData.text || ""
                                textFormat: Text.PlainText
                                color: page.ink; font.pixelSize: page.chatFontSize
                                lineHeight: 1.33
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                visible: bubble.hasDetails || bubble.hasSources
                                spacing: 8
                                ActionButton {
                                    text: bubble.modelData.detailsOpen ? "Ocultar análisis" : "Ver análisis completo"
                                    secondary: true; Layout.preferredWidth: bubble.modelData.detailsOpen ? 140 : 155
                                    visible: bubble.hasDetails
                                    // Expansión LOCAL: no genera preguntas ni consume Groq.
                                    onClicked: corepulseAI.toggleMessageDetails(bubble.index)
                                }
                                ActionButton {
                                    text: bubble.modelData.sourcesOpen ? "Ocultar fuentes" : "Fuentes (" + (bubble.hasSources ? bubble.modelData.sources.length : 0) + ")"
                                    secondary: true; Layout.preferredWidth: 120
                                    visible: bubble.hasSources
                                    onClicked: corepulseAI.toggleMessageSources(bubble.index)
                                }
                                Item { Layout.fillWidth: true }
                            }
                            Rectangle {
                                visible: bubble.hasDetails && Boolean(bubble.modelData.detailsOpen)
                                Layout.fillWidth: true
                                Layout.preferredHeight: fullAnalysis.implicitHeight + 26
                                radius: 8; color: "#1A3440"; border.width: 1; border.color: "#315563"
                                Text {
                                    id: fullAnalysis
                                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                                    anchors.leftMargin: 12; anchors.rightMargin: 12; anchors.topMargin: 13
                                    text: bubble.modelData.details || ""
                                    textFormat: Text.PlainText
                                    color: page.ink; font.pixelSize: Math.max(13, page.chatFontSize - 1)
                                    lineHeight: 1.25; wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: bubble.hasSources && Boolean(bubble.modelData.sourcesOpen)
                                spacing: 5
                                Text { text: "Documentación oficial consultada"; color: page.muted; font.pixelSize: 11 }
                                Repeater {
                                    model: bubble.hasSources ? bubble.modelData.sources : []
                                    delegate: Text {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        text: "↗ " + modelData.title
                                        color: page.accent; font.pixelSize: 12
                                        wrapMode: Text.WordWrap
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: Qt.openUrlExternally(modelData.url)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    onCountChanged: Qt.callLater(function() { if (transcript.count > 0) transcript.positionViewAtEnd() })
                    Text {
                        anchors.centerIn: parent
                        visible: transcript.count === 0
                        width: Math.max(0, Math.min(parent.width - 28, 420))
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        color: page.muted; font.pixelSize: 14
                        text: "Puedes preguntarme sobre mantenimiento, rendimiento y hardware. Solo se enviarán datos cuando tú lo autorices."
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 9
            TextArea {
                id: questionInput
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                placeholderText: cuenta.conectado ? "Escribe tu pregunta a CorePulse AI…" : "Inicia sesión para preguntar a CorePulse AI…"
                placeholderTextColor: page.muted
                wrapMode: TextEdit.Wrap
                font.pixelSize: 15; color: page.ink
                enabled: page.info.enabled && page.info.ready && !page.info.busy && page.info.consent
                background: Rectangle { radius: 10; color: page.panel; border.width: 1; border.color: questionInput.activeFocus ? page.accent : page.borderTone }
            }
            ActionButton {
                text: page.info.busy ? "Esperando…" : "Enviar"
                Layout.preferredWidth: 98
                Layout.preferredHeight: 42
                enabled: questionInput.enabled && questionInput.text.trim().length > 0 && questionInput.text.length <= 1800
                onClicked: { const value = questionInput.text; questionInput.text = ""; corepulseAI.send(value) }
            }
        }
        Text {
            Layout.fillWidth: true
            text: "La IA utiliza ai.corepulse.cl sin pedir claves. Al pulsar Enviar se transmite tu pregunta. Solo compartes lecturas o Tendencias si lo autorizas en Ajustes. La IA no cambia Windows."
            color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
        }
    }
}
