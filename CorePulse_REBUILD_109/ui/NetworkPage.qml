import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    signal goBack()
    readonly property var d: networkHealth.data || ({})
    readonly property color panel: themeManager.palette.panel
    readonly property color raised: themeManager.palette.panelRaised
    readonly property color edge: themeManager.palette.panelBorder
    readonly property color ink: themeManager.palette.ink
    readonly property color muted: themeManager.palette.muted
    readonly property color accent: themeManager.palette.accent
    readonly property color cyan: themeManager.palette.cyan
    readonly property var speedInfo: networkSpeedTest && networkSpeedTest.data ? networkSpeedTest.data : ({busy:false,percent:0,status:"N/A",message:"N/A",result:{},ooklaAvailable:false,ooklaDownloading:false})
    property string speedProvider: "cloudflare"
    property string pendingSpeedProvider: ""
    property bool confirmSpeedTest: false
    property bool ooklaTermsAccepted: false

    Component.onCompleted: networkHealth.startWatch()
    Component.onDestruction: networkHealth.stopWatch()

    component MiniButton: Rectangle {
        id: button
        property string label: ""
        property bool enabledAction: true
        property bool actionStyle: false   // ejecuta algo: texto en color de acción (REBUILD 082)
        property bool solidStyle: false    // Aplicar/Actualizar: botón entero de color
        signal activated()
        implicitWidth: Math.max(108, content.implicitWidth + 28)
        implicitHeight: 35
        radius: 10
        color: solidStyle ? (!enabledAction ? themeManager.palette.actionMuted : pointer.containsMouse ? Qt.lighter(themeManager.palette.action, 1.16) : themeManager.palette.action)
                      : pointer.containsMouse && enabledAction ? themeManager.palette.panelRaised : themeManager.palette.panel
        opacity: enabledAction || solidStyle ? 1 : 0.5
        border.width: 1; border.color: (solidStyle || (actionStyle && pointer.containsMouse)) && enabledAction ? themeManager.palette.action : themeManager.palette.panelBorder
        Text { id: content; anchors.centerIn: parent; text: button.label; font.pixelSize: 11; font.bold: true
               color: button.solidStyle ? (button.enabledAction ? themeManager.palette.actionText : themeManager.palette.actionMutedText)
                    : button.actionStyle ? themeManager.palette.action : themeManager.palette.ink }
        MouseArea { id: pointer; anchors.fill: parent; enabled: button.enabledAction; hoverEnabled: true
            cursorShape: Qt.PointingHandCursor; onClicked: button.activated() }
    }

    component DataTile: Rectangle {
        id: tile
        property string title: ""
        property string value: "N/A"
        property string detail: ""
        property string privacyKey: ""   // campo sensible: muestra el ojo
        Layout.fillWidth: true
        Layout.preferredHeight: 122
        radius: 15
        color: themeManager.palette.panel
        border.width: 1; border.color: themeManager.palette.panelBorder
        ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 6
            RowLayout { Layout.fillWidth: true; spacing: 6
                Text { text: tile.title; color: themeManager.palette.muted; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
                PrivacyEye { visible: tile.privacyKey !== "" && !!(page.d.hasSensitive || {})[tile.privacyKey]
                    revealed: !!(page.d.revealed || {})[tile.privacyKey]; hint: tile.title
                    onToggled: networkHealth.toggleReveal(tile.privacyKey) }
            }
            Text { Layout.fillWidth: true; text: tile.value; color: themeManager.palette.accent; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight }
            Text { Layout.fillWidth: true; text: tile.detail; color: themeManager.palette.muted; font.pixelSize: 10; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
        }
    }

    FastFlickable {
        id: scroller
        anchors.fill: parent
        anchors.margins: 0
        contentWidth: width
        contentHeight: content.implicitHeight + 22
        clip: true; boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: content
            width: scroller.width - 12
            spacing: 15
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Rectangle { Layout.preferredWidth: 45; Layout.preferredHeight: 45; radius: 13; color: page.raised
                    Glyph { anchors.centerIn: parent; width: 25; height: 25; kind: "network"; ink: page.cyan }
                }
                ColumnLayout { Layout.fillWidth: true; spacing: 3
                    Text { text: "Red avanzada"; color: page.ink; font.pixelSize: 21; font.bold: true }
                    Text { Layout.fillWidth: true; text: "Inventario y conectividad reales, recuperados desde CorePulse V485."; color: page.muted; font.pixelSize: 11; elide: Text.ElideRight }
                }
                MiniButton { actionStyle: true; solidStyle: true; label: d.busy ? "Consultando…" : "Actualizar"; enabledAction: !d.busy; onActivated: networkHealth.refresh() }
                MiniButton { label: "Volver"; onActivated: page.goBack() }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 72; radius: 15; color: page.panel; border.width: 1; border.color: page.edge
                ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 6
                    RowLayout { Layout.fillWidth: true
                        Text { text: "CONEXIÓN PRINCIPAL"; color: page.muted; font.pixelSize: 10; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: "Actualizado: " + (d.lastUpdate || "N/A"); color: page.muted; font.pixelSize: 10 }
                    }
                    Text { text: (d.primary || "N/A") + " · " + (d.total === undefined ? "N/A" : d.total) + " adaptadores"; color: page.accent; font.pixelSize: 17; font.bold: true }
                    Text { visible: !!d.busy; text: d.phase || "Consultando…"; color: page.muted; font.pixelSize: 10 }
                }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: content.width < 800 ? 2 : 4
                columnSpacing: 12; rowSpacing: 12
                DataTile { title: "IPV4"; value: d.ipv4 || "N/A"; detail: "Dirección publicada por Windows"; privacyKey: "ipv4" }
                DataTile { title: "VELOCIDAD DE ENLACE"; value: d.linkSpeed || "N/A"; detail: "Enlace local, no velocidad de Internet" }
                DataTile { title: "DESCARGA ACTUAL"; value: d.download || "N/A"; detail: "Cambio real de bytes por segundo" }
                DataTile { title: "SUBIDA ACTUAL"; value: d.upload || "N/A"; detail: "Cambio real de bytes por segundo" }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: connections.implicitHeight + 28; radius: 16; color: page.panel; border.width: 1; border.color: page.edge
                ColumnLayout { id: connections; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14; spacing: 9
                    Text { text: "Configuración de la conexión"; color: page.ink; font.pixelSize: 15; font.bold: true }
                    Repeater { model: [{t:"Gateway",v:d.gateway || "N/A",k:"gateway"}, {t:"DNS",v:d.dns || "N/A",k:"dns"}, {t:"IPv6",v:d.ipv6 || "N/A",k:"ipv6"}, {t:"Wi-Fi / SSID",v:d.ssid || "N/A",k:"ssid"}, {t:"Señal Wi-Fi",v:d.signal || "N/A",k:""}]
                        delegate: RowLayout { required property var modelData; Layout.fillWidth: true; spacing: 10
                            Text { text: modelData.t; color: page.muted; font.pixelSize: 11; Layout.preferredWidth: 118 }
                            Text { text: modelData.v; color: page.ink; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                            PrivacyEye { visible: modelData.k !== "" && !!(d.hasSensitive || {})[modelData.k]
                                revealed: !!(d.revealed || {})[modelData.k]; hint: modelData.t
                                onToggled: networkHealth.toggleReveal(modelData.k) }
                        }
                    }
                    Text { Layout.fillWidth: true; text: "Los datos que identifican tu red se muestran ocultos. Tocá el ojo para verlos; se vuelven a ocultar solos a los 30 s o al salir de esta pantalla."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
                }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: speedContents.implicitHeight + 28; radius: 16; color: page.panel; border.width: 1; border.color: page.edge
                ColumnLayout { id:speedContents; anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top; anchors.margins:14; spacing:9
                    RowLayout { Layout.fillWidth:true
                        Text { text:"Prueba de velocidad de Internet"; color:page.ink; font.pixelSize:15; font.bold:true; Layout.fillWidth:true }
                        MiniButton { actionStyle: true; label:speedInfo.busy?"Midiendo…":"Iniciar prueba"; enabledAction:!speedInfo.busy; onActivated:{ page.pendingSpeedProvider=page.speedProvider; page.ooklaTermsAccepted=false; page.confirmSpeedTest=true } }
                    }
                    Text { Layout.fillWidth:true; text:"Medición bajo demanda. Con Ookla oficial, el resultado se abre automáticamente en Speedtest.net cuando termina. Cloudflare solo muestra sus mediciones locales y puede transferir hasta 315 MB."; color:page.muted; font.pixelSize:10; wrapMode:Text.WordWrap }
                    RowLayout { Layout.fillWidth:true; spacing:8
                        MiniButton { label:page.speedProvider==="cloudflare"?"✓ Cloudflare":"Cloudflare"; enabledAction:!speedInfo.busy; onActivated:page.speedProvider="cloudflare" }
                        MiniButton { label:page.speedProvider==="ookla"?"✓ Ookla oficial":"Ookla oficial"; enabledAction:!speedInfo.busy && speedInfo.ooklaAvailable; onActivated:page.speedProvider="ookla" }
                        MiniButton { visible:!speedInfo.ooklaAvailable; actionStyle: true; label:speedInfo.ooklaDownloading?"Descargando Ookla…":"Reintentar instalación"; enabledAction:!speedInfo.busy && !speedInfo.ooklaDownloading; onActivated:networkSpeedTest.checkOokla() }
                        Text { Layout.fillWidth:true; text:speedInfo.ooklaAvailable?"CLI Ookla · "+(speedInfo.ooklaVersion||"disponible"):speedInfo.ooklaDownloading?"Descarga oficial verificada en curso":"Ookla aún no disponible"; color:page.muted; font.pixelSize:9; elide:Text.ElideRight }
                    }
                    Rectangle { visible:speedInfo.busy; Layout.fillWidth:true; Layout.preferredHeight:6; radius:3; color:page.panel; border.width:1; border.color:page.edge
                        Rectangle { width:parent.width*Math.max(0,Math.min(1,(speedInfo.percent||0)/100)); height:parent.height; radius:3; color:page.accent }
                    }
                    Text { Layout.fillWidth:true; text:(speedInfo.status||"Sin prueba")+" · "+(speedInfo.message||""); color:page.muted; font.pixelSize:10; wrapMode:Text.WordWrap }
                    GridLayout { Layout.fillWidth:true; columns:content.width<760?2:4; columnSpacing:9; rowSpacing:8
                        Repeater { model:[
                            {title:"DESCARGA",value:typeof speedInfo.result.download_mbps==="number"?speedInfo.result.download_mbps.toFixed(2)+" Mb/s":"N/A"},
                            {title:"SUBIDA",value:typeof speedInfo.result.upload_mbps==="number"?speedInfo.result.upload_mbps.toFixed(2)+" Mb/s":"N/A"},
                            {title:"LATENCIA",value:typeof speedInfo.result.latency_ms==="number"?speedInfo.result.latency_ms.toFixed(1)+" ms":"N/A"},
                            {title:"JITTER",value:typeof speedInfo.result.jitter_ms==="number"?speedInfo.result.jitter_ms.toFixed(1)+" ms":"N/A"}
                        ]; delegate:Rectangle{required property var modelData;Layout.fillWidth:true;Layout.preferredHeight:61;radius:11;color:page.panel;border.width:1;border.color:page.edge
                            ColumnLayout{anchors.fill:parent;anchors.margins:10;spacing:4
                                Text{text:modelData.title;color:page.muted;font.pixelSize:8;font.bold:true}
                                Text{text:modelData.value;color:page.accent;font.pixelSize:15;font.bold:true}
                            }
                        }}
                    }
                    Text { visible:!!speedInfo.result.provider; Layout.fillWidth:true; text:(speedInfo.result.provider||"")+(speedInfo.result.speedtest_net_comparable?" · Metodología oficial Ookla":" · Motor alternativo; no comparable 1:1 con Speedtest.net")+" · Datos transferidos: "+(speedInfo.result.data_mb!==undefined?speedInfo.result.data_mb+" MB":"N/A"); color:page.muted; font.pixelSize:9; wrapMode:Text.WordWrap }
                }
            }
            Text { text: "Adaptadores detectados"; color: page.ink; font.pixelSize: 15; font.bold: true }
            Repeater { model: d.adapters || []
                delegate: Rectangle { required property var modelData; required property int index
                    Layout.fillWidth: true; Layout.preferredHeight: 94; radius: 15; color: page.panel; border.width: 1; border.color: page.edge
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 6
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { text: modelData.name; color: page.ink; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                            Text { text: modelData.status; color: modelData.isUp ? "#36D6A0" : page.muted; font.pixelSize: 11 }
                            PrivacyEye { visible: !!modelData.hasSensitive; revealed: !!modelData.revealed; hint: "direcciones de " + modelData.name
                                onToggled: networkHealth.toggleReveal("adapter:" + index) }
                        }
                        Text { Layout.fillWidth: true; text: "IPv4: " + modelData.ipv4 + " · Gateway: " + modelData.gateway; color: page.muted; font.pixelSize: 10; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: "DNS: " + modelData.dns + " · Enlace: " + modelData.linkSpeed; color: page.muted; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
            }
            Text { Layout.fillWidth: true; text: "Fuentes: psutil / Get-NetAdapter / Get-NetIPConfiguration / netsh wlan. Esta pantalla no cambia DNS, rutas, IP ni adaptadores."; color: page.muted; font.pixelSize: 10; wrapMode: Text.WordWrap }
            Item { Layout.preferredHeight: 12 }
        }
    }
    Rectangle { visible:page.confirmSpeedTest; anchors.fill:parent; z:40; color:"#B5000000"
        Rectangle { width:Math.min(parent.width-24,460);height:speedConfirmContents.implicitHeight+34;anchors.centerIn:parent;radius:16;color:page.panel;border.width:1;border.color:page.edge
            ColumnLayout { id:speedConfirmContents;anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top;anchors.margins:17;spacing:12
                Text { text:"Iniciar prueba activa de red";color:page.ink;font.pixelSize:17;font.bold:true }
                Text { text:page.pendingSpeedProvider==="ookla"?"La CLI oficial de Ookla medirá descarga, subida y latencia. Al terminar correctamente, CorePulse abrirá el enlace del resultado oficial en tu navegador, si Ookla lo entrega.":"Cloudflare probará descarga, subida y latencia en speed.cloudflare.com. El motor puede transferir hasta 315 MB y no genera un resultado web compartible.";color:page.muted;font.pixelSize:11;Layout.fillWidth:true;wrapMode:Text.WordWrap }
                Rectangle { visible:page.pendingSpeedProvider==="ookla";Layout.fillWidth:true;Layout.preferredHeight:50;radius:10;color:page.raised;border.width:1;border.color:page.edge
                    RowLayout { anchors.fill:parent; anchors.margins:10; spacing:10
                        Rectangle { Layout.preferredWidth:20;Layout.preferredHeight:20;radius:5;color:page.ooklaTermsAccepted?page.cyan:page.panel;border.width:1;border.color:page.ooklaTermsAccepted?page.cyan:page.edge
                            Text { anchors.centerIn:parent;text:page.ooklaTermsAccepted?"✓":"";color:"#07121C";font.bold:true;font.pixelSize:14 }
                        }
                        Text { Layout.fillWidth:true;text:"Leí y acepto las condiciones y el aviso de privacidad de Ookla para esta prueba.";color:page.ink;font.pixelSize:10;wrapMode:Text.WordWrap }
                    }
                    MouseArea { anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:page.ooklaTermsAccepted=!page.ooklaTermsAccepted }
                }
                Text { visible:page.pendingSpeedProvider==="ookla";Layout.fillWidth:true;textFormat:Text.RichText;text:"<a href=\"https://www.speedtest.net/about/terms\">Condiciones de uso</a> · <a href=\"https://www.speedtest.net/about/privacy\">Aviso de privacidad</a>";color:page.cyan;font.pixelSize:10;onLinkActivated:function(link){Qt.openUrlExternally(link)} }
                RowLayout { Layout.fillWidth:true;Item{Layout.fillWidth:true}
                    MiniButton { label:"Cancelar";onActivated:{page.confirmSpeedTest=false;page.ooklaTermsAccepted=false} }
                    MiniButton { actionStyle: true; label:"Iniciar prueba";enabledAction:page.pendingSpeedProvider!=="ookla" || page.ooklaTermsAccepted;onActivated:{const provider=page.pendingSpeedProvider;const accepted=page.ooklaTermsAccepted;page.confirmSpeedTest=false;networkSpeedTest.startWithConsent(provider,accepted)} }
                }
            }
        }
    }
}
