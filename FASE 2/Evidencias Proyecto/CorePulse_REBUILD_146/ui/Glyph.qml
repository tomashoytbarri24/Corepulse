import QtQuick
import QtQuick.Shapes

// Iconos vectoriales nativos de Qt Quick Shapes: sin Canvas ni texturas.
// Se recalculan las rutas al tamaño LOGICO real antes del trazado, sin
// escalar después una Shape de 24x24 (degrada la calidad en DPI fraccionario).
Item {
    id: glyph
    property string kind: "chart"
    property color ink: "#AEB8CB"
    property real stroke: 1.9
    width: 24
    height: 24

    // SVG path data para pintar vectores directamente en la escena Qt Quick.
    // Se comparte una sola Shape y una sola ShapePath para todo el catálogo.
    function circle(cx, cy, radius) {
        const k = radius * 0.55228475
        return "M " + (cx + radius) + " " + cy
            + " C " + (cx + radius) + " " + (cy + k) + " " + (cx + k) + " " + (cy + radius) + " " + cx + " " + (cy + radius)
            + " C " + (cx - k) + " " + (cy + radius) + " " + (cx - radius) + " " + (cy + k) + " " + (cx - radius) + " " + cy
            + " C " + (cx - radius) + " " + (cy - k) + " " + (cx - k) + " " + (cy - radius) + " " + cx + " " + (cy - radius)
            + " C " + (cx + k) + " " + (cy - radius) + " " + (cx + radius) + " " + (cy - k) + " " + (cx + radius) + " " + cy + " Z "
    }


    // Adaptación geométrica previa al render: las coordenadas SVG se convierten
    // directamente al tamaño final. No se emplea transform: Scale ni bitmaps.
    // Se mantienen las instrucciones y parámetros de arcos SVG intactos.
    readonly property real pixelScale: Math.max(0.01, kind === "gpu_amd" ? width / 24 : Math.min(width, height) / 24)
    // NVIDIA y el logotipo AMD son apaisados; ambos se ajustan a su proporción.
    // La geometría se corrige antes del trazado, sin estirar texturas o Shapes.
    // El resto del catálogo conserva sus coordenadas y escala.
    readonly property real iconYScale: kind === "gpu_nvidia" ? pixelScale * (383 / 597) : pixelScale
    readonly property real offsetX: (width - 24 * pixelScale) / 2
    readonly property real offsetY: (height - 24 * iconYScale) / 2
    readonly property real effectiveStroke: Math.max(1.8, stroke * pixelScale)

    function fittedPath(source) {
        const tokens = source.match(/[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g) || []
        const arity = {M:2,L:2,H:1,V:1,C:6,S:4,Q:4,T:2,A:7,Z:0}
        let command = ""
        let parameter = 0
        const output = []
        for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i]
            if (/^[A-Za-z]$/.test(token)) {
                command = token
                parameter = 0
                output.push(token)
                continue
            }
            const type = command.toUpperCase()
            const n = arity[type]
            if (n === undefined || n === 0) return ""
            const pos = parameter % n
            const relative = command !== type
            let number = Number(token)
            if (type === "A") {
                // SVG arc: rx, ry, rotation, large-arc-flag, sweep-flag, x, y.
                if (pos === 0)
                    number *= pixelScale
                else if (pos === 1)
                    number *= iconYScale
                else if (pos === 5)
                    number = number * pixelScale + (relative ? 0 : offsetX)
                else if (pos === 6)
                    number = number * iconYScale + (relative ? 0 : offsetY)
            } else if (type === "H") {
                number = number * pixelScale + (relative ? 0 : offsetX)
            } else if (type === "V") {
                number = number * iconYScale + (relative ? 0 : offsetY)
            } else {
                const xCoordinate = pos % 2 === 0
                number = number * (xCoordinate ? pixelScale : iconYScale)
                    + (relative ? 0 : (xCoordinate ? offsetX : offsetY))
            }
            output.push(String(Math.round(number * 10000) / 10000))
            parameter++
        }
        return output.join(" ")
    }

    function iconPath(name) {
        switch (name) {
        case "menu":
            return "M 5 7 H 19 M 5 12 H 19 M 5 17 H 19"
        case "home":
            return "M 3.8 11 L 12 4 L 20.2 11 M 6.8 10 V 20 H 17.2 V 10 M 10 20 V 14 H 14 V 20"
        case "dashboard":
            return "M 5.8 4.5 H 9.6 Q 10.6 4.5 10.6 5.5 V 9.4 Q 10.6 10.4 9.6 10.4 H 5.8 Q 4.8 10.4 4.8 9.4 V 5.5 Q 4.8 4.5 5.8 4.5 Z "
                + "M 14.4 4.5 H 18.2 Q 19.2 4.5 19.2 5.5 V 9.4 Q 19.2 10.4 18.2 10.4 H 14.4 Q 13.4 10.4 13.4 9.4 V 5.5 Q 13.4 4.5 14.4 4.5 Z "
                + "M 5.8 13.6 H 9.6 Q 10.6 13.6 10.6 14.6 V 18.5 Q 10.6 19.5 9.6 19.5 H 5.8 Q 4.8 19.5 4.8 18.5 V 14.6 Q 4.8 13.6 5.8 13.6 Z "
                + "M 14.4 13.6 H 18.2 Q 19.2 13.6 19.2 14.6 V 18.5 Q 19.2 19.5 18.2 19.5 H 14.4 Q 13.4 19.5 13.4 18.5 V 14.6 Q 13.4 13.6 14.4 13.6 Z"
        case "chart":
            return "M 4 4 V 20 H 20 M 6.2 16 L 10 12 L 13.7 14 L 19 7.2"
        case "gauge":
            // Velocímetro de benchmark: semicírculo nítido y aguja visible.
            // Curva Bézier explícita en vez de A: evita que el arco SVG
            // se interprete como un segmento casi plano en algunos Qt/DPI.
            return "M 4 17 C 4 12 7.6 8 12 8 C 16.4 8 20 12 20 17 "
                + "M 6 18.7 H 18 M 12 15.8 L 16.9 11.1 "
                + "M 6.9 13.1 L 8.2 13.8 M 12 9.8 V 11 "
                + circle(12, 15.8, 1.4)
        case "scan":
            return "M 8 4 H 6 Q 4 4 4 6 V 8 M 16 4 H 18 Q 20 4 20 6 V 8 "
                + "M 4 16 V 18 Q 4 20 6 20 H 8 M 20 16 V 18 Q 20 20 18 20 H 16 "
                + "M 6.5 12.5 H 9.3 L 11.2 9.3 L 13.7 15.2 L 15.2 12.5 H 17.5"
        case "shield":
            return "M 12 2.7 L 19 5.2 V 11.4 Q 19 17.5 12 21.2 Q 5 17.5 5 11.4 V 5.2 Z"
        case "health":
        case "health_shield":
            return "M 12 2.7 L 19 5.2 V 11.4 Q 19 17.5 12 21.2 Q 5 17.5 5 11.4 V 5.2 Z "
                + "M 12 7.7 V 15.6 M 8.1 11.65 H 15.9"
        case "clean":
        case "broom":
            return "M 5 4.5 L 14.7 14.2 M 12.8 16.1 L 17.5 11.4 L 20 13.9 L 15.3 18.6 "
                + "M 10 18.6 L 15.3 18.6 M 12 16.6 L 15.3 19.9"
        case "settings":
        case "tools":
            return circle(12, 12, 6.2) + circle(12, 12, 2.1)
                + " M 12 2 V 5.8 M 12 18.2 V 22 M 2 12 H 5.8 M 18.2 12 H 22"
                + " M 5 5 L 7.7 7.7 M 16.3 16.3 L 19 19 M 19 5 L 16.3 7.7 M 7.7 16.3 L 5 19"
        case "sliders":
            return "M 4.3 6.3 H 19.7 M 4.3 12 H 19.7 M 4.3 17.7 H 19.7 "
                + circle(8.6, 6.3, 1.9) + circle(15.3, 12, 1.9) + circle(10.7, 17.7, 1.9)
        case "network":
        case "trace":
            return circle(5.8, 5.8, 2) + circle(18, 9.2, 2) + circle(8.2, 18.2, 2)
                + " M 7.8 6.2 L 16.1 8.7 M 16.4 10.7 L 9.7 16.8 M 6.2 7.8 L 7.8 16.3"
        case "wifi":
            return "M 3.8 9.2 Q 12 2.6 20.2 9.2 M 6.8 12.8 Q 12 8.6 17.2 12.8 "
                + "M 9.9 16.4 Q 12 14.9 14.1 16.4 " + circle(12, 19.4, 0.9)
        case "bell":
            return "M 6 17 H 18 L 16.7 15 V 10 Q 16.7 5.7 12 5.7 Q 7.3 5.7 7.3 10 V 15 Z "
                + "M 10.1 19.7 Q 12 21.7 13.9 19.7"
        case "alerts":
        case "bell_alert":
            return "M 6 17 H 18 L 16.7 15 V 10 Q 16.7 5.7 12 5.7 Q 7.3 5.7 7.3 10 V 15 Z "
                + "M 10.1 19.7 Q 12 21.7 13.9 19.7 M 19.5 5 V 9.2 M 19.5 12 V 12.2"
        case "trends":
        case "trend_up":
            return "M 4 19.5 H 20 M 5.3 15.7 L 9.5 11.8 L 13.2 13 L 18.5 6.5 "
                + "M 14.5 6.5 H 18.5 V 10.5"
        case "refresh":
            return "M 19.2 8.8 Q 16.8 5 12 5 Q 7.3 5 4.9 8.9 Q 2.7 12.5 4.5 16.2 Q 6.6 20.1 11.2 20.7 Q 15.7 21.3 18.7 17.9 M 19 4.9 V 9.3 H 14.6"
        case "history":
            return "M 5.8 8.2 A 7.9 7.9 0 1 1 4.5 14.8 M 4.2 4.8 V 8.9 H 8.3 "
                + "M 4.2 8.9 Q 7.4 3.6 12.1 4.1 M 12 8.5 V 12.6 L 15.7 14.8"
        case "clock":
            return circle(12, 12, 8.4) + " M 12 7 V 12 L 15.9 14.3"
        case "palette":
            return "M 12 3.6 C 7 3.6 3.5 7.6 3.5 12.3 C 3.5 17.1 7.7 20.3 12.3 20.3 "
                + "C 14.6 20.3 15.3 18.6 14.3 16.6 C 13.5 14.9 14.6 13.8 16.2 13.8 "
                + "C 18.8 13.8 20.5 12.6 20.5 10.3 C 20.5 6.4 16.8 3.6 12 3.6 Z "
                + circle(8.1, 8.9, 0.8) + circle(12.1, 7.2, 0.8)
                + circle(16.2, 9.3, 0.8) + circle(8.1, 13.3, 0.8)
        case "ai":
        case "spark_ai":
            return "M 12 3.3 L 13.8 8.2 L 18.7 10 L 13.8 11.8 L 12 16.7 L 10.2 11.8 L 5.3 10 L 10.2 8.2 Z "
                + "M 19 3.5 L 19.7 5.7 L 21.9 6.4 L 19.7 7.1 L 19 9.3 L 18.3 7.1 L 16.1 6.4 L 18.3 5.7 Z "
                + "M 6.3 15.1 L 6.9 16.8 L 8.6 17.4 L 6.9 18 L 6.3 19.7 L 5.7 18 L 4 17.4 L 5.7 16.8 Z"
        case "cpu":
            return "M 7 6 H 17 Q 18 6 18 7 V 17 Q 18 18 17 18 H 7 Q 6 18 6 17 V 7 Q 6 6 7 6 Z "
                + "M 9 9 H 15 V 15 H 9 Z M 8 2 V 6 M 12 2 V 6 M 16 2 V 6 M 8 18 V 22 M 12 18 V 22 M 16 18 V 22 "
                + "M 2 8 H 6 M 2 12 H 6 M 2 16 H 6 M 18 8 H 22 M 18 12 H 22 M 18 16 H 22"
        case "gpu_nvidia":
            // NVIDIA estilo overlay: bloque verde con ojo blanco e intercalado
            // con el bloque blanco, como en la referencia pedida.
            // Este path contiene únicamente las formas blancas visibles.
            return "M 9.5 0 L 9.5 2.89 L 14.58 4.34 L 19.13 9.86 L 14.66 15.58 L 9.5 17.53 "
                + "L 9.5 19.35 L 14.9 17.72 L 20.05 12.44 L 22.63 14.83 L 16.63 19.54 "
                + "L 9.5 21.36 L 9.5 24 L 24 24 L 24 0 Z "
                + "M 0 10.37 L 1.69 14.7 L 4.15 18.47 L 6.48 20.42 L 9.42 21.3 "
                + "L 9.42 19.41 L 7.21 18.66 L 4.67 15.83 L 2.58 10.55 L 3.91 8.42 "
                + "L 6 6.28 L 9.42 4.9 L 9.42 3.02 L 5.15 4.84 L 2.38 7.35 Z "
                + "M 9.5 15.58 L 11.15 15.52 L 12.93 14.51 L 14.78 12.5 L 16.31 9.86 "
                + "L 14.7 7.48 L 12.97 5.91 L 11.4 5.15 L 9.5 4.96 L 9.5 6.85 "
                + "L 12.04 7.48 L 14.26 9.86 L 12.08 12.63 L 10.83 9.68 L 9.5 8.92 Z "
                + "M 9.38 6.97 L 8.01 7.35 L 6.68 8.23 L 4.47 10.87 L 5.44 13.57 "
                + "L 6.6 15.58 L 8.01 16.9 L 9.42 17.4 L 9.42 15.71 L 7.89 14.58 "
                + "L 7.09 13.13 L 6.44 11.06 L 7.13 9.93 L 8.05 9.11 L 9.42 8.8 Z"
        case "gpu_amd":
            // Logotipo AMD completo: letras de la marca y flecha oficial.
            return "M18.324 9.137l1.559 1.56h2.556v2.557L24 14.814V9.137z M2 9.52l-2 4.96h1.309l.37-.982H3.9l.408.982h1.338L3.432 9.52z M6.209 9.52v4.955h1.238v-3.092l1.338 1.562h.188l1.338-1.556v3.091h1.238V9.52H10.47l-1.592 1.845L7.287 9.52z M12.492 9.52v4.96h2.057c1.979 0 2.88-1.046 2.88-2.472 0-1.36-.937-2.488-2.747-2.488zm1.237.91h.792c1.17 0 1.63.711 1.63 1.57 0 .728-.372 1.572-1.616 1.572h-.806zm-10.985.273l.791 1.932H2.008zm17.137.307l-1.604 1.603v2.25h2.246l1.604-1.607h-2.246z"
        case "gpu":
        case "gpu":
            return "M 4.5 5.5 H 19 Q 20.5 5.5 20.5 7 V 17 Q 20.5 18.5 19 18.5 H 4.5 Q 3 18.5 3 17 V 7 Q 3 5.5 4.5 5.5 Z "
                + circle(9.4, 12, 3) + " M 15 10 H 18 V 14 H 15 Z M 20.5 9 H 22 M 20.5 15 H 22"
        case "ram":
            // Módulo DIMM con cuatro chips y contactos inferiores.
            return "M 4.2 5.5 H 19.8 Q 21 5.5 21 6.7 V 14.3 Q 21 15.5 19.8 15.5 H 4.2 Q 3 15.5 3 14.3 V 6.7 Q 3 5.5 4.2 5.5 Z "
                + "M 4.8 7.5 H 7.8 V 13.4 H 4.8 Z M 8.7 7.5 H 11.7 V 13.4 H 8.7 Z "
                + "M 12.3 7.5 H 15.3 V 13.4 H 12.3 Z M 16.2 7.5 H 19.2 V 13.4 H 16.2 Z "
                + "M 5.7 15.5 V 19.8 M 8.1 15.5 V 19.8 M 10.5 15.5 V 19.8 "
                + "M 12.9 15.5 V 19.8 M 15.3 15.5 V 19.8 M 17.7 15.5 V 19.8"
        case "storage":
            // Silueta genérica cuando Windows no informa medio o conexión.
            return "M 5 4.5 H 19 Q 20.5 4.5 20.5 6 V 18 Q 20.5 19.5 19 19.5 H 5 Q 3.5 19.5 3.5 18 V 6 Q 3.5 4.5 5 4.5 Z "
                + "M 7 8 H 17 V 16 H 7 Z M 9 18 H 15"
        case "storage_hdd":
            // Disco mecánico: plato giratorio, eje y brazo de lectura.
            return "M 4.5 4.5 H 19.5 Q 21 4.5 21 6 V 18 Q 21 19.5 19.5 19.5 H 4.5 Q 3 19.5 3 18 V 6 Q 3 4.5 4.5 4.5 Z "
                + circle(12, 11.5, 5.1) + circle(12, 11.5, 1.1)
                + " M 13 12.2 L 17.5 7.7 M 15.8 8 H 17.8"
        case "storage_sata":
            // SSD SATA de 2,5 pulgadas: carcasa, placa y contactos.
            return "M 5 4 H 19 Q 20.5 4 20.5 5.5 V 18.5 Q 20.5 20 19 20 H 5 Q 3.5 20 3.5 18.5 V 5.5 Q 3.5 4 5 4 Z "
                + "M 7 6.5 H 17 V 15.5 H 7 Z M 8 17 H 9 V 18.5 H 8 Z "
                + "M 10.2 17 H 11.2 V 18.5 H 10.2 Z M 12.4 17 H 13.4 V 18.5 H 12.4 Z "
                + "M 14.6 17 H 15.6 V 18.5 H 14.6 Z M 16.8 17 H 17.8 V 18.5 H 16.8 Z"
        case "storage_nvme":
            // Se conserva la placa M.2 existente para SSD NVMe.
            return "M 4 8.5 H 20 V 10.4 H 18.5 V 12.1 H 20 V 15.5 H 4 Z "
                + circle(5.6, 12, 1.1)
                + " M 8 9.7 H 11.7 V 14.3 H 8 Z M 12.7 9.7 H 16.4 V 14.3 H 12.7 Z"
        case "laptop":
        case "laptop":
            return "M 6 4 H 18 Q 19 4 19 5 V 15 H 5 V 5 Q 5 4 6 4 Z M 3 19.5 H 21 L 18.5 17.5 H 5.5 Z"
        case "box":
            return "M 5.5 5 H 18.5 Q 20 5 20 6.5 V 17.5 Q 20 19 18.5 19 H 5.5 Q 4 19 4 17.5 V 6.5 Q 4 5 5.5 5 Z M 4 10 H 20"
        case "battery":
            return "M 5.5 7.5 H 17.5 Q 19 7.5 19 9 V 15 Q 19 16.5 17.5 16.5 H 5.5 Q 4 16.5 4 15 V 9 Q 4 7.5 5.5 7.5 Z "
                + "M 19 10 H 21 V 14 H 19 M 7.5 10 H 11.2 V 14 H 7.5 Z"
        case "gamepad":
            return "M 6 8 H 18 Q 20 8 21 13 L 22 17 Q 22 19.5 19 19 L 15 16 H 9 L 5 19 Q 2 19.5 2 17 L 3 13 Q 4 8 6 8 Z "
                + "M 7 11 V 15 M 5 13 H 9 " + circle(16, 12, 0.8) + circle(18, 14, 0.8)
        case "drivers":
            return "M 4.5 5 H 19.5 V 15 H 4.5 Z M 9 19 H 15 M 12 15 V 19 "
                + "M 8 10 L 10.4 12.2 L 16.5 7.7"
        case "headphones":
            return "M 4 13 V 11 Q 4 3.8 12 3.8 Q 20 3.8 20 11 V 13 "
                + "M 4 13 H 7 V 20 H 5 Q 3.5 20 3.5 18 V 15 Q 3.5 13 4 13 Z "
                + "M 20 13 H 17 V 20 H 19 Q 20.5 20 20.5 18 V 15 Q 20.5 13 20 13 Z"
        case "services":
            return "M 4 6 H 20 M 4 12 H 20 M 4 18 H 20 "
                + "M 8 4 V 8 M 15 10 V 14 M 10 16 V 20"
        case "power":
            return "M 12 3 V 12 M 7.3 6 Q 3.5 9 3.5 13 Q 3.5 20.5 12 20.5 Q 20.5 20.5 20.5 13 Q 20.5 9 16.7 6"
        case "file_chart":
            return "M 6 3.5 H 15 L 19 7.5 V 20.5 H 6 Z "
                + "M 15 3.5 V 7.5 H 19 M 8.5 17 V 13 M 11.5 17 V 10.5 M 14.5 17 V 14"
        case "file_clock":
            return "M 5 3 H 14 L 19 8 V 21 H 5 Z M 14 3 V 8 H 19 "
                + circle(11.5, 14, 3.6) + " M 11.5 11.8 V 14.2 L 13.2 15.3"
        case "restore":
            return "M 4.5 10 L 4.5 5.8 H 8.7 M 4.5 5.8 Q 8 2.5 13 4 Q 20 5.4 20 12.6 Q 20 19.9 12.8 20 "
                + "M 12 8 V 12 L 15.2 14.1"
        case "wrench":
            return "M 13.5 4 Q 18.7 2.8 20 6 L 16.5 9.5 L 18.5 11.5 Q 21.8 10 20.5 5 "
                + "M 16.5 10 L 7 19.5 Q 4.5 21.5 3 19 Q 1.7 16.5 4 15 L 13.5 5.5"
        case "layers":
            return "M 12 4 L 21 9 L 12 14 L 3 9 Z M 3.5 13 L 12 18 L 20.5 13 M 3.5 17 L 12 22 L 20.5 17"
        case "activity":
            return "M 3 12 H 7 L 9.5 6 L 13 18 L 16 9 L 18 12 H 21"
        case "login":
            return "M 14 4 H 18 Q 20 4 20 6 V 18 Q 20 20 18 20 H 14 M 4 12 H 14 M 10 8 L 14 12 L 10 16"
        case "logout":
            return "M 10 4 H 6 Q 4 4 4 6 V 18 Q 4 20 6 20 H 10 M 10 12 H 20 M 16 8 L 20 12 L 16 16"
        case "user":
            return circle(12, 8, 4) + " M 4 20.5 Q 4 14 12 14 Q 20 14 20 20.5"
        case "user_plus":
            return circle(9, 8, 3.6) + " M 2.5 20 Q 2.5 14 9 14 Q 15.5 14 15.5 20 M 19 8 V 14 M 16 11 H 22"
        case "eye":
            return "M 2.5 12 C 5 7.4 8.4 5.4 12 5.4 C 15.6 5.4 19 7.4 21.5 12 C 19 16.6 15.6 18.6 12 18.6 C 8.4 18.6 5 16.6 2.5 12 Z "
                + circle(12, 12, 3)
        case "eye_off":
            return "M 2.5 12 C 5 7.4 8.4 5.4 12 5.4 C 15.6 5.4 19 7.4 21.5 12 C 19 16.6 15.6 18.6 12 18.6 C 8.4 18.6 5 16.6 2.5 12 Z "
                + circle(12, 12, 3) + " M 4 4 L 20 20"
        case "clipboard":
            return "M 8 5 H 6 Q 4 5 4 7 V 20 H 20 V 7 Q 20 5 18 5 H 16 "
                + "M 9 3 H 15 V 7 H 9 Z M 8 11 H 16 M 8 14 H 16 M 8 17 H 13"
        default:
            return circle(12, 12, 8)
        }
    }

    Shape {
        id: vectorIcon
        anchors.fill: parent
        antialiasing: true
        // CurveRenderer (Qt 6.7+) suaviza contornos sin depender de MSAA.
        // Qt 6.6 utiliza GeometryRenderer como alternativa compatible.
        // La geometría se entrega al tamaño de destino en ambos modos.
        preferredRendererType: typeof Shape.CurveRenderer === "number"
                               ? Shape.CurveRenderer : Shape.GeometryRenderer
        ShapePath {
            strokeColor: (glyph.kind === "gpu_amd" || glyph.kind === "gpu_nvidia") ? "transparent" : glyph.ink
            strokeWidth: (glyph.kind === "gpu_amd" || glyph.kind === "gpu_nvidia") ? 0 : glyph.effectiveStroke
            fillColor: (glyph.kind === "gpu_amd" || glyph.kind === "gpu_nvidia") ? glyph.ink : "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: glyph.fittedPath(glyph.iconPath(glyph.kind)) }
        }
    }
}
