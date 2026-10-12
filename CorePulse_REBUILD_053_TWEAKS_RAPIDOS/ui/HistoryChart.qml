import QtQuick

Item {
    id: history
    property var cpuValues: []
    property var gpuValues: []
    property color cpuColor: "#1AB9F7"
    property color gpuColor: "#BB57EF"
    onCpuValuesChanged: chart.requestPaint()
    onGpuValuesChanged: chart.requestPaint()

    Canvas {
        id: chart
        anchors.fill: parent
        antialiasing: true
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const c = getContext("2d")
            c.reset()
            const left = 44, right = 10, top = 12, bottom = 34
            const w = Math.max(2, width-left-right), h = Math.max(2, height-top-bottom)
            c.lineWidth = 1
            c.font = '11px "Segoe UI"'
            for (let i=0; i<=4; ++i) {
                const y = top + h * i / 4
                c.strokeStyle = "#272b38"
                c.beginPath(); c.moveTo(left,y); c.lineTo(left+w,y); c.stroke()
                c.fillStyle = "#9BA4B6"; c.textAlign = "right"
                c.fillText((100 - i*25)+"%", left-10, y+4)
            }
            for (let i=0; i<=4; ++i) {
                const x = left+w*i/4
                c.strokeStyle = "#222632"
                c.beginPath(); c.moveTo(x,top); c.lineTo(x,top+h); c.stroke()
            }
            c.fillStyle = "#9BA4B6"; c.textAlign = "left"
            c.fillText("Inicio", left, height - 8)
            c.textAlign = "right"
            c.fillText("Ahora", left + w, height - 8)
            function plot(values, ink) {
                if (!values || values.length < 2) return
                const count = values.length
                let open = false, visible = 0
                c.beginPath()
                for(let i=0; i<count; ++i) {
                    const v=values[i]
                    if (v === null || v === undefined || typeof v !== "number" || !isFinite(v) || v < 0 || v > 100) {
                        open = false
                        continue
                    }
                    let x = left + w*(i/59)
                    let y = top + h*(1-v/100)
                    if(!open) c.moveTo(x,y)
                    else c.lineTo(x,y)
                    open=true
                    visible++
                }
                if (visible < 2) return
                c.strokeStyle = ink.toString()
                c.lineWidth=2.5
                c.lineCap="round"
                c.lineJoin="round"
                c.stroke()
                // No rellenamos tramos con N/A para no inventar continuidad.
            }
            plot(history.cpuValues, history.cpuColor)
            plot(history.gpuValues, history.gpuColor)
            if ((!history.cpuValues || history.cpuValues.length<2) &&
                (!history.gpuValues || history.gpuValues.length<2)) {
                c.textAlign="center"; c.fillStyle="#8592A6"
                c.fillText("Esperando lecturas reales…",left+w/2,top+h/2)
            }
        }
    }
}
