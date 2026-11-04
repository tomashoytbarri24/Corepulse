import QtQuick

Canvas {
    id: chart
    property var samples: []
    property bool timed: false
    property color accent: "#27B6F0"
    property color muted: "#AABCCF"
    property color grid: "#334155"
    property bool showMarker: false
    onSamplesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onAccentChanged: requestPaint()
    onGridChanged: requestPaint()
    onPaint: {
        const ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        const rows = samples || []
        const values = rows.map(r => timed ? r.ms : r)
        const valid = values.filter(v => typeof v === "number" && isFinite(v) && v > 0)
        if (!valid.length) {
            ctx.fillStyle = muted
            ctx.font = "11px 'Segoe UI'"
            ctx.fillText("Sin fotogramas ETW recientes", 0, height * 0.55)
            return
        }
        const ceiling = Math.max(50, ...valid)
        const chartWidth = Math.max(1, width - 42)
        const plotHeight = Math.max(1, height - 22)
        const from = timed ? rows[0].time : 0
        const to = timed ? rows[rows.length-1].time : Math.max(1, rows.length-1)
        ctx.font = "10px 'Segoe UI'"
        for (const reference of [16.667, 33.333]) {
            const y = plotHeight - reference / ceiling * plotHeight + 4
            ctx.strokeStyle = grid; ctx.lineWidth = 1
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(chartWidth, y); ctx.stroke()
            ctx.fillStyle = muted; ctx.fillText(reference.toFixed(1), chartWidth+5, y+3)
        }
        if (showMarker && from <= 0 && to >= 0) {
            const x = (0-from) / Math.max(0.001, to-from) * chartWidth
            ctx.strokeStyle = "#E9B86B"; ctx.lineWidth = 1
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, plotHeight+4); ctx.stroke()
            ctx.fillStyle = "#E9B86B"; ctx.fillText("Atajo", Math.min(x+5, chartWidth-30), height-2)
        }
        ctx.strokeStyle = accent; ctx.lineWidth = 1.5; ctx.beginPath()
        let started = false
        for (let i=0; i<rows.length; ++i) {
            const v = values[i]
            if (typeof v !== "number" || !isFinite(v) || v <= 0) { started=false; continue }
            const x = ((timed ? rows[i].time : i)-from) / Math.max(0.001, to-from) * chartWidth
            const y = plotHeight+4-v/ceiling*plotHeight
            if (started) ctx.lineTo(x, y); else { ctx.moveTo(x, y); started=true }
        }
        ctx.stroke()
        ctx.fillStyle = muted
        ctx.fillText(timed ? from.toFixed(1)+" s" : "Fotogramas anteriores", 0, height-2)
    }
}
