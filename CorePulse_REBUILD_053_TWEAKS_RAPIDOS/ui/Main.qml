import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible:true
    title:"CorePulse — Rebuild 053"
    width:initialWindowWidth
    height:initialWindowHeight
    minimumWidth:Math.min(900,initialWindowWidth)
    minimumHeight:Math.min(600,initialWindowHeight)
    x:initialWindowX
    y:initialWindowY
    flags:Qt.Window | Qt.FramelessWindowHint
    color:window.activeTheme.bgStart

    property bool sidebarCollapsed:false
    property bool moreOpen:false
    property string selectedPage:"summary"
    property string componentBackTarget:"summary"
    property bool restartConfirmOpen:false
    property bool restartResultOpen:false
    property string selectedThemeId:"corepulse"
    readonly property var themeCatalog:[
        {id:"corepulse", title:"CorePulse", accent:"#4EDDC8", cyan:"#17B9F7", purple:"#B756EA", bgStart:"#111319", bgMid:"#14131E", bgEnd:"#201529", sidebar:"#14131D", sidebarBorder:"#2C2A37", sidebarActive:"#1B3D58", sidebarActiveIcon:"#173449", sidebarActiveBorder:"#21516C", panel:"#1A1C26", panelBorder:"#303647", description:"Base oficial oscura de CorePulse."},
        {id:"aurora", title:"Aurora", accent:"#59E3C0", cyan:"#42C8FF", purple:"#7C73FF", bgStart:"#0F1720", bgMid:"#111D27", bgEnd:"#142633", sidebar:"#101923", sidebarBorder:"#223444", sidebarActive:"#173F52", sidebarActiveIcon:"#143747", sidebarActiveBorder:"#2A6078", panel:"#18232D", panelBorder:"#314453", description:"Azul petróleo con acentos turquesa."},
        {id:"violet", title:"Violet Neon", accent:"#7EE0FF", cyan:"#5EB8FF", purple:"#C06BFF", bgStart:"#12111A", bgMid:"#18142A", bgEnd:"#241536", sidebar:"#171222", sidebarBorder:"#352847", sidebarActive:"#392B52", sidebarActiveIcon:"#2E2344", sidebarActiveBorder:"#6A4C94", panel:"#1D1A28", panelBorder:"#433651", description:"Violeta técnico con brillo frío."},
        {id:"ember", title:"Ember Tech", accent:"#F6C166", cyan:"#FF9D5C", purple:"#D8699B", bgStart:"#151216", bgMid:"#1C161D", bgEnd:"#27161F", sidebar:"#18131A", sidebarBorder:"#3A2933", sidebarActive:"#4A2E33", sidebarActiveIcon:"#3B2428", sidebarActiveBorder:"#7A4B54", panel:"#211A22", panelBorder:"#493642", description:"Ámbar cálido y magenta suave."}
    ]
    function themeById(id) {
        for (let i = 0; i < themeCatalog.length; ++i) if (themeCatalog[i].id === id) return themeCatalog[i]
        return themeCatalog[0]
    }
    readonly property var activeTheme: themeById(selectedThemeId)
    readonly property color cyan:activeTheme.cyan
    readonly property color purple:activeTheme.purple
    readonly property color muted:"#9DA9BA"
    readonly property color ink:"#F0F3FB"
    readonly property var primaryGroups:[
        {title:"MONITOREO",items:[{id:"summary",label:"Resumen",icon:"dashboard"},{id:"benchmark",label:"Benchmark",icon:"gauge"}]},
        {title:"DIAGNÓSTICO",items:[{id:"diagnostic",label:"Iniciar diagnóstico",icon:"scan"},{id:"health",label:"Centro de salud",icon:"health_shield"}]},
        {title:"MANTENIMIENTO",items:[{id:"cleanup",label:"Limpieza de sistema",icon:"broom"},{id:"tweaks",label:"Tweaks Windows 11",icon:"sliders"},{id:"advanced_network",label:"Red avanzada",icon:"network"}]},
        {title:"HISTORIAL",items:[{id:"alerts",label:"Alertas técnicas",icon:"bell_alert"},{id:"trends",label:"Tendencias",icon:"trend_up"},{id:"alert_history",label:"Historial de alertas",icon:"history"}]},
        {title:"PERSONALIZACIÓN",items:[{id:"themes",label:"Temas",icon:"palette"},{id:"ai",label:"CorePulse AI",icon:"spark_ai"}]}
    ]
    readonly property var additionalModules:[
        {id:"cpu",label:"Procesador",icon:"cpu"},
        {id:"gpu",label:"Tarjeta gráfica",icon:"gpu"},
        {id:"ram",label:"Memoria RAM",icon:"ram"},
        {id:"storage",label:"Almacenamiento",icon:"storage"},
        {id:"windows_health",label:"Análisis de Windows",icon:"settings"},
        {id:"battery",label:"Batería",icon:"battery"},
        {id:"network",label:"Red",icon:"wifi"},
        {id:"gaming",label:"Game Boost",icon:"gamepad"},
        {id:"drivers",label:"Drivers",icon:"drivers"},
        {id:"audio",label:"Audio",icon:"headphones"},
        {id:"services",label:"Servicios",icon:"services"},
        {id:"startup",label:"Inicio",icon:"power"},
        {id:"reports",label:"Reportes",icon:"file_chart"},
        {id:"restore",label:"Recuperación",icon:"restore"},
        {id:"change_history",label:"Historial de cambios",icon:"file_clock"},
        {id:"repair",label:"Reparación",icon:"wrench"},
        {id:"overlay",label:"Overlay",icon:"layers"},
        {id:"telemetry",label:"Telemetría",icon:"activity"},
        {id:"evidence",label:"Evidencias",icon:"clipboard"}
    ]
    function pageTitle(pageId) {
        for (const group of primaryGroups) for (const p of group.items) if(p.id===pageId)return p.label
        for (const p of additionalModules) if(p.id===pageId)return p.label
        if (pageId === "readings") return "Lecturas disponibles"
        return pageId
    }
    function openComponent(kind) {
        if (kind !== "cpu" && kind !== "gpu" && kind !== "ram" && kind !== "storage") return
        window.moreOpen = true
        window.componentBackTarget = "summary"
        window.selectedPage = kind
    }
    function toggleMaximize() {
        window.visibility = window.visibility === Window.Maximized ? Window.Windowed : Window.Maximized
    }

    // Una sola zona de arrastre reutilizable: cabecera y marca lateral.
    // Windows se encarga del movimiento nativo; se conserva fallback manual
    // para entornos en los que startSystemMove() devuelva false.
    component WindowDragArea: MouseArea {
        acceptedButtons:Qt.LeftButton
        cursorShape:Qt.OpenHandCursor
        property bool manualMove:false
        property point startPointer:Qt.point(0,0)
        property point startWindow:Qt.point(0,0)
        onPressed:function(mouse) {
            manualMove=false
            if(window.visibility===Window.FullScreen) return
            if(window.startSystemMove()) return
            if(window.visibility===Window.Maximized) window.showNormal()
            startPointer=mapToGlobal(mouse.x,mouse.y)
            startWindow=Qt.point(window.x,window.y)
            manualMove=true
        }
        onPositionChanged:function(mouse) {
            if(!manualMove) return
            const pointer=mapToGlobal(mouse.x,mouse.y)
            window.x=startWindow.x + pointer.x - startPointer.x
            window.y=startWindow.y + pointer.y - startPointer.y
        }
        onReleased:manualMove=false
        onCanceled:manualMove=false
        onDoubleClicked:window.toggleMaximize()
    }
    Shortcut {
        sequence:"F11"
        onActivated:window.visibility=window.visibility===Window.FullScreen ? Window.Windowed:Window.FullScreen
    }
    Shortcut {
        sequence:"Escape"
        onActivated:if (window.visibility===Window.FullScreen)window.visibility=Window.Windowed
    }

    Rectangle {
        id: background
        anchors.fill:parent
        radius:window.visibility===Window.Windowed ? 16 : 0
        border.width:1
        border.color:window.activeTheme.panelBorder
        gradient:Gradient {
            GradientStop { position:0; color:window.activeTheme.bgStart }
            GradientStop { position:0.76; color:window.activeTheme.bgMid }
            GradientStop { position:1; color:window.activeTheme.bgEnd }
        }
        clip:true

        Rectangle {
            id: sidebar
            width:window.sidebarCollapsed ? 74 : 270
            height:parent.height
            color:window.activeTheme.sidebar
            Behavior on width { NumberAnimation { duration:160; easing.type:Easing.OutCubic } }
            Rectangle{anchors.right:parent.right;width:1;height:parent.height;color:window.activeTheme.sidebarBorder}

            // Barra lateral sin bloque de marca: la navegación comienza más arriba.
            // La franja libre de la izquierda sigue permitiendo mover la ventana.
            Item {
                id: sideTop
                width:parent.width
                height:52
                WindowDragArea {
                    anchors.left:parent.left
                    anchors.right:sidebarToggle.left
                    anchors.top:parent.top
                    anchors.bottom:parent.bottom
                }
                Rectangle {
                    id: sidebarToggle
                    x:window.sidebarCollapsed ? (parent.width-width)/2 : parent.width-width-13
                    y:12
                    width:27;height:27;radius:8
                    color:toggleArea.containsMouse?"#363B51":"#242A3A"
                    Glyph{anchors.centerIn:parent;width:18;height:18;kind:"menu";ink:"#CFD7E7"}
                    MouseArea {
                        id:toggleArea;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                        onClicked:window.sidebarCollapsed=!window.sidebarCollapsed
                    }
                }
            }
            Flickable {
                id:navScroll
                anchors.top:sideTop.bottom;anchors.bottom:parent.bottom
                anchors.left:parent.left;anchors.right:parent.right
                anchors.bottomMargin:14
                contentWidth:width
                contentHeight:navColumn.implicitHeight+12
                flickableDirection:Flickable.VerticalFlick
                boundsBehavior:Flickable.StopAtBounds
                clip:true

                Column {
                    id:navColumn
                    width:navScroll.width
                    spacing:4
                    Repeater {
                        model: window.primaryGroups
                        delegate:Column {
                            id:groupColumn
                            required property var modelData
                            width:navColumn.width
                            spacing:1
                            Item {
                                width:parent.width;height:window.sidebarCollapsed?9:26
                                Text {
                                    visible:!window.sidebarCollapsed
                                    x:23;anchors.verticalCenter:parent.verticalCenter
                                    text:groupColumn.modelData.title
                                    color:"#8292AB";font.pixelSize:10;font.bold:true
                                }
                            }
                            Repeater {
                                model:groupColumn.modelData.items
                                delegate:Rectangle {
                                    id: entry
                                    required property var modelData
                                    readonly property bool active:modelData.id==="health" ? (["health","battery","windows_health","repair","restore","change_history","audio"].indexOf(window.selectedPage) >= 0) : window.selectedPage===modelData.id
                                    width:groupColumn.width-16;height:41;x:8;radius:11
                                    color:active?window.activeTheme.sidebarActive:entryMouse.containsMouse?"#20232F":"transparent"
                                    Rectangle {
                                        visible:entry.active
                                        anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter
                                        width:3;height:parent.height-11;radius:2;color:window.cyan
                                    }
                                    Rectangle {
                                        x:window.sidebarCollapsed?(parent.width-width)/2:12
                                        anchors.verticalCenter:parent.verticalCenter
                                        width:26;height:26;radius:9
                                        color:entry.active?window.activeTheme.sidebarActiveIcon:entryMouse.containsMouse?"#171C27":"transparent"
                                        border.width:entry.active?1:0
                                        border.color:entry.active?window.activeTheme.sidebarActiveBorder:"transparent"
                                        Glyph {
                                            anchors.centerIn:parent
                                            width:22;height:22;kind:entry.modelData.icon
                                            ink:entry.active?window.cyan:(entryMouse.containsMouse?"#C5D0E0":"#AEB8CB")
                                        }
                                    }
                                    Text {
                                        visible:!window.sidebarCollapsed
                                        x:49;anchors.verticalCenter:parent.verticalCenter
                                        width:parent.width-56;text:entry.modelData.label
                                        font.pixelSize:12;font.bold:entry.active
                                        color:entry.active?window.ink:"#C2CAD9"
                                        elide:Text.ElideRight
                                    }
                                    MouseArea {
                                        id:entryMouse;anchors.fill:parent;hoverEnabled:true
                                        cursorShape:Qt.PointingHandCursor
                                        onClicked:window.selectedPage=entry.modelData.id
                                    }
                                }
                            }
                        }
                    }
                    Rectangle {
                        width:parent.width-16;x:8;height:39;radius:10
                        color:moreMouse.containsMouse?"#222531":"transparent"
                        Rectangle {
                            x:window.sidebarCollapsed?(parent.width-width)/2:12
                            anchors.verticalCenter:parent.verticalCenter
                            width:26;height:26;radius:9
                            color:moreMouse.containsMouse?"#171C27":"transparent"
                            Glyph {
                                anchors.centerIn:parent
                                width:19;height:19;kind:"menu";ink:window.cyan
                            }
                        }
                        Text {
                            visible:!window.sidebarCollapsed
                            x:49;anchors.verticalCenter:parent.verticalCenter
                            text:window.moreOpen?"Menos módulos":"Más módulos"
                            color:window.ink;font.bold:true;font.pixelSize:12
                        }
                        Text {
                            visible:!window.sidebarCollapsed
                            anchors.right:parent.right;anchors.rightMargin:14
                            anchors.verticalCenter:parent.verticalCenter
                            text:window.moreOpen?"⌃":"⌄";color:window.cyan;font.pixelSize:16
                        }
                        MouseArea {
                            id:moreMouse;anchors.fill:parent;hoverEnabled:true
                            cursorShape:Qt.PointingHandCursor
                            onClicked:window.moreOpen=!window.moreOpen
                        }
                    }
                    Repeater {
                        model:window.moreOpen?window.additionalModules.filter(function(item) { return item.id !== "battery" || (batteryHealth && batteryHealth.data && batteryHealth.data.hasBattery) }):[]
                        delegate:Rectangle {
                            id:extraEntry
                            required property var modelData
                            readonly property bool active:window.selectedPage===modelData.id
                            width:navColumn.width-16;x:8;height:39;radius:10
                            color:active?window.activeTheme.sidebarActive:extraMouse.containsMouse?"#222531":"transparent"
                            Rectangle {
                                x:window.sidebarCollapsed?(parent.width-width)/2:12
                                anchors.verticalCenter:parent.verticalCenter
                                width:26;height:26;radius:9
                                color:extraEntry.active?window.activeTheme.sidebarActiveIcon:extraMouse.containsMouse?"#171C27":"transparent"
                                border.width:extraEntry.active?1:0
                                border.color:extraEntry.active?window.activeTheme.sidebarActiveBorder:"transparent"
                                Glyph {
                                    anchors.centerIn:parent
                                    width:22;height:22;kind:extraEntry.modelData.icon
                                    ink:extraEntry.active?window.cyan:(extraMouse.containsMouse?"#C5D0E0":"#AEB8CB")
                                }
                            }
                            Text{
                                visible:!window.sidebarCollapsed
                                x:49;anchors.verticalCenter:parent.verticalCenter
                                text:extraEntry.modelData.label
                                font.pixelSize:12;color:extraEntry.active?window.ink:"#C2CAD9"
                            }
                            MouseArea {
                                id:extraMouse;anchors.fill:parent;hoverEnabled:true
                                cursorShape:Qt.PointingHandCursor
                                onClicked:window.selectedPage=extraEntry.modelData.id
                            }
                        }
                    }
                }
            }
        }

        Item {
            id:workspace
            anchors.left:sidebar.right;anchors.right:parent.right
            anchors.top:parent.top;anchors.bottom:parent.bottom

            Item {
                id:toolbar
                anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
                height:106
                // Se puede arrastrar desde toda la cabecera, no solo 16 px.
                // Queda por debajo de los controles de ventana.
                WindowDragArea {
                    anchors.left:parent.left
                    anchors.right:windowActions.left
                    anchors.top:parent.top
                    anchors.bottom:parent.bottom
                }
                RowLayout {
                    anchors.left:parent.left;anchors.leftMargin:34
                    anchors.top:parent.top;anchors.topMargin:29
                    width:Math.max(0,parent.width-320)
                    spacing:18
                    Text {text:"Core";font.bold:true;font.pixelSize:26;color:window.ink}
                    Text {text:"Pulse";font.bold:true;font.pixelSize:26;color:"#238FEB";Layout.leftMargin:-18}
                    Rectangle {Layout.preferredWidth:1;Layout.preferredHeight:38;color:"#333644"}
                    Glyph {kind:"laptop";ink:"#259BEF";Layout.preferredWidth:33;Layout.preferredHeight:33}
                    ColumnLayout {
                        Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                        Text {
                            text:telemetry && telemetry.metrics ? telemetry.metrics.computer : "N/A"
                            color:window.ink;font.bold:true;font.pixelSize:16
                            elide:Text.ElideRight;Layout.fillWidth:true
                        }
                        Text {
                            text:"Monitoreo real del equipo · Rebuild 053"
                            color:window.muted;font.pixelSize:11
                        }
                    }
                }
                Row {
                    id:windowActions
                    anchors.top:parent.top;anchors.topMargin:23
                    anchors.right:parent.right;anchors.rightMargin:19
                    height:44;spacing:7
                    Rectangle {
                        width:43;height:43;radius:22;color:"#1E405C"
                        Text {anchors.centerIn:parent;text:"U";color:"#F5F8FD";font.bold:true;font.pixelSize:15}
                    }
                    Item {width:62;height:43
                        Text {anchors.centerIn:parent;text:"Usuario";color:"#EDF0F8";font.pixelSize:12}
                    }
                    Repeater {
                        model:[{symbol:"−",action:"min"},{symbol:"□",action:"max"},{symbol:"×",action:"close"}]
                        delegate:Rectangle {
                            required property var modelData
                            width:35;height:43;radius:9;color:controlMouse.containsMouse?"#252C38":"transparent"
                            Text {anchors.centerIn:parent;text:modelData.symbol;color:"#B2C0D2";font.pixelSize:20}
                            MouseArea {
                                id:controlMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                                onClicked:{
                                    if(modelData.action==="min")window.showMinimized()
                                    else if(modelData.action==="max")window.toggleMaximize()
                                    else window.close()
                                }
                            }
                        }
                    }
                }
            }

            Loader {
                id:pageLoader
                anchors.left:parent.left;anchors.leftMargin:34
                anchors.right:parent.right;anchors.rightMargin:28
                anchors.top:toolbar.bottom
                anchors.bottom:parent.bottom;anchors.bottomMargin:29
                sourceComponent:window.selectedPage==="summary"?overviewComponent:
                                window.selectedPage==="readings"?readingsComponent:
                                window.selectedPage==="themes"?themesComponent:
                                window.selectedPage==="tweaks"?tweaksComponent:
                                window.selectedPage==="cleanup"?cleanupComponent:
                                (window.selectedPage==="health" || window.selectedPage==="battery" || window.selectedPage==="windows_health" || window.selectedPage==="repair" || window.selectedPage==="storage" || window.selectedPage==="restore" || window.selectedPage==="change_history" || window.selectedPage==="audio" || window.selectedPage==="health_performance")?healthComponent:
                                (window.selectedPage==="cpu" || window.selectedPage==="gpu" || window.selectedPage==="ram")
                                    ?componentDetail:placeholderComponent
            }
            Component {id:overviewComponent; Overview {
                onOpenReadings: window.selectedPage="readings"
                onOpenComponent: function(componentKind) { window.openComponent(componentKind) }
                onRestartRequested: {
                    if (systemActions.pending) window.restartResultOpen = true
                    else window.restartConfirmOpen = true
                }
            }}
            Component {
                id:componentDetail
                ComponentDetail {
                    componentKind:window.selectedPage
                    onGoBack:window.selectedPage=window.componentBackTarget
                }
            }
            Component {
                id:cleanupComponent
                CleanupPage { onGoBack:window.selectedPage="summary" }
            }
            Component {
                id:healthComponent
                HealthPage {
                    requestedModule: window.selectedPage === "storage" ? "storage" :
                        window.selectedPage === "windows_health" ? "windows" :
                        window.selectedPage === "repair" ? "repair" :
                        window.selectedPage === "restore" ? "recovery" :
                        window.selectedPage === "change_history" ? "history" :
                        window.selectedPage === "audio" ? "audio" :
                        window.selectedPage === "health_performance" ? "performance" :
                        window.selectedPage === "battery" ? "battery" : "auto"
                    onGoBack: window.selectedPage="summary"
                    onNavigateTo: function(target) { if (["cpu","gpu","ram"].indexOf(target) >= 0) window.componentBackTarget = "health"; window.selectedPage = target }
                }
            }
            Component {
                id:themesComponent
                ThemesPage {
                    themeCatalog: window.themeCatalog
                    selectedThemeId: window.selectedThemeId
                    currentAccent: window.activeTheme.accent
                    onApplyTheme: function(themeId) { window.selectedThemeId = themeId }
                    onGoBack: window.selectedPage = "summary"
                }
            }
            Component {
                id:tweaksComponent
                TweaksPage {
                    onGoBack:window.selectedPage="summary"
                }
            }
            Component {
                id:readingsComponent
                Rectangle {
                    id: readingsPage
                    radius:22;color:"#1A1C26";border.width:1;border.color:"#2B3040"
                    readonly property var readingRows:telemetry && telemetry.metrics ? (telemetry.metrics.readings || []) : []
                    readonly property string count:telemetry && telemetry.metrics ? (telemetry.metrics.coverage || "N/A") : "N/A"
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:Math.min(22,Math.max(12,parent.width*0.025))
                        spacing:14
                        RowLayout {
                            Layout.fillWidth:true;spacing:12
                            Rectangle {
                                Layout.preferredWidth:43;Layout.preferredHeight:43;radius:13
                                color:"#30223F"
                                Glyph { anchors.centerIn:parent;width:24;height:24;kind:"trace";ink:window.purple }
                            }
                            ColumnLayout {
                                Layout.fillWidth:true;Layout.minimumWidth:0;spacing:3
                                Text {text:"Lecturas disponibles";color:window.ink;font.pixelSize:18;font.bold:true}
                                Text {text:"Verificación de las siete métricas del equipo";color:window.muted;font.pixelSize:11}
                            }
                            Rectangle {
                                Layout.preferredWidth:62;Layout.preferredHeight:34
                                radius:10;color:"#30223F"
                                Text {anchors.centerIn:parent;text:readingsPage.count;color:window.purple;font.bold:true;font.pixelSize:17}
                            }
                            Rectangle {
                                Layout.preferredWidth:75;Layout.preferredHeight:34
                                radius:10;color:backMouse.containsMouse?"#324055":"#22293A"
                                Text {anchors.centerIn:parent;text:"Volver";color:window.ink;font.pixelSize:11;font.bold:true}
                                MouseArea {
                                    id:backMouse;anchors.fill:parent;hoverEnabled:true
                                    cursorShape:Qt.PointingHandCursor
                                    onClicked:window.selectedPage="summary"
                                }
                            }
                        }
                        Text {
                            Layout.fillWidth:true
                            text:"Las lecturas sin sensor confirmado se muestran como N/A. Las estimaciones se identifican expresamente."
                            wrapMode:Text.WordWrap;color:window.muted;font.pixelSize:11
                        }
                        // Mantener la barra fuera del contentItem: un Flickable reubica a sus hijos visuales.
                        Item {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            Flickable {
                                id:readingsScroll
                                anchors.fill: parent
                                contentWidth:width
                                contentHeight:readingsList.implicitHeight
                                clip:true;boundsBehavior:Flickable.StopAtBounds
                                // Dejar un canal de 16 px evita que la barra tape los valores.
                                Column {
                                    id:readingsList
                                    width:Math.max(0,readingsScroll.width-16)
                                    spacing:8
                                    Repeater {
                                        model:readingsPage.readingRows
                                        delegate:Rectangle {
                                            id:readingEntry
                                            required property var modelData
                                            width:readingsList.width
                                            height:Math.max(73,infoColumn.implicitHeight+19)
                                            radius:13;color:"#202430";border.width:1;border.color:"#313646"
                                            readonly property color stateTone:modelData.status==="Disponible"?"#43D6B3":
                                                                                 modelData.status==="Evaluando"?"#E8B75A":"#929DAF"
                                            RowLayout {
                                                anchors.fill:parent;anchors.margins:13;spacing:11
                                                Rectangle {
                                                    Layout.preferredWidth:8;Layout.preferredHeight:8;radius:4
                                                    color:readingEntry.stateTone
                                                }
                                                ColumnLayout {
                                                    id:infoColumn
                                                    Layout.fillWidth:true;Layout.minimumWidth:0;spacing:3
                                                    Text {
                                                        Layout.fillWidth:true;text:readingEntry.modelData.name
                                                        color:window.ink;font.pixelSize:13;font.bold:true;elide:Text.ElideRight
                                                    }
                                                    Text {
                                                        Layout.fillWidth:true
                                                        text:"Fuente: "+readingEntry.modelData.source
                                                        color:window.muted;font.pixelSize:10;elide:Text.ElideRight
                                                        ToolTip.visible:sourceHover.containsMouse && truncated
                                                        ToolTip.text:"Fuente: "+readingEntry.modelData.source
                                                        MouseArea {
                                                            id:sourceHover;anchors.fill:parent
                                                            hoverEnabled:true;acceptedButtons:Qt.NoButton
                                                        }
                                                    }
                                                }
                                                ColumnLayout {
                                                    Layout.alignment:Qt.AlignVCenter|Qt.AlignRight
                                                    Layout.preferredWidth:Math.min(164,readingsList.width*0.32)
                                                    spacing:4
                                                    Text {
                                                        Layout.fillWidth:true
                                                        text:readingEntry.modelData.value
                                                        horizontalAlignment:Text.AlignRight
                                                        color:window.ink;font.bold:true;font.pixelSize:13
                                                        elide:Text.ElideRight
                                                    }
                                                    Text {
                                                        Layout.fillWidth:true;text:readingEntry.modelData.status
                                                        horizontalAlignment:Text.AlignRight
                                                        color:readingEntry.stateTone;font.pixelSize:10
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            ThinScroll {
                                target: readingsScroll
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                anchors.right: parent.right
                                anchors.rightMargin: 2
                            }
                        }
                    }
                }
            }
            Component {
                id:placeholderComponent
                Rectangle {
                    radius:22;color:"#1A1C26";border.width:1;border.color:"#2B3040"
                    Column {
                        anchors.centerIn:parent;spacing:17;width:Math.min(parent.width-40,510)
                        Glyph {anchors.horizontalCenter:parent.horizontalCenter;width:45;height:45;kind:"tools";ink:window.cyan}
                        Text {
                            anchors.horizontalCenter:parent.horizontalCenter
                            text:window.pageTitle(window.selectedPage)
                            font.pixelSize:22;font.bold:true;color:window.ink
                        }
                        Text {
                            width:parent.width
                            text:"Módulo pendiente de reconstrucción. Esta versión es una base nueva y no incluye todavía las funciones del proyecto anterior."
                            wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter
                            font.pixelSize:14;lineHeight:1.3;color:window.muted
                        }
                        Rectangle {
                            anchors.horizontalCenter:parent.horizontalCenter
                            width:190;height:43;radius:12;color:"#1B425E"
                            Text {anchors.centerIn:parent;text:"Volver al Resumen";font.bold:true;color:"#EFF6FF";font.pixelSize:13}
                            MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:window.selectedPage="summary"}
                        }
                    }
                }
            }
        }
        MouseArea {
            anchors.left:parent.left;anchors.top:parent.top;anchors.bottom:parent.bottom
            anchors.topMargin:8;anchors.bottomMargin:8
            width:6;cursorShape:Qt.SizeHorCursor
            onPressed:if(window.visibility===Window.Windowed)window.startSystemResize(Qt.LeftEdge)
        }
        MouseArea {
            anchors.top:parent.top;anchors.left:parent.left;anchors.right:parent.right
            anchors.leftMargin:8;anchors.rightMargin:8
            height:6;cursorShape:Qt.SizeVerCursor
            onPressed:if(window.visibility===Window.Windowed)window.startSystemResize(Qt.TopEdge)
        }
        MouseArea {
            anchors.right:parent.right;anchors.top:parent.top;anchors.bottom:parent.bottom
            width:6;cursorShape:Qt.SizeHorCursor
            onPressed:if(window.visibility===Window.Windowed)window.startSystemResize(Qt.RightEdge)
        }
        MouseArea {
            anchors.bottom:parent.bottom;anchors.left:parent.left;anchors.right:parent.right
            height:6;cursorShape:Qt.SizeVerCursor
            onPressed:if(window.visibility===Window.Windowed)window.startSystemResize(Qt.BottomEdge)
        }

        // Confirmación explícita: la alerta de 10 h nunca reinicia el equipo automáticamente.
        Rectangle {
            id: restartOverlay
            anchors.fill:parent
            z:999
            visible: window.restartConfirmOpen || window.restartResultOpen
            color:"#B9000000"
            MouseArea { anchors.fill:parent; acceptedButtons:Qt.AllButtons }
            Rectangle {
                anchors.centerIn:parent
                width:Math.min(420, parent.width-30)
                height: restartColumn.implicitHeight+38
                radius:17;color:"#1A1C26";border.width:1;border.color:"#303647"
                ColumnLayout {
                    id:restartColumn
                    anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top
                    anchors.margins:19;spacing:13
                    Text {
                        text:window.restartConfirmOpen ? "Confirmar reinicio" : "Estado del reinicio"
                        color:window.ink;font.pixelSize:18;font.bold:true
                    }
                    Text {
                        Layout.fillWidth:true;wrapMode:Text.WordWrap;font.pixelSize:12;color:window.muted
                        text:window.restartConfirmOpen
                            ? "CorePulse detectó más de 10 horas de actividad del sistema. Guarda tu trabajo: Windows cerrará las aplicaciones y reiniciará el PC 60 segundos después de confirmar."
                            : systemActions.status
                    }
                    RowLayout {
                        Layout.fillWidth:true;spacing:10
                        Item { Layout.fillWidth:true }
                        Rectangle {
                            Layout.preferredWidth:95;Layout.preferredHeight:36;radius:10
                            color:cancelRestartMouse.containsMouse ? "#323441" : "#242633"
                            border.width:1;border.color:"#303647"
                            Text { anchors.centerIn:parent;text:window.restartConfirmOpen ? "Cancelar" : "Cerrar";color:window.ink;font.pixelSize:12 }
                            MouseArea {
                                id:cancelRestartMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                                onClicked:{window.restartConfirmOpen=false;window.restartResultOpen=false}
                            }
                        }
                        Rectangle {
                            Layout.preferredWidth:window.restartConfirmOpen ? 140 : 155
                            Layout.preferredHeight:36;radius:10
                            visible:window.restartConfirmOpen || systemActions.pending
                            color:confirmRestartMouse.containsMouse ? "#642F39" : "#432730"
                            border.width:1;border.color:"#F36B75"
                            Text {
                                anchors.centerIn:parent
                                text:window.restartConfirmOpen ? "Reiniciar en 60 s" : "Cancelar reinicio"
                                color:"#FFB3B8";font.bold:true;font.pixelSize:12
                            }
                            MouseArea {
                                id:confirmRestartMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                                onClicked:{
                                    if(window.restartConfirmOpen) {
                                        window.restartConfirmOpen=false
                                        systemActions.scheduleRestart()
                                        window.restartResultOpen=true
                                    } else {
                                        systemActions.cancelRestart()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
