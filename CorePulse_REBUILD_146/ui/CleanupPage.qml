import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    // Acceso desde bandeja: abre la confirmación, nunca ejecuta limpieza de forma automática.
    function showRamDeepConfirmation() { if (!info.busy) deepConfirm.open() }
    readonly property color surface: themeManager.palette.panel
    readonly property color ramModalAccent: "#4EDDC8"
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    // Altura uniforme por fila para conservar la simetría entre tarjetas.
    readonly property int cleanupCardHeight: 270
    readonly property int cleanupExpandedRamHeight: 342
    readonly property var info: cleanup && cleanup.data ? cleanup.data : ({
        busy: false, resultSequence: 0, resultPartial: false, ramMeterValid: false, ramMeterPercent: 0,
        lastRamKind: "", resultKind: "", status: "N/A", size: "N/A", found: 0,
        cacheSize: "N/A", cacheFound: 0, cacheAnalyzed: false, cacheStatus: "N/A",
        recycleSize: "N/A", recycleFound: 0, recycleAnalyzed: false, recycleStatus: "N/A",
        storageSize: "Sin analizar", storageFound: 0, storageAnalyzed: false, storageStatus: "N/A",
        duplicateFiles: 0, duplicateGroups: 0, duplicateWasted: "Sin analizar",
        duplicateStatus: "Selecciona una carpeta", duplicatePreview: "",
        dnsStatus: "N/A"
    })
    property bool ramDetailsOpen: false
    readonly property bool hasRamResult: info.lastRamKind === "ram" || info.lastRamKind === "ram_safe" || info.lastRamKind === "ram_deep"
    readonly property string lastRamVariation: info.lastRamKind === "ram_deep" ? info.deepChange : info.ramChange
    readonly property string lastRamBefore: info.lastRamKind === "ram_deep" ? info.deepBefore : info.ramBefore
    readonly property string lastRamAfter: info.lastRamKind === "ram_deep" ? info.deepAfter : info.ramAfter
    // Cuadros flotantes opacos: evitan mezclar textos con el contenido de
    // tarjetas traslúcidas visible detrás. El fondo normal sigue adaptable.
    readonly property color modalShade: "#B20C0C16"
    component ModalSurface: Rectangle {
        radius: 19
        color: themeManager.palette.panelOpaque
        border.width: 1
        border.color: page.edge
    }
    component ActionButton: AbstractButton {
        id: control
        property color accent: "#4EDDC8"
        property bool secondary: false
        property bool actionStyle: false   // ejecuta algo: texto del color de la tarjeta
        property bool solidStyle: false    // Aplicar/Actualizar: botón entero de color
        implicitHeight: 40
        implicitWidth: Math.max(112, contentText.implicitWidth + 30)
        hoverEnabled: true
        leftPadding: 14; rightPadding: 14
        background: Rectangle {
            radius: 9
            color: control.solidStyle
                   ? (!control.enabled ? themeManager.palette.actionMuted : control.down ? Qt.darker(control.accent, 1.12) : control.hovered ? Qt.lighter(control.accent, 1.12) : control.accent)
                   : (!control.enabled ? "#242631" : (control.down ? "#232432" : (control.hovered ? "#30303E" : themeManager.palette.panelRaised)))
            border.width: 1
            border.color: control.solidStyle ? (control.enabled ? control.accent : themeManager.palette.actionMuted)
                          : (!control.enabled ? "#333746" : (control.hovered ? control.accent : (control.secondary ? "#3C4150" : page.edge)))
            opacity: control.enabled || control.solidStyle ? 1 : 0.68
        }
        contentItem: Text {
            id: contentText
            text: control.text
            color: control.solidStyle ? (control.enabled ? themeManager.palette.actionText : themeManager.palette.actionMutedText)
                   : control.enabled ? (control.secondary && !control.actionStyle ? page.ink : control.accent) : "#8993A5"
            font.pixelSize: 12
            font.weight: control.solidStyle ? Font.Bold : Font.DemiBold
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    FastFlickable {
        id: cleanupScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: cleanupContents.implicitHeight + 12
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: cleanupContents
            width: Math.max(320, page.width - 24)
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 46; height: 46; radius: 13; color: "#123E3D"
                    Glyph { anchors.centerIn: parent; width: 26; height: 26; kind: "broom"; ink: "#4EDDC8" }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    Text { text: "Limpieza de sistema"; color: page.ink; font.bold: true; font.pixelSize: 21 }
                    Text { text: "Temporales y memoria, bajo tu control"; color: page.muted; font.pixelSize: 11 }
                }
                ActionButton { text: "Volver"; secondary: true; onClicked: page.goBack() }
            }
            // No hay panel permanente de estado. Los mensajes aparecen solo
            // mientras trabajamos o cuando falla el análisis de temporales.
            Rectangle {
                Layout.fillWidth: true
                readonly property bool tempError: !info.busy &&
                    (info.resultKind === "scan" || info.resultKind === "clean") &&
                    String(info.status).indexOf("No se pudo completar:") === 0
                visible: info.busy || tempError
                Layout.preferredHeight: visible ? (compactStatus.implicitHeight + 22) : 0
                radius: 10
                color: tempError ? "#31271F" : "#182833"
                border.width: 1
                border.color: tempError ? "#A17B51" : "#304A58"
                Text {
                    id: compactStatus
                    anchors.fill: parent
                    anchors.margins: 11
                    text: parent.tempError ? info.status : "Operación en curso…"
                    color: parent.tempError ? "#F6BA64" : "#81D4E7"
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.WordWrap
                }
            }
            GridLayout {
                columns: page.width < 850 ? 1 : 2
                columnSpacing: 14
                rowSpacing: 14
                Layout.fillWidth: true
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.cleanupCardHeight
                    radius: 19
                    color: page.surface; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                        Text { text: "TEMPORALES"; color: "#F6BA64"; font.pixelSize: 12; font.bold: true }
                        Text { text: "Archivos temporales"; color: page.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Carpeta Temp · Archivos de más de 24 h"; color: page.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        RowLayout {
                            spacing: 8
                            Text { text: info.size; color: page.ink; font.pixelSize: 28; font.bold: true }
                            Text { text: "· " + info.found + " archivos"; color: page.muted; font.pixelSize: 12 }
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            ActionButton { actionStyle: true; text: "Analizar"; accent: "#F6BA64"; enabled: !info.busy; onClicked: cleanup.analyze() }
                            ActionButton { actionStyle: true; text: "Eliminar…"; accent: "#F6BA64"; secondary: true; enabled: !info.busy && info.found > 0; onClicked: confirmDialog.open() }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.ramDetailsOpen && page.hasRamResult ? page.cleanupExpandedRamHeight : page.cleanupCardHeight
                    radius: 19
                    color: page.surface; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                        Text { text: "MEMORIA RAM"; color: "#77A9FF"; font.pixelSize: 12; font.bold: true }
                        Text { text: "Optimización de memoria"; color: page.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Normal, standby o limpieza completa"; color: page.muted; font.pixelSize: 12 }
                        Rectangle { Layout.fillWidth: true; height: 1; color: themeManager.palette.panelBorder }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: page.hasRamResult ? "Última variación disponible" : "Elige el tipo de limpieza"
                                color: page.muted; font.pixelSize: 12
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Text {
                                visible: page.hasRamResult
                                text: page.lastRamVariation
                                color: "#77D7C2"; font.pixelSize: 14; font.bold: true
                            }
                        }
                        // Las cifras completas se muestran solamente a petición.
                        ColumnLayout {
                            visible: page.ramDetailsOpen && page.hasRamResult
                            Layout.fillWidth: true
                            spacing: 4
                            Text {
                                text: "Disponible: " + page.lastRamBefore + "  →  " + page.lastRamAfter
                                color: page.ink; font.pixelSize: 11
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                            Text {
                                visible: info.lastRamKind === "ram_deep"
                                text: info.deepDetail
                                color: page.muted; font.pixelSize: 11
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                        }
                        Text {
                            visible: page.hasRamResult
                            text: page.ramDetailsOpen ? "Ocultar detalles  −" : "Ver detalles  +"
                            color: "#88B9E6"; font.pixelSize: 11; font.bold: true
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: page.ramDetailsOpen = !page.ramDetailsOpen
                            }
                        }
                        Item { Layout.fillHeight: true }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: page.width < 580 ? 1 : 3
                            columnSpacing: 8; rowSpacing: 8
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Normal segura"; accent: "#77A9FF"; enabled: !info.busy; onClicked: cleanup.cleanRamSafely() }
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Limpiar standby"; accent: "#77A9FF"; enabled: !info.busy; onClicked: cleanup.cleanRam() }
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Completa…"; accent: "#4EDDC8"; enabled: !info.busy; onClicked: deepConfirm.open() }
                        }
                    }
                }
            }
            // Funciones independientes de los temporales y de la RAM.
            // Nunca se confunden las cifras de caché con las de la carpeta Temp.
            GridLayout {
                columns: page.width < 850 ? 1 : 2
                columnSpacing: 14; rowSpacing: 14
                Layout.fillWidth: true
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.cleanupCardHeight
                    radius: 19; color: page.surface; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                        Text { text: "CACHÉ"; color: "#B69CFF"; font.pixelSize: 12; font.bold: true }
                        Text { text: "Caché de Windows"; color: page.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Shaders y miniaturas regenerables"; color: page.muted; font.pixelSize: 12 }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            Text { text: info.cacheSize; color: page.ink; font.pixelSize: 24; font.bold: true }
                            Text { text: info.cacheAnalyzed ? "· " + info.cacheFound + " archivos" : ""; color: page.muted; font.pixelSize: 12 }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: info.cacheStatus
                            color: String(info.cacheStatus).startsWith("No se pudo") ? "#F6BA64" : page.muted
                            font.pixelSize: 11; maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.WordWrap
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Analizar caché"; accent: "#B69CFF"; enabled: !info.busy; onClicked: cleanup.analyzeCache() }
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Limpiar caché"; accent: "#B69CFF"; secondary: true; enabled: !info.busy && (!info.cacheAnalyzed || info.cacheFound > 0); onClicked: cacheConfirm.open() }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.cleanupCardHeight
                    radius: 19; color: page.surface; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 9
                        Text { text: "ESPACIO SEGURO"; color: "#8AD6BC"; font.pixelSize: 12; font.bold: true }
                        Text { text: "Liberar almacenamiento"; color: page.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Solo ubicaciones regenerables permitidas"; color: page.muted; font.pixelSize: 12 }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            Text { text: info.storageSize; color: page.ink; font.pixelSize: 24; font.bold: true }
                            Text { text: info.storageAnalyzed ? "· " + info.storageFound + " archivos" : ""; color: page.muted; font.pixelSize: 12 }
                        }
                        Text {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            text: info.storageStatus
                            color: String(info.storageStatus).startsWith("No se pudo") ? "#F6BA64" : page.muted
                            font.pixelSize: 10; wrapMode: Text.WordWrap; maximumLineCount: 4; elide: Text.ElideRight
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Analizar"; accent: "#8AD6BC"; enabled: !info.busy; onClicked: cleanup.analyzeStorage() }
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Liberar…"; accent: "#8AD6BC"; secondary: true; enabled: !info.busy && info.storageAnalyzed && info.storageFound > 0; onClicked: storageConfirm.open() }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.cleanupCardHeight
                    radius: 19; color: page.surface; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 9
                        Text { text: "VERIFICACIÓN LOCAL"; color: "#E5B768"; font.pixelSize: 12; font.bold: true }
                        Text { text: "Archivos duplicados"; color: page.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: info.duplicateFolder || "Elige una carpeta para comparar"; color: page.muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            Text { text: info.duplicateWasted; color: page.ink; font.pixelSize: 24; font.bold: true }
                            Text { text: info.duplicateGroups > 0 ? "· " + info.duplicateGroups + " grupos" : ""; color: page.muted; font.pixelSize: 12 }
                        }
                        Text { Layout.fillWidth: true; text: info.duplicateStatus; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; Layout.fillHeight: true; text: info.duplicatePreview; color: page.ink; font.pixelSize: 9; wrapMode: Text.WordWrap; maximumLineCount: 4; elide: Text.ElideRight }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Elegir carpeta"; accent: "#E5B768"; enabled: !info.busy; onClicked: cleanup.analyzeDuplicates() }
                            ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Ver resultados"; secondary: true; accent: "#E5B768"; enabled: !info.busy && info.duplicateGroups > 0; onClicked: duplicatesDialog.open() }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: page.cleanupCardHeight
                    radius: 19; color: page.surface; border.color: page.edge
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                        Text { text: "ALMACENAMIENTO"; color: "#FFAA80"; font.pixelSize: 12; font.bold: true }
                        Text { text: "Papelera de reciclaje"; color: page.ink; font.pixelSize: 17; font.bold: true }
                        Text { text: "Consulta y vaciado bajo confirmación"; color: page.muted; font.pixelSize: 12 }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            Text { text: info.recycleSize; color: page.ink; font.pixelSize: 24; font.bold: true }
                            Text { text: info.recycleAnalyzed ? "· " + info.recycleFound + " elementos" : ""; color: page.muted; font.pixelSize: 12 }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: info.recycleStatus
                            color: String(info.recycleStatus).startsWith("No se pudo") ? "#F6BA64" : page.muted
                            font.pixelSize: 11; maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.WordWrap
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Consultar"; accent: "#FFAA80"; enabled: !info.busy; onClicked: cleanup.analyzeRecycleBin() }
                            ActionButton { actionStyle: true; Layout.fillWidth: true; Layout.minimumWidth: 0; text: "Vaciar Papelera"; accent: "#FFAA80"; secondary: true; enabled: !info.busy && info.recycleAnalyzed && info.recycleFound > 0; onClicked: recycleConfirm.open() }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true; Layout.columnSpan: page.width < 850 ? 1 : 2
                    Layout.preferredHeight: page.width < 580 ? 204 : 158
                    radius: 19; color: page.surface; border.color: page.edge
                    GridLayout {
                        anchors.fill: parent; anchors.margins: 20; columnSpacing: 16; rowSpacing: 8
                        columns: page.width < 580 ? 1 : 2
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 8
                            Text { text: "RED"; color: "#65D8BA"; font.pixelSize: 12; font.bold: true }
                            Text { text: "Caché DNS"; color: page.ink; font.pixelSize: 17; font.bold: true }
                            Text { text: "Renueva las entradas de resolución de nombres"; color: page.muted; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Text {
                                text: info.dnsStatus; color: String(info.dnsStatus).startsWith("No se pudo") ? "#F6BA64" : page.muted
                                font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight
                            }
                        }
                        ActionButton { actionStyle: true; Layout.fillWidth: page.width < 580; text: "Vaciar caché DNS"; accent: "#65D8BA"; enabled: !info.busy; onClicked: cleanup.flushDns() }
                    }
                }
            }
            Text {
                text: "La limpieza profunda puede provocar recargas temporales."
                color: page.muted; font.pixelSize: 11
                Layout.fillWidth: true; wrapMode: Text.WordWrap
            }
        }
    }
    // Las confirmaciones se anclan al overlay de la ventana, no al item
    // desplazable. La atenuación mantiene el contenido visible con profundidad.
    component DarkDialog: Popup {
        id: dialogRoot
        property string heading: ""
        property string message: ""
        property string actionText: "Continuar"
        property color actionColor: "#4EDDC8"
        signal confirmed()
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(480, parent.width - 36)
        height: contentColumn.implicitHeight + topPadding + bottomPadding
        padding: 24
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: page.modalShade }
        background: ModalSurface {}
        contentItem: ColumnLayout {
            id: contentColumn
            width: dialogRoot.availableWidth
            spacing: 18
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    width: 42; height: 42; radius: 12
                    color: "#252733"
                    border.width: 1; border.color: page.edge
                    Text { anchors.centerIn: parent; text: "!"; color: dialogRoot.actionColor; font.bold: true; font.pixelSize: 23 }
                }
                Text {
                    Layout.fillWidth: true
                    text: dialogRoot.heading
                    color: page.ink
                    font.pixelSize: 18
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
            }
            Text {
                Layout.fillWidth: true
                text: dialogRoot.message
                color: page.muted
                font.pixelSize: 13
                lineHeight: 1.35
                wrapMode: Text.WordWrap
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: page.edge }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Item { Layout.fillWidth: true }
                ActionButton { text: "Cancelar"; secondary: true; onClicked: dialogRoot.close() }
                ActionButton { actionStyle: true;
                    text: dialogRoot.actionText
                    accent: dialogRoot.actionColor
                    onClicked: { dialogRoot.close(); dialogRoot.confirmed() }
                }
            }
        }
    }

    DarkDialog {
        id: deepConfirm
        heading: "Limpieza profunda de RAM"
        message: "Se recortarán conjuntos de trabajo de procesos accesibles y se solicitará vaciar listas y cachés de Windows. Puede causar lentitud temporal y recargas de aplicaciones. Requiere administrador. ¿Continuar?"
        actionText: "Limpiar RAM"
        actionColor: "#4EDDC8"
        onConfirmed: cleanup.cleanRamDeep()
    }
    DarkDialog {
        id: cacheConfirm
        heading: "Limpiar caché de Windows"
        message: "Se eliminarán archivos de caché regenerables de shaders y miniaturas del perfil actual. Los programas abiertos pueden bloquear algunos archivos y la primera carga posterior puede ser más lenta. ¿Continuar?"
        actionText: "Limpiar caché"
        actionColor: "#B69CFF"
        onConfirmed: cleanup.cleanCache()
    }
    DarkDialog {
        id: recycleConfirm
        heading: "Vaciar Papelera de reciclaje"
        message: "Se borrarán de forma permanente los elementos de la Papelera, sin posibilidad de recuperarlos desde ella. Esta acción no se puede deshacer. ¿Confirmas?"
        actionText: "Vaciar Papelera"
        actionColor: "#FFAA80"
        onConfirmed: cleanup.emptyRecycleBin()
    }
    DarkDialog {
        id: storageConfirm
        heading: "Liberar almacenamiento seguro"
        message: "El análisis encontró " + info.storageFound + " archivos elegibles (" + info.storageSize + "). Solo se eliminarán temporales antiguos de ubicaciones autorizadas; cada archivo se vuelve a verificar justo antes de borrarlo. Los archivos personales y las rutas desconocidas quedan fuera. ¿Continuar?"
        actionText: "Liberar espacio"
        actionColor: "#8AD6BC"
        onConfirmed: cleanup.cleanStorage()
    }
    Popup {
        id: duplicatesDialog
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(620, parent.width - 32)
        height: Math.min(560, parent.height - 36)
        padding: 22
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: page.modalShade }
        background: ModalSurface {}
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: "Copias idénticas verificadas"; color: "#E5B768"; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: info.duplicateFolder + "\n" + info.duplicateFiles + " copias · " + info.duplicateWasted + " repetidos · SHA-256"; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            ScrollView {
                id: duplicatePreviewScroll
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true
                FastWheelHandler { scrollTarget: duplicatePreview }
                TextArea {
                    id: duplicatePreview
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    text: info.duplicatePreview
                    color: page.ink; font.pixelSize: 10
                    background: Rectangle { color: themeManager.palette.panelRaised; radius: 10; border.width: 1; border.color: page.edge }
                }
            }
            ActionButton { text: "Cerrar"; Layout.alignment: Qt.AlignRight; accent: "#E5B768"; onClicked: duplicatesDialog.close() }
        }
    }
    DarkDialog {
        id: confirmDialog
        heading: "Eliminar temporales"
        message: "Se eliminarán archivos temporales de más de 24 horas. Los archivos eliminados no van a la Papelera. ¿Quieres continuar?"
        actionText: "Eliminar archivos"
        actionColor: "#F6BA64"
        onConfirmed: cleanup.clean()
    }

    Connections {
        target: cleanup
        function onChanged() {
            if (!cleanup || !cleanup.data) return
            const result = cleanup.data
            // El medidor solo aparece con una limpieza de RAM en ejecución.
            // No debe aparecer para el análisis o borrado de temporales.
            if (result.ramUiFeedback !== false && result.busy && result.ramMeterActive && !ramProgress.opened)
                ramProgress.open()
            if (!result.busy && ramProgress.opened)
                ramProgress.close()
            if (result.ramUiFeedback === false)
                page.seenResultSequence = Math.max(page.seenResultSequence, Number(result.resultSequence) || 0)
            if (result.ramUiFeedback !== false && result.resultSequence > page.seenResultSequence) {
                page.seenResultSequence = result.resultSequence
                if (result.resultKind === "ram" || result.resultKind === "ram_safe" || result.resultKind === "ram_deep") {
                    if (result.resultPartial)
                        Qt.callLater(function() { ramPartial.open() })
                    else if (result.resultSuccess)
                        Qt.callLater(function() { ramSuccess.open() })
                    else
                        Qt.callLater(function() { ramFailure.open() })
                }
            }
        }
    }
    // No repetir avisos de ejecuciones anteriores al regresar a esta pestaña.
    property int seenResultSequence: info.resultSequence || 0

    Popup {
        id: ramProgress
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(454, parent.width - 36)
        height: Math.min(498, parent.height - 32)
        padding: 24
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose
        property real animatedPercent: info.ramMeterValid ? info.ramMeterPercent : 0
        Behavior on animatedPercent {
            NumberAnimation { duration: 230; easing.type: Easing.OutCubic }
        }
        onAnimatedPercentChanged: {
            if (gaugeCanvas) gaugeCanvas.requestPaint()
        }
        Overlay.modal: Rectangle { color: page.modalShade }
        background: ModalSurface {}
        contentItem: ColumnLayout {
            width: ramProgress.availableWidth
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    width: 38; height: 38; radius: 11; color: "#252733"
                    border.width: 1; border.color: page.edge
                    Glyph { anchors.centerIn: parent; width: 23; height: 23; kind: "ram"; ink: page.ramModalAccent }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: "LIMPIEZA EN PROCESO"; color: page.muted; font.bold: true; font.pixelSize: 10 }
                    Text { text: "Monitor de memoria RAM"; color: page.ink; font.bold: true; font.pixelSize: 17 }
                }
            }
            Text {
                Layout.fillWidth: true
                text: "Lecturas reales de Windows durante la limpieza"
                color: page.muted; font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 168
                Canvas {
                    id: gaugeCanvas
                    anchors.centerIn: parent
                    width: 164; height: 164
                    antialiasing: true
                    onPaint: {
                        const ctx = getContext("2d")
                        const cx = width / 2, cy = height / 2, radius = 65
                        const start = -Math.PI / 2
                        ctx.clearRect(0, 0, width, height)
                        ctx.lineWidth = 12
                        ctx.lineCap = "round"
                        ctx.beginPath()
                        ctx.arc(cx, cy, radius, 0, Math.PI * 2)
                        ctx.strokeStyle = themeManager.palette.panelBorder
                        ctx.stroke()
                        if (info.ramMeterValid) {
                            ctx.beginPath()
                            ctx.arc(cx, cy, radius, start,
                                    start + Math.PI * 2 * Math.min(100, Math.max(0, ramProgress.animatedPercent)) / 100)
                            ctx.strokeStyle = String(page.ramModalAccent)
                            ctx.stroke()
                        }
                    }
                }
                Column {
                    anchors.centerIn: parent
                    spacing: 3
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: info.ramMeterValid ? Number(info.ramMeterPercent).toFixed(1) + "%" : "N/A"
                        color: page.ink; font.pixelSize: 31; font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "RAM ocupada"
                        color: page.muted; font.pixelSize: 11
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 13
                radius: 7
                color: themeManager.palette.panelBorder
                clip: true
                Rectangle {
                    width: info.ramMeterValid ? parent.width * ramProgress.animatedPercent / 100 : 0
                    height: parent.height; radius: parent.radius
                    color: page.ramModalAccent
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: "ANTES"; color: page.muted; font.pixelSize: 10; font.bold: true }
                    Text { text: info.ramMeterStart; color: page.ink; font.pixelSize: 16; font.bold: true }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: "AHORA"; color: page.ramModalAccent; font.pixelSize: 10; font.bold: true }
                    Text { text: info.ramMeterUsed; color: page.ink; font.pixelSize: 16; font.bold: true }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: "VARIACIÓN"; color: page.muted; font.pixelSize: 10; font.bold: true }
                    Text { text: info.ramMeterDelta; color: !info.ramMeterValid ? page.muted : (String(info.ramMeterDelta).startsWith("-") ? "#F6BA64" : "#4EDDC8"); font.pixelSize: 15; font.bold: true }
                }
            }
            Text {
                Layout.fillWidth: true
                text: "Disponible: " + info.ramMeterAvailable + "  ·  Total: " + info.ramMeterTotal
                color: page.muted; font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: "El uso puede subir o bajar por otras aplicaciones. No es un porcentaje de limpieza."
                color: page.muted; font.pixelSize: 10
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }
    Popup {
        id: ramFailure
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(380, parent.width - 44)
        padding: 22
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: page.modalShade }
        background: ModalSurface {}
        contentItem: ColumnLayout {
            spacing: 14
            Text {
                Layout.fillWidth: true
                text: "No se completó la limpieza"
                color: "#F6BA64"; font.pixelSize: 18; font.bold: true
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: info.status
                color: page.ink; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
            ActionButton {
                Layout.alignment: Qt.AlignHCenter
                text: "Entendido"; accent: "#F6BA64"
                onClicked: ramFailure.close()
            }
        }
    }
    Popup {
        id: ramPartial
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(425, parent.width - 32)
        height: partialCol.implicitHeight + 44
        padding: 22
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        Overlay.modal: Rectangle { color: page.modalShade }
        background: ModalSurface {}
        contentItem: ColumnLayout {
            id: partialCol
            spacing: 12
            Text { text: "Limpieza parcialmente completada"; color: "#E5B768"; font.pixelSize: 17; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: info.deepDetail || info.status; color: page.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: "Windows no completó todas las operaciones. La variación mostrada es una medida, no un porcentaje de RAM limpiada."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            ActionButton { text: "Entendido"; Layout.alignment: Qt.AlignRight; onClicked: ramPartial.close() }
        }
    }
    Popup {
        id: ramSuccess
        parent: Overlay.overlay
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        width: Math.min(340, parent.width - 44)
        height: 310
        padding: 24
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: page.modalShade }
        background: ModalSurface {}
        contentItem: ColumnLayout {
            spacing: 14
            Item { Layout.fillHeight: true }
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 96; height: 96; radius: 48
                color: "#252733"
                border.width: 3
                border.color: "#43D68B"
                // Ticket vectorial: nítido en cualquier escala DPI.
                Canvas {
                    anchors.centerIn: parent
                    width: 58; height: 58
                    onPaint: {
                        const ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        ctx.strokeStyle = "#43D68B"
                        ctx.lineWidth = 6
                        ctx.lineCap = "round"
                        ctx.lineJoin = "round"
                        ctx.beginPath()
                        ctx.moveTo(12, 30)
                        ctx.lineTo(24, 42)
                        ctx.lineTo(47, 17)
                        ctx.stroke()
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                text: info.lastRamKind === "ram_safe" ? "Optimización normal completada" : "RAM limpiada correctamente"
                color: page.ink
                font.pixelSize: 18
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: info.lastRamKind === "ram_safe" ? "CorePulse recogió objetos propios. La variación RAM es una lectura del sistema y no se atribuye a la operación." : "Operación aceptada. La variación real de memoria está disponible en la tarjeta RAM."
                color: page.muted
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
            ActionButton {
                Layout.alignment: Qt.AlignHCenter
                text: "Entendido"
                accent: "#43D68B"
                onClicked: ramSuccess.close()
            }
            Item { Layout.fillHeight: true }
        }
    }
    ThinScroll {
        target: cleanupScroll
        anchors.top: cleanupScroll.top
        anchors.bottom: cleanupScroll.bottom
        anchors.right: cleanupScroll.right
        anchors.rightMargin: 2
        z: 1
    }
}
