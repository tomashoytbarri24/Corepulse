import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: page
    signal goBack()

    property bool compactMode: overlayController.data.compact
    property bool showTemps: overlayController.data.temperatures
    property string corner: overlayController.data.corner
    property string captureAction: ""
    property string captureMessage: ""

    readonly property var m: telemetry && telemetry.metrics ? telemetry.metrics : ({})
    readonly property var performanceInfo: performanceHealth && performanceHealth.data ? performanceHealth.data : ({activeGame:{active:false, name:"", source:"", artUrl:"", artKind:"", session:"N/A", state:"N/A"}, probableGames:[]})
    readonly property var activeGame: performanceInfo.activeGame || ({active:false, name:"", source:"", artUrl:"", artKind:"", session:"N/A", state:"N/A"})

    readonly property color panel: themeManager.palette.panel
    readonly property color panelRaised: themeManager.palette.panelRaised
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.accent
    readonly property color cyan: themeManager.palette.cyan
    readonly property color purple: themeManager.palette.purple


    function valid(value) { return typeof value === "number" && isFinite(value) }
    function percent(value) { return valid(value) ? Math.round(value) + "%" : "N/A" }
    function temp(value) { return valid(value) ? Number(value).toFixed(1) + " °C" : "N/A" }
    function amount(value) { return valid(value) ? Number(value).toFixed(1) + " GB" : "N/A" }
    function labelForCorner(code) {
        return code === "top-left" ? "Superior izquierda" :
               code === "top-right" ? "Superior derecha" :
               code === "bottom-left" ? "Inferior izquierda" : "Inferior derecha"
    }

    // Entrar a esta página NO arranca RTSS. Lo hace el monitor de juegos y tiendas,
    // o el usuario mediante Mostrar / el atajo explícito.

    FileDialog {
        id: rtssChooser
        title: "Localizar RivaTuner Statistics Server (RTSS.exe)"
        nameFilters: ["Ejecutable RTSS (RTSS.exe)", "Aplicaciones (*.exe)"]
        onAccepted: overlayController.setRtssPath(selectedFile.toString())
    }

    FocusScope {
        id: shortcutCapture
        width: 1; height: 1
        focus: false
        Keys.onPressed: function(event) {
            if (!page.captureAction) return
            event.accepted = true
            if (event.key === Qt.Key_Escape) { page.captureAction = ""; page.captureMessage = "Captura cancelada."; return }
            if ([Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta].indexOf(event.key) >= 0) return
            if (event.modifiers & Qt.MetaModifier) {
                page.captureMessage = "No se admite la tecla Windows como modificador."
                return
            }
            var modifiers = []
            if (event.modifiers & Qt.ControlModifier) modifiers.push("Ctrl")
            if (event.modifiers & Qt.AltModifier) modifiers.push("Alt")
            if (event.modifiers & Qt.ShiftModifier) modifiers.push("Shift")
            if (modifiers.length < 2) {
                page.captureMessage = "Usa al menos dos modificadores (Ctrl, Alt o Shift)."
                return
            }
            var key = ""
            if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) key = String.fromCharCode(event.key)
            else if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) key = String.fromCharCode(event.key)
            else if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F12) key = "F" + (event.key - Qt.Key_F1 + 1)
            else {
                page.captureMessage = "Usa una letra, número o F1–F12."
                return
            }
            overlayController.setShortcut(page.captureAction, modifiers.join("+") + "+" + key)
            page.captureAction = ""
            page.captureMessage = "Validando el atajo con Windows…"
        }
    }

    Shortcut {
        sequence: "Escape"
        context: Qt.ApplicationShortcut
        enabled: page.captureAction !== ""
        onActivated: {
            page.captureAction = ""
            page.captureMessage = "Captura cancelada."
        }
    }


    FastFlickable {
        id: pageScroll
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + 16
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
        id: contentColumn
        width: Math.max(0, pageScroll.width - 12)
        x: 0
        y: 0
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Rectangle {
                Layout.preferredWidth: 48; Layout.preferredHeight: 48
                radius: 14; color: page.panelRaised
                Glyph { anchors.centerIn: parent; width: 26; height: 26; kind: "layers"; ink: page.cyan }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 4
                Text { text: "Overlay"; color: page.ink; font.pixelSize: 22; font.bold: true }
                Text { text: "RivaTuner Statistics Server · OSD real en juegos compatibles"; color: page.muted; font.pixelSize: 11 }
            }
            Rectangle {
                Layout.preferredWidth: 92; Layout.preferredHeight: 36
                radius: 10; color: backMouse.containsMouse ? page.panelRaised : "#22293A"
                Text { anchors.centerIn: parent; text: "Volver"; color: page.ink; font.pixelSize: 12; font.bold: true }
                MouseArea { id: backMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.goBack() }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: statusColumn.implicitHeight + 30
            radius: 16; color: page.panel; border.width: 1; border.color: page.edge
            ColumnLayout {
                id: statusColumn
                anchors.fill: parent; anchors.margins: 15; spacing: 9
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    Rectangle {
                        Layout.preferredWidth: 10; Layout.preferredHeight: 10; radius: 5
                        color: overlayController.data.active ? "#6BAE86" : overlayController.data.busy ? "#D1AB67" : "#A8AAB4"
                    }
                    Text { text: overlayController.data.busy ? "INICIANDO RTSS" : overlayController.data.osdPublished ? "OSD PUBLICADO" : overlayController.data.active ? "RTSS CONECTADO · ENVIANDO" : "OVERLAY OCULTO"; color: page.ink; font.pixelSize: 13; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        Layout.preferredWidth: 125; Layout.preferredHeight: 36; radius: 11
                        color: startMouse.containsMouse?Qt.lighter(themeManager.palette.panelRaised,1.22):themeManager.palette.panelRaised
                        border.width: 1; border.color: startMouse.containsMouse?themeManager.palette.action:themeManager.palette.panelBorder
                        Text { anchors.centerIn: parent; text: overlayController.data.busy ? "Iniciando…" : "Mostrar"; color: (overlayController.data.busy)?"#8993A5":themeManager.palette.action; font.pixelSize: 12; font.bold: true }
                        MouseArea { id: startMouse; anchors.fill: parent; hoverEnabled: true; enabled: !overlayController.data.busy; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.start() }
                    }
                    Rectangle {
                        Layout.preferredWidth: 112; Layout.preferredHeight: 36; radius: 11
                        color: stopMouse.containsMouse?Qt.lighter(themeManager.palette.panelRaised,1.22):themeManager.palette.panelRaised
                        border.width: 1; border.color: stopMouse.containsMouse?themeManager.palette.action:themeManager.palette.panelBorder
                        Text { anchors.centerIn: parent; text: "Ocultar"; color: themeManager.palette.action; font.pixelSize: 12; font.bold: true }
                        MouseArea { id: stopMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.hide() }
                    }
                }
                Text { Layout.fillWidth: true; text: overlayController.data.message; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: "RTSS se inicia cuando aparece un juego o plataforma nueva (Steam, Epic, Riot, EA, Xbox y otras compatibles). Abrir CorePulse o esta pestaña no lo inicia. El botón Mostrar y su atajo permiten iniciarlo manualmente."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; visible: !!overlayController.data.osdPublished; text: "Última publicación: " + overlayController.data.lastPublish + ". Publicado no significa visible en un juego: en RTSS revisa Show On-Screen Display y el nivel de detección de la aplicación."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; text: "Si sigue invisible: verifica que RTSS tenga activado Show On-Screen Display, revisa que el perfil del juego no esté deshabilitado y prueba en un juego compatible sin protecciones anticheat. CorePulse no fuerza la inyección ni modifica perfiles RTSS."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
            }
        }

        GridLayout {
            id: overlayBody
            Layout.fillWidth: true
            columns: contentColumn.width < 920 ? 1 : 2
            rowSpacing: 14
            columnSpacing: 14

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(360, Math.min(page.height * 0.66, 540))
                Layout.minimumHeight: 320
                radius: 18; color: page.panel; border.width: 1; border.color: page.edge

                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Vista previa"; color: page.ink; font.pixelSize: 16; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: labelForCorner(page.corner); color: page.muted; font.pixelSize: 11 }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 16
                        color: "#0B1020"
                        border.width: 1; border.color: Qt.alpha(page.cyan, 0.20)
                        gradient: Gradient {
                            GradientStop { position: 0; color: "#0B1020" }
                            GradientStop { position: 1; color: "#171124" }
                        }
                        Rectangle {
                            id: overlayPreview
                            width: Math.min(parent.width - 24, page.compactMode ? 280 : 392)
                            height: Math.min(parent.height - 24, page.compactMode ? previewContent.implicitHeight + 24 : 170)
                            radius: 14
                            color: "#BC081018"
                            border.width: 1; border.color: Qt.alpha(page.cyan, 0.35)
                            anchors.top: page.corner.indexOf("top") === 0 ? parent.top : undefined
                            anchors.bottom: page.corner.indexOf("bottom") === 0 ? parent.bottom : undefined
                            anchors.left: page.corner.indexOf("left") >= 0 ? parent.left : undefined
                            anchors.right: page.corner.indexOf("right") >= 0 ? parent.right : undefined
                            anchors.margins: 18
                            ColumnLayout {
                                id: previewContent
                                anchors.fill: parent; anchors.margins: 12; spacing: page.compactMode ? 6 : 8
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: activeGame.active ? activeGame.name : "Sin juego activo"; color: "#F6F8FD"; font.pixelSize: page.compactMode ? 13 : 15; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Rectangle { radius: 8; color: Qt.alpha(page.accent, 0.18); border.width: 1; border.color: Qt.alpha(page.accent, 0.5); implicitWidth: badgeText.implicitWidth + 16; implicitHeight: 24
                                        Text { id: badgeText; anchors.centerIn: parent; text: activeGame.active ? (activeGame.source || "Juego") : "Esperando"; color: page.accent; font.pixelSize: 10; font.bold: true }
                                    }
                                }
                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: page.compactMode ? 2 : 3
                                    columnSpacing: 8; rowSpacing: 8
                                    Repeater {
                                        model: [
                                            {name:"CPU", value: percent(m.cpuPercent), detail: showTemps ? temp(m.cpuTemp) : ""},
                                            {name:"GPU", value: percent(m.gpuPercent), detail: showTemps ? temp(m.gpuTemp) : ""},
                                            {name:"RAM", value: percent(m.ramPercent), detail: amount(m.ramUsed) + " / " + amount(m.ramTotal)},
                                            {name:"VRAM", value: amount(m.gpuVramUsed), detail: amount(m.gpuVramTotal)},
                                            {name:"FPS", value: overlayController.data.fpsValue || "N/A", detail: overlayController.data.fpsMessage || "Esperando RTSS"},
                                            {name:"Tiempo", value: activeGame.active ? activeGame.session : "N/A", detail: activeGame.active ? (activeGame.state || "En ejecución") : "Sin juego"}
                                        ]
                                        delegate: Rectangle {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: page.compactMode ? 34 : 42
                                            radius: 10
                                            color: "#7D0C1422"
                                            border.width: 1
                                            border.color: "#25374A"
                                            Column {
                                                anchors.fill: parent; anchors.margins: 8; spacing: 1
                                                Text { text: modelData.name + "  " + modelData.value; color: "#F1F4FA"; font.pixelSize: page.compactMode ? 10 : 11; font.bold: true; elide: Text.ElideRight }
                                                Text { visible: !page.compactMode; text: modelData.detail; color: "#AEB8CB"; font.pixelSize: 9; elide: Text.ElideRight }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "FPS solo se muestra cuando RTSS entrega una muestra fresca para el proceso de juego detectado. Sin muestra válida, se mantiene N/A."
                        color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredWidth: contentColumn.width >= 920 ? Math.max(300, contentColumn.width * 0.30) : -1
                Layout.maximumWidth: contentColumn.width >= 920 ? Math.max(340, contentColumn.width * 0.38) : contentColumn.width
                Layout.preferredHeight: Math.max(360, Math.min(page.height * 0.66, 540))
                Layout.minimumHeight: 320
                radius: 18; color: page.panel; border.width: 1; border.color: page.edge
                Flickable {
                    id: optionsScroll
                    anchors.fill: parent
                    anchors.rightMargin: 13
                    contentWidth: width
                    contentHeight: optionsColumn.implicitHeight + 32
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    FastWheelHandler { scrollTarget: optionsScroll }
                    ColumnLayout {
                        id: optionsColumn
                        width: Math.max(0, optionsScroll.width - 30)
                        anchors.left: parent.left; anchors.leftMargin: 15
                        anchors.top: parent.top; anchors.topMargin: 16
                        spacing: 12

                        Text { text: "Ajustes del overlay"; color: page.ink; font.pixelSize: 16; font.bold: true }
                        Text { Layout.fillWidth: true; text: "Puedes cambiar la composición del overlay y ver el resultado inmediatamente en la vista previa."; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }

                        Rectangle {
                            Layout.fillWidth: true; radius: 14; color: page.panel
                            border.width: 1; border.color: page.edge
                            implicitHeight: hotkeyColumn.implicitHeight + 24
                            ColumnLayout {
                                id: hotkeyColumn; anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "Atajos de teclado globales"; color: page.ink; font.pixelSize: 13; font.bold: true }
                                Text { Layout.fillWidth: true; text: "Captura dos modificadores y una tecla. Funcionan sin CorePulse visible, cuando Windows permite registrarlos."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Repeater {
                                    model: [{id:"show", label:"Mostrar overlay"}, {id:"hide", label:"Ocultar overlay"}]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true; Layout.preferredHeight: 52
                                        radius: 11; color: page.panelRaised; border.width: 1
                                        border.color: page.captureAction === modelData.id ? page.accent : page.edge
                                        Item {
                                            anchors.fill: parent; anchors.margins: 10
                                            ColumnLayout {
                                                anchors.left: parent.left; anchors.right: parent.horizontalCenter; anchors.rightMargin: 42
                                                anchors.verticalCenter: parent.verticalCenter; spacing: 3
                                                Text { Layout.fillWidth: true; text: modelData.label; color: page.ink; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                                Text {
                                                    Layout.fillWidth: true
                                                    text: page.captureAction === modelData.id ? "Pulsa tu combinación… (Esc cancela)" : (modelData.id === "show" ? overlayController.data.showShortcut : overlayController.data.hideShortcut)
                                                    color: page.captureAction === modelData.id ? page.accent : page.muted; font.pixelSize: 10; elide: Text.ElideRight
                                                }
                                            }
                                            Rectangle {
                                                anchors.centerIn: parent
                                                width: 70; height: 30
                                                radius: 9
                                                color: page.captureAction === modelData.id ? Qt.alpha(page.accent, 0.16) : page.panel
                                                border.width: 1; border.color: page.edge
                                                Text { anchors.centerIn: parent; text: "Cambiar"; color: themeManager.palette.action; font.pixelSize: 10; font.bold: true }
                                                MouseArea {
                                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                    onClicked: { page.captureAction = modelData.id; page.captureMessage = ""; shortcutCapture.forceActiveFocus() }
                                                }
                                            }
                                        }
                                    }
                                }
                                Text { Layout.fillWidth: true; text: page.captureMessage ? page.captureMessage : overlayController.data.hotkeyStatus; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true; radius: 14; color: page.panel
                            border.width: 1; border.color: page.edge
                            implicitHeight: locationColumn.implicitHeight + 22
                            ColumnLayout {
                                id: locationColumn; anchors.fill: parent; anchors.margins: 11; spacing: 9
                                Text { text: "RivaTuner Statistics Server"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text { Layout.fillWidth: true; text: overlayController.data.rtssPath || "Búsqueda automática en carpetas de instalación"; color: page.muted; font.pixelSize: 10; wrapMode: Text.WrapAnywhere }
                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 32; radius: 9
                                    color: browseMouse.containsMouse?Qt.lighter(themeManager.palette.panelRaised,1.22):themeManager.palette.panelRaised
                                    border.width: 1; border.color: browseMouse.containsMouse?themeManager.palette.action:themeManager.palette.panelBorder
                                    Text { anchors.centerIn: parent; text: "Localizar RTSS.exe"; color: themeManager.palette.action; font.pixelSize: 11; font.bold: true }
                                    MouseArea { id: browseMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: rtssChooser.open() }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: modeBox.implicitHeight + 20
                            ColumnLayout { id: modeBox; anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "Modo"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                RowLayout { Layout.fillWidth: true; spacing: 8
                                    Repeater { model: [{id:true, label:"Compacto"}, {id:false, label:"Extendido"}]
                                        delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 10; color: page.compactMode === modelData.id ? Qt.alpha(page.accent, 0.16) : page.panelRaised; border.width: 1; border.color: page.compactMode === modelData.id ? Qt.alpha(page.accent, 0.6) : page.edge
                                            Text { anchors.centerIn: parent; text: modelData.label; color: page.ink; font.pixelSize: 11; font.bold: true }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setOption("compact", modelData.id) }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: posBox.implicitHeight + 20
                            ColumnLayout { id: posBox; anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "Posición"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                GridLayout { Layout.fillWidth: true; columns: 2; columnSpacing: 8; rowSpacing: 8
                                    Repeater { model: [{id:"top-left", label:"Sup. izquierda"}, {id:"top-right", label:"Sup. derecha"}, {id:"bottom-left", label:"Inf. izquierda"}, {id:"bottom-right", label:"Inf. derecha"}]
                                        delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 10; color: page.corner === modelData.id ? Qt.alpha(page.cyan, 0.16) : page.panelRaised; border.width: 1; border.color: page.corner === modelData.id ? Qt.alpha(page.cyan, 0.55) : page.edge
                                            Text { anchors.centerIn: parent; text: modelData.label; color: page.ink; font.pixelSize: 11; font.bold: true }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setCorner(modelData.id) }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: dataBox.implicitHeight + 20
                            ColumnLayout { id: dataBox; anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "Lecturas"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 36; radius: 10; color: page.showTemps ? Qt.alpha(page.purple, 0.16) : page.panelRaised; border.width: 1; border.color: page.showTemps ? Qt.alpha(page.purple, 0.55) : page.edge
                                    Text { anchors.centerIn: parent; text: page.showTemps ? "Ocultar temperaturas" : "Mostrar temperaturas"; color: page.ink; font.pixelSize: 11; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setOption("temperatures", !page.showTemps) }
                                }
                                Text { Layout.fillWidth: true; text: "CPU, GPU, RAM y FPS usan lecturas directas. FPS proviene de RTSS Shared Memory y queda como N/A si no hay una muestra reciente para el juego. La posición final se configura en RTSS."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: stateBox.implicitHeight + 20
                            ColumnLayout { id: stateBox; anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Text { text: "Estado"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text { Layout.fillWidth: true; text: activeGame.active ? ("Juego detectado: " + activeGame.name) : "Aún no hay juego activo"; color: activeGame.active ? page.accent : page.ink; font.pixelSize: 12; font.bold: true; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: activeGame.active ? ("Origen: " + activeGame.source + " · Sesión: " + activeGame.session) : "Abre un juego compatible para que el overlay use la misma detección del módulo de rendimiento."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                            }
                        }
                    }
                }
                ThinScroll {
                    target: optionsScroll
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.right: parent.right
                    anchors.topMargin: 10
                    anchors.bottomMargin: 10
                    z: 2
                }
            }
        }
        }
    }
    ThinScroll {
        target: pageScroll
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        z: 3
    }
}
