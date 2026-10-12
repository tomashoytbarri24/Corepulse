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

    readonly property color surface: "#1A1C26"
    readonly property color edge: "#303647"
    readonly property color ink: "#F1F4FB"
    readonly property color muted: "#A4B3C8"

    component OutlineButton: AbstractButton {
        id: button
        property color accentColor: page.currentAccent
        property bool selected: false
        implicitWidth: Math.max(88, textLabel.implicitWidth + 28)
        implicitHeight: 38
        hoverEnabled: true
        background: Rectangle {
            radius: 10
            color: !button.enabled ? "#232530" : button.down ? "#252936" : button.selected ? "#193A35" : button.hovered ? "#313340" : "#242633"
            border.width: 1
            border.color: button.enabled && (button.hovered || button.selected) ? button.accentColor : page.edge
        }
        contentItem: Text {
            id: textLabel
            text: button.text
            color: !button.enabled ? "#8993A5" : button.selected ? button.accentColor : page.ink
            font.pixelSize: 12
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    Flickable {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight + 18
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: content
            width: Math.max(0, pageScroll.width - 17)
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    Layout.preferredWidth: 45
                    Layout.preferredHeight: 45
                    radius: 13
                    color: "#30223F"
                    Glyph { anchors.centerIn: parent; width: 26; height: 26; kind: "palette"; ink: "#C78DFF" }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 4
                    Text { text: "Temas"; color: page.ink; font.pixelSize: 21; font.bold: true }
                    Text { text: "Personalización visual · base inicial del módulo"; color: page.muted; font.pixelSize: 11 }
                }
                OutlineButton { text: "Volver"; onClicked: page.goBack() }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 17
                color: page.surface
                border.width: 1
                border.color: page.edge
                Layout.preferredHeight: introCol.implicitHeight + 32
                ColumnLayout {
                    id: introCol
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 7
                    Text { text: "Tema activo"; color: page.muted; font.pixelSize: 11; font.bold: true }
                    Text {
                        text: (function() {
                            for (let i = 0; i < page.themeCatalog.length; ++i) if (page.themeCatalog[i].id === page.selectedThemeId) return page.themeCatalog[i].title
                            return "CorePulse"
                        })()
                        color: page.currentAccent
                        font.pixelSize: 22
                        font.bold: true
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "En esta primera etapa el módulo de Temas cambia la paleta global del shell principal: fondo, barra lateral y acentos base. Después ampliaremos la cobertura al resto de módulos." 
                        color: page.muted
                        font.pixelSize: 11
                    }
                }
            }

            Text { text: "Colección disponible"; color: page.ink; font.pixelSize: 16; font.bold: true }
            Text { text: "Selecciona un estilo para aplicar inmediatamente la apariencia base de la interfaz."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }

            GridLayout {
                Layout.fillWidth: true
                columns: content.width < 900 ? 1 : 2
                columnSpacing: 12
                rowSpacing: 12
                Repeater {
                    model: page.themeCatalog
                    delegate: Rectangle {
                        id: themeCard
                        required property var modelData
                        readonly property bool active: page.selectedThemeId === modelData.id
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        radius: 16
                        color: page.surface
                        border.width: 1
                        border.color: active ? modelData.accent : page.edge
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: themeCard.modelData.title; color: page.ink; font.pixelSize: 15; font.bold: true; Layout.fillWidth: true }
                                Rectangle {
                                    visible: themeCard.active
                                    radius: 9
                                    color: "#18332E"
                                    border.width: 1
                                    border.color: themeCard.modelData.accent
                                    Layout.preferredWidth: 74
                                    Layout.preferredHeight: 26
                                    Text { anchors.centerIn: parent; text: "Activo"; color: themeCard.modelData.accent; font.pixelSize: 11; font.bold: true }
                                }
                            }
                            Text { text: themeCard.modelData.description; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 84
                                radius: 13
                                border.width: 1
                                border.color: themeCard.modelData.panelBorder
                                gradient: Gradient {
                                    GradientStop { position: 0; color: themeCard.modelData.bgStart }
                                    GradientStop { position: .75; color: themeCard.modelData.bgMid }
                                    GradientStop { position: 1; color: themeCard.modelData.bgEnd }
                                }
                                Rectangle {
                                    x: 10; y: 10
                                    width: 52; height: 64; radius: 10
                                    color: themeCard.modelData.sidebar
                                    border.width: 1
                                    border.color: themeCard.modelData.sidebarBorder
                                    Rectangle {
                                        x: 8; y: 10; width: 36; height: 11; radius: 5
                                        color: themeCard.modelData.sidebarActive
                                    }
                                    Rectangle {
                                        x: 8; y: 28; width: 26; height: 7; radius: 3
                                        color: themeCard.modelData.accent
                                    }
                                    Rectangle {
                                        x: 8; y: 40; width: 22; height: 7; radius: 3
                                        color: themeCard.modelData.cyan
                                    }
                                }
                                Rectangle {
                                    x: 72; y: 10; width: parent.width - 84; height: 64; radius: 10
                                    color: themeCard.modelData.panel
                                    border.width: 1
                                    border.color: themeCard.modelData.panelBorder
                                    Rectangle {
                                        x: 12; y: 12; width: parent.width - 24; height: 12; radius: 6
                                        color: themeCard.modelData.accent
                                        opacity: .22
                                    }
                                    Row {
                                        x: 12; y: 34; spacing: 8
                                        Repeater {
                                            model: [themeCard.modelData.accent, themeCard.modelData.cyan, themeCard.modelData.purple, themeCard.modelData.panelBorder]
                                            delegate: Rectangle {
                                                required property color modelData
                                                width: 22; height: 22; radius: 11
                                                color: modelData
                                                border.width: 1
                                                border.color: "#E0E6F0"
                                                opacity: .95
                                            }
                                        }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Repeater {
                                    model: [themeCard.modelData.accent, themeCard.modelData.cyan, themeCard.modelData.purple, themeCard.modelData.panelBorder]
                                    delegate: Rectangle {
                                        required property color modelData
                                        width: 18; height: 18; radius: 9
                                        color: modelData
                                        border.width: 1
                                        border.color: "#D5DCEA"
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                OutlineButton {
                                    text: themeCard.active ? "Aplicado" : "Aplicar"
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
                radius: 16
                color: page.surface
                border.width: 1
                border.color: page.edge
                Layout.preferredHeight: notes.implicitHeight + 32
                ColumnLayout {
                    id: notes
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8
                    Text { text: "Estado del módulo"; color: page.ink; font.pixelSize: 14; font.bold: true }
                    Text { text: "• Ya puedes cambiar la paleta base de la aplicación en caliente."; color: page.muted; font.pixelSize: 11 }
                    Text { text: "• La integración profunda del tema en todos los módulos se seguirá ampliando versión por versión."; color: page.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
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
