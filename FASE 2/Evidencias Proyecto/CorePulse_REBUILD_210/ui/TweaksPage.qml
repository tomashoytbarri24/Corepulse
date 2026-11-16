import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// REBUILD 190 · Flujo inspirado en WinUtil: presets que SOLO seleccionan,
// casillas compactas, confirmación explícita y operaciones secuenciales.
// Las escrituras y restauraciones verificadas siguen exclusivamente en tweaks.py.
Item {
    id: page
    signal goBack()

    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.cyan
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color raised: themeManager.palette.panelRaised
    readonly property color purple: themeManager.palette.purple
    property var selectedIds: []
    property string searchTerm: ""
    property string pendingAction: ""
    onPendingActionChanged: {
        if (pendingAction) tweakConfirm.open()
        else tweakConfirm.close()
    }
    property var pendingIds: []
    property string feedback: ""
    property bool showBatchLog: false
    onShowBatchLogChanged: {
        if (showBatchLog) batchLogDialog.open()
        else batchLogDialog.close()
    }
    property var collapsedGroups: []
    property var focusRequest: null
    property real handledStamp: 0
    property string highlightId: ""

    readonly property var groups: ["Explorador", "Barra de tareas", "Interfaz", "Privacidad", "Gaming", "Rendimiento", "Energía", "Sistema", "Actualizaciones", "Red", "Apps y debloat", "Seguridad avanzada"]
    readonly property var essentialKeys: ["extensions", "hidden", "this_pc", "compact", "end_task_taskbar", "widgets", "hide_taskbar_search", "disable_web_search", "disable_advertising_id", "disable_sync_provider_ads", "disable_feedback_prompts", "disable_gamebar_startup"]
    readonly property var minimalKeys: ["extensions", "hidden", "this_pc", "widgets", "disable_advertising_id", "disable_sync_provider_ads"]
    readonly property var advancedKeys: ["disable_startup_delay", "disable_error_reporting", "disable_copilot_policy", "disable_recent_documents_tracking"]
    readonly property bool batchRunning: !!tweaks.batchState.running

    function groupColor(category) {
        switch (category) {
        case "Explorador": return "#27BDF5"
        case "Barra de tareas": return "#9A8CFF"
        case "Interfaz": return "#F6B35B"
        case "Privacidad": return "#CB8AFF"
        case "Gaming": return "#50D69B"
        case "Rendimiento": return "#3F8FFF"
        case "Energía": return "#E0C36D"
        case "Sistema": return "#3DD4CD"
        case "Actualizaciones": return "#F58C5F"
        case "Red": return "#68B4F4"
        case "Apps y debloat": return "#EB7DA5"
        case "Seguridad avanzada": return "#F06C75"
        default: return "#8FA7C3"
        }
    }
    function isPreference(opt) {
        return (opt.category === "Explorador" || opt.category === "Barra de tareas" || opt.category === "Interfaz") && opt.risk === "Bajo"
    }
    function canApply(opt) {
        return !!opt.available && !opt.active && opt.risk !== "Alto" && opt.risk !== "Crítico"
    }
    function canUndo(opt) { return !!opt.available && !!opt.canRestore }
    function selectable(opt) { return canApply(opt) || canUndo(opt) }
    function isSelected(id) { return page.selectedIds.indexOf(id) >= 0 }
    function toggle(id) {
        const option = tweaks.options.find(function(row) { return row.id === id })
        if (!option || !selectable(option) || tweaks.busy || batchRunning) return
        const next = page.selectedIds.slice()
        const index = next.indexOf(id)
        if (index < 0) next.push(id)
        else next.splice(index, 1)
        page.selectedIds = next
    }
    function choosePreset(preset) {
        if (tweaks.busy || batchRunning) return
        if (preset === "clear") { page.selectedIds = []; return }
        const available = tweaks.options.filter(function(opt) { return page.canApply(opt) })
        if (preset === "minimal") {
            page.selectedIds = available.filter(function(opt) { return page.minimalKeys.indexOf(opt.id) >= 0 }).map(function(opt) { return opt.id })
        } else if (preset === "standard") {
            page.selectedIds = available.filter(function(opt) { return page.essentialKeys.indexOf(opt.id) >= 0 }).map(function(opt) { return opt.id })
        } else if (preset === "advanced") {
            page.selectedIds = available.filter(function(opt) { return page.advancedKeys.indexOf(opt.id) >= 0 }).map(function(opt) { return opt.id })
        } else if (preset === "installed") {
            page.selectedIds = tweaks.options.filter(function(opt) { return opt.active && page.canUndo(opt) }).map(function(opt) { return opt.id })
        }
    }
    function actionIds(action) {
        return tweaks.options.filter(function(opt) {
            return page.isSelected(opt.id) && (action === "apply" ? page.canApply(opt) : page.canUndo(opt))
        }).map(function(opt) { return opt.id })
    }
    function toggleGroup(group) {
        const next = page.collapsedGroups.slice()
        const index = next.indexOf(group)
        if (index >= 0) next.splice(index, 1)
        else next.push(group)
        page.collapsedGroups = next
    }
    function matches(opt) {
        const term = page.searchTerm.trim().toLowerCase()
        return !term || (opt.title + " " + opt.description + " " + opt.category + " " + opt.status).toLowerCase().indexOf(term) >= 0
    }
    readonly property var displayRows: {
        const options = tweaks.options.filter(function(opt) { return !page.isPreference(opt) && page.matches(opt) })
        const result = []
        const definitions = [
            {key: "essential", title: "ESENCIALES", description: "Ajustes de menor riesgo disponibles"},
            {key: "advanced", title: "AVANZADOS · PRECAUCIÓN", description: "Revisar efectos antes de aplicar"}
        ]
        for (const group of definitions) {
            const members = options.filter(function(opt) {
                return group.key === "essential" ? opt.risk === "Bajo" : opt.risk !== "Bajo"
            })
            result.push({kind: "header", key: group.key, title: group.title, description: group.description, count: members.length})
            if (page.collapsedGroups.indexOf(group.key) < 0)
                for (const opt of members) result.push({kind: "option", opt: opt})
        }
        return result
    }
    readonly property var preferenceRows: tweaks.options.filter(function(opt) { return page.isPreference(opt) && page.matches(opt) })
    readonly property int applyCount: page.actionIds("apply").length
    readonly property int undoCount: page.actionIds("restore").length
    readonly property int selectedCount: page.selectedIds.length

    function applyFocus() {
        const request = page.focusRequest
        if (!request || request.stamp === page.handledStamp || page.width <= 0) return
        page.searchTerm = ""
        page.collapsedGroups = []
        const target = tweaks.options.find(function(opt) { return opt.id === request.id }) || tweaks.options.find(function(opt) { return request.category && opt.category === request.category })
        Qt.callLater(function() {
            if (target && page.isPreference(target)) {
                const index = page.preferenceRows.findIndex(function(opt) { return opt.id === target.id })
                if (index >= 0) preferencesView.positionViewAtIndex(index, ListView.Center)
            } else {
                const rows = page.displayRows
                let found = -1
                for (let i = 0; i < rows.length; ++i) {
                    if (target && rows[i].kind === "option" && rows[i].opt.id === target.id) { found = i; break }
                    if (!target && rows[i].kind === "header") { found = i; break }
                }
                if (found >= 0) scroller.positionViewAtIndex(found, ListView.Center)
            }
            page.highlightId = request.id || (target ? target.id : "")
            highlightTimer.restart()
        })
        page.handledStamp = request.stamp
    }
    onSearchTermChanged: if (filterInput.text !== page.searchTerm) filterInput.text = page.searchTerm
    onFocusRequestChanged: Qt.callLater(page.applyFocus)
    onWidthChanged: Qt.callLater(page.applyFocus)
    Timer { id: highlightTimer; interval: 2700; onTriggered: page.highlightId = "" }
    Component.onCompleted: { tweaks.ensureFresh(); Qt.callLater(page.applyFocus) }

    component SoftButton: Rectangle {
        id: button
        property string label: ""
        property bool emphasized: false
        property bool destructive: false
        property bool available: true
        signal activated()
        implicitWidth: Math.max(75, buttonLabel.implicitWidth + 25)
        implicitHeight: 35
        radius: 10
        color: emphasized ? (available ? themeManager.palette.action : page.raised)
             : pressed.containsMouse && available ? Qt.alpha(page.accent, 0.14) : themeManager.palette.panel
        opacity: available ? 1 : 0.50
        border.width: 1
        border.color: emphasized ? themeManager.palette.action : page.edge
        Text {
            id: buttonLabel
            anchors.centerIn: parent
            text: button.label
            color: button.emphasized && button.available ? themeManager.palette.actionText : button.destructive ? "#F0A5AE" : page.ink
            font.pixelSize: 11; font.weight: Font.DemiBold
        }
        MouseArea {
            id: pressed; anchors.fill: parent; hoverEnabled: true
            enabled: button.available
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.activated()
        }
    }

    component TweakLine: Rectangle {
        id: line
        property var opt: ({id:"", title:"", description:"", risk:"Bajo", available:false, active:false, canRestore:false, category:"", status:""})
        readonly property bool checked: page.isSelected(opt.id)
        readonly property bool canChoose: page.selectable(opt) && !tweaks.busy && !page.batchRunning
        implicitHeight: 71
        height: 71
        radius: 10
        color: checked ? Qt.alpha(page.accent, 0.095) : lineMouse.containsMouse ? Qt.alpha(page.raised, 0.36) : "transparent"
        border.width: checked || page.highlightId === opt.id ? 1 : 0
        border.color: page.highlightId === opt.id ? page.accent : Qt.alpha(page.accent, 0.36)
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10; anchors.rightMargin: 11
            anchors.topMargin: 7; anchors.bottomMargin: 7
            spacing: 11
            Rectangle {
                Layout.preferredWidth: 20; Layout.preferredHeight: 20
                Layout.alignment: Qt.AlignVCenter
                radius: 5
                color: line.checked ? page.accent : "transparent"
                border.width: 1.5
                border.color: line.checked ? page.accent : line.canChoose ? page.muted : Qt.alpha(page.muted, 0.28)
                Text { anchors.centerIn: parent; text: "✓"; visible: line.checked; color: "#0C1725"; font.pixelSize: 13; font.bold: true }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.minimumWidth: 0
                spacing: 3
                Text {
                    Layout.fillWidth: true
                    text: line.opt.title || ""
                    color: line.canChoose || line.opt.active ? page.ink : page.muted
                    font.pixelSize: 12; font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: line.opt.description || ""
                    color: page.muted; font.pixelSize: 10
                    elide: Text.ElideRight; maximumLineCount: 1
                }
                Text {
                    Layout.fillWidth: true
                    text: line.opt.category + "  ·  " + (line.opt.available ? line.opt.status : (line.opt.detail || line.opt.status))
                    color: line.opt.active ? page.accent : page.muted
                    opacity: 0.85; font.pixelSize: 9
                    elide: Text.ElideRight; maximumLineCount: 1
                }
            }
            Text {
                Layout.alignment: Qt.AlignVCenter
                text: line.opt.risk === "Bajo" ? "BAJO" : line.opt.risk === "Medio" ? "MEDIO" : "BLOQUEADO"
                color: line.opt.risk === "Bajo" ? page.muted : line.opt.risk === "Medio" ? "#F2BD70" : "#EE9DA6"
                font.pixelSize: 9; font.weight: Font.DemiBold
            }
        }
        MouseArea {
            id: lineMouse
            anchors.fill: parent; hoverEnabled: true
            enabled: line.canChoose
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: page.toggle(line.opt.id)
        }
        ToolTip.visible: lineMouse.containsMouse
        ToolTip.delay: 800
        ToolTip.text: line.opt.title + "\n" + line.opt.description + "\n" + (line.opt.detail || line.opt.status)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Glyph { Layout.preferredWidth: 32; Layout.preferredHeight: 32; kind: "sliders"; ink: page.accent }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text { text: "Tweaks Windows 11"; color: page.ink; font.pixelSize: 21; font.bold: true }
                Text { text: "" + tweaks.options.length + " ajustes · Selección múltiple y restauración verificada"; color: page.muted; font.pixelSize: 11 }
            }
            HeaderAction { label: "Actualizar"; available: !tweaks.busy && !page.batchRunning; onActivated: tweaks.refresh() }
            HeaderAction { label: "Volver"; onActivated: page.goBack() }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: presetControls.implicitHeight + 20
            radius: 13
            RowLayout {
                id: presetControls
                anchors.left: parent.left; anchors.right: parent.right
                anchors.top: parent.top; anchors.margins: 10
                spacing: 7
                Flow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: childrenRect.height
                    spacing: 7
                    SoftButton { label: "Estándar"; available: !tweaks.busy && !page.batchRunning; onActivated: page.choosePreset("standard") }
                    SoftButton { label: "Mínimo"; available: !tweaks.busy && !page.batchRunning; onActivated: page.choosePreset("minimal") }
                    SoftButton { label: "Avanzado"; available: !tweaks.busy && !page.batchRunning; onActivated: page.choosePreset("advanced") }
                    SoftButton { label: "Limpiar"; available: !tweaks.busy && !page.batchRunning; onActivated: page.choosePreset("clear") }
                    SoftButton { label: "Aplicados"; available: !tweaks.busy && !page.batchRunning; onActivated: page.choosePreset("installed") }
                }
                TextField {
                    id: filterInput
                    Layout.preferredWidth: Math.max(155, Math.min(230, page.width * 0.235))
                    Layout.preferredHeight: 35
                    placeholderText: "Buscar ajustes..."
                    text: page.searchTerm
                    onTextChanged: if (page.searchTerm !== text) page.searchTerm = text
                    color: page.ink
                    placeholderTextColor: page.muted
                    font.pixelSize: 11
                    background: Rectangle { radius: 10; color: page.raised; border.width: 1; border.color: page.edge }
                }
            }
        }

        Rectangle {
            visible: page.feedback !== "" || page.batchRunning || !!tweaks.batchState.message
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 42 : 0
            radius: 10
            color: Qt.alpha(page.accent, 0.06)
            border.width: 1; border.color: Qt.alpha(page.accent, 0.22)
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                spacing: 8
                Text {
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    text: page.batchRunning
                        ? "Procesando " + tweaks.batchState.done + "/" + tweaks.batchState.total + " · " + (tweaks.batchState.current || "Preparando...")
                        : (tweaks.batchState.log.length ? tweaks.batchState.message : page.feedback || tweaks.batchState.message)
                    color: page.ink; font.pixelSize: 11; elide: Text.ElideRight
                }
                SoftButton {
                    visible: !page.batchRunning && tweaks.batchState.log.length > 0
                    label: "Ver resultados"
                    onActivated: page.showBatchLog = true
                }
                Text { visible: page.batchRunning; text: "No cierres la ventana"; color: page.muted; font.pixelSize: 10 }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 12
            GlassPanel {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.minimumWidth: 300
                radius: 15
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Ajustes del sistema"; color: page.ink; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Item { Layout.fillWidth: true }
                        Text { text: "ESENCIALES + AVANZADOS"; color: page.muted; font.pixelSize: 9 }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.edge }
                    Item {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        ListView {
                        id: scroller
                        anchors.fill: parent
                        clip: true; cacheBuffer: 280; spacing: 3
                        model: page.displayRows
                        boundsBehavior: Flickable.StopAtBounds; interactive: false
                        FastWheelHandler { scrollTarget: scroller }
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 7 }
                        delegate: Item {
                            id: displayRow
                            required property var modelData
                            width: Math.max(0, scroller.width - 8)
                            height: modelData.kind === "header" ? 49 : 71
                            RowLayout {
                                visible: displayRow.modelData.kind === "header"
                                anchors.fill: parent
                                spacing: 7
                                Rectangle {
                                    Layout.preferredWidth: 3; Layout.preferredHeight: 18; radius: 2
                                    color: displayRow.modelData.key === "advanced" ? "#F2BD70" : page.accent
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 1
                                    Text { text: displayRow.modelData.title || ""; color: page.ink; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    Text { text: (displayRow.modelData.count || 0) + " opciones · " + (displayRow.modelData.description || ""); color: page.muted; font.pixelSize: 9 }
                                }
                                SoftButton {
                                    label: page.collapsedGroups.indexOf(displayRow.modelData.key || "") >= 0 ? "+" : "−"
                                    implicitWidth: 28; implicitHeight: 26
                                    onActivated: page.toggleGroup(displayRow.modelData.key)
                                }
                            }
                            TweakLine {
                                visible: displayRow.modelData.kind === "option"
                                anchors.fill: parent
                                opt: displayRow.modelData.opt || ({})
                            }
                        }
                        footer: Text {
                            width: scroller.width - 12
                            topPadding: 11; bottomPadding: 15
                            text: "Los cambios avanzados requieren revisión individual. Defender, SmartScreen, UAC y los ajustes irreversibles no entran en los presets."
                            wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 10
                        }
                    }
                        ThinScroll {
                            target: scroller
                            anchors.top: parent.top; anchors.bottom: parent.bottom
                            anchors.right: parent.right; anchors.rightMargin: 2
                        }
                    }
                }
            }
            GlassPanel {
                Layout.preferredWidth: Math.max(260, Math.min(355, page.width * 0.36))
                Layout.fillHeight: true
                radius: 15
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    Text { text: "Personalizar Windows"; color: page.ink; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text {
                        Layout.fillWidth: true
                        text: "Explorador, barra de tareas e interfaz. Las casillas seleccionan cambios; no los aplican automáticamente."
                        color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.edge }
                    ListView {
                        id: preferencesView
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; cacheBuffer: 280; spacing: 4
                        model: page.preferenceRows
                        boundsBehavior: Flickable.StopAtBounds; interactive: false
                        FastWheelHandler { scrollTarget: preferencesView }
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 7 }
                        delegate: TweakLine {
                            required property var modelData
                            width: Math.max(0, preferencesView.width - 8)
                            opt: modelData
                        }
                        footer: Text {
                            width: preferencesView.width - 10
                            topPadding: 12; bottomPadding: 12
                            text: "Estado verificado en Windows. Restaurar solo está disponible cuando existe un respaldo válido."
                            wrapMode: Text.WordWrap; color: page.muted; font.pixelSize: 10
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 68
            radius: 13
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    Text {
                        text: page.selectedCount + " seleccionados · " + page.applyCount + " para aplicar · " + page.undoCount + " para restaurar"
                        color: page.ink; font.pixelSize: 12; font.weight: Font.DemiBold
                    }
                    Text { text: "Los presets solo marcan casillas. Ningún cambio se ejecuta sin confirmar."; color: page.muted; font.pixelSize: 10 }
                }
                SoftButton {
                    label: "Restaurar seleccionados"
                    available: page.undoCount > 0 && !tweaks.busy && !page.batchRunning
                    onActivated: { page.pendingIds = page.actionIds("restore"); page.pendingAction = "restore" }
                }
                SoftButton {
                    emphasized: true; label: "Aplicar seleccionados"
                    available: page.applyCount > 0 && !tweaks.busy && !page.batchRunning
                    onActivated: { page.pendingIds = page.actionIds("apply"); page.pendingAction = "apply" }
                }
            }
        }
    }

    // Registro por elemento de la última aplicación/restauración; no confundir
    // "procesado" con éxito si Windows devolvió un fallo o comprobación parcial.
    Popup {
        id: batchLogDialog
        parent: Overlay.overlay
        modal: true; focus: true; padding: 22
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#B20C0C16" }
        width: Math.max(1, Math.min(parent.width - 32, 630))
        height: Math.max(1, Math.min(parent.height - 32, 500))
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        background: ModalSurface {}
        onClosed: page.showBatchLog = false
        contentItem: ColumnLayout {
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Resultados de los ajustes"; color: page.ink; font.pixelSize: 17; font.bold: true }
                    Item { Layout.fillWidth: true }
                    SoftButton { label: "Cerrar"; onActivated: page.showBatchLog = false }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Cada resultado se verifica individualmente. Un fallo no equivale a un cambio aplicado."
                    color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap
                }
                ListView {
                    id: batchLogList
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true; spacing: 9; interactive: false
                    model: tweaks.batchState.log
                    FastWheelHandler { scrollTarget: batchLogList }
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 7 }
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width
                        height: resultColumn.implicitHeight + 20
                        radius: 10
                        color: Qt.alpha(page.raised, 0.46)
                        ColumnLayout {
                            id: resultColumn
                            anchors.left: parent.left; anchors.right: parent.right
                            anchors.top: parent.top; anchors.margins: 10; spacing: 4
                            Text { text: modelData.title; color: page.ink; font.bold: true; font.pixelSize: 12 }
                            Text { Layout.fillWidth: true; text: modelData.message; color: page.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
                        }
                    }
                }
        }
    }

    Popup {
        id: tweakConfirm
        parent: Overlay.overlay
        modal: true; focus: true; padding: 22
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: "#B20C0C16" }
        width: Math.max(1, Math.min(parent.width - 32, 520))
        height: Math.max(1, Math.min(parent.height - 32, tweakConfirmContents.implicitHeight + 44))
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        background: ModalSurface {}
        onClosed: page.pendingAction = ""
        contentItem: ColumnLayout {
            id: tweakConfirmContents
            spacing: 16
            Text { Layout.fillWidth: true; text: page.pendingAction === "apply" ? "¿Aplicar los ajustes seleccionados?" : "¿Restaurar los ajustes seleccionados?"; color: page.ink; font.pixelSize: 18; font.bold: true; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: page.pendingIds.length + " cambios seleccionados. Se ejecutarán uno por uno, verificando cada resultado."; color: page.ink; font.pixelSize: 13; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: page.pendingAction === "apply" ? "CorePulse conservará los respaldos verificables antes de aplicar ajustes. Algunos requieren reiniciar el Explorador o Windows. No se desactivarán protecciones de seguridad mediante presets." : "Solo se restaurarán los ajustes que tengan un respaldo válido. Los valores originales verificados se recuperarán individualmente."; color: page.muted; font.pixelSize: 13; wrapMode: Text.WordWrap }
            Rectangle { Layout.fillWidth: true; height: 1; color: Qt.alpha(page.ink, 0.10) }
            RowLayout {
                Layout.alignment: Qt.AlignRight; spacing: 10
                SoftButton { label: "Cancelar"; onActivated: tweakConfirm.close() }
                SoftButton {
                    label: page.pendingAction === "apply" ? "Confirmar aplicación" : "Confirmar restauración"
                    emphasized: true
                    onActivated: {
                        const answer = tweaks.runSelected(page.pendingIds, page.pendingAction)
                        page.feedback = answer
                        if (answer.indexOf("Iniciando ") === 0) page.selectedIds = []
                        page.pendingIds = []
                        page.pendingAction = ""
                    }
                }
            }
        }
    }
}
