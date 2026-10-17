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
    property bool editKey: false
    // V064: la configuracion solo ocupa altura mientras se necesita conectar
    // o cuando el usuario decide mostrarla. Al conectar, priorizar el chat.
    property bool settingsExpanded: false
    readonly property bool showSettings: page.info.enabled &&
                                       (page.settingsExpanded || !page.info.ready || page.editKey)
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
                    text: "Tu asistente de hardware y mantenimiento · GPT-OSS 120B en la nube"
                    color: page.muted; font.pixelSize: 11; elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
            ActionButton { text: "Volver"; secondary: true; Layout.preferredWidth: 88; onClicked: page.goBack() }
        }

        Rectangle {
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
                    visible: page.info.enabled && page.info.ready
                    text: page.showSettings ? "Ocultar ajustes" : "Ajustes"
                    secondary: true
                    Layout.preferredWidth: page.showSettings ? 117 : 88
                    onClicked: {
                        page.settingsExpanded = !page.settingsExpanded
                        if (!page.settingsExpanded) page.editKey = false
                    }
                }
                ActionButton {
                    text: page.info.enabled ? "Apagar IA" : "Activar IA"
                    Layout.preferredWidth: 118
                    onClicked: {
                        keyInput.text = ""
                        page.editKey = false
                        page.settingsExpanded = false
                        corepulseAI.enable(!page.info.enabled)
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: page.showSettings ? (keyArea.visible ? 161 : 111) : 0
            visible: page.showSettings
            radius: 11; color: page.panel; border.width: 1; border.color: page.borderTone
            clip: true
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 5
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 35
                    spacing: 8
                    ConsentCheck {
                        id: questions
                        Layout.fillWidth: true
                        checked: page.info.consent
                        text: "Autorizo enviar mis preguntas a Groq Cloud"
                        onToggled: corepulseAI.allowQuestions(checked)
                    }
                    ActionButton {
                        text: page.info.hasKey ? "Cambiar clave" : "Configurar clave"
                        secondary: true; Layout.preferredWidth: 127
                        onClicked: page.editKey = !page.editKey
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 35
                    spacing: 8
                    ConsentCheck {
                        id: hardware
                        Layout.fillWidth: true
                        enabled: page.info.consent
                        checked: page.info.hardware
                        text: "Compartir lecturas técnicas del equipo (opcional)"
                        onToggled: corepulseAI.allowHardware(checked)
                    }
                    ActionButton {
                        text: page.info.ready ? "Reconectar" : "Conectar IA"
                        Layout.preferredWidth: 127
                        enabled: page.info.consent && page.info.hasKey && !page.info.busy
                        onClicked: corepulseAI.connectCloud()
                    }
                }
                RowLayout {
                    id: keyArea
                    visible: page.editKey || !page.info.hasKey
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    spacing: 8
                    TextField {
                        id: keyInput
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        placeholderText: "Clave privada de Groq · se guarda solo en Windows"
                        echoMode: TextInput.Password
                        font.pixelSize: 12
                        color: page.ink
                        background: Rectangle { radius: 8; color: page.raised; border.width: 1; border.color: keyInput.activeFocus ? page.accent : page.borderTone }
                    }
                    ActionButton {
                        text: "Guardar clave"
                        Layout.preferredWidth: 127
                        enabled: keyInput.text.trim().length > 0 && !page.info.busy
                        onClicked: {
                            const ok = corepulseAI.saveApiKey(keyInput.text)
                            keyInput.text = ""
                            if (ok) page.editKey = false
                        }
                    }
                }
            }
        }

        Rectangle {
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
                        readonly property bool fromUser: bubble.modelData.role === "user"
                        width: fromUser ? Math.min(transcript.width - 10, 730) : Math.min(transcript.width - 9, 1000)
                        x: fromUser ? Math.max(0, transcript.width - width - 5) : 4
                        height: speaker.implicitHeight + messageText.implicitHeight + 38
                        radius: 10
                        color: fromUser ? page.raised : "#172A32"
                        border.width: 1
                        border.color: fromUser ? page.borderTone : "#28444D"
                        Text {
                            id: speaker
                            anchors.top: parent.top; anchors.topMargin: 12
                            anchors.left: parent.left; anchors.leftMargin: 17
                            anchors.right: parent.right; anchors.rightMargin: 17
                            text: bubble.fromUser ? "Tú" : "CorePulse AI"
                            color: bubble.fromUser ? page.muted : page.accent
                            font.pixelSize: 12; font.bold: true
                            elide: Text.ElideRight
                        }
                        Text {
                            id: messageText
                            anchors.top: speaker.bottom; anchors.topMargin: 8
                            anchors.left: parent.left; anchors.leftMargin: 17
                            anchors.right: parent.right; anchors.rightMargin: 17
                            text: bubble.modelData.text
                            textFormat: Text.PlainText
                            color: page.ink; font.pixelSize: page.chatFontSize
                            lineHeight: 1.33
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
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
                placeholderText: "Escribe tu pregunta a CorePulse AI…"
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
            text: "Sin cambios automáticos. Datos ausentes: N/A. El contenido enviado a Groq no puede retirarse después."
            color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
        }
    }
}
