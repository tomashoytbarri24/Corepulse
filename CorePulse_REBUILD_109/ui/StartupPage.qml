import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    property string pendingId: ""
    property string pendingName: ""
    property bool pendingRestore: false
    readonly property var theme: themeManager.palette
    readonly property var info: startupManager && startupManager.data ? startupManager.data : ({busy:false,items:[],count:0,enabled_count:0,disabled_count:0,actionMessage:"N/A",lastUpdate:"N/A"})
    Component.onCompleted: startupManager.refresh()

    Item {
        anchors.fill: parent
        ColumnLayout { anchors.fill: parent; anchors.margins: 0; spacing: 12
            RowLayout { Layout.fillWidth: true; spacing: 12
                Rectangle { width: 44; height: 44; radius: 13; color: page.theme.panelRaised; Glyph { anchors.centerIn: parent; width: 24; height: 24; kind:"power"; ink:page.theme.accent } }
                ColumnLayout { Layout.fillWidth:true; spacing:3
                    Text { text:"Inicio de Windows"; color:page.theme.ink; font.pixelSize:22; font.bold:true }
                    Text { text:"Entradas de usuario verificadas; Microsoft, seguridad, drivers y ámbitos del sistema quedan solo en observación."; color:page.theme.muted; font.pixelSize:10; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                }
                Rectangle { Layout.preferredWidth:108; Layout.preferredHeight:36; radius:10; color:(info.busy)?themeManager.palette.actionMuted:refreshMouse.containsMouse?Qt.lighter(themeManager.palette.action,1.16):themeManager.palette.action; border.width:1; border.color:(info.busy)?themeManager.palette.actionMuted:themeManager.palette.action
                    Text { anchors.centerIn:parent; text:info.busy?"Consultando…":"Actualizar"; color:(info.busy)?themeManager.palette.actionMutedText:themeManager.palette.actionText; font.pixelSize:11; font.bold:true }
                    MouseArea { id:refreshMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; enabled:!info.busy; onClicked:startupManager.refresh() }
                }
            }
            RowLayout { Layout.fillWidth:true; spacing:10
                Repeater { model:[{title:"Entradas",value:String(info.count)},{title:"Habilitadas",value:String(info.enabled_count)},{title:"Deshabilitadas",value:String(info.disabled_count)}]
                    delegate: Rectangle { required property var modelData; Layout.fillWidth:true; Layout.preferredHeight:58; radius:12; color:page.theme.panel; border.width:1; border.color:page.theme.panelBorder
                        RowLayout { anchors.fill:parent; anchors.margins:12; Text { text:modelData.title; color:page.theme.muted; font.pixelSize:10; Layout.fillWidth:true } Text { text:modelData.value; color:page.theme.ink; font.pixelSize:17; font.bold:true } }
                    }
                }
            }
            Text { Layout.fillWidth:true; text:info.actionMessage + " · Actualizado: " + info.lastUpdate; color:page.theme.muted; font.pixelSize:10; wrapMode:Text.WordWrap }
            FastFlickable { Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:width; contentHeight:items.implicitHeight; clip:true
                ColumnLayout { id:items; width:parent.width; spacing:8
                    Repeater { model:info.items || []
                        delegate: Rectangle { required property var modelData; Layout.fillWidth:true; implicitHeight:entry.implicitHeight+22; radius:12; color:page.theme.panel; border.width:1; border.color:page.theme.panelBorder
                            ColumnLayout { id:entry; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:11; spacing:5
                                RowLayout { Layout.fillWidth:true
                                    Text { text:modelData.name || "Elemento"; color:page.theme.ink; font.pixelSize:12; font.bold:true; Layout.fillWidth:true; elide:Text.ElideRight }
                                    Text { text:modelData.enabled?"HABILITADO":"DESHABILITADO"; color:modelData.enabled?"#36D6A0":"#E9B768"; font.pixelSize:9; font.bold:true }
                                }
                                Text { text:(modelData.publisher || "Editor N/A") + " · " + (modelData.location || "Ubicación N/A"); color:page.theme.muted; font.pixelSize:9; Layout.fillWidth:true; wrapMode:Text.WrapAnywhere }
                                Text { text:(modelData.impact === "NO_MEDIDO" ? "Impacto no medido" : "Memoria del proceso en ejecución: " + Number(modelData.running_memory_mb).toFixed(0) + " MB") + " · " + (modelData.action_reason || ""); color:page.theme.muted; font.pixelSize:9; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                                RowLayout { Layout.fillWidth:true
                                    Item { Layout.fillWidth:true }
                                    Rectangle { visible:modelData.enabled && modelData.safe_to_disable; Layout.preferredWidth:118; Layout.preferredHeight:31; radius:9; color:disableMouse.containsMouse?page.theme.panel:page.theme.panel; border.width:1; border.color:"#9B7845"
                                        Text { anchors.centerIn:parent; text:"Deshabilitar"; color:"#EBC277"; font.pixelSize:10; font.bold:true }
                                        MouseArea { id:disableMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; enabled:!info.busy; onClicked:{ page.pendingId=modelData.source_id; page.pendingName=modelData.name; page.pendingRestore=false } }
                                    }
                                    Rectangle { visible:!modelData.enabled && modelData.can_restore; Layout.preferredWidth:110; Layout.preferredHeight:31; radius:9; color:page.theme.panel; border.width:1; border.color:page.theme.accent
                                        Text { anchors.centerIn:parent; text:"Restaurar"; color:page.theme.accent; font.pixelSize:10; font.bold:true }
                                        MouseArea { anchors.fill:parent; cursorShape:Qt.PointingHandCursor; enabled:!info.busy; onClicked:{ page.pendingId=modelData.source_id; page.pendingName=modelData.name; page.pendingRestore=true } }
                                    }
                                }
                            }
                        }
                    }
                    Text { visible:!info.busy && (info.items || []).length===0; text:"Windows no proporcionó entradas de inicio verificables."; color:page.theme.muted; font.pixelSize:11; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                }
            }
            RowLayout { Layout.fillWidth:true
                Rectangle {
                    Layout.preferredWidth:108; Layout.preferredHeight:34; radius:10
                    color:page.theme.panelRaised; border.width:1; border.color:page.theme.panelBorder
                    Text { anchors.centerIn:parent; text:"Volver"; color:page.theme.ink; font.pixelSize:11; font.bold:true }
                    MouseArea { anchors.fill:parent; cursorShape:Qt.PointingHandCursor; onClicked:page.goBack() }
                }
                Item { Layout.fillWidth:true }
                Text { text:"Solo se permite desactivar entradas HKCU y archivos Startup de usuario que tengan copia reversible."; color:page.theme.muted; font.pixelSize:9; Layout.fillWidth:true; horizontalAlignment:Text.AlignRight; wrapMode:Text.WordWrap }
            }
        }
    }
    Rectangle { visible:page.pendingId!==""; anchors.fill:parent; z:30; color:"#B5000000"
        Rectangle { width:Math.min(parent.width-24,440); height:confirmColumn.implicitHeight+34; anchors.centerIn:parent; radius:16; color:page.theme.panel; border.width:1; border.color:page.theme.panelBorder
            ColumnLayout { id:confirmColumn; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:17; spacing:12
                Text { text:page.pendingRestore?"Restaurar al inicio":"Deshabilitar del inicio"; color:page.theme.ink; font.pixelSize:17; font.bold:true }
                Text { text:page.pendingRestore?"CorePulse restaurará «"+page.pendingName+"» desde su copia. Si la entrada volvió a existir, se conserva sin sobrescribirla.":"CorePulse quitará «"+page.pendingName+"» del inicio de sesión y guardará una copia exacta para poder restaurarlo. Esta acción no cierra el programa si ya está abierto."; color:page.theme.muted; font.pixelSize:11; Layout.fillWidth:true; wrapMode:Text.WordWrap }
                RowLayout { Layout.fillWidth:true; Item{Layout.fillWidth:true}
                    Rectangle {
                        Layout.preferredWidth:95; Layout.preferredHeight:32; radius:9
                        color:page.theme.panelRaised; border.width:1; border.color:page.theme.panelBorder
                        Text { anchors.centerIn:parent; text:"Cancelar"; color:page.theme.ink; font.pixelSize:10 }
                        MouseArea { anchors.fill:parent; cursorShape:Qt.PointingHandCursor; onClicked:page.pendingId="" }
                    }
                    Rectangle {
                        Layout.preferredWidth:105; Layout.preferredHeight:32; radius:9
                        color:page.theme.panelRaised; border.width:1; border.color:page.theme.accent
                        Text { anchors.centerIn:parent; text:"Confirmar"; color:page.theme.accent; font.pixelSize:10; font.bold:true }
                        MouseArea {
                            anchors.fill:parent; cursorShape:Qt.PointingHandCursor
                            onClicked: {
                                const id=page.pendingId
                                const restore=page.pendingRestore
                                page.pendingId=""
                                if(restore) startupManager.restoreItem(id)
                                else startupManager.disableItem(id)
                            }
                        }
                    }
                }
            }
        }
    }
}
