import QtQuick

// Gráfico de CPU/GPU en tiempo real con movimiento continuo.
// Entre una muestra y la siguiente (1 s) la línea se desliza a 60 fps y el
// punto nuevo entra por la derecha: nada salta. La curva es monótona
// (Fritsch–Carlson): suaviza sin inventar picos ni pasar de 0–100 %.
Item {
    id: history
    property var cpuValues: []
    property var gpuValues: []
    property color cpuColor: "#1688F3"
    property color gpuColor: "#76B900"
    property int capacity: 60      // muestras visibles (telemetry guarda las últimas 60)
    property int sampleMs: 1000    // intervalo de muestreo de telemetry
    property real advance: 1       // 0 → 1 durante el deslizamiento entre muestras
    property int bridgeGapSamples: 2 // unir visualmente huecos breves sin tocar las lecturas

    onCpuValuesChanged: slide.restart()
    onGpuValuesChanged: slide.restart()
    onAdvanceChanged: chart.requestPaint()
    // Las líneas heredan exactamente el color de marca de sus medidores.
    onCpuColorChanged: chart.requestPaint()
    onGpuColorChanged: chart.requestPaint()

    NumberAnimation {
        id: slide
        target: history
        property: "advance"
        from: 0; to: 1
        duration: history.sampleMs
        easing.type: Easing.Linear   // velocidad constante, como un monitor real
    }

    Canvas {
        id: chart
        anchors.fill: parent
        antialiasing: true
        renderTarget: Canvas.FramebufferObject
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
                c.strokeStyle = themeManager.palette.panelBorder
                c.beginPath(); c.moveTo(left,y); c.lineTo(left+w,y); c.stroke()
                c.fillStyle = "#9BA4B6"; c.textAlign = "right"
                c.fillText((100 - i*25)+"%", left-10, y+4)
            }
            for (let i=0; i<=4; ++i) {
                const x = left+w*i/4
                c.strokeStyle = themeManager.palette.panelRaised
                c.beginPath(); c.moveTo(x,top); c.lineTo(x,top+h); c.stroke()
            }
            c.fillStyle = "#9BA4B6"; c.textAlign = "left"
            c.fillText("Hace " + history.capacity + " s", left, height - 8)
            c.textAlign = "right"
            c.fillText("Ahora", left + w, height - 8)

            const step = w / Math.max(1, history.capacity - 1)
            // La muestra más reciente termina en el borde derecho; mientras dura
            // el deslizamiento viene entrando desde fuera del área (recortada).
            const shift = step * (1 - history.advance)

            function valid(v) {
                return v !== null && v !== undefined && typeof v === "number" && isFinite(v) && v >= 0 && v <= 100
            }

            // Curva monótona por tramos de puntos visibles. Usa la separación real entre
            // puntos, así un hueco breve puede unirse visualmente sin que la curva se corte.
            function strokeRun(pts) {
                const n = pts.length
                if (n < 2) return
                const d = [], m = []
                for (let k=0; k<n-1; ++k) {
                    const dx = Math.max(1e-6, pts[k+1].x - pts[k].x)
                    d.push((pts[k+1].y - pts[k].y) / dx)
                }
                m.push(d[0])
                for (let k=1; k<n-1; ++k) m.push(d[k-1]*d[k] <= 0 ? 0 : (d[k-1] + d[k]) / 2)
                m.push(d[n-2])
                for (let k=0; k<n-1; ++k) {
                    if (d[k] === 0) { m[k] = 0; m[k+1] = 0; continue }
                    const a = m[k] / d[k], b = m[k+1] / d[k], s = a*a + b*b
                    if (s > 9) { const t = 3 / Math.sqrt(s); m[k] = t*a*d[k]; m[k+1] = t*b*d[k] }
                }
                c.moveTo(pts[0].x, pts[0].y)
                for (let k=0; k<n-1; ++k) {
                    const dx = pts[k+1].x - pts[k].x
                    const t = dx / 3
                    c.bezierCurveTo(pts[k].x + t, pts[k].y + m[k]*t,
                                    pts[k+1].x - t, pts[k+1].y - m[k+1]*t,
                                    pts[k+1].x, pts[k+1].y)
                }
            }

            function plot(values, ink) {
                if (!values || values.length < 2) return 0
                const count = values.length
                let run = [], visible = 0, gapCount = 0
                c.beginPath()
                for (let i=0; i<count; ++i) {
                    const v = values[i]
                    if (!valid(v)) {
                        if (run.length > 0) gapCount++
                        continue
                    }
                    if (gapCount > history.bridgeGapSamples) {
                        strokeRun(run)
                        run = []
                    }
                    gapCount = 0
                    run.push({ x: left + w - (count - 1 - i) * step + shift, y: top + h * (1 - v / 100) })
                    visible++
                }
                strokeRun(run)
                if (visible < 2) return visible
                c.strokeStyle = ink.toString()
                c.lineWidth = 2.5
                c.lineCap = "round"
                c.lineJoin = "round"
                c.stroke()
                return visible
            }

            // Solo se dibuja dentro del área del gráfico: lo que entra y sale queda oculto.
            c.save()
            c.beginPath(); c.rect(left, top - 2, w, h + 4); c.clip()
            const shown = plot(history.cpuValues, history.cpuColor) + plot(history.gpuValues, history.gpuColor)
            c.restore()

            // Desvanecido en el borde izquierdo: la muestra más antigua sale sin cortes bruscos.
            const fade = c.createLinearGradient(left, 0, left + 28, 0)
            fade.addColorStop(0, themeManager.palette.panel)
            fade.addColorStop(1, "transparent")
            c.fillStyle = fade
            c.fillRect(left + 1, top - 2, 28, h + 4)

            if (shown < 2) {
                c.textAlign="center"; c.fillStyle="#8592A6"
                c.fillText("Esperando lecturas reales…",left+w/2,top+h/2)
            }
        }
    }
}
