import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()

    property bool compactMode: overlayController.data.compact
    property bool showTemps: overlayController.data.temperatures
    property string corner: overlayController.data.corner
    property string captureAction: ""
    property string captureMessage: ""
    // REBUILD 210: separar el uso diario del ajuste técnico sin quitar opciones.
    property string settingsSection: "design"

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
    function hardwareAccent(name, kind) {
        const brand = String(name || "").toLowerCase()
        if (brand.indexOf("nvidia") >= 0 || brand.indexOf("geforce") >= 0) return "#76B900"
        if (brand.indexOf("intel") >= 0 || brand.indexOf("arc") >= 0) return "#1688F3"
        if (brand.indexOf("amd") >= 0 || brand.indexOf("ryzen") >= 0 || brand.indexOf("radeon") >= 0)
            return kind === "gpu" && /amd|ryzen|radeon/i.test(String(m.cpuName || "")) ? "#F28C28" : "#E34245"
        return kind === "gpu" ? "#BB57EF" : "#1AB9F7"
    }
    function labelForCorner(code) {
        return code === "top-left" ? "Superior izquierda" :
               code === "top-right" ? "Superior derecha" :
               code === "bottom-left" ? "Inferior izquierda" : "Inferior derecha"
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
            if (modifiers.length < 1) {
                page.captureMessage = "Usa al menos un modificador (Ctrl, Alt o Shift), por ejemplo Shift+P."
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
            Glyph { Layout.preferredWidth: 36; Layout.preferredHeight: 36; kind: "layers"; ink: page.cyan }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 4
                Text { text: "Overlay"; color: page.ink; font.pixelSize: 22; font.bold: true }
                Text { text: "Estado, diseño y controles del overlay"; color: page.muted; font.pixelSize: 11 }
            }
            HeaderAction { label: "Volver"; onActivated: page.goBack() }
        }

        GlassPanel {
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
                    Text { text: overlayController.data.busy ? "INICIANDO" : overlayController.data.active ? "OVERLAY ACTIVO" : "OVERLAY OCULTO"; color: page.ink; font.pixelSize: 13; font.bold: true }
                    Item { Layout.fillWidth: true }
                    // REBUILD 200: activar o desactivar el overlay desde aquí (igual que Ctrl+Shift+O).
                    Rectangle {
                        id: overlayToggle
                        readonly property bool on: !!overlayController.data.active
                        Layout.preferredWidth: toggleLabel.implicitWidth + 34; Layout.preferredHeight: 34; radius: 10
                        opacity: overlayController.data.busy ? 0.5 : 1
                        color: on ? (toggleMouse.containsMouse ? "#542831" : "#38232D")
                                  : (toggleMouse.containsMouse ? Qt.alpha(page.accent, 0.30) : Qt.alpha(page.accent, 0.18))
                        border.width: 1; border.color: on ? "#8D4852" : Qt.alpha(page.accent, 0.7)
                        Text { id: toggleLabel; anchors.centerIn: parent; text: overlayToggle.on ? "Desactivar overlay" : "Activar overlay"; color: overlayToggle.on ? "#FFAFB5" : page.ink; font.pixelSize: 12; font.bold: true }
                        MouseArea {
                            id: toggleMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            enabled: !overlayController.data.busy
                            onClicked: overlayToggle.on ? overlayController.hide() : overlayController.start()
                        }
                    }
                }
                Text { Layout.fillWidth: true; visible: !!overlayController.data.osdPublished; text: "Actualizado " + overlayController.data.lastPublish + " · " + overlayController.data.fpsMessage; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                Text { Layout.fillWidth: true; visible: !!overlayController.data.fpsPermissionRequired; text: "Windows bloqueó la medición de FPS. Puedes reiniciar CorePulse con permisos de administrador antes de entrar al juego; Windows pedirá autorización."; color: "#E6B669"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                Rectangle { Layout.preferredWidth: 255; Layout.preferredHeight: 36; visible: !!overlayController.data.fpsPermissionRequired; radius: 10; color: fpsAdminMouse.containsMouse ? Qt.alpha(page.accent, 0.24) : page.panelRaised; border.width: 1; border.color: Qt.alpha(page.accent, 0.7)
                    Text { anchors.centerIn: parent; text: "Activar FPS · reiniciar con UAC"; color: page.ink; font.pixelSize: 11; font.bold: true }
                    MouseArea { id: fpsAdminMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.restartElevated() }
                }
                Text { Layout.fillWidth: true; visible: overlayController.data.fpsQuality === "VALID_ETW"; text: "API: " + overlayController.data.graphicsRuntime + " · Presentación: " + overlayController.data.presentMode; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
            }
        }

        // Acceso claro a lo esencial y a la configuración técnica.
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [
                    {id:"design", title:"Diseño", hint:"Vista y estilo"},
                    {id:"controls", title:"Controles", hint:"Atajos y posición"},
                    {id:"advanced", title:"Avanzado", hint:"Detección y permisos"}
                ]
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool selected: page.settingsSection === modelData.id
                    Layout.fillWidth: true
                    Layout.preferredHeight: 54
                    radius: 12
                    color: selected ? Qt.alpha(page.accent, 0.13) : page.panel
                    border.width: selected ? 1.5 : 1
                    border.color: selected ? page.accent : page.edge
                    Column {
                        anchors.left: parent.left; anchors.leftMargin: 13
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3
                        Text { text: modelData.title; color: selected ? page.accent : page.ink; font.pixelSize: 12; font.bold: true }
                        Text { text: modelData.hint; color: page.muted; font.pixelSize: 10 }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: page.settingsSection = modelData.id }
                }
            }
        }

        // REBUILD 200: estilo del overlay, justo debajo del estado.
        GlassPanel {
            visible: page.settingsSection === "design"
            Layout.fillWidth: true
            Layout.preferredHeight: styleColumn.implicitHeight + 30
            radius: 16; color: page.panel; border.width: 1; border.color: page.edge
            ColumnLayout {
                id: styleColumn
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 15
                spacing: 10
                Text { text: "Estilo del overlay"; color: page.ink; font.pixelSize: 13; font.bold: true }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    Repeater {
                        model: [{id: "minimal", title: "Minimalista", text: "Una sola línea: FPS, frametime, CPU, GPU y RAM."},
                                {id: "advanced", title: "Avanzada", text: "Panel completo con tarjetas y gráfico de frametime."}]
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool chosen: (overlayController.data.style || "advanced") === modelData.id
                            Layout.fillWidth: true; Layout.preferredHeight: 70; radius: 12
                            color: chosen ? Qt.alpha(page.accent, 0.14) : page.panelRaised
                            border.width: chosen ? 2 : 1; border.color: chosen ? page.accent : styleMouse.containsMouse ? Qt.alpha(page.accent, 0.45) : page.edge
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Rectangle {
                                    Layout.preferredWidth: 18; Layout.preferredHeight: 18; radius: 9; color: "transparent"
                                    border.width: 2; border.color: parent.parent.chosen ? page.accent : page.edge
                                    Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: page.accent; visible: parent.parent.parent.chosen }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text { text: modelData.title; color: page.ink; font.pixelSize: 13; font.bold: true }
                                    Text { Layout.fillWidth: true; text: modelData.text; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                }
                            }
                            MouseArea { id: styleMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setStyle(modelData.id) }
                        }
                    }
                }
            }
        }

        GridLayout {
            id: overlayBody
            Layout.fillWidth: true
            columns: 1
            rowSpacing: 14
            columnSpacing: 14

            GlassPanel {
                visible: page.settingsSection === "design"
                Layout.fillWidth:true
                Layout.preferredHeight:designEditor.implicitHeight+32
                OverlayDesigner { id:designEditor;anchors.fill:parent;anchors.margins:16 }
            }

            GlassPanel {
                visible: page.settingsSection !== "design"
                Layout.fillWidth: true
                Layout.preferredWidth: contentColumn.width
                Layout.maximumWidth: contentColumn.width
                // REBUILD 197: altura completa; la página entera baja con un solo scroll.
                Layout.preferredHeight: optionsColumn.implicitHeight + 32
                radius: 18; color: page.panel; border.width: 1; border.color: page.edge
                Item {
                    id: optionsArea
                    anchors.fill: parent
                    ColumnLayout {
                        id: optionsColumn
                        width: Math.max(0, optionsArea.width - 30)
                        anchors.left: parent.left; anchors.leftMargin: 15
                        anchors.top: parent.top; anchors.topMargin: 16
                        spacing: 12

                        Text {
                            text: page.settingsSection === "controls" ? "Controles del overlay" : "Detección y permisos"
                            color: page.ink; font.pixelSize: 16; font.bold: true
                        }
                        Text {
                            Layout.fillWidth: true
                            text: page.settingsSection === "controls" ? "Configura cómo abrirlo y qué información mostrar." : "Opciones para compatibilidad y diagnóstico."
                            color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }

                        GlassPanel {
                            visible: page.settingsSection === "controls"
                            Layout.fillWidth: true; radius: 14; color: page.panel
                            border.width: 1; border.color: page.edge
                            implicitHeight: hotkeyColumn.implicitHeight + 24
                            ColumnLayout {
                                id: hotkeyColumn; anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "Atajos de teclado globales"; color: page.ink; font.pixelSize: 13; font.bold: true }
                                Repeater {
                                    model: [{id:"show", label:"Mostrar / ocultar overlay"}, {id:"quick", label:"Panel rápido"}]
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
                                                    text: page.captureAction === modelData.id ? "Pulsa tu combinación… (Esc cancela)" : (modelData.id === "show" ? overlayController.data.showShortcut : overlayController.data.quickPanelShortcut)
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

                        GlassPanel { visible: page.settingsSection === "controls"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: modeBox.implicitHeight + 20
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

                        GlassPanel { visible: page.settingsSection === "controls"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: posBox.implicitHeight + 20
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

                        GlassPanel { visible: page.settingsSection === "controls"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: dataBox.implicitHeight + 20
                            ColumnLayout { id: dataBox; anchors.fill: parent; anchors.margins: 12; spacing: 10
                                Text { text: "Lecturas"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 36; radius: 10; color: page.showTemps ? Qt.alpha(page.purple, 0.16) : page.panelRaised; border.width: 1; border.color: page.showTemps ? Qt.alpha(page.purple, 0.55) : page.edge
                                    Text { anchors.centerIn: parent; text: page.showTemps ? "Ocultar temperaturas" : "Mostrar temperaturas"; color: page.ink; font.pixelSize: 11; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setOption("temperatures", !page.showTemps) }
                                }
                            }
                        }

                        GlassPanel { visible: page.settingsSection === "advanced"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: hookBox.implicitHeight + 20
                            ColumnLayout { id: hookBox; anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Text { text: "Módulo dentro del juego"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text { Layout.fillWidth: true; text: "Opcional. Inyecta el módulo en el juego; puede causar incompatibilidades o sanciones. Úsalo solo en juegos sin antitrampas ni modo en línea."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: overlayController.data.lastGameKey ? "Juego: " + overlayController.data.lastGameName : "Abre un juego para poder elegirlo."; color: page.ink; font.pixelSize: 11; wrapMode: Text.WordWrap }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; visible: !!overlayController.data.lastGameKey; radius: 9; color: overlayController.data.lastGameAllowed ? Qt.alpha("#E6B669", 0.16) : page.panelRaised; border.width: 1; border.color: overlayController.data.lastGameAllowed ? Qt.alpha("#E6B669", 0.6) : page.edge
                                    Text { anchors.centerIn: parent; text: overlayController.data.lastGameAllowed ? "Apagar módulo en este juego" : "Permitir módulo en este juego"; color: page.ink; font.pixelSize: 11; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setHookAllowed(!overlayController.data.lastGameAllowed) }
                                }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 32; visible: (overlayController.data.hookGameCount || 0) > 0; radius: 9; color: page.panelRaised; border.width: 1; border.color: page.edge
                                    Text { anchors.centerIn: parent; text: "Quitar todos los permisos (" + overlayController.data.hookGameCount + ")"; color: page.ink; font.pixelSize: 10; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.clearHookGames() }
                                }
                            }
                        }

                        // REBUILD 197: los FPS se miden en cualquier ventana; aquí se corrige la detección.
                        GlassPanel { visible: page.settingsSection === "advanced"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: measureBox.implicitHeight + 20
                            ColumnLayout { id: measureBox; anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Text { text: "Medición de FPS"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text { Layout.fillWidth: true; text: "Elige qué programas deben incluir medición de FPS."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: overlayController.data.measureName ? ("Último programa al frente: " + overlayController.data.measureName) : "Pon un programa o juego al frente para poder elegirlo."; color: page.ink; font.pixelSize: 11; font.bold: true; wrapMode: Text.WordWrap }
                                RowLayout { Layout.fillWidth: true; spacing: 6; visible: !!overlayController.data.measureName
                                    Repeater {
                                        model: [{id:"auto", label:"Automático"}, {id:"always", label:"Medir siempre"}, {id:"never", label:"No medir"}]
                                        delegate: Rectangle {
                                            required property var modelData
                                            readonly property bool chosen: (overlayController.data.measureRule || "auto") === modelData.id
                                            Layout.fillWidth: true; Layout.preferredHeight: 32; radius: 9
                                            color: chosen ? Qt.alpha(page.accent, 0.18) : page.panelRaised
                                            border.width: 1; border.color: chosen ? Qt.alpha(page.accent, 0.7) : page.edge
                                            Text { anchors.centerIn: parent; text: modelData.label; color: page.ink; font.pixelSize: 10; font.bold: chosen }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setMeasureRule(modelData.id) }
                                        }
                                    }
                                }
                            }
                        }

                        GlassPanel { visible: page.settingsSection === "advanced"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: permitBox.implicitHeight + 20
                            ColumnLayout { id: permitBox; anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Text { text: "Permisos de Windows"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text { Layout.fillWidth: true; text: overlayController.data.elevated ? "CorePulse tiene permisos completos." : "CorePulse funciona sin administrador. La temperatura de CPU, los FPS por eventos y la limpieza profunda pueden requerir permisos completos."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; visible: !overlayController.data.elevated; radius: 9; color: page.panelRaised; border.width: 1; border.color: Qt.alpha(page.accent, 0.7)
                                    Text { anchors.centerIn: parent; text: "Reiniciar con permisos completos"; color: page.ink; font.pixelSize: 11; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.restartElevated() }
                                }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; visible: !overlayController.data.elevated && !overlayController.data.perfLogMember && !overlayController.data.perfLogPending; radius: 9; color: page.panelRaised; border.width: 1; border.color: page.edge
                                    Text { anchors.centerIn: parent; text: "Permitir FPS sin administrador"; color: page.ink; font.pixelSize: 11; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.allowFpsWithoutAdmin() }
                                }
                                Text { Layout.fillWidth: true; visible: !overlayController.data.elevated; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap
                                    text: overlayController.data.perfLogMember ? "Los FPS funcionan sin administrador en esta cuenta."
                                        : overlayController.data.perfLogPending ? "Cambio aplicado: cierra sesión en Windows y vuelve a entrar."
                                        : "Agrega tu usuario al grupo de Windows «Performance Log Users». Windows lo confirma una vez y hay que cerrar sesión." }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 9; color: overlayController.data.alwaysAdmin ? Qt.alpha(page.accent, 0.18) : page.panelRaised; border.width: 1; border.color: overlayController.data.alwaysAdmin ? Qt.alpha(page.accent, 0.6) : page.edge
                                    Text { anchors.centerIn: parent; text: "Abrir siempre con permisos: " + (overlayController.data.alwaysAdmin ? "Sí" : "No"); color: page.ink; font.pixelSize: 11; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.setAlwaysAdmin(!overlayController.data.alwaysAdmin) }
                                }
                            }
                        }

                        GlassPanel { visible: page.settingsSection === "advanced"; Layout.fillWidth: true; radius: 14; color: page.panel; border.width: 1; border.color: page.edge; implicitHeight: stateBox.implicitHeight + 20
                            ColumnLayout { id: stateBox; anchors.fill: parent; anchors.margins: 12; spacing: 8
                                Text { text: "Estado"; color: page.ink; font.pixelSize: 12; font.bold: true }
                                Text { Layout.fillWidth: true; text: activeGame.active ? ("Juego detectado: " + activeGame.name) : "Aún no hay juego activo"; color: activeGame.active ? page.accent : page.ink; font.pixelSize: 12; font.bold: true; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: activeGame.active ? ("Origen: " + activeGame.source + " · Sesión: " + activeGame.session) : "CorePulse espera un juego en primer plano. El atajo de mostrar también permite apuntar a juegos fuera de las tiendas reconocidas."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: "Ventana al frente: " + (overlayController.data.foregroundName || "N/A") + " · PID objetivo: " + (overlayController.data.targetPid || "ninguno"); color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: "Último juego: " + (overlayController.data.lastGameName || "N/A") + " · " + (overlayController.data.lastGameHook || "PENDIENTE"); color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: "Comunicación con el juego: " + (overlayController.data.ipcReady ? "LISTA" : (overlayController.data.ipcError || "NO DISPONIBLE")); color: overlayController.data.ipcReady ? page.muted : "#E6B669"; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: "Render: " + (overlayController.data.renderMode || "N/A") + " · Módulo: " + (overlayController.data.inGameHook || "N/A"); color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: overlayController.data.hookDetail || ""; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Text { Layout.fillWidth: true; text: overlayController.data.message || ""; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                Rectangle { Layout.preferredWidth: 166; Layout.preferredHeight: 32; radius: 9; color: page.panelRaised; border.width: 1; border.color: page.edge
                                    Text { anchors.centerIn: parent; text: "Copiar diagnóstico"; color: page.ink; font.pixelSize: 10; font.bold: true }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: overlayController.copyDiagnostics() }
                                }
                            }
                        }
                    }
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

