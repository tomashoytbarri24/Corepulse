import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Tweaks de bajo riesgo: solo HKCU, confirmación visible y restauración exacta.
// Toda lectura/escritura pasa por tweaks.py; QML no ejecuta comandos de Windows.
Item {
    id: page
    signal goBack()
    property string pendingId: ""
    property string pendingAction: ""
    property string pendingTitle: ""
    property string feedback: ""
    readonly property var groups: ["Explorador", "Barra de tareas", "Interfaz", "Privacidad", "Gaming", "Rendimiento", "Energía", "Sistema", "Actualizaciones", "Red", "Apps y debloat", "Seguridad avanzada"]
    // Colores de categoría: cambian únicamente la presentación, no la operación.
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
    readonly property color surface: "#1A1C26"
    readonly property color edge: "#2D3243"
    readonly property color cyan: "#17B9F7"
    readonly property color secondary: "#9FABBF"
    readonly property var displayRows: {
        const rows = []
        const cols = page.width >= 790 ? 2 : 1
        for (const category of page.groups) {
            const options = tweaks.options.filter(function(opt) { return opt.category === category })
            rows.push({kind: "header", category: category})
            for (let n = 0; n < options.length; n += cols)
                rows.push({kind: "cards", items: options.slice(n, n + cols)})
        }
        return rows
    }
    Component.onCompleted: tweaks.ensureFresh()

    component OptionCard: Rectangle {
        id:optionCard
        property var opt: ({id:"", title:"", category:"", description:"", detail:"", status:"", active:false, available:false, canRestore:false, requiresExplorer:false})
        Layout.fillWidth:true
        Layout.minimumWidth:0
        Layout.preferredHeight:188
        radius:17;color:"#1B1F2B";border.width:1
        border.color:optionCard.opt.active?page.groupColor(optionCard.opt.category):page.edge
        ColumnLayout {
            anchors.fill:parent;anchors.margins:14;spacing:7
            RowLayout {
                Layout.fillWidth:true;spacing:9
                Text {
                    Layout.fillWidth:true;Layout.minimumWidth:0
                    text:optionCard.opt.title
                    color:"#F0F3FB";font.bold:true;font.pixelSize:13
                    elide:Text.ElideRight
                    ToolTip.visible:titleHover.containsMouse && truncated
                    ToolTip.text:optionCard.opt.title
                    MouseArea {id:titleHover;anchors.fill:parent;hoverEnabled:true;acceptedButtons:Qt.NoButton}
                }
                Rectangle {
                    Layout.preferredWidth:optionStatus.implicitWidth+18
                    Layout.preferredHeight:23;radius:9
                    color:optionCard.opt.active?"#293143":"#292E3A"
                    Text {
                        id:optionStatus
                        anchors.centerIn:parent
                        text:optionCard.opt.status
                        color:optionCard.opt.active?page.groupColor(optionCard.opt.category):"#BAC2D2"
                        font.pixelSize:10
                    }
                }
            }
            Text {
                Layout.fillWidth:true;Layout.fillHeight:true
                text:optionCard.opt.description + (optionCard.opt.detail && !optionCard.opt.available ? "\n" + optionCard.opt.detail : "")
                wrapMode:Text.WordWrap
                color:"#AAB7CB";font.pixelSize:11;lineHeight:1.13
            }
            RowLayout {
                Layout.fillWidth:true;spacing:8
                Text {
                    visible:optionCard.opt.requiresExplorer
                    Layout.fillWidth:true;Layout.minimumWidth:0
                    text:"Puede requerir reabrir el Explorador"
                    color:"#8699AF";font.pixelSize:9;elide:Text.ElideRight
                }
                Item {Layout.fillWidth:!optionCard.opt.requiresExplorer}
                Rectangle {
                    Layout.preferredWidth:82;Layout.preferredHeight:30;radius:9
                    color:!tweaks.busy && optionCard.opt.available && !optionCard.opt.active
                           ?applyHover.containsMouse?Qt.lighter(page.groupColor(optionCard.opt.category),1.16):page.groupColor(optionCard.opt.category):"#303746"
                    Text {
                        anchors.centerIn:parent;text:"Aplicar";font.bold:true;font.pixelSize:11
                        color:!tweaks.busy && optionCard.opt.available && !optionCard.opt.active?"#101823":"#8D9CB0"
                    }
                    MouseArea {
                        id:applyHover;anchors.fill:parent;hoverEnabled:true
                        enabled:!tweaks.busy && optionCard.opt.available && !optionCard.opt.active
                        cursorShape:enabled?Qt.PointingHandCursor:Qt.ArrowCursor
                        onClicked:{page.pendingId=optionCard.opt.id;page.pendingTitle=optionCard.opt.title;page.pendingAction="apply"}
                    }
                }
                Rectangle {
                    Layout.preferredWidth:81;Layout.preferredHeight:30;radius:9
                    color:!tweaks.busy && optionCard.opt.available && optionCard.opt.canRestore
                          ?restoreHover.containsMouse?"#3D4558":"#2C3343":"#252A36"
                    Text {
                        anchors.centerIn:parent;text:"Restaurar";font.pixelSize:11
                        color:!tweaks.busy && optionCard.opt.available && optionCard.opt.canRestore?"#DBE5F3":"#7C8598"
                    }
                    MouseArea {
                        id:restoreHover;anchors.fill:parent;hoverEnabled:true
                        enabled:!tweaks.busy && optionCard.opt.available && optionCard.opt.canRestore
                        cursorShape:enabled?Qt.PointingHandCursor:Qt.ArrowCursor
                        onClicked:{page.pendingId=optionCard.opt.id;page.pendingTitle=optionCard.opt.title;page.pendingAction="restore"}
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill:parent
        spacing:13
        RowLayout {
            Layout.fillWidth:true
            spacing:13
            Rectangle {
                Layout.preferredWidth:46;Layout.preferredHeight:46
                radius:14;color:"#18394B"
                Glyph {anchors.centerIn:parent;width:27;height:27;kind:"sliders";ink:page.cyan}
            }
            ColumnLayout {
                Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                Text {
                    text:"Tweaks Windows 11"
                    Layout.fillWidth:true;elide:Text.ElideRight
                    color:"#F3F5FC";font.pixelSize:20;font.bold:true
                }
                Text {
                    text:tweaks.busy ? tweaks.options.length + " ajustes originales · Comprobando en segundo plano…" : tweaks.options.length + " ajustes originales · " + tweaks.options.filter(function(o) {return o.available}).length + " disponibles en este equipo"
                    Layout.fillWidth:true;elide:Text.ElideRight
                    color:page.secondary;font.pixelSize:11
                }
            }
            Rectangle {
                Layout.preferredWidth:67;Layout.preferredHeight:34
                radius:11;color:backHover.containsMouse?"#314055":"#222B3A"
                Text {anchors.centerIn:parent;text:"Volver";color:"#DCE8FA";font.pixelSize:11}
                MouseArea {
                    id:backHover;anchors.fill:parent;hoverEnabled:true
                    cursorShape:Qt.PointingHandCursor;onClicked:page.goBack()
                }
            }
            Rectangle {
                Layout.preferredWidth:87;Layout.preferredHeight:34
                radius:11;color:refreshHover.containsMouse?"#314055":"#222B3A"
                Text {anchors.centerIn:parent;text:"Actualizar";color:"#DCE8FA";font.pixelSize:11}
                MouseArea {
                    id:refreshHover;anchors.fill:parent;hoverEnabled:true
                    cursorShape:Qt.PointingHandCursor;onClicked:tweaks.refresh()
                }
            }
        }

        Rectangle {
            visible:page.feedback!==""
            Layout.fillWidth:true
            Layout.preferredHeight:visible?Math.max(40,feedbackText.implicitHeight+18):0
            radius:11;color:"#242B3A";border.width:1;border.color:"#384158"
            Text {
                id:feedbackText
                anchors.left:parent.left;anchors.right:parent.right
                anchors.leftMargin:12;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter
                text:page.feedback;wrapMode:Text.WordWrap;color:"#DCE5F1";font.pixelSize:11
            }
        }

        // ListView crea tarjetas solo cuando llegan a la zona visible.
        // No instanciar 78 controles de golpe al abrir Tweaks.
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            ListView {
                id: scroller
                anchors.fill: parent
                clip: true
                model: page.displayRows
                cacheBuffer: 280
                spacing: 10
                boundsBehavior: Flickable.StopAtBounds
                delegate: Item {
                    id: displayRow
                    required property var modelData
                    width: Math.max(0, scroller.width - 16)
                    height: modelData.kind === "header" ? 25 : 188
                    RowLayout {
                        visible: displayRow.modelData.kind === "header"
                        anchors.fill: parent
                        spacing: 10
                        Rectangle {
                            Layout.preferredWidth: 5; Layout.preferredHeight: 17; radius: 2
                            color: page.groupColor(displayRow.modelData.category || "")
                        }
                        Text {
                            text: (displayRow.modelData.category || "").toUpperCase()
                            color: page.groupColor(displayRow.modelData.category || "")
                            font.pixelSize: 11; font.bold: true
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 1
                            color: page.groupColor(displayRow.modelData.category || ""); opacity: 0.4
                        }
                    }
                    RowLayout {
                        visible: displayRow.modelData.kind === "cards"
                        anchors.fill: parent
                        spacing: 12
                        Repeater {
                            model: displayRow.modelData.items || []
                            delegate: OptionCard {
                                opt: modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                            }
                        }
                    }
                }
                footer: Text {
                    width: Math.max(0, scroller.width - 16)
                    topPadding: 14
                    bottomPadding: 12
                    text: "La disponibilidad depende de la edición de Windows, permisos y reversión verificable; no se cambian Defender, Windows Update, servicios ni controladores automáticamente. Los ajustes críticos o irreversibles no pueden aplicarse. Restaurar requiere respaldo exacto."
                    wrapMode: Text.WordWrap; color: "#7D8A9D"; font.pixelSize: 10
                }
            }
            ThinScroll {
                target: scroller
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                anchors.rightMargin: 2
            }
        }
    }

    Item {
        z:20;anchors.fill:parent
        visible:page.pendingAction!==""
        Rectangle {anchors.fill:parent;color:"#B9000000"}
        MouseArea {anchors.fill:parent}
        Rectangle {
            anchors.centerIn:parent
            width:Math.min(parent.width-26,480)
            height:Math.min(parent.height-20,248)
            radius:19;color:"#212634";border.width:1;border.color:"#3B465D"
            ColumnLayout {
                anchors.fill:parent;anchors.margins:21;spacing:14
                Text {
                    Layout.fillWidth:true
                    text:page.pendingAction==="apply"?"¿Aplicar ajuste?":"¿Restaurar valor anterior?"
                    font.pixelSize:18;font.bold:true;color:"#F3F5FC"
                }
                Text {
                    Layout.fillWidth:true;Layout.fillHeight:true
                    text:page.pendingAction==="apply"
                        ?"Se respaldará el estado antes de cambiar: "+page.pendingTitle+". Algunos cambios requieren administrador, reinicio o reabrir el Explorador."
                        :"Se restaurará el valor exacto guardado por CorePulse antes de modificar: "+page.pendingTitle+"."
                    wrapMode:Text.WordWrap;font.pixelSize:12;lineHeight:1.14;color:"#B8C5D7"
                }
                RowLayout {
                    Layout.alignment:Qt.AlignRight;spacing:12
                    Rectangle {
                        Layout.preferredWidth:100;Layout.preferredHeight:39;radius:11;color:cancelHover.containsMouse?"#364055":"#2D3545"
                        Text {anchors.centerIn:parent;text:"Cancelar";color:"#E6EAF3";font.pixelSize:12}
                        MouseArea {id:cancelHover;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:page.pendingAction=""}
                    }
                    Rectangle {
                        Layout.preferredWidth:120;Layout.preferredHeight:39;radius:11;color:confirmHover.containsMouse?"#2678A4":"#19628A"
                        Text {anchors.centerIn:parent;text:page.pendingAction==="apply"?"Sí, aplicar":"Sí, restaurar";color:"#FFF";font.bold:true;font.pixelSize:12}
                        MouseArea {
                            id:confirmHover;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                            onClicked:{
                                if(page.pendingAction==="apply") page.feedback=tweaks.applyTweak(page.pendingId)
                                else page.feedback=tweaks.restoreTweak(page.pendingId)
                                page.pendingAction=""
                                page.pendingId=""
                                // applyTweak/restoreTweak inicia un único refresh asíncrono.
                            }
                        }
                    }
                }
            }
        }
    }
}
