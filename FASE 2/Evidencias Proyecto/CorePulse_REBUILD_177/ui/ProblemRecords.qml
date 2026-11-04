import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts

ColumnLayout {
    id: page
    property var state: problemCapture.data || ({})
    readonly property var detail: state.selected || ({})
    readonly property var palette: themeManager.palette
    property real cursorTime: 0
    readonly property var reading: {
        const samples=detail.samples || []
        if(!samples.length)return ({})
        return samples.reduce((best,row)=>Math.abs(row.time-cursorTime)<Math.abs(best.time-cursorTime)?row:best,samples[0])
    }
    spacing:12
    component ActionButton: Basic.Button {
        id: button
        implicitHeight:36
        implicitWidth:Math.max(90,label.implicitWidth+26)
        contentItem:Text { id:label;text:button.text;color:button.enabled?page.palette.ink:page.palette.muted;font.pixelSize:12;font.weight:Font.DemiBold;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter }
        background:Rectangle {radius:10;color:button.hovered?Qt.alpha(page.palette.cyan,.18):page.palette.panelRaised;border.width:1;border.color:button.hovered?page.palette.cyan:page.palette.panelBorder;opacity:button.enabled?1:.5}
    }
    component Choice: Basic.ComboBox {
        implicitHeight:36
        palette.button:page.palette.panelRaised
        palette.buttonText:page.palette.ink
        palette.text:page.palette.ink
        palette.window:page.palette.panelRaised
        palette.windowText:page.palette.ink
        palette.base:page.palette.panelRaised
        palette.highlight:page.palette.cyan
        palette.highlightedText:"#071018"
    }
    function number(value,suffix){return typeof value==="number" && isFinite(value)?Number(value).toFixed(1)+(suffix || ""):"N/A"}
    RowLayout {
        Layout.fillWidth:true
        Text { text:"Registros de problemas";color:page.palette.ink;font.pixelSize:20;font.bold:true;Layout.fillWidth:true }
        ActionButton { text:page.state.recording?"Registrando · "+page.state.remaining+" s":"Registrar ahora";enabled:!page.state.recording;onClicked:problemCapture.record() }
        ActionButton { text:"Carpeta";onClicked:problemCapture.openFolder() }
    }
    Text { Layout.fillWidth:true;text:"Durante el juego pulsa "+overlayController.data.problemShortcut+". Guarda hasta 30 s anteriores y 15 s posteriores, sin abrir CorePulse ni salir de la partida.";color:page.palette.muted;font.pixelSize:12;wrapMode:Text.WordWrap }
    Text { Layout.fillWidth:true;visible:!!page.state.message;text:page.state.message || "";color:page.palette.cyan;font.pixelSize:12;wrapMode:Text.WordWrap }
    Text { visible:!(page.state.captures || []).length;text:"Todavía no hay registros. La captura previa se prepara mientras juegas con el overlay activo.";color:page.palette.muted;font.pixelSize:12;Layout.fillWidth:true;wrapMode:Text.WordWrap }
    Choice { Layout.fillWidth:true;visible:(page.state.captures || []).length>0;model:page.state.captures || [];textRole:"label";currentIndex:(page.state.captures || []).findIndex(row=>row.id===page.detail.id);onActivated:problemCapture.select(model[currentIndex].id) }
    GlassPanel {
        Layout.fillWidth:true;implicitHeight:recordBody.implicitHeight+32;visible:!!page.detail.id
        ColumnLayout {
            id:recordBody;anchors.fill:parent;anchors.margins:16;spacing:12
            RowLayout {
                Layout.fillWidth:true
                ColumnLayout {
                    Layout.fillWidth:true
                    Text { text:page.detail.name || "";color:page.palette.ink;font.pixelSize:18;font.bold:true }
                    Text { text:(page.detail.preSeconds || 0)+" s antes · "+(page.detail.postSeconds || 0)+" s después · "+(page.detail.partial?"Parcial":"Completo");color:page.palette.muted;font.pixelSize:11 }
                }
                ActionButton { text:"Informe PDF";onClicked:problemCapture.exportPdf() }
                ActionButton { text:"Abrir PDF";enabled:!!page.state.pdfPath;onClicked:problemCapture.openPdf() }
            }
            Text { Layout.fillWidth:true;text:"Frametime · milisegundos por fotograma";color:page.palette.ink;font.pixelSize:13;font.bold:true }
            Text { Layout.fillWidth:true;text:"Mediana "+page.number((page.detail.summary || {}).median," ms")+"   ·   P99 "+page.number((page.detail.summary || {}).p99," ms")+"   ·   Pico "+page.number((page.detail.summary || {}).maximum," ms")+"   ·   "+((page.detail.summary || {}).count || 0)+" fotogramas";color:page.palette.cyan;font.pixelSize:12;wrapMode:Text.WordWrap }
            FrametimeChart {
                id:timeline;Layout.fillWidth:true;Layout.preferredHeight:160
                samples:page.detail.frames || [];timed:true;showMarker:true;accent:page.palette.cyan;muted:page.palette.muted;grid:page.palette.panelBorder
                MouseArea {
                    anchors.fill:parent;hoverEnabled:true
                    onPositionChanged:function(mouse){
                        const rows=page.detail.frames || []
                        if(rows.length>1)page.cursorTime=rows[0].time+Math.max(0,Math.min(1,mouse.x/Math.max(1,width-42)))*(rows[rows.length-1].time-rows[0].time)
                    }
                    onExited:page.cursorTime=0
                }
            }
            Text { text:"Lecturas a "+page.number(page.reading.time," s")+" del atajo · pasa el mouse por la línea";color:page.palette.muted;font.pixelSize:11 }
            Flow {
                Layout.fillWidth:true;spacing:16
                Repeater {
                    model:[{label:"CPU",key:"cpu",unit:" %"},{label:"GPU",key:"gpu",unit:" %"},{label:"RAM",key:"ram",unit:" %"},{label:"CPU",key:"cpuTemp",unit:" °C"},{label:"GPU",key:"gpuTemp",unit:" °C"},{label:"VRAM",key:"gpuMemoryUsed",unit:" GiB"},{label:"CPU",key:"cpuClock",unit:" GHz"}]
                    delegate:Text { required property var modelData;text:modelData.label+" "+page.number(page.reading[modelData.key],modelData.unit);color:page.palette.ink;font.pixelSize:12 }
                }
            }
            Text { Layout.fillWidth:true;visible:!!page.detail.note;text:page.detail.note || "";color:"#E9B86B";font.pixelSize:11;wrapMode:Text.WordWrap }
            Text { Layout.fillWidth:true;text:"Frecuencia CPU: "+(page.reading.cpuClockSource || "N/A");color:page.palette.muted;font.pixelSize:11;wrapMode:Text.WordWrap }
            Text { Layout.fillWidth:true;text:"La línea conserva el mayor pico por bloque al resumir registros largos. Los intervalos originales quedan en el JSON. Lecturas cercanas a un pico no demuestran su causa.";color:page.palette.muted;font.pixelSize:11;wrapMode:Text.WordWrap }
        }
    }
}
