import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    signal applyTheme(string themeId)
    property var themeCatalog: []
    property string selectedThemeId: "corepulse"
    property color currentAccent: "#4EDDC8"
    readonly property color brandBlue: "#259BEF"

    readonly property color surface: themeManager.palette.panel
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted

    function findTheme(themeId) {
        for (let i = 0; i < page.themeCatalog.length; ++i) {
            if (page.themeCatalog[i].id === themeId) return page.themeCatalog[i]
        }
        return null
    }
    readonly property var baseTheme: page.findTheme("corepulse") || ({
        id: "corepulse", title: "CorePulse", isBase: true,
        bgStart: "#070B14", bgMid: "#0B1020", bgEnd: "#20142F",
        sidebar: "#101420", sidebarBorder: "#37415A", sidebarActive: "#21283A",
        panel: "#181D2C", panelRaised: "#21283A", panelBorder: "#37415A",
        accent: "#2C7F77", cyan: "#2F8FC4", purple: "#8257B5",
        description: "La identidad original de CorePulse."
    })
    readonly property var activeTheme: page.findTheme(page.selectedThemeId) || page.baseTheme

    component OutlineButton: AbstractButton {
        id: button
        property color accentColor: page.currentAccent
        property bool selected: false
        property bool actionStyle: false   // ejecuta algo: texto en color de acción (REBUILD 082)
        property bool solidStyle: false    // Aplicar/Actualizar: botón entero de color
        readonly property color actionFill: themeManager.palette.action
        implicitWidth: Math.max(112, textLabel.implicitWidth + 30)
        implicitHeight: 38
        hoverEnabled: true
        background: Rectangle {
            radius: 11
            color: button.solidStyle ? (!button.enabled ? themeManager.palette.actionMuted : button.down ? Qt.darker(button.actionFill, 1.12) : button.hovered ? Qt.lighter(button.actionFill, 1.16) : button.actionFill)
                 : !button.enabled ? "#232530" : button.down ? "#252936" : button.selected ? Qt.rgba(button.accentColor.r, button.accentColor.g, button.accentColor.b, 0.16) : button.hovered ? "#313340" : themeManager.palette.panelRaised
            border.width: button.selected ? 1.5 : 1
            border.color: button.solidStyle ? (button.enabled ? button.actionFill : themeManager.palette.actionMuted)
                          : button.enabled && (button.hovered || button.selected) ? (button.actionStyle ? button.actionFill : button.accentColor) : page.edge
            Behavior on color { ColorAnimation { duration: 150 } }
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }
        contentItem: Text {
            id: textLabel
            text: button.text
            color: button.solidStyle ? (button.enabled ? themeManager.palette.actionText : themeManager.palette.actionMutedText)
                 : button.actionStyle ? (button.enabled ? button.actionFill : "#8993A5")
                 : !button.enabled ? "#8993A5" : button.selected ? button.accentColor : page.ink
            font.pixelSize: 12
            font.weight: button.solidStyle ? Font.Bold : Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    FastFlickable {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight + 24
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: content
            width: Math.max(0, pageScroll.width - 17)
            spacing: 15

            RowLayout {
                Layout.fillWidth: true
                spacing: 13
                Rectangle {
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    radius: 15
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#263B52" }
                        GradientStop { position: 1; color: "#342347" }
                    }
                    border.width: 1
                    border.color: page.activeTheme.accent
                    Glyph { anchors.centerIn: parent; width: 25; height: 25; kind: "palette"; ink: page.activeTheme.accent }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 3
                    Text { text: "TEMAS · IDENTIDAD VISUAL"; color: page.activeTheme.accent; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.3 }
                    Text { text: "Temas"; color: page.ink; font.pixelSize: 22; font.bold: true }
                }
                OutlineButton { text: "Volver"; onClicked: page.goBack() }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 218
                radius: 21
                clip: true
                gradient: Gradient {
                    GradientStop { position: 0; color: page.baseTheme.bgStart }
                    GradientStop { position: .58; color: page.baseTheme.bgMid }
                    GradientStop { position: 1; color: page.baseTheme.bgEnd }
                }
                border.width: 1
                border.color: page.activeTheme.accent
                Rectangle {
                    width: 245; height: 245; radius: 123
                    anchors.right: parent.right; anchors.rightMargin: 150; anchors.top: parent.top; anchors.topMargin: -105
                    color: page.activeTheme.accent; opacity: .075
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 18
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 230
                        Layout.fillHeight: true
                        spacing: 7
                        RowLayout {
                            spacing: 8
                            Rectangle {
                                radius: 8; color: Qt.rgba(page.activeTheme.accent.r, page.activeTheme.accent.g, page.activeTheme.accent.b, .15)
                                border.width: 1; border.color: page.activeTheme.accent
                                Layout.preferredWidth: 122; Layout.preferredHeight: 23
                                Text { anchors.centerIn: parent; text: "CAPA VISUAL ACTIVA"; color: page.activeTheme.accent; font.pixelSize: 8; font.bold: true; font.letterSpacing: .7 }
                            }
                            Text { text: page.activeTheme.title; color: page.ink; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        Text {
                            text: "Tu CorePulse,\ntu identidad."
                            color: page.ink
                            font.pixelSize: 25
                            font.bold: true
                            lineHeight: 1.03
                            Layout.fillWidth: true
                        }
                        Text {
                            text: "Elige una atmósfera para las superficies y acentos decorativos. La identidad CorePulse, los colores de hardware y los estados conservan sus colores."
                            color: page.muted
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            Layout.maximumWidth: 450
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            spacing: 6
                            Repeater {
                                model: [page.activeTheme.accent, page.activeTheme.cyan, page.activeTheme.purple, page.activeTheme.panelBorder]
                                delegate: Rectangle {
                                    required property color modelData
                                    Layout.preferredWidth: 25; Layout.preferredHeight: 6
                                    radius: 3; color: modelData
                                }
                            }
                            Text { text: "Vista previa del estilo seleccionado"; color: page.muted; font.pixelSize: 9; Layout.leftMargin: 5 }
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 258
                        Layout.minimumWidth: 220
                        Layout.preferredHeight: 174
                        radius: 17
                        color: page.activeTheme.panel
                        border.width: 1
                        border.color: page.activeTheme.panelBorder
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 11
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: page.brandBlue }
                                Text { text: "COREPULSE"; color: page.ink; font.pixelSize: 9; font.bold: true; font.letterSpacing: .7; Layout.fillWidth: true }
                                Text { text: "VISTA EN VIVO"; color: page.activeTheme.cyan; font.pixelSize: 7; font.bold: true }
                            }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: page.activeTheme.panelBorder; opacity: .7 }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 8
                                Rectangle {
                                    Layout.preferredWidth: 42; Layout.fillHeight: true
                                    radius: 9; color: page.activeTheme.sidebar; border.width: 1; border.color: page.activeTheme.sidebarBorder
                                    Column {
                                        anchors.centerIn: parent
                                        spacing: 7
                                        Repeater {
                                            model: [page.activeTheme.accent, page.activeTheme.cyan, page.activeTheme.panelBorder]
                                            delegate: Rectangle { required property color modelData; width: 21; height: 5; radius: 2.5; color: modelData }
                                        }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    spacing: 6
                                    Text { text: "Rendimiento"; color: page.ink; font.pixelSize: 8; font.bold: true }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Repeater {
                                            model: [
                                                {name:"Intel", tint:"#1688F3"},
                                                {name:"NVIDIA", tint:"#76B900"},
                                                {name:"AMD", tint:"#E34245"},
                                                {name:"RAM", tint:"#20A99A"},
                                                {name:"SSD", tint:"#9970D0"}
                                            ]
                                            delegate: Rectangle {
                                                required property var modelData
                                                Layout.fillWidth: true; Layout.preferredHeight: 36
                                                radius: 8; color: page.activeTheme.panelRaised; border.width: 1; border.color: page.activeTheme.panelBorder
                                                Column {
                                                    anchors.left: parent.left; anchors.leftMargin: 7; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                                                    Text { width: parent.width; text: modelData.name; color: page.muted; font.pixelSize: 7; elide: Text.ElideRight }
                                                    Rectangle { width: Math.min(24, parent.width); height: 4; radius: 2; color: modelData.tint }
                                                }
                                            }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 20
                                        radius: 7; color: page.activeTheme.panelRaised; border.width: 1; border.color: page.activeTheme.panelBorder
                                        Rectangle { x: 6; y: 7; width: parent.width * .53; height: 5; radius: 2.5; color: page.activeTheme.accent }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                radius: 16
                color: page.surface
                border.width: 1
                border.color: page.edge
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 15; anchors.rightMargin: 15; anchors.topMargin: 11; anchors.bottomMargin: 11
                    spacing: 11
                    Rectangle {
                        Layout.preferredWidth: 42; Layout.preferredHeight: 42; radius: 13
                        color: Qt.rgba(page.baseTheme.accent.r, page.baseTheme.accent.g, page.baseTheme.accent.b, .16)
                        border.width: 1; border.color: page.baseTheme.accent
                        Glyph { anchors.centerIn: parent; width: 22; height: 22; kind: "palette"; ink: page.baseTheme.accent }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 120
                        spacing: 3
                        Text { text: "CAPA BASE · PERMANENTE"; color: page.baseTheme.accent; font.pixelSize: 9; font.bold: true; font.letterSpacing: .8 }
                        Text { text: "Fondo y estructura original de CorePulse: siempre presentes, incluso al cambiar de estilo."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    RowLayout {
                        spacing: 5
                        Repeater {
                            model: [page.baseTheme.bgStart, page.baseTheme.bgMid, page.baseTheme.bgEnd]
                            delegate: Rectangle {
                                required property color modelData
                                Layout.preferredWidth: 17; Layout.preferredHeight: 25; radius: 6
                                color: modelData; border.width: 1; border.color: page.baseTheme.panelBorder
                            }
                        }
                    }
                    Rectangle {
                        Layout.preferredWidth: 80; Layout.preferredHeight: 27; radius: 9
                        color: Qt.rgba(page.baseTheme.accent.r, page.baseTheme.accent.g, page.baseTheme.accent.b, .12)
                        border.width: 1; border.color: page.baseTheme.accent
                        Text { anchors.centerIn: parent; text: "FIJA · NO SE BORRA"; color: page.baseTheme.accent; font.pixelSize: 7; font.bold: true }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: "Capas de color"; color: page.ink; font.pixelSize: 17; font.bold: true }
                    Text { text: "La base permanece; cada estilo aporta su propia paleta de superficies y acentos."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                Rectangle {
                    Layout.preferredWidth: 92; Layout.preferredHeight: 29; radius: 10
                    color: page.surface; border.width: 1; border.color: page.edge
                    Text { anchors.centerIn: parent; text: Math.max(0, page.themeCatalog.length - 1) + " estilos"; color: page.muted; font.pixelSize: 10; font.bold: true }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: content.width < 860 ? 1 : 2
                columnSpacing: 12
                rowSpacing: 12
                Repeater {
                    model: page.themeCatalog
                    delegate: Rectangle {
                        id: themeCard
                        required property var modelData
                        readonly property bool active: page.selectedThemeId === modelData.id
                        readonly property bool hovered: hover.hovered
                        Layout.fillWidth: true
                        Layout.preferredHeight: 252
                        radius: 17
                        color: themeManager.palette.panel
                        border.width: active ? 1.5 : 1
                        border.color: active ? modelData.accent : hovered ? page.activeTheme.panelBorder : page.edge
                        Behavior on border.color { ColorAnimation { duration: 150 } }
                        HoverHandler { id: hover }

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 13
                            spacing: 7
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                Text {
                                    text: themeCard.modelData.isBase ? "BASE PERMANENTE" : "CAPA VISUAL"
                                    color: themeCard.modelData.accent
                                    font.pixelSize: 8; font.bold: true; font.letterSpacing: .7
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    visible: themeCard.active
                                    Layout.preferredWidth: 60; Layout.preferredHeight: 21; radius: 8
                                    color: Qt.rgba(themeCard.modelData.accent.r, themeCard.modelData.accent.g, themeCard.modelData.accent.b, .15)
                                    border.width: 1; border.color: themeCard.modelData.accent
                                    Text { anchors.centerIn: parent; text: "EN USO"; color: themeCard.modelData.accent; font.pixelSize: 8; font.bold: true }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 7
                                Text { text: themeCard.modelData.title; color: page.ink; font.pixelSize: 15; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Rectangle {
                                    visible: themeCard.modelData.isBase
                                    Layout.preferredWidth: 58; Layout.preferredHeight: 21; radius: 8
                                    color: themeCard.modelData.panelRaised
                                    border.width: 1; border.color: themeCard.modelData.panelBorder
                                    Text { anchors.centerIn: parent; text: "FIJA"; color: page.muted; font.pixelSize: 8; font.bold: true }
                                }
                            }
                            Text {
                                text: themeCard.modelData.description
                                color: page.muted; font.pixelSize: 10; Layout.fillWidth: true
                                wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 84
                                radius: 12; clip: true
                                gradient: Gradient {
                                    GradientStop { position: 0; color: themeCard.modelData.bgStart }
                                    GradientStop { position: .72; color: themeCard.modelData.bgMid }
                                    GradientStop { position: 1; color: themeCard.modelData.bgEnd }
                                }
                                border.width: 1; border.color: themeCard.modelData.panelBorder
                                Rectangle {
                                    x: 9; y: 8; width: 42; height: 68; radius: 9
                                    color: themeCard.modelData.sidebar
                                    border.width: 1; border.color: themeCard.modelData.sidebarBorder
                                    Column {
                                        anchors.centerIn: parent; spacing: 7
                                        Rectangle { width: 23; height: 5; radius: 2.5; color: themeCard.modelData.sidebarActive }
                                        Rectangle { width: 16; height: 4; radius: 2; color: themeCard.modelData.accent }
                                        Rectangle { width: 19; height: 4; radius: 2; color: themeCard.modelData.cyan }
                                    }
                                }
                                Rectangle {
                                    x: 59; y: 8; width: parent.width - 68; height: 68; radius: 9
                                    color: themeCard.modelData.panel
                                    border.width: 1; border.color: themeCard.modelData.panelBorder
                                    Rectangle {
                                        x: 9; y: 9; width: parent.width - 18; height: 8; radius: 4
                                        color: themeCard.modelData.accent; opacity: .78
                                    }
                                    Row {
                                        x: 9; y: 27; spacing: 6
                                        Repeater {
                                            model: [themeCard.modelData.accent, themeCard.modelData.cyan, themeCard.modelData.purple]
                                            delegate: Rectangle {
                                                required property color modelData
                                                width: Math.min(28, (themeCard.width - 130) / 7); height: 28; radius: 7
                                                color: themeCard.modelData.panelRaised
                                                border.width: 1; border.color: modelData
                                                Rectangle { x: 5; y: 5; width: 12; height: 4; radius: 2; color: modelData }
                                                Rectangle { x: 5; y: 14; width: 16; height: 5; radius: 2.5; color: modelData; opacity: .45 }
                                            }
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 5
                                Repeater {
                                    model: [themeCard.modelData.accent, themeCard.modelData.cyan, themeCard.modelData.purple, themeCard.modelData.panelBorder]
                                    delegate: Rectangle {
                                        required property color modelData
                                        Layout.preferredWidth: 15; Layout.preferredHeight: 15; radius: 7.5
                                        color: modelData; border.width: 1; border.color: "#B7C4D8"
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                OutlineButton { actionStyle: !themeCard.active; solidStyle: !themeCard.active;
                                    text: themeCard.active ? "En uso" : themeCard.modelData.isBase ? "Volver a CorePulse" : "Aplicar capa"
                                    selected: themeCard.active
                                    accentColor: themeCard.modelData.accent
                                    onClicked: page.applyTheme(themeCard.modelData.id)
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 55
                radius: 14
                color: page.surface
                border.width: 1; border.color: page.edge
                RowLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 9
                    Rectangle { Layout.preferredWidth: 4; Layout.fillHeight: true; radius: 2; color: page.activeTheme.cyan }
                    Text {
                        text: "Los colores de CPU, GPU y alertas conservan su significado; solo cambia la identidad visual de la interfaz."
                        color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true
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
        anchors.rightMargin: 2
    }
}
