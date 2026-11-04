import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts

ColumnLayout {
    id: editor
    spacing:12
    component ActionButton: Basic.Button {
        id: button
        implicitHeight:36
        implicitWidth:Math.max(90,label.implicitWidth+26)
        contentItem:Text { id:label;text:button.text;color:button.enabled?editor.palette.ink:editor.palette.muted;font.pixelSize:12;font.weight:Font.DemiBold;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter }
        background:Rectangle {radius:10;color:button.hovered?Qt.alpha(editor.palette.cyan,.18):editor.palette.panelRaised;border.width:1;border.color:button.hovered?editor.palette.cyan:editor.palette.panelBorder;opacity:button.enabled?1:.5}
    }
    component Choice: Basic.ComboBox {
        implicitHeight:36
        palette.button:editor.palette.panelRaised
        palette.buttonText:editor.palette.ink
        palette.text:editor.palette.ink
        palette.window:editor.palette.panelRaised
        palette.windowText:editor.palette.ink
        palette.base:editor.palette.panelRaised
        palette.highlight:editor.palette.cyan
        palette.highlightedText:"#071018"
    }
    component Toggle: Basic.CheckBox {
        id: toggle
        contentItem:Text { text:toggle.text;color:editor.palette.ink;font.pixelSize:12;leftPadding:toggle.indicator.width+8;verticalAlignment:Text.AlignVCenter }
        indicator:Rectangle {
            width:18;height:18;x:toggle.leftPadding;y:(toggle.height-height)/2;radius:5
            color:toggle.checked?editor.palette.cyan:editor.palette.panelRaised
            border.width:1;border.color:toggle.checked?editor.palette.cyan:editor.palette.panelBorder
            Canvas { anchors.centerIn:parent;width:12;height:12;visible:toggle.checked
                onPaint: { const ctx=getContext("2d");ctx.clearRect(0,0,width,height);ctx.strokeStyle="#071018";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(2,6);ctx.lineTo(5,9);ctx.lineTo(10,3);ctx.stroke() }
            }
        }
    }
    readonly property var design: overlayController.data.design || ({scale:100,opacity:94,gap:8,x:1000,y:0,metrics:["fps","cpu","gpu","ram"],frametime:true})
    readonly property var palette: themeManager.palette
    readonly property var metrics: telemetry.metrics || ({})
    property int gameIndex: 0
    readonly property var choices: [{key:"",name:"General"}].concat((gameSessions.data || {}).gameChoices || [])
    readonly property string gameKey: choices[Math.min(gameIndex,choices.length-1)].key
    function update(key,value) { const next=Object.assign({},design); next[key]=value; overlayController.setDesign(next) }
    function tint(key) {
        const name = String(key === "cpu" ? metrics.cpuName : metrics.gpuName).toLowerCase()
        if (key === "ram") return "#37CBB8"
        if (key === "disk") return "#A66BD6"
        if (key === "fps") return "#27B6F0"
        if (/nvidia|geforce/.test(name)) return "#76B900"
        if (/amd|ryzen|radeon/.test(name)) return key === "gpu" && /amd|ryzen/.test(String(metrics.cpuName).toLowerCase()) ? "#F28C28" : "#E34245"
        return "#1688F3"
    }
    function number(key) {
        if (key === "fps") return String(overlayController.data.fpsValue || "N/A").replace(" FPS","")
        const value = metrics[key === "disk" ? "diskPercent" : key+"Percent"]
        return typeof value === "number" ? Math.round(value)+"%" : "N/A"
    }
    Text { text: "Editor visual"; color: editor.palette.ink; font.pixelSize: 19; font.bold: true }
    Text { Layout.fillWidth:true; text:"Arrastra la cabecera para mover el OSD y las métricas para cambiar su orden. Los cambios se ven al instante; guarda el diseño al terminar."; wrapMode:Text.WordWrap; color:editor.palette.muted; font.pixelSize:12 }
    RowLayout {
        Layout.fillWidth:true
        Choice {
            Layout.fillWidth:true; model:editor.choices; textRole:"name"; currentIndex:editor.gameIndex
            onActivated: { editor.gameIndex=currentIndex; overlayController.previewDesignGame(editor.gameKey) }
        }
        ActionButton { text:"Guardar diseño"; onClicked: overlayController.saveDesign(editor.gameKey) }
        ActionButton { text:"Usar general";visible:!!editor.gameKey;onClicked:overlayController.inheritDesign(editor.gameKey) }
        ActionButton { text:"Restablecer"; onClicked: overlayController.resetDesign() }
    }
    Text { text:overlayController.data.designScope || "General"; color:editor.palette.muted; font.pixelSize:11 }
    Rectangle {
        id: arena
        Layout.fillWidth:true; Layout.preferredHeight:340; radius:14
        color:editor.palette.bgStart; border.width:1; border.color:editor.palette.panelBorder; clip:true
        Text { x:14; y:12; text:"PANTALLA · VISTA PREVIA"; color:editor.palette.muted; font.pixelSize:10 }
        Rectangle {
            id: osd
            property real factor: Math.min((arena.width-24)/382,(arena.height-24)/logicalHeight,Math.max(.4,Math.min(arena.width*.55/382,1.2))*editor.design.scale/100)
            property real logicalHeight: 40+(overlayController.data.compact?52:70)+12+(editor.design.frametime?76:0)
            width:382*factor; height:logicalHeight*factor
            x:12+(arena.width-width-24)*editor.design.x/1000
            y:12+(arena.height-height-24)*editor.design.y/1000
            radius:18*factor; color:editor.palette.bgMid; opacity:editor.design.opacity/100
            Item {
                id: canvas; width:382; height:osd.logicalHeight; scale:osd.factor; transformOrigin:Item.TopLeft
                Text { x:14;y:9;text:"Core";color:"#F1F8FF";font.pixelSize:17;font.bold:true }
                Text { x:53;y:9;text:"Pulse";color:"#27B6F0";font.pixelSize:17;font.bold:true }
                Text { x:132;y:13;text:overlayController.data.captureStatus || "EN JUEGO";color:"#37CBB8";font.pixelSize:10 }
                MouseArea {
                    id: mover; x:0;y:0;width:382;height:38; cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor
                    objectName:"overlayMoveHandle"
                    property point start
                    property real originalX
                    property real originalY
                    onPressed:function(mouse){start=mapToItem(arena,mouse.x,mouse.y);originalX=editor.design.x;originalY=editor.design.y}
                    onPositionChanged:function(mouse){
                        if(!pressed)return
                        const at=mapToItem(arena,mouse.x,mouse.y)
                        const next=Object.assign({},editor.design)
                        next.x=Math.max(0,Math.min(1000,originalX+(at.x-start.x)/Math.max(1,arena.width-osd.width-24)*1000))
                        next.y=Math.max(0,Math.min(1000,originalY+(at.y-start.y)/Math.max(1,arena.height-osd.height-24)*1000))
                        overlayController.setDesign(next)
                    }
                }
                Repeater {
                    model:editor.design.metrics
                    delegate:Rectangle {
                        id:tile
                        objectName:"metric_"+modelData
                        required property string modelData
                        required property int index
                        property real tileW:(354-(editor.design.metrics.length-1)*editor.design.gap)/editor.design.metrics.length
                        x:14+index*(tileW+editor.design.gap);y:40;width:tileW;height:overlayController.data.compact?52:70;radius:10
                        color:Qt.alpha(editor.tint(modelData),.14)
                        Text { x:8;y:7;text:tile.modelData === "disk"?"DISCO":tile.modelData.toUpperCase();color:editor.tint(tile.modelData);font.pixelSize:10 }
                        Text { x:8;y:22;width:parent.width-12;text:editor.number(tile.modelData);color:"#F1F8FF";font.pixelSize:tile.modelData==="fps"?22:16;font.bold:true;elide:Text.ElideRight }
                        Text { x:8;y:50;visible:!overlayController.data.compact && overlayController.data.temperatures;text:tile.modelData==="cpu"||tile.modelData==="gpu"?(typeof editor.metrics[tile.modelData+"Temp"]==="number"?Number(editor.metrics[tile.modelData+"Temp"]).toFixed(1)+" °C":"N/A"):"";color:editor.palette.muted;font.pixelSize:10 }
                        MouseArea {
                            anchors.fill:parent;cursorShape:Qt.SizeHorCursor
                            onReleased:function(mouse){
                                const point=mapToItem(canvas,mouse.x,mouse.y)
                                const target=Math.max(0,Math.min(editor.design.metrics.length-1,Math.floor((point.x-14)/(tile.tileW+editor.design.gap))))
                                const order=editor.design.metrics.slice();const item=order.splice(tile.index,1)[0];order.splice(target,0,item)
                                editor.update("metrics",order)
                            }
                        }
                    }
                }
                Text { x:14;y:40+(overlayController.data.compact?52:70)+12;visible:editor.design.frametime;text:"Frametime · ms";color:editor.palette.muted;font.pixelSize:10 }
                FrametimeChart { x:14;y:40+(overlayController.data.compact?52:70)+31;width:354;height:50;visible:editor.design.frametime;samples:overlayController.data.frameTimes || [];grid:editor.palette.panelBorder;muted:editor.palette.muted }
            }
        }
    }
    GridLayout {
        Layout.fillWidth:true;columns:3;columnSpacing:20
        Repeater {
            model:[{key:"scale",label:"Tamaño",from:60,to:160,suffix:" %"},{key:"opacity",label:"Opacidad",from:25,to:100,suffix:" %"},{key:"gap",label:"Separación",from:0,to:24,suffix:" px"}]
            delegate:ColumnLayout {
                required property var modelData
                Layout.fillWidth:true
                Text { text:modelData.label+" · "+editor.design[modelData.key]+modelData.suffix;color:editor.palette.ink;font.pixelSize:12 }
                Basic.Slider {
                    id: slider
                    objectName:"design_"+modelData.key
                    Layout.fillWidth:true;from:modelData.from;to:modelData.to;stepSize:1;value:editor.design[modelData.key];onMoved:editor.update(modelData.key,value)
                    background:Rectangle { x:slider.leftPadding;y:(slider.height-height)/2;width:slider.availableWidth;height:4;radius:2;color:editor.palette.panelBorder
                        Rectangle { width:slider.visualPosition*parent.width;height:parent.height;radius:2;color:editor.palette.cyan }
                    }
                    handle:Rectangle { x:slider.leftPadding+slider.visualPosition*(slider.availableWidth-width);y:(slider.height-height)/2;width:16;height:16;radius:8;color:editor.palette.cyan }
                }
            }
        }
    }
    Flow {
        Layout.fillWidth:true;spacing:8
        Repeater {
            model:["fps","cpu","gpu","ram","disk"]
            delegate:Toggle {
                required property string modelData
                text:modelData==="disk"?"Disco":modelData.toUpperCase();checked:editor.design.metrics.indexOf(modelData)>=0
                onToggled: { let items=editor.design.metrics.slice();if(checked)items.push(modelData);else items=items.filter(k=>k!==modelData);editor.update("metrics",items) }
            }
        }
        Toggle { text:"Línea de frametime";checked:editor.design.frametime;onToggled:editor.update("frametime",checked) }
    }
}
