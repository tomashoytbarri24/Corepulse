import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes

ApplicationWindow {
    id: window
    visible:true
    title:"CorePulse — Rebuild 109"
    width:initialWindowWidth
    height:initialWindowHeight
    minimumWidth:Math.min(820,initialWindowWidth)
    minimumHeight:Math.min(480,initialWindowHeight)
    x:initialWindowX
    y:initialWindowY
    flags:Qt.Window | Qt.FramelessWindowHint
    readonly property color shellBgStart:themeManager.palette.bgStart
    readonly property color shellBgMid:themeManager.palette.bgMid
    readonly property color shellBgEnd:themeManager.palette.bgEnd
    color:window.shellBgStart

    property bool sidebarCollapsed:false
    readonly property bool effectiveSidebarCollapsed:sidebarCollapsed || width < 1080
    property bool moreOpen:false
    property string selectedPage:"summary"
    property string componentBackTarget:"summary"
    property bool restartConfirmOpen:false
    property bool restartResultOpen:false
    // La prueba oficial terminada abre su resultado exacto aunque el usuario
    // haya navegado fuera de Red avanzada. Nunca abre una prueba fallida.
    Connections {
        target: networkSpeedTest
        function onOfficialResultReady(url) { Qt.openUrlExternally(url) }
    }
    // Cuenta: el inicio de sesión ocurre en la web y vuelve a la app (core/cuenta.py).
    readonly property string accountName: cuenta.nombre !== "" ? cuenta.nombre : cuenta.email
    readonly property var accountOptions: cuenta.conectado ? [
        {label:"Ajustes de cuenta",icon:"settings",action:"web",path:"/cuenta"},
        {label:"Ver planes",icon:"spark_ai",action:"web",path:"/precios"},
        {label:"Cerrar sesión",icon:"logout",action:"salir"}
    ] : cuenta.ocupado ? [
        {label:"Cancelar inicio de sesión",icon:"logout",action:"cancelar"}
    ] : [
        {label:"Iniciar sesión",icon:"login",action:"entrar"},
        {label:"Registrarse",icon:"user_plus",action:"web",path:"/registro"}
    ]
    function runAccountOption(option) {
        if (option.action === "entrar") cuenta.iniciarSesion()
        else if (option.action === "cancelar") cuenta.cancelar()
        else if (option.action === "salir") cuenta.cerrarSesion()
        else cuenta.abrirWeb(option.path)
        // Al iniciar sesión el menú queda abierto mostrando el estado.
        if (option.action !== "entrar") accountMenu.close()
    }
    readonly property string selectedThemeId: themeManager.themeId
    readonly property var themeCatalog: themeManager.themes
    readonly property var activeTheme: themeManager.palette
    readonly property color cyan: activeTheme.cyan
    readonly property color purple: "#BB57EF"
    readonly property color brandBlue: "#259BEF"
    readonly property color muted: activeTheme.muted
    readonly property color ink: activeTheme.ink

    onClosing: function(close) {
        if (trayController.available && !trayController.quitRequested) {
            close.accepted = false
            window.hide()
            trayController.notifyHidden()
        }
    }
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
        enabled:window.visibility===Window.FullScreen
        onActivated:if (window.visibility===Window.FullScreen)window.visibility=Window.Windowed
    }

    Rectangle {
        id: background
        anchors.fill:parent
        radius:0 // Ventana exterior rectangular en modo normal y maximizado
        border.width:1
        border.color:window.activeTheme.panelBorder
        gradient:Gradient {
            GradientStop { position:0; color:window.shellBgStart }
            GradientStop { position:0.76; color:window.shellBgMid }
            GradientStop { position:1; color:window.shellBgEnd }
        }
        clip:true

        Rectangle {
            id: sidebar
            width:window.effectiveSidebarCollapsed ? 74 : 270
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
                    x:window.effectiveSidebarCollapsed ? (parent.width-width)/2 : parent.width-width-13
                    y:12
                    width:30;height:30;radius:15
                    color:toggleArea.containsMouse?Qt.alpha(window.cyan,0.14):"transparent"
                    Glyph{anchors.centerIn:parent;width:23;height:23;kind:"menu";ink:toggleArea.containsMouse?window.cyan:"#CFD7E7"}
                    MouseArea {
                        id:toggleArea;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                        onClicked:window.sidebarCollapsed=!window.sidebarCollapsed
                    }
                }
            }
            FastFlickable {
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
                width:parent.width;height:window.effectiveSidebarCollapsed?9:26
                                Text {
                                    visible:!window.effectiveSidebarCollapsed
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
                                    color:active?window.activeTheme.sidebarActive:entryMouse.containsMouse?window.activeTheme.panelRaised:"transparent"
                                    Behavior on color { ColorAnimation { duration: 130 } }
                                    Rectangle {
                                        visible:entry.active
                                        anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter
                                        width:3;height:parent.height-11;radius:2;color:window.cyan
                                    }
                                    Rectangle {
                                        x:window.effectiveSidebarCollapsed?(parent.width-width)/2:12
                                        anchors.verticalCenter:parent.verticalCenter
                                        width:30;height:30;radius:15
                                        scale:entryMouse.containsMouse ? 1.12 : 1.0
                                        z:entryMouse.containsMouse ? 2 : 0
                                        Behavior on scale { NumberAnimation { duration:145; easing.type:Easing.OutCubic } }
                                        color:"transparent"
                                        Glyph {
                                            anchors.centerIn:parent
                                            width:25;height:25;kind:entry.modelData.icon
                                            ink:entry.active?window.cyan:(entryMouse.containsMouse?"#C5D0E0":"#AEB8CB")
                                        }
                                    }
                                    Text {
                                        visible:!window.effectiveSidebarCollapsed
                                        x:49;anchors.verticalCenter:parent.verticalCenter
                                        width:parent.width-56;text:entry.modelData.label
                                        font.pixelSize:12;font.bold:entry.active
                                        color:entry.active?window.ink:"#C2CAD9"
                                        elide:Text.ElideRight
                                    }
                                    ToolTip.visible:window.effectiveSidebarCollapsed && entryMouse.containsMouse
                                    ToolTip.delay:400
                                    ToolTip.text:entry.modelData.label
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
                        color:moreMouse.containsMouse?window.activeTheme.panelRaised:"transparent"
                        Behavior on color { ColorAnimation { duration: 130 } }
                        Rectangle {
                            x:window.effectiveSidebarCollapsed?(parent.width-width)/2:12
                            anchors.verticalCenter:parent.verticalCenter
                            width:30;height:30;radius:15
                            scale:moreMouse.containsMouse ? 1.12 : 1.0
                            Behavior on scale { NumberAnimation { duration:145; easing.type:Easing.OutCubic } }
                            color:"transparent"
                            Glyph {
                                anchors.centerIn:parent
                                width:22;height:22;kind:"menu";ink:window.cyan
                            }
                        }
                        Text {
                            visible:!window.effectiveSidebarCollapsed
                            x:49;anchors.verticalCenter:parent.verticalCenter
                            text:window.moreOpen?"Menos módulos":"Más módulos"
                            color:window.ink;font.bold:true;font.pixelSize:12
                        }
                        Text {
                            visible:!window.effectiveSidebarCollapsed
                            anchors.right:parent.right;anchors.rightMargin:14
                            anchors.verticalCenter:parent.verticalCenter
                            text:window.moreOpen?"⌃":"⌄";color:window.cyan;font.pixelSize:16
                        }
                        ToolTip.visible:window.effectiveSidebarCollapsed && moreMouse.containsMouse
                        ToolTip.delay:400
                        ToolTip.text:window.moreOpen?"Menos módulos":"Más módulos"
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
                            color:active?window.activeTheme.sidebarActive:extraMouse.containsMouse?window.activeTheme.panelRaised:"transparent"
                            Behavior on color { ColorAnimation { duration: 130 } }
                            Rectangle {
                                x:window.effectiveSidebarCollapsed?(parent.width-width)/2:12
                                anchors.verticalCenter:parent.verticalCenter
                                width:30;height:30;radius:15
                                scale:extraMouse.containsMouse ? 1.12 : 1.0
                                z:extraMouse.containsMouse ? 2 : 0
                                Behavior on scale { NumberAnimation { duration:145; easing.type:Easing.OutCubic } }
                                color:"transparent"
                                Glyph {
                                    anchors.centerIn:parent
                                    width:25;height:25;kind:extraEntry.modelData.icon
                                    ink:extraEntry.active?window.cyan:(extraMouse.containsMouse?"#C5D0E0":"#AEB8CB")
                                }
                            }
                            Text{
                                visible:!window.effectiveSidebarCollapsed
                                x:49;anchors.verticalCenter:parent.verticalCenter
                                text:extraEntry.modelData.label
                                font.pixelSize:12;color:extraEntry.active?window.ink:"#C2CAD9"
                            }
                            ToolTip.visible:window.effectiveSidebarCollapsed && extraMouse.containsMouse
                            ToolTip.delay:400
                            ToolTip.text:extraEntry.modelData.label
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
                height:Math.max(76,Math.min(96,parent.height*0.15))
                // Se puede arrastrar desde toda la cabecera, no solo 16 px.
                // Queda por debajo de los controles de ventana.
                WindowDragArea {
                    anchors.left:parent.left
                    anchors.right:windowActions.left
                    anchors.top:parent.top
                    anchors.bottom:parent.bottom
                }
                RowLayout {
                    anchors.left:parent.left;anchors.leftMargin:window.width<1080?20:34
                    anchors.top:parent.top;anchors.topMargin:Math.max(10,(parent.height-48)/2)
                    width:Math.max(0,parent.width-windowActions.width-(window.width<1080?36:64))
                    spacing:window.width<1080?10:18
                    Text {text:"Core";font.bold:true;font.pixelSize:window.width<1080?22:26;color:window.ink}
                    Text {text:"Pulse";font.bold:true;font.pixelSize:window.width<1080?22:26;color:window.brandBlue;Layout.leftMargin:-18}
                    Rectangle {visible:window.width>=1080;Layout.preferredWidth:1;Layout.preferredHeight:38;color:"#333644"}
                    Glyph {visible:window.width>=1080;kind:"laptop";ink:"#259BEF";Layout.preferredWidth:33;Layout.preferredHeight:33}
                    ColumnLayout {
                        Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                        Text {
                            text:telemetry && telemetry.metrics ? telemetry.metrics.computer : "N/A"
                            color:window.ink;font.bold:true;font.pixelSize:16
                            elide:Text.ElideRight;Layout.fillWidth:true
                        }
                        Text {
                            text:window.width<1080?"Rebuild 109":"Monitoreo real del equipo · Rebuild 109"
                            color:window.muted;font.pixelSize:11
                        }
                    }
                }
                Row {
                    id:windowActions
                    anchors.top:parent.top;anchors.topMargin:Math.max(10,(parent.height-44)/2)
                    anchors.right:parent.right;anchors.rightMargin:window.width<1080?10:19
                    height:44;spacing:7
                    // Botón de cuenta: abre la lista de opciones justo debajo.
                    Rectangle {
                        id:accountButton
                        width:accountLabel.x+accountLabel.width+34;height:43;radius:22
                        color:accountMenu.opened ? window.activeTheme.panelRaised : accountMouse.containsMouse ? window.activeTheme.panel : "transparent"
                        border.width:accountMenu.opened ? 1 : 0
                        border.color:window.activeTheme.panelBorder
                        // Sin sesión: icono de persona e invitación a entrar. Con sesión: inicial y nombre.
                        Rectangle {
                            width:43;height:43;radius:22;color:window.activeTheme.sidebarActive
                            border.width:cuenta.conectado && cuenta.plan === "pro" ? 2 : 0
                            border.color:window.cyan
                            Glyph {visible:!cuenta.conectado;anchors.centerIn:parent;width:22;height:22;kind:"user";ink:"#F5F8FD"}
                            Text {
                                visible:cuenta.conectado;anchors.centerIn:parent
                                text:window.accountName.length > 0 ? window.accountName.charAt(0).toUpperCase() : "?"
                                color:"#F5F8FD";font.bold:true;font.pixelSize:16
                            }
                        }
                        Text {
                            id:accountLabel;x:53;anchors.verticalCenter:parent.verticalCenter
                            width:Math.min(implicitWidth,150);elide:Text.ElideRight
                            text:cuenta.conectado ? window.accountName : cuenta.ocupado ? "Esperando navegador…" : "Iniciar sesión"
                            color:"#EDF0F8";font.pixelSize:12
                        }
                        Text {
                            anchors.right:parent.right;anchors.rightMargin:12
                            anchors.verticalCenter:parent.verticalCenter
                            text:accountMenu.opened ? "⌃" : "⌄";color:window.cyan;font.pixelSize:14
                        }
                        MouseArea {
                            id:accountMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                            onClicked:{
                                if (accountMenu.opened) accountMenu.close()
                                else { accountMenu.open(); cuenta.actualizar() }
                            }
                        }
                        Popup {
                            id:accountMenu
                            y:accountButton.height+8
                            x:accountButton.width-width
                            width:250
                            padding:6
                            closePolicy:Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                            background:Rectangle {
                                radius:14;color:window.activeTheme.panel
                                border.width:1;border.color:window.activeTheme.panelBorder
                            }
                            contentItem:Column {
                                spacing:2
                                // Cabecera con la cuenta conectada y su plan.
                                Item {
                                    visible:cuenta.conectado
                                    width:accountMenu.availableWidth;height:visible ? 58 : 0
                                    Column {
                                        x:10;anchors.verticalCenter:parent.verticalCenter;spacing:3
                                        width:parent.width-70
                                        Text {text:cuenta.nombre !== "" ? cuenta.nombre : "Tu cuenta";color:window.ink;font.bold:true;font.pixelSize:13;elide:Text.ElideRight;width:parent.width}
                                        Text {text:cuenta.email;color:window.muted;font.pixelSize:11;elide:Text.ElideRight;width:parent.width}
                                    }
                                    Rectangle {
                                        anchors.right:parent.right;anchors.rightMargin:10;anchors.verticalCenter:parent.verticalCenter
                                        width:planText.implicitWidth+16;height:22;radius:11
                                        color:cuenta.plan === "pro" ? window.cyan : window.activeTheme.panelRaised
                                        Text {id:planText;anchors.centerIn:parent;text:cuenta.plan === "pro" ? "PRO" : "FREE";font.bold:true;font.pixelSize:10;color:cuenta.plan === "pro" ? "#0B0E14" : window.muted}
                                    }
                                }
                                Rectangle {visible:cuenta.conectado;width:accountMenu.availableWidth-12;x:6;height:1;color:window.activeTheme.panelBorder}
                                Repeater {
                                    model:window.accountOptions
                                    delegate:Column {
                                        id:accountEntry
                                        required property var modelData
                                        required property int index
                                        width:accountMenu.availableWidth
                                        Rectangle {
                                            visible:window.accountOptions.length > 2 && accountEntry.index === window.accountOptions.length-1
                                            width:parent.width-12;x:6;height:1;color:window.activeTheme.panelBorder
                                        }
                                        Rectangle {
                                            width:parent.width;height:38;radius:9
                                            color:optionMouse.containsMouse ? window.activeTheme.panelRaised : "transparent"
                                            Glyph {
                                                x:10;anchors.verticalCenter:parent.verticalCenter
                                                width:18;height:18;kind:accountEntry.modelData.icon
                                                ink:optionMouse.containsMouse ? window.cyan : "#AEB8CB"
                                            }
                                            Text {
                                                x:38;anchors.verticalCenter:parent.verticalCenter
                                                text:accountEntry.modelData.label
                                                color:window.ink;font.pixelSize:12
                                            }
                                            MouseArea {
                                                id:optionMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor
                                                onClicked:window.runAccountOption(accountEntry.modelData)
                                            }
                                        }
                                    }
                                }
                                Text {
                                    visible:cuenta.mensaje !== ""
                                    width:accountMenu.availableWidth;leftPadding:10;rightPadding:10;topPadding:4;bottomPadding:4
                                    text:cuenta.mensaje;wrapMode:Text.WordWrap
                                    color:window.muted;font.pixelSize:11
                                }
                            }
                        }
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
                                    else window.close()  // la X minimiza a la bandeja si está disponible
                                }
                            }
                        }
                    }
                }
            }

            Loader {
                id:pageLoader
                anchors.left:parent.left;anchors.leftMargin:window.width<1080?18:34
                anchors.right:parent.right;anchors.rightMargin:window.width<1080?18:28
                anchors.top:toolbar.bottom
                anchors.bottom:parent.bottom;anchors.bottomMargin:window.height<620?16:29
                sourceComponent:window.selectedPage==="summary"?overviewComponent:
                                window.selectedPage==="benchmark"?benchmarkComponent:
                                window.selectedPage==="diagnostic"?diagnosticComponent:
                                (window.selectedPage==="alerts" || window.selectedPage==="trends" || window.selectedPage==="alert_history")?insightsComponent:
                                window.selectedPage==="reports"?reportsComponent:
                                window.selectedPage==="startup"?startupComponent:
                                window.selectedPage==="drivers"?driversComponent:
                                (window.selectedPage==="telemetry" || window.selectedPage==="evidence")?readingsComponent:
                                window.selectedPage==="readings"?readingsComponent:
                                window.selectedPage==="themes"?themesComponent:
                                window.selectedPage==="tweaks"?tweaksComponent:
                                window.selectedPage==="ai"?aiComponent:
                                window.selectedPage==="cleanup"?cleanupComponent:
                                window.selectedPage==="overlay"?overlayComponent:
                                (window.selectedPage==="advanced_network" || window.selectedPage==="network")?networkComponent:
                                (window.selectedPage==="health" || window.selectedPage==="battery" || window.selectedPage==="windows_health" || window.selectedPage==="services" || window.selectedPage==="gaming" || window.selectedPage==="repair" || window.selectedPage==="storage" || window.selectedPage==="restore" || window.selectedPage==="change_history" || window.selectedPage==="audio" || window.selectedPage==="health_performance")?healthComponent:
                                (window.selectedPage==="cpu" || window.selectedPage==="gpu" || window.selectedPage==="ram")
                                    ?componentDetail:placeholderComponent
            }
            Component {
                id:benchmarkComponent
                BenchmarkPage { onGoBack: window.selectedPage = "summary" }
            }
            Component {
                id:aiComponent
                AIPage { onGoBack:window.selectedPage="summary" }
            }
            Component {
                id:insightsComponent
                InsightsPage { section: window.selectedPage; onGoBack:window.selectedPage="summary" }
            }
            Component {
                id:reportsComponent
                ReportsPage { onGoBack:window.selectedPage="summary" }
            }
            Component {
                id:startupComponent
                StartupPage { onGoBack:window.selectedPage="summary" }
            }
            Component {
                id:driversComponent
                DriversPage { onGoBack:window.selectedPage="summary" }
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
                id:diagnosticComponent
                Item {
                    id: diagnosticPage
                    readonly property var summary: systemHealth && systemHealth.data ? systemHealth.data : ({headline:"Información insuficiente",state:"partial",coverage:"0/0",verified:0,total:0,critical:0,attention:0,unknown:0,checks:[],note:"Sin lecturas confirmadas."})
                    readonly property var diagnostic: systemHealth && systemHealth.diagnostic ? systemHealth.diagnostic : ({status:"idle",progress:0,stage:"Aún no se ha ejecutado.",summary:{},runId:0})
                    readonly property var result: diagnostic.summary || ({})
                    readonly property var aiDiagnostic: corepulseAI && corepulseAI.state ? (corepulseAI.state.diagnostic || ({})) : ({})
                    readonly property bool aiMatches: Number(aiDiagnostic.runId || 0) === Number(diagnostic.runId || 0)
                    readonly property color resultTone: result.state === "critical" ? "#F36B75" : result.state === "attention" ? "#E9B86B" : result.state === "ok" ? "#36D6A0" : window.activeTheme.cyan
                    readonly property color tone: diagnostic.status === "running" ? window.activeTheme.cyan : resultTone
                    function componentName(check) {
                        if (check.key === "cpu") return telemetry.metrics.cpuName || "CPU"
                        if (check.key === "gpu") return telemetry.metrics.gpuName || "GPU"
                        if (check.key === "disks") {
                            const detail = String(check.detail || "")
                            if (detail.indexOf("Windows informa incidencia en: ") === 0)
                                return detail.substring("Windows informa incidencia en: ".length).split(",")[0].replace(/\.$/, "")
                            return (storageHealth.data.selectedPhysical || {}).name || telemetry.metrics.diskName || "Disco físico"
                        }
                        if (check.key === "space") {
                            const match = String(check.value || check.detail || "").match(/[A-Z]:\\/i)
                            return match ? match[0] : ((storageHealth.data.selectedVolume || {}).mount || telemetry.metrics.diskLabel || "Unidad local")
                        }
                        return check.key === "ram" ? "Memoria RAM" : check.title || "Equipo"
                    }
                    function tutorialUrl(check) {
                        const model = componentName(check)
                        const query = model + " " + (check.title || "") + " " + (check.value || "") + " " + (check.detail || "") + " " + stateLabel(check.state) + " solución"
                        return "https://www.youtube.com/results?search_query=" + encodeURIComponent(query)
                    }
                    function stateLabel(state) {
                        return state === "critical" ? "PRIORIDAD" : state === "attention" ? "REVISAR" : state === "ok" ? "CORRECTO" : "SIN CONFIRMAR"
                    }
                    Connections {
                        target: systemHealth
                        function onDiagnosticChanged() {
                            const current = diagnosticPage.diagnostic
                            if ((current.status === "complete" || current.status === "partial") &&
                                Number(current.runId || 0) > 0)
                                corepulseAI.diagnose()
                        }
                    }
                    Connections {
                        target: corepulseAI
                        function onChanged() {
                            const aiState = corepulseAI.state
                            if ((diagnosticPage.diagnostic.status === "complete" || diagnosticPage.diagnostic.status === "partial") &&
                                diagnosticPage.aiMatches && diagnosticPage.aiDiagnostic.status === "unavailable" &&
                                aiState.enabled && aiState.consent && aiState.hardware && aiState.ready && !aiState.busy)
                                corepulseAI.diagnose()
                        }
                    }
                    FastFlickable {
                        id: diagnosticScroller
                        anchors.fill: parent
                        contentWidth: width
                        contentHeight: Math.max(diagnosticContent.implicitHeight, diagnosticContent.height) + 16
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        ColumnLayout {
                            id: diagnosticContent
                            width: Math.max(0, diagnosticScroller.width - 14)
                            // El contenido ocupa toda el área visible cuando aún no hay resultados.
                            // Si aparecen resultados, crece y conserva el desplazamiento vertical.
                            height: Math.max(implicitHeight, diagnosticScroller.height - 16)
                            x: 0
                            y: 0
                            spacing: 15
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Glyph { Layout.preferredWidth: 34; Layout.preferredHeight: 34; kind: "scan"; ink: diagnosticPage.tone }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: "Iniciar diagnóstico"; color: window.ink; font.pixelSize: 21; font.bold: true }
                                    Text { text: "Revisión local de los componentes y Windows"; color: window.muted; font.pixelSize: 11 }
                                }
                                Rectangle {
                                    visible: diagnostic.status === "complete" || diagnostic.status === "partial"
                                    Layout.preferredWidth: 112
                                    Layout.preferredHeight: 36
                                    radius: 11
                                    color: pdfMouse.containsMouse?Qt.lighter(themeManager.palette.panelRaised,1.22):themeManager.palette.panelRaised
                                    border.width: 1
                                    border.color: pdfMouse.containsMouse?themeManager.palette.action:themeManager.palette.panelBorder
                                    Text { anchors.centerIn: parent; text: reportExporter.data.busy ? "Creando PDF…" : "Crear PDF"; color: (reportExporter.data.busy)?"#8993A5":themeManager.palette.action; font.pixelSize: 11; font.bold: true }
                                    MouseArea {
                                        id: pdfMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: !reportExporter.data.busy
                                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: reportExporter.generate()
                                    }
                                }
                            }
                            Item {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 430
                                // La zona del círculo llena el espacio libre solo antes de mostrar resultados.
                                Layout.fillHeight: diagnostic.status !== "complete" && diagnostic.status !== "partial"
                                Item {
                                    id: diagnosticCircle
                                    width: 320
                                    height: 320
                                    anchors.centerIn: parent
                                    scale: circleMouse.containsMouse && diagnostic.status !== "running" ? 1.035 : 1
                                    Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                    // REBUILD 083 «Latido»: el anillo late (más rápido mientras
                                    // analiza) y queda quieto al terminar.
                                    readonly property bool idle: diagnostic.status !== "running" && diagnostic.status !== "complete" && diagnostic.status !== "partial"
                                    readonly property bool running: diagnostic.status === "running"
                                    readonly property int beatPeriod: running ? 900 : 1600
                                    Item {
                                        id: beatLayer
                                        anchors.fill: parent
                                        transformOrigin: Item.Center
                                        SequentialAnimation on scale {
                                            running: diagnosticCircle.idle || diagnosticCircle.running
                                            loops: Animation.Infinite
                                            alwaysRunToEnd: true
                                            NumberAnimation { to: 1.06; duration: diagnosticCircle.beatPeriod * 0.12; easing.type: Easing.OutQuad }
                                            NumberAnimation { to: 0.99; duration: diagnosticCircle.beatPeriod * 0.12; easing.type: Easing.InOutQuad }
                                            NumberAnimation { to: 1.03; duration: diagnosticCircle.beatPeriod * 0.12; easing.type: Easing.OutQuad }
                                            NumberAnimation { to: 1.0; duration: diagnosticCircle.beatPeriod * 0.20; easing.type: Easing.InOutQuad }
                                            PauseAnimation { duration: diagnosticCircle.beatPeriod * 0.44 }
                                        }
                                    // REBUILD 083: sin disco de fondo, borde ni pista gris; sólo la
                                    // barra de carga queda «en el aire».
                                    Canvas {
                                        id: diagnosticRing
                                        anchors.fill: parent
                                        antialiasing: true
                                        // En reposo es un botón circular completo; al iniciarlo
                                        // vuelve de inmediato a 0 y usa únicamente el avance real.
                                        property real drawnProgress: {
                                            const state = diagnosticPage.diagnostic.status
                                            if (state === "idle" || state === "complete") return 1
                                            const value = Number(diagnosticPage.diagnostic.progress)
                                            return isFinite(value) ? Math.max(0, Math.min(1, value / 100)) : 0
                                        }
                                        Behavior on drawnProgress {
                                            // La animación suaviza solo aumentos; nunca anima el reinicio 100 -> 0.
                                            enabled: diagnosticPage.diagnostic.status === "running" &&
                                                     Number(diagnosticPage.diagnostic.progress) > 0
                                            NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
                                        }
                                        onDrawnProgressChanged: requestPaint()
                                        onPaint: {
                                            const ctx = getContext("2d")
                                            ctx.reset()
                                            ctx.clearRect(0, 0, width, height)
                                            if (drawnProgress <= 0) return
                                            const center = width / 2
                                            const radius = center - 11
                                            ctx.beginPath()
                                            ctx.strokeStyle = diagnosticPage.tone
                                            ctx.lineWidth = 9
                                            ctx.lineCap = "round"
                                            ctx.arc(center, center, radius, -Math.PI / 2,
                                                    -Math.PI / 2 + Math.PI * 2 * drawnProgress, false)
                                            ctx.stroke()
                                        }
                                        Connections {
                                            target: diagnosticPage
                                            function onToneChanged() { diagnosticRing.requestPaint() }
                                        }
                                    }
                                    }
                                    ColumnLayout {
                                        anchors.centerIn: parent
                                        width: 250
                                        spacing: 11
                                        Item {
                                            Layout.alignment: Qt.AlignHCenter
                                            Layout.preferredWidth: 92
                                            Layout.preferredHeight: 92
                                            Glyph {
                                                anchors.fill: parent
                                                visible: !diagnosticCircle.idle && !diagnosticCircle.running
                                                kind: diagnostic.status === "complete" && result.state === "ok" ? "health_shield" : "scan"
                                                ink: diagnosticPage.tone
                                            }
                                            // Línea de pulso (ECG): traza tenue fija y un tramo brillante que la recorre.
                                            Shape {
                                                anchors.fill: parent
                                                visible: diagnosticCircle.idle || diagnosticCircle.running
                                                preferredRendererType: typeof Shape.CurveRenderer === "number" ? Shape.CurveRenderer : Shape.GeometryRenderer
                                                ShapePath {
                                                    strokeColor: Qt.alpha(diagnosticPage.tone, 0.22)
                                                    strokeWidth: 3.4
                                                    fillColor: "transparent"
                                                    capStyle: ShapePath.RoundCap
                                                    joinStyle: ShapePath.RoundJoin
                                                    PathSvg { path: "M 2 40 H 22 L 30 22 L 40 58 L 50 30 L 56 40 H 72" }
                                                }
                                                ShapePath {
                                                    strokeColor: diagnosticPage.tone
                                                    strokeWidth: 3.4
                                                    fillColor: "transparent"
                                                    capStyle: ShapePath.RoundCap
                                                    joinStyle: ShapePath.RoundJoin
                                                    strokeStyle: ShapePath.DashLine
                                                    // Largo del trazo de unos 134 px = 39,6 anchos de línea.
                                                    dashPattern: [39.6, 39.6]
                                                    PathSvg { path: "M 2 40 H 22 L 30 22 L 40 58 L 50 30 L 56 40 H 72" }
                                                    NumberAnimation on dashOffset {
                                                        from: 39.6; to: -39.6
                                                        duration: diagnosticCircle.beatPeriod
                                                        loops: Animation.Infinite
                                                        running: diagnosticCircle.idle || diagnosticCircle.running
                                                    }
                                                }
                                            }
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: diagnostic.status === "running" ? "Analizando" : diagnostic.status === "complete" || diagnostic.status === "partial" ? "Diagnóstico listo" : "Iniciar diagnóstico"
                                            color: window.ink
                                            font.pixelSize: 21
                                            font.bold: true
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: diagnostic.status === "running" ? diagnostic.stage : diagnostic.status === "complete" || diagnostic.status === "partial" ? (result.coverage || "N/A") + " lecturas verificadas" : "Pulsa el círculo para revisar tu equipo"
                                            color: window.muted
                                            font.pixelSize: 12
                                            horizontalAlignment: Text.AlignHCenter
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                    MouseArea {
                                        id: circleMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: diagnostic.status !== "running"
                                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: systemHealth.runDiagnostic()
                                    }
                                    Connections {
                                        target: systemHealth
                                        function onDiagnosticChanged() { diagnosticRing.requestPaint() }
                                    }
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.top: diagnosticCircle.bottom
                                    anchors.topMargin: 20
                                    width: Math.min(parent.width, 620)
                                    horizontalAlignment: Text.AlignHCenter
                                    // REBUILD 083: sin texto en reposo; sólo progreso y etapa cuando corresponde.
                                    visible: text !== ""
                                    text: diagnostic.status === "running" ? diagnostic.progress + "% · " + diagnostic.stage :
                                          diagnostic.status === "complete" || diagnostic.status === "partial" ? diagnostic.stage : ""
                                    color: window.muted
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }
                            Rectangle {
                                visible: diagnostic.status === "complete" || diagnostic.status === "partial"
                                Layout.fillWidth: true
                                implicitHeight: resultColumn.implicitHeight + 28
                                radius: 17
                                color: window.activeTheme.panel
                                border.width: 1
                                border.color: diagnosticPage.tone
                                ColumnLayout {
                                    id: resultColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 14
                                    spacing: 8
                                    Text {
                                        Layout.fillWidth: true
                                        text: result.state === "ok" ? "Todo está en orden" : result.headline || "Diagnóstico parcial"
                                        color: diagnosticPage.tone
                                        font.pixelSize: 20
                                        font.bold: true
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: (result.verified || 0) + " de " + (result.total || 0) + " indicadores confirmados · " + (result.critical || 0) + " prioritarios · " + (result.attention || 0) + " por revisar · " + (result.unknown || 0) + " sin confirmar."
                                        color: window.muted
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: result.note || "Los límites son preventivos y no confirman una avería."
                                        color: window.muted
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                    }
                                    Repeater {
                                        model: result.checks || []
                                        delegate: Rectangle {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            implicitHeight: findingColumn.implicitHeight + 20
                                            radius: 12
                                            color: window.activeTheme.panel
                                            border.width: 1
                                            border.color: modelData.state === "critical" ? "#A85864" : modelData.state === "attention" ? "#9B7845" : window.activeTheme.panelBorder
                                            ColumnLayout {
                                                id: findingColumn
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.top: parent.top
                                                anchors.margins: 10
                                                spacing: 4
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Text { Layout.fillWidth: true; text: modelData.title || "Indicador"; color: window.ink; font.pixelSize: 11; font.bold: true }
                                                    Text { text: diagnosticPage.stateLabel(modelData.state); color: modelData.state === "critical" ? "#F36B75" : modelData.state === "attention" ? "#E9B86B" : modelData.state === "ok" ? "#36D6A0" : window.muted; font.pixelSize: 9; font.bold: true }
                                                }
                                                Text { Layout.fillWidth: true; text: (modelData.value || "N/A") + " · " + (modelData.detail || "Sin detalle."); color: window.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                                                Text {
                                                    visible: modelData.state === "critical" || modelData.state === "attention"
                                                    Layout.fillWidth: true
                                                    text: '<a href="' + diagnosticPage.tutorialUrl(modelData) + '">Buscar tutorial específico en YouTube</a>'
                                                    textFormat: Text.RichText
                                                    color: window.activeTheme.cyan
                                                    font.pixelSize: 10
                                                    onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                visible: diagnostic.status === "complete" || diagnostic.status === "partial"
                                Layout.fillWidth: true
                                implicitHeight: aiColumn.implicitHeight + 26
                                radius: 16
                                color: window.activeTheme.panel
                                border.width: 1
                                border.color: window.activeTheme.panelBorder
                                ColumnLayout {
                                    id: aiColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 13
                                    spacing: 7
                                    Text { text: "Análisis consolidado con CorePulse AI"; color: window.ink; font.pixelSize: 14; font.bold: true }
                                    Text {
                                        Layout.fillWidth: true
                                        text: aiMatches ? (aiDiagnostic.statusText || "Análisis de IA pendiente.") :
                                              "El análisis anterior corresponde a otra ejecución. Cuando termine, vuelve a ejecutar el diagnóstico."
                                        color: window.muted
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        visible: aiMatches && String(aiDiagnostic.text || "").length > 0
                                        Layout.fillWidth: true
                                        text: aiDiagnostic.text || ""
                                        color: window.ink
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                    }
                                    Rectangle {
                                        visible: !aiMatches || aiDiagnostic.status === "unavailable" || aiDiagnostic.status === "error"
                                        Layout.preferredWidth: 150
                                        Layout.preferredHeight: 34
                                        radius: 10
                                        color: aiConnectMouse.containsMouse ? window.activeTheme.panel : Qt.alpha(window.activeTheme.accent, 0.18)
                                        border.width: 1
                                        border.color: window.activeTheme.accent
                                        Text { anchors.centerIn: parent; text: aiMatches && aiDiagnostic.status === "unavailable" ? "Configurar CorePulse AI" : "Analizar este resultado con IA"; color: themeManager.palette.action; font.pixelSize: 10; font.bold: true }
                                        MouseArea { id: aiConnectMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { if (aiMatches && aiDiagnostic.status === "unavailable") window.selectedPage = "ai"; else corepulseAI.diagnose() } }
                                    }
                                }
                            }
                            RowLayout {
                                visible: diagnostic.status === "complete" || diagnostic.status === "partial"
                                Layout.fillWidth: true
                                spacing: 10
                                Rectangle {
                                    visible: String(reportExporter.data.path || "").length > 0
                                    Layout.preferredWidth: 96
                                    Layout.preferredHeight: 36
                                    radius: 10
                                    color: openPdfMouse.containsMouse ? window.activeTheme.panel : window.activeTheme.panelRaised
                                    border.width: 1
                                    border.color: window.activeTheme.panelBorder
                                    Text { anchors.centerIn: parent; text: "Abrir PDF"; color: window.ink; font.pixelSize: 10; font.bold: true }
                                    MouseArea { id: openPdfMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: reportExporter.openLast() }
                                }
                                Rectangle {
                                    Layout.preferredWidth: 160
                                    Layout.preferredHeight: 36
                                    radius: 10
                                    color: reportExporter.data.busy ? window.activeTheme.panel : repeatMouse.containsMouse ? window.activeTheme.panel : window.activeTheme.panelRaised
                                    border.width: 1
                                    border.color: window.activeTheme.panelBorder
                                    Text { anchors.centerIn: parent; text: "Repetir diagnóstico"; color: window.ink; font.pixelSize: 10; font.bold: true }
                                    MouseArea { id: repeatMouse; anchors.fill: parent; hoverEnabled: true; enabled: diagnostic.status !== "running"; cursorShape: Qt.PointingHandCursor; onClicked: systemHealth.runDiagnostic() }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: reportExporter.data.status || ""
                                    color: window.muted
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }
            Component {
                id:componentDetail
                ComponentDetail {
                    componentKind:window.selectedPage
                    onGoBack:window.selectedPage=window.componentBackTarget
                }
            }
            Component {
                id:networkComponent
                NetworkPage { onGoBack: window.selectedPage = "summary" }
            }
            Component {
                id:overlayComponent
                OverlayPage { onGoBack: window.selectedPage = "summary" }
            }
            Component {
                id:cleanupComponent
                CleanupPage { onGoBack:window.selectedPage="summary" }
            }
            Component {
                id:healthComponent
                HealthPage {
                    requestedModule: window.selectedPage === "storage" ? "storage" :
                        window.selectedPage === "gaming" ? "performance" :
                        window.selectedPage === "windows_health" ? "windows" :
                        window.selectedPage === "drivers" || window.selectedPage === "services" || window.selectedPage === "startup" ? "windows" :
                        window.selectedPage === "repair" ? "repair" :
                        window.selectedPage === "restore" ? "recovery" :
                        window.selectedPage === "change_history" ? "history" :
                        window.selectedPage === "audio" ? "audio" :
                        window.selectedPage === "health_performance" ? "performance" :
                        window.selectedPage === "battery" ? "battery" : "auto"
                    requestedWindowsSection: window.selectedPage === "services" ? "services" : ""
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
                    onApplyTheme: function(themeId) { themeManager.applyTheme(themeId) }
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
                Item {
                    id: readingsPage
                    readonly property var readingRows:telemetry && telemetry.metrics ? (telemetry.metrics.readings || []) : []
                    readonly property string count:telemetry && telemetry.metrics ? (telemetry.metrics.coverage || "N/A") : "N/A"
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:0
                        spacing:14
                        RowLayout {
                            Layout.fillWidth:true;spacing:12
                            Rectangle {
                                Layout.preferredWidth:43;Layout.preferredHeight:43;radius:13
                                color:window.activeTheme.panelRaised
                                Glyph { anchors.centerIn:parent;width:24;height:24;kind:"trace";ink:window.purple }
                            }
                            ColumnLayout {
                                Layout.fillWidth:true;Layout.minimumWidth:0;spacing:3
                                Text {text:"Lecturas disponibles";color:window.ink;font.pixelSize:18;font.bold:true}
                                Text {text:"Verificación de las siete métricas del equipo";color:window.muted;font.pixelSize:11}
                            }
                            Rectangle {
                                Layout.preferredWidth:62;Layout.preferredHeight:34
                                radius:10;color:window.activeTheme.panelRaised
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
                            FastFlickable {
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
                                            radius:13;color:window.activeTheme.panel;border.width:1;border.color:window.activeTheme.panelBorder
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
                    radius:22;color:window.activeTheme.panel;border.width:1;border.color:window.activeTheme.panelBorder
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
                radius:17;color:window.activeTheme.panel;border.width:1;border.color:window.activeTheme.panelBorder
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
                            border.width:1;border.color:window.activeTheme.panelBorder
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
