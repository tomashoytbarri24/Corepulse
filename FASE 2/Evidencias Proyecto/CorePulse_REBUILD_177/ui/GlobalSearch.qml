import QtQuick
import QtQuick.Controls

// REBUILD 161, integrado en 169: buscador global de la barra lateral.
// Indexa secciones, funciones internas de cada página, los tweaks y los temas.
// Sin acentos ni mayúsculas, acepta palabras incompletas ("energi") y un error
// de tipeo. Solo navega: nunca ejecuta acciones desde un resultado.
Item {
    id: search
    property bool compact: false
    property string query: ""
    property int currentIndex: 0
    signal openEntry(var entry)

    readonly property var pal: themeManager.palette
    readonly property color cyan: pal.cyan
    readonly property int maxResults: 8

    // t: título · s: ubicación · p: página (window.selectedPage) · i: icono · k: palabras clave
    readonly property var staticEntries: [
        {t:"Resumen", s:"Monitoreo", p:"summary", i:"dashboard", k:"inicio panel principal dashboard uso cpu gpu ram ssd disco en vivo"},
        {t:"Rendimiento en tiempo real", s:"Resumen", p:"summary", i:"chart", k:"grafico uso cpu gpu ultimas 60 muestras monitor"},
        {t:"Tiempo de sesión", s:"Resumen", p:"summary", i:"clock", k:"uptime tiempo activo encendido sesion de windows"},
        {t:"Benchmark", s:"Monitoreo", p:"benchmark", i:"gauge", k:"prueba de rendimiento puntaje score test velocidad cpu ram ssd"},
        {t:"Prueba GPU DirectX 11 · Ciudad de neón", s:"Benchmark", p:"benchmark", i:"gpu", k:"gpu grafica directx 11 dx11 ciudad neon v29 estres rapido estandar extendido"},
        {t:"Historial de benchmark e informes", s:"Benchmark", p:"benchmark", i:"file_chart", k:"historial sesiones exportar csv informe pdf resultados comparar puntajes"},
        {t:"Sesiones de juego", s:"Monitoreo", p:"game_sessions", i:"game_history", k:"historial partidas fps promedio 1 por ciento low rendimiento juego perfiles incidencias pdf"},
        {t:"Perfiles por juego", s:"Sesiones de juego", p:"game_sessions", i:"power", k:"plan energia automatico por juego overlay temperaturas posicion"},
        {t:"Incidencias en partidas", s:"Sesiones de juego", p:"game_sessions", i:"history", k:"caidas fps frametime temperatura whea error windows linea tiempo"},
        {t:"Iniciar diagnóstico", s:"Diagnóstico", p:"diagnostic", i:"scan", k:"diagnostico analisis escaneo revisar pc problemas fallas pdf dos minutos"},
        {t:"Centro de salud", s:"Diagnóstico", p:"health", i:"health_shield", k:"salud estado general mantenimiento areas herramientas"},
        {t:"Batería", s:"Centro de salud", p:"battery", i:"battery", k:"bateria capacidad desgaste ciclos de carga autonomia portatil notebook laptop energia"},
        {t:"Análisis de Windows", s:"Centro de salud", p:"windows_health", i:"settings", k:"windows estabilidad controladores drivers errores eventos pnp"},
        {t:"Servicios de Windows", s:"Centro de salud · Windows", p:"services", i:"services", k:"servicios procesos en segundo plano windows"},
        {t:"Inicio de Windows", s:"Más módulos", p:"startup", i:"power", k:"programas al inicio arranque startup deshabilitar habilitar entradas"},
        {t:"Reparación DISM / SFC", s:"Centro de salud", p:"repair", i:"wrench", k:"reparar windows dism sfc integridad archivos corruptos sistema"},
        {t:"Historial y cambios", s:"Centro de salud", p:"change_history", i:"file_clock", k:"historial de cambios registros mantenimiento modificaciones"},
        {t:"Recuperación y puntos de restauración", s:"Centro de salud", p:"restore", i:"restore", k:"punto de restauracion recuperacion restaurar sistema copia de seguridad"},
        {t:"Rendimiento, temperatura y throttling", s:"Centro de salud", p:"health_performance", i:"gauge", k:"throttling temperatura termica calor sobrecalentamiento estabilidad termica riesgo"},
        {t:"Planes de energía de Windows", s:"Centro de salud · Rendimiento", p:"health_performance", i:"power", k:"energia plan de energia alto rendimiento maximo rendimiento equilibrado ahorro consumo powercfg"},
        {t:"Energía automática para juegos", s:"Centro de salud · Rendimiento", p:"health_performance", i:"gamepad", k:"energia automatica plan por juego juegos gaming restaurar plan anterior"},
        {t:"Game Boost", s:"Más módulos", p:"gaming", i:"gamepad", k:"game boost juegos gaming prioridad highqos game mode modo juego fps rendimiento"},
        {t:"Test de audio", s:"Centro de salud", p:"audio", i:"headphones", k:"audio sonido parlantes altavoces auriculares microfono canales izquierdo derecho"},
        {t:"Almacenamiento y salud del disco", s:"Más módulos", p:"storage", i:"storage", k:"disco ssd hdd nvme smart salud desgaste temperatura unidad almacenamiento horas encendido"},
        {t:"Procesador", s:"Más módulos", p:"cpu", i:"cpu", k:"cpu procesador nucleos hilos temperatura frecuencia potencia intel amd"},
        {t:"Tarjeta gráfica", s:"Más módulos", p:"gpu", i:"gpu", k:"gpu grafica tarjeta de video vram nvidia amd intel controlador"},
        {t:"Memoria RAM", s:"Más módulos", p:"ram", i:"ram", k:"ram memoria modulos dimm uso disponible"},
        {t:"Limpieza de sistema", s:"Mantenimiento", p:"cleanup", i:"broom", k:"limpiar limpieza basura optimizar"},
        {t:"Archivos temporales", s:"Limpieza de sistema", p:"cleanup", i:"broom", k:"temporales temp borrar eliminar archivos"},
        {t:"Optimización de memoria RAM", s:"Limpieza de sistema", p:"cleanup", i:"ram", k:"liberar ram standby limpieza profunda memoria"},
        {t:"Caché de Windows", s:"Limpieza de sistema", p:"cleanup", i:"broom", k:"cache shaders miniaturas limpiar"},
        {t:"Liberar almacenamiento", s:"Limpieza de sistema", p:"cleanup", i:"storage", k:"espacio en disco liberar ubicaciones regenerables"},
        {t:"Archivos duplicados", s:"Limpieza de sistema", p:"cleanup", i:"clipboard", k:"duplicados copias identicas carpeta"},
        {t:"Papelera de reciclaje", s:"Limpieza de sistema", p:"cleanup", i:"broom", k:"papelera vaciar reciclaje"},
        {t:"Caché DNS", s:"Limpieza de sistema", p:"cleanup", i:"network", k:"dns flush vaciar cache red resolucion de nombres"},
        {t:"Tweaks Windows 11", s:"Mantenimiento", p:"tweaks", i:"sliders", k:"tweaks ajustes optimizaciones registro windows 11 restaurar"},
        {t:"Red avanzada", s:"Mantenimiento", p:"advanced_network", i:"network", k:"red internet conexion adaptadores ip ipv4 dns velocidad de enlace"},
        {t:"Prueba de velocidad de Internet", s:"Red avanzada", p:"advanced_network", i:"network", k:"speedtest test velocidad internet descarga subida latencia ping jitter"},
        {t:"Red", s:"Más módulos", p:"network", i:"wifi", k:"red wifi ethernet conexion adaptadores"},
        {t:"Alertas técnicas", s:"Historial", p:"alerts", i:"bell_alert", k:"alertas avisos advertencias activas"},
        {t:"Tendencias", s:"Historial", p:"trends", i:"trend_up", k:"tendencias sesiones historial de uso comparar sesiones"},
        {t:"Historial de alertas", s:"Historial", p:"alert_history", i:"history", k:"historial alertas transiciones limpiar"},
        {t:"Temas", s:"Personalización", p:"themes", i:"palette", k:"temas colores apariencia paleta liquid glass identidad visual"},
        {t:"CorePulse AI", s:"Personalización", p:"ai", i:"spark_ai", k:"ia inteligencia artificial chat asistente preguntar consultar"},
        {t:"Overlay en juegos", s:"Monitoreo", p:"overlay", i:"layers", k:"overlay osd fps en juego pantalla captura etw presentmon"},
        {t:"Editor visual del overlay", s:"Overlay", p:"overlay", i:"layers", k:"diseño tamaño opacidad transparencia arrastrar ordenar metricas frametime"},
        {t:"Registros de problemas", s:"Sesiones de juego", p:"game_sessions", i:"history", k:"tirones stutter lag problema registrar atajo frametime"},
        {t:"Atajos de teclado", s:"Overlay", p:"overlay", i:"layers", k:"atajos teclas hotkeys shift f2 mostrar ocultar overlay"},
        {t:"Panel rápido (Shift+F2)", s:"Overlay", p:"overlay", i:"sliders", k:"panel rapido control rapido barra superior perfiles de energia ram a fondo shift f2"},
        {t:"Reportes", s:"Más módulos", p:"reports", i:"file_chart", k:"reportes informe pdf exportar"},
        {t:"Telemetría", s:"Más módulos", p:"telemetry", i:"activity", k:"telemetria lecturas sensores fuentes datos"},
        {t:"Evidencias", s:"Más módulos", p:"evidence", i:"clipboard", k:"evidencias lecturas verificadas fuentes"}
    ]

    // Índice completo: estáticos + tweaks (uno por ajuste y por categoría) + temas.
    readonly property var entries: {
        // Igual que la barra lateral: Batería solo aparece si Windows informa una.
        const hasBattery = !!(batteryHealth && batteryHealth.data && batteryHealth.data.hasBattery)
        const list = staticEntries.filter(function(e) { return e.p !== "battery" || hasBattery })
                                  .map(function(e) { return Object.assign({kind: "page"}, e) })
        const options = (tweaks && tweaks.options) ? tweaks.options : []
        const categories = []
        for (const opt of options) {
            if (categories.indexOf(opt.category) < 0) categories.push(opt.category)
            list.push({t: opt.title, s: "Tweaks · " + opt.category, p: "tweaks", i: "sliders",
                       k: (opt.description || "") + " tweak ajuste " + opt.category,
                       kind: "tweak", tweakId: opt.id, category: opt.category})
        }
        for (const category of categories)
            list.push({t: "Tweaks de " + category, s: "Tweaks Windows 11", p: "tweaks", i: "sliders",
                       k: "categoria grupo tweaks ajustes " + category, kind: "tweakGroup", category: category})
        const themes = themeManager && themeManager.themes ? themeManager.themes : []
        for (const theme of themes)
            list.push({t: "Tema " + theme.title, s: "Temas", p: "themes", i: "palette",
                       k: (theme.description || "") + " tema color paleta", kind: "theme"})
        for (const e of list) {
            e.nt = normalize(e.t)
            e.nk = normalize(e.s + " " + e.k)
        }
        return list
    }

    readonly property var results: rank(query)

    // Misma longitud que el original: permite resaltar la coincidencia.
    function normalize(text) {
        const from = "áàäâãåéèëêíìïîóòöôõúùüûñç"
        const to = "aaaaaaeeeeiiiiooooouuuunc"
        let out = ""
        const lower = String(text || "").toLowerCase()
        for (let n = 0; n < lower.length; n++) {
            const at = from.indexOf(lower[n])
            out += at >= 0 ? to[at] : lower[n]
        }
        return out
    }
    function words(text) { return text.split(/[^a-z0-9]+/).filter(function(w) { return w.length > 0 }) }
    function editDistance(a, b, limit) {
        if (Math.abs(a.length - b.length) > limit) return limit + 1
        let prev = []
        for (let j = 0; j <= b.length; j++) prev.push(j)
        for (let i = 1; i <= a.length; i++) {
            const row = [i]
            let best = i
            for (let j = 1; j <= b.length; j++) {
                const cost = a[i - 1] === b[j - 1] ? 0 : 1
                row.push(Math.min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + cost))
                best = Math.min(best, row[j])
            }
            if (best > limit) return limit + 1
            prev = row
        }
        return prev[b.length]
    }
    // Tolera un error (dos en palabras largas) contra el comienzo de cada palabra.
    function fuzzy(token, list) {
        if (token.length < 4) return false
        const limit = token.length >= 7 ? 2 : 1
        for (const w of list) {
            for (const size of [token.length - 1, token.length, token.length + 1]) {
                if (size < 3 || size > w.length) continue
                if (editDistance(token, w.slice(0, size), limit) <= limit) return true
            }
        }
        return false
    }
    function tokenScore(token, entry) {
        const titleWords = words(entry.nt)
        const otherWords = words(entry.nk)
        if (titleWords.some(function(w) { return w.indexOf(token) === 0 })) return 10
        if (entry.nt.indexOf(token) >= 0) return 7
        if (otherWords.some(function(w) { return w.indexOf(token) === 0 })) return 5
        if (entry.nk.indexOf(token) >= 0) return 3
        if (fuzzy(token, titleWords)) return 4
        if (fuzzy(token, otherWords)) return 2
        return 0
    }
    function rank(text) {
        const q = normalize(text).trim()
        const tokens = words(q)
        if (tokens.length === 0) return []
        const found = []
        for (const entry of entries) {
            let score = 0
            let all = true
            for (const token of tokens) {
                const s = tokenScore(token, entry)
                if (s === 0) { all = false; break }
                score += s
            }
            if (!all) continue
            if (entry.nt.indexOf(q) === 0) score += 6
            if (entry.kind === "page") score += 1
            found.push({entry: entry, score: score})
        }
        found.sort(function(a, b) { return b.score - a.score || a.entry.t.localeCompare(b.entry.t) })
        return found.slice(0, maxResults).map(function(f) { return f.entry })
    }
    function escapeHtml(text) {
        return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    }
    // Resalta en cian el primer tramo del título que coincide con la búsqueda.
    function highlighted(entry) {
        const tokens = words(normalize(query))
        let at = -1, size = 0
        for (const token of tokens) {
            at = entry.nt.indexOf(token)
            if (at >= 0) { size = token.length; break }
        }
        if (at < 0) return escapeHtml(entry.t)
        return escapeHtml(entry.t.slice(0, at)) + "<font color='" + search.cyan + "'>"
            + escapeHtml(entry.t.slice(at, at + size)) + "</font>" + escapeHtml(entry.t.slice(at + size))
    }

    function activate() {
        if (compact || query.trim().length > 0) popup.open()
        Qt.callLater(function() { input.forceActiveFocus(); input.selectAll() })
    }
    function choose(index) {
        const entry = results[index]
        if (!entry) return
        search.openEntry(entry)
        search.query = ""
        popup.close()
        input.focus = false
    }
    onQueryChanged: {
        currentIndex = 0
        if (query.trim().length > 0) { if (!popup.opened) popup.open() }
        else if (!compact) popup.close()
    }

    // Lupa en modo colapsado: abre el mismo buscador como paleta flotante.
    Rectangle {
        visible: search.compact
        anchors.fill: parent
        radius: width / 2
        color: lensMouse.containsMouse ? Qt.alpha(search.cyan, 0.055) : "transparent"
        Glyph { anchors.centerIn: parent; width: 22; height: 22; kind: "search"; ink: lensMouse.containsMouse ? search.cyan : search.pal.muted }
        MouseArea { id: lensMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: search.activate() }
        ToolTip.visible: lensMouse.containsMouse
        ToolTip.delay: 400
        ToolTip.text: "Buscar en CorePulse (Ctrl+K)"
    }

    // Campo integrado en la barra lateral expandida.
    Rectangle {
        id: field
        visible: !search.compact
        anchors.fill: parent
        radius: 11
        color: input.activeFocus ? Qt.alpha(search.cyan, 0.08) : (fieldMouse.containsMouse ? Qt.alpha(search.cyan, 0.055) : Qt.alpha("#FFFFFF", 0.035))
        border.width: 1
        border.color: input.activeFocus ? Qt.alpha(search.cyan, 0.45) : Qt.alpha(search.cyan, 0.14)
        Behavior on color { ColorAnimation { duration: 130 } }
        MouseArea { id: fieldMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.IBeamCursor; onClicked: search.activate() }
        Glyph { id: fieldLens; x: 9; anchors.verticalCenter: parent.verticalCenter; width: 17; height: 17; kind: "search"; ink: input.activeFocus ? search.cyan : search.pal.muted }
        Text {
            visible: search.query.length === 0
            anchors.left: fieldLens.right; anchors.leftMargin: 7; anchors.right: parent.right; anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            text: "Buscar en CorePulse…"
            color: search.pal.muted; opacity: 0.75; font.pixelSize: 12; elide: Text.ElideRight
        }
        Text {
            visible: search.query.length === 0 && !input.activeFocus && parent.width > 170
            anchors.right: parent.right; anchors.rightMargin: 9; anchors.verticalCenter: parent.verticalCenter
            text: "Ctrl+K"; color: search.pal.muted; opacity: 0.55; font.pixelSize: 10
        }
    }

    TextInput {
        id: input
        parent: search.compact ? paletteRow : field
        anchors.left: parent.left; anchors.leftMargin: search.compact ? 36 : 33
        anchors.right: parent.right; anchors.rightMargin: clearButton.visible ? 30 : 9
        anchors.verticalCenter: parent.verticalCenter
        text: search.query
        onTextEdited: search.query = text
        color: search.pal.ink
        selectionColor: Qt.alpha(search.cyan, 0.35)
        font.pixelSize: 12
        clip: true
        selectByMouse: true
        onActiveFocusChanged: if (activeFocus && search.query.trim().length > 0) popup.open()
        Keys.onDownPressed: search.currentIndex = Math.min(search.currentIndex + 1, search.results.length - 1)
        Keys.onUpPressed: search.currentIndex = Math.max(search.currentIndex - 1, 0)
        Keys.onReturnPressed: search.choose(search.currentIndex)
        Keys.onEnterPressed: search.choose(search.currentIndex)
        Keys.onEscapePressed: { search.query = ""; popup.close(); input.focus = false }
    }
    Rectangle {
        id: clearButton
        visible: search.query.length > 0
        parent: input.parent
        anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter
        width: 20; height: 20; radius: 10
        color: clearMouse.containsMouse ? Qt.alpha(search.cyan, 0.16) : "transparent"
        Text { anchors.centerIn: parent; text: "×"; color: search.pal.muted; font.pixelSize: 15 }
        MouseArea { id: clearMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { search.query = ""; input.forceActiveFocus() } }
    }

    Popup {
        id: popup
        objectName: "globalSearchPopup"
        parent: Overlay.overlay
        // La posición se calcula al abrir: la geometría ya es la definitiva.
        onAboutToShow: {
            const origin = search.mapToItem(popup.parent, 0, 0)
            popup.x = search.compact ? origin.x + search.width + 10 : origin.x - 2
            popup.y = search.compact ? origin.y - 6 : origin.y + search.height + 6
        }
        width: 420
        padding: 8
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onClosed: if (search.compact) search.query = ""
        background: Rectangle {
            radius: 14
            color: search.pal.panelOpaque
            border.width: 1
            border.color: Qt.alpha(search.cyan, 0.22)
        }
        contentItem: Column {
            spacing: 6
            // Solo en modo colapsado: el campo vive dentro de la paleta.
            Rectangle {
                id: paletteRow
                visible: search.compact
                width: parent.width; height: visible ? 36 : 0
                radius: 10
                color: Qt.alpha(search.cyan, 0.08)
                border.width: 1; border.color: Qt.alpha(search.cyan, 0.4)
                Glyph { x: 10; anchors.verticalCenter: parent.verticalCenter; width: 17; height: 17; kind: "search"; ink: search.cyan }
                Text {
                    visible: search.query.length === 0
                    x: 36; anchors.verticalCenter: parent.verticalCenter
                    text: "Buscar en CorePulse…"; color: search.pal.muted; opacity: 0.75; font.pixelSize: 12
                }
            }
            Text {
                visible: search.query.trim().length > 0
                width: parent.width; leftPadding: 6
                text: search.results.length > 0
                    ? (search.results.length === search.maxResults ? "Mejores resultados" : search.results.length + (search.results.length === 1 ? " resultado" : " resultados"))
                      + "  ·  ↑↓ para moverte · Enter para abrir"
                    : ""
                color: search.pal.muted; opacity: 0.8; font.pixelSize: 10
            }
            Text {
                visible: search.query.trim().length > 0 && search.results.length === 0
                width: parent.width; padding: 10; wrapMode: Text.WordWrap
                text: "Sin coincidencias para «" + search.query.trim() + "». Prueba con otra palabra, por ejemplo: energía, disco, temperatura o RAM."
                color: search.pal.muted; font.pixelSize: 12
            }
            Repeater {
                model: search.results
                delegate: Rectangle {
                    id: row
                    required property var modelData
                    required property int index
                    readonly property bool current: index === search.currentIndex
                    width: parent ? parent.width : 0
                    height: 48; radius: 10
                    color: current ? Qt.alpha(search.cyan, 0.12) : "transparent"
                    border.width: current ? 1 : 0
                    border.color: Qt.alpha(search.cyan, 0.18)
                    Glyph {
                        x: 10; anchors.verticalCenter: parent.verticalCenter; width: 22; height: 22
                        kind: row.modelData.i; ink: row.current ? search.cyan : search.pal.muted
                    }
                    Column {
                        x: 42; width: parent.width - 52
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text {
                            width: parent.width; elide: Text.ElideRight
                            textFormat: Text.StyledText
                            text: search.highlighted(row.modelData)
                            color: search.pal.ink; font.pixelSize: 12; font.bold: true
                        }
                        Text {
                            width: parent.width; elide: Text.ElideRight
                            text: row.modelData.s
                            color: search.pal.muted; font.pixelSize: 10
                        }
                    }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onEntered: search.currentIndex = row.index
                        onClicked: search.choose(row.index)
                    }
                }
            }
        }
    }
}
