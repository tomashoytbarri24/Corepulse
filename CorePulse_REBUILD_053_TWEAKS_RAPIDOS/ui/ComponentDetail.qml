import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

// Una sola pantalla reutilizable para CPU, GPU y RAM.
// Primero lo comprensible; los detalles técnicos se muestran solo al solicitarlos.
Item {
    id: page
    property string componentKind: "cpu"
    property bool advancedOpen: false
    signal goBack()

    readonly property var m: telemetry && telemetry.metrics ? telemetry.metrics : ({})
    readonly property color accent: componentKind === "gpu" ? "#BA5AEC" : "#19B9F4"
    readonly property string heading: componentKind === "cpu" ? "Procesador" :
                                      componentKind === "gpu" ? "Tarjeta gráfica" : "Memoria RAM"
    readonly property string iconName: componentKind === "cpu" ? "cpu" : componentKind === "gpu" ? "gpu" : "ram"
    readonly property string identity: componentKind === "cpu" ? readable(m.cpuName) :
                                       componentKind === "gpu" ? readable(m.gpuName) : "Memoria del equipo"
    readonly property string introduction: componentKind === "cpu"
        ? "El procesador ejecuta los programas y tareas de tu computador."
        : componentKind === "gpu"
        ? "La tarjeta gráfica se encarga de los gráficos, juegos y tareas visuales."
        : "La RAM mantiene disponibles las aplicaciones y datos que estás usando."
    readonly property string guidance: componentKind === "cpu"
        ? "El uso y la velocidad cambian según las tareas que realizas. Un porcentaje alto no significa por sí solo que el procesador tenga un problema."
        : componentKind === "gpu"
        ? "El porcentaje corresponde a la GPU que informa NVIDIA. Puede ser distinto al Administrador de tareas porque no siempre miden los mismos motores gráficos."
        : "Memoria disponible incluye la que Windows puede liberar rápidamente. La cantidad en uso no significa que la RAM esté dañada."

    function valid(value) { return typeof value === "number" && isFinite(value) }
    function readable(value) {
        if (value === undefined || value === null || String(value).trim() === "" ||
            String(value).toLowerCase() === "undefined") return "N/A"
        return String(value)
    }
    function number(value, unit, digits) {
        return valid(value) ? Number(value).toFixed(digits === undefined ? 1 : digits) + (unit || "") : "N/A"
    }
    function integer(value) { return valid(value) ? String(Math.round(value)) : "N/A" }
    function measuredClock() {
        return number(m.cpuGHz, " GHz", 2) +
            (valid(m.cpuGHz) && m.cpuClockSource && m.cpuClockSource.indexOf("Estimación") === 0 ? " (est.)" : "")
    }
    function detectedCount(items) {
        return !m.inventoryReady ? "Evaluando…" : (items && items.length ? String(items.length) : "N/A")
    }

    readonly property var quickFacts: {
        if (componentKind === "cpu") return [
            {label:"Uso actual", value:number(m.cpuPercent,"%"), tip:"Qué parte del procesador se utiliza ahora."},
            {label:"Temperatura", value:number(m.cpuTemp," °C"), tip:"Calor detectado por un sensor del procesador."},
            {label:"Velocidad", value:measuredClock(), tip:"Frecuencia actual medida o estimada con datos de Windows."},
            {label:"Potencia", value:number(m.cpuPackagePower," W"), tip:"Energía eléctrica medida por un sensor CPU; no siempre está disponible."}
        ]
        if (componentKind === "gpu") return [
            {label:"Uso actual", value:number(m.gpuPercent,"%"), tip:"Actividad del núcleo gráfico NVIDIA."},
            {label:"Temperatura", value:number(m.gpuTemp," °C"), tip:"Calor informado por la GPU."},
            {label:"Memoria ocupada", value:number(m.gpuVramUsed," GiB",2), tip:"Memoria de video utilizada actualmente."},
            {label:"Memoria total", value:number(m.gpuVramTotal," GiB",2), tip:"Capacidad de memoria de video informada por la GPU."}
        ]
        return [
            {label:"Uso actual", value:number(m.ramPercent,"%"), tip:"Porción de la memoria utilizable que está ocupada."},
            {label:"En uso", value:number(m.ramUsed," GiB"), tip:"Memoria que Windows no considera disponible ahora."},
            {label:"Disponible", value:number(m.ramAvailable," GiB"), tip:"Memoria que Windows puede entregar a nuevas aplicaciones."},
            {label:"Capacidad", value:number(m.ramTotal," GiB"), tip:"Memoria física utilizable publicada por Windows."}
        ]
    }

    readonly property var keyFacts: {
        if (componentKind === "cpu") return [
            {label:"Modelo", value:readable(m.cpuName), help:"Identifica exactamente qué procesador tienes."},
            {label:"Fabricante", value:readable(m.cpuManufacturer), help:"Empresa que fabricó el procesador."},
            {label:"Núcleos", value:integer(m.cpuPhysicalCores), help:"Unidades físicas que pueden realizar tareas de procesamiento."},
            {label:"Hilos de trabajo", value:integer(m.cpuLogicalThreads), help:"Tareas que el procesador puede atender en paralelo."},
            {label:"Velocidad de referencia", value:number(m.cpuBaseGHz," GHz",2), help:"Frecuencia nominal, no necesariamente la velocidad de este instante."},
            {label:"Arquitectura", value:readable(m.cpuArchitecture), help:"Tipo de arquitectura utilizado por el sistema."}
        ]
        if (componentKind === "gpu") return [
            {label:"Modelo", value:readable(m.gpuName), help:"Tarjeta gráfica que estamos monitorizando."},
            {label:"Memoria de video", value:number(m.gpuVramTotal," GiB",2), help:"Memoria propia para texturas y otras tareas gráficas."},
            {label:"Controlador", value:readable(m.gpuDriver), help:"Versión que Windows asocia a esta tarjeta."},
            {label:"Gráficos detectados", value:detectedCount(m.gpuAdapters), help:"Cantidad de adaptadores publicados por Windows; pueden existir gráficos integrados."}
        ]
        return [
            {label:"Memoria instalada utilizable", value:number(m.ramTotal," GiB"), help:"Cantidad disponible para el sistema operativo."},
            {label:"Memoria usada", value:number(m.ramUsed," GiB"), help:"Parte de la RAM actualmente ocupada."},
            {label:"Memoria libre o reutilizable", value:number(m.ramAvailable," GiB"), help:"Memoria disponible para abrir programas."},
            {label:"Módulos encontrados", value:detectedCount(m.ramModules), help:"Cantidad de módulos físicos que informa Windows."}
        ]
    }
    readonly property var technicalFacts: {
        if (componentKind === "cpu") return [
            {label:"Socket del procesador",value:readable(m.cpuSocket)},
            {label:"Reloj de referencia Windows",value:number(m.cpuBaseGHz," GHz",2)},
            {label:"Fuente de frecuencia",value:readable(m.cpuClockSource)},
            {label:"Fuente de temperatura",value:readable(m.cpuTempSource)},
            {label:"Potencia del procesador",value:number(m.cpuPackagePower," W")},
            {label:"Origen de sensores adicionales",value:readable(m.cpuDetailSource)}
        ]
        if (componentKind === "gpu") return [
            {label:"Fuente de utilización",value:readable(m.gpuUtilSource)},
            {label:"Controlador gráfico Windows",value:readable(m.gpuDriver)},
            {label:"VRAM utilizada",value:number(m.gpuVramUsed," GiB",2)},
            {label:"VRAM total",value:number(m.gpuVramTotal," GiB",2)}
        ]
        return [
            {label:"Medición de uso",value:"Windows / psutil (total menos disponible)"},
            {label:"Origen de módulos",value:"Windows / SMBIOS (CIM)"},
            {label:"Módulos detectados",value:detectedCount(m.ramModules)}
        ]
    }

    Rectangle {
        anchors.fill: parent
        color: "#1A1C26"
        radius: 22
        border.width: 1
        border.color: "#2B3040"
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Math.min(22, Math.max(12, parent.width * 0.027))
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Rectangle {
                Layout.preferredWidth: 44; Layout.preferredHeight: 44
                radius: 13; color: Qt.alpha(page.accent, 0.16)
                Glyph { anchors.centerIn: parent; width: 25; height: 25; kind: page.iconName; ink: page.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 4
                Text { Layout.fillWidth:true; text:page.heading; color:"#F4F5FA"; font.pixelSize:19; font.bold:true; elide:Text.ElideRight }
                Text { Layout.fillWidth:true; text:page.identity; color:"#B4BED0"; font.pixelSize:11; elide:Text.ElideRight }
            }
            Rectangle {
                Layout.preferredWidth: 78; Layout.preferredHeight: 35
                radius: 10; color: backMouse.containsMouse ? "#344158" : "#22293A"
                Text { anchors.centerIn:parent; text:"Volver"; color:"#F4F5FA"; font.pixelSize:12; font.bold:true }
                MouseArea { id:backMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; onClicked:page.goBack() }
            }
        }
        // Mantener la barra fuera del contentItem: un Flickable reubica a sus hijos visuales.
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            Flickable {
                id: scroller
                anchors.fill: parent
                contentWidth: width; contentHeight: content.implicitHeight + 16
                clip: true; boundsBehavior: Flickable.StopAtBounds
                ColumnLayout {
                    id: content
                    width: Math.max(0, scroller.width - 18)
                    spacing: 13

                    Text {
                        Layout.fillWidth: true
                        text: page.introduction
                        color: "#ACB9CD"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                    Text { text:"AHORA MISMO"; color:"#9DADCA"; font.pixelSize:10; font.bold:true; Layout.topMargin:4 }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: content.width >= 650 ? 4 : content.width >= 350 ? 2 : 1
                        columnSpacing: 10; rowSpacing: 10
                        Repeater {
                            model:page.quickFacts
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth:true; Layout.minimumWidth:0
                                Layout.preferredHeight: 112
                                radius: 14; color:"#202431"; border.width:1; border.color:"#303849"
                                ColumnLayout {
                                    anchors.fill:parent; anchors.margins:12; spacing:4
                                    Text { Layout.fillWidth:true; text:modelData.label; color:"#A9B7CC"; font.pixelSize:11; font.bold:true; elide:Text.ElideRight }
                                    Text {
                                        Layout.fillWidth:true; text:modelData.value; color:page.accent
                                        font.pixelSize:content.width >= 650 ? 19 : 20; font.bold:true
                                        elide:Text.ElideRight
                                        ToolTip.visible:quickHover.containsMouse && truncated
                                        ToolTip.text:modelData.value
                                    }
                                    Text {
                                        Layout.fillWidth:true; text:modelData.tip
                                        color:"#8D9AAF"; font.pixelSize:10
                                        wrapMode:Text.WordWrap; maximumLineCount:2; elide:Text.ElideRight
                                    }
                                }
                                MouseArea { id:quickHover; anchors.fill:parent; hoverEnabled:true; acceptedButtons:Qt.NoButton }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth:true
                        Layout.preferredHeight: infoContent.implicitHeight + 24
                        radius:13; color:"#1B2937"; border.width:1; border.color:"#2D4154"
                        ColumnLayout {
                            id:infoContent
                            anchors.left:parent.left; anchors.right:parent.right; anchors.top:parent.top
                            anchors.margins:12; spacing:6
                            Text { text:"CÓMO INTERPRETARLO"; color:"#68C7F2"; font.pixelSize:10; font.bold:true }
                            Text { Layout.fillWidth:true; text:page.guidance; color:"#B2C6D7"; font.pixelSize:11; wrapMode:Text.WordWrap }
                        }
                    }
                    Text {
                        text: page.componentKind === "cpu" ? "CONOCE TU PROCESADOR" :
                              page.componentKind === "gpu" ? "CONOCE TU TARJETA GRÁFICA" : "CONOCE TU MEMORIA RAM"
                        color:"#B2BCD0"; font.bold:true; font.pixelSize:11; Layout.topMargin:4
                    }
                    GridLayout {
                        Layout.fillWidth:true
                        columns:content.width >= 590 ? 2 : 1
                        columnSpacing:10; rowSpacing:10
                        Repeater {
                            model:page.keyFacts
                            delegate:Rectangle {
                                required property var modelData
                                Layout.fillWidth:true; Layout.minimumWidth:0
                                Layout.preferredHeight:79
                                radius:12; color:"#202430"; border.width:1; border.color:"#303647"
                                ColumnLayout {
                                    anchors.fill:parent; anchors.margins:11; spacing:3
                                    RowLayout {
                                        Layout.fillWidth:true; spacing:8
                                        Text { Layout.fillWidth:true; text:modelData.label; color:"#A5B4C9"; font.pixelSize:10; elide:Text.ElideRight }
                                        Text {
                                            Layout.fillWidth:true; Layout.maximumWidth:Math.max(82,parent.width*.64)
                                            text:modelData.value; color:"#F0F3FA"; font.pixelSize:12; font.bold:true
                                            horizontalAlignment:Text.AlignRight; elide:Text.ElideRight
                                            ToolTip.visible: factHover.containsMouse && truncated
                                            ToolTip.text: modelData.value
                                        }
                                    }
                                    Text { Layout.fillWidth:true; text:modelData.help; color:"#8495AD"; font.pixelSize:10; wrapMode:Text.WordWrap; maximumLineCount:2; elide:Text.ElideRight }
                                }
                                MouseArea {id:factHover; anchors.fill:parent; hoverEnabled:true; acceptedButtons:Qt.NoButton}
                            }
                        }
                    }
                    // Información adicional solo donde el equipo publique inventario real.
                    Text {
                        visible:page.componentKind === "ram"
                        text:"TUS MÓDULOS DE RAM" + (!page.m.inventoryReady ? " · Evaluando…" : "")
                        color:"#B2BCD0"; font.bold:true; font.pixelSize:11; Layout.topMargin:2
                    }
                    Repeater {
                        model:page.componentKind === "ram" ? (page.m.ramModules || []) : []
                        delegate:Rectangle {
                            required property var modelData
                            Layout.fillWidth:true; Layout.preferredHeight:82
                            radius:12; color:"#202430"; border.width:1; border.color:"#313746"
                            ColumnLayout {
                                anchors.fill:parent; anchors.margins:11; spacing:5
                                Text {Layout.fillWidth:true; text:page.readable(modelData.slot) + "  ·  " + page.number(modelData.capacityGB," GiB"); color:"#EFF2FB"; font.pixelSize:12; font.bold:true; elide:Text.ElideRight}
                                Text {Layout.fillWidth:true; text:page.readable(modelData.type) + " · " + page.number(modelData.speedMHz," MHz",0) + " · " + page.readable(modelData.manufacturer); color:"#A5B4CA"; font.pixelSize:11; elide:Text.ElideRight}
                                Text {Layout.fillWidth:true; text:"Referencia: " + page.readable(modelData.partNumber); color:"#8A9AB0"; font.pixelSize:10; elide:Text.ElideRight}
                            }
                        }
                    }
                    Text {
                        visible:page.componentKind === "gpu"
                        text:"GRÁFICOS DETECTADOS" + (!page.m.inventoryReady ? " · Evaluando…" : "")
                        color:"#B2BCD0"; font.bold:true; font.pixelSize:11; Layout.topMargin:2
                    }
                    Repeater {
                        model:page.componentKind === "gpu" ? (page.m.gpuAdapters || []) : []
                        delegate:Rectangle {
                            required property var modelData
                            Layout.fillWidth:true; Layout.preferredHeight:55
                            radius:12; color:"#202430"; border.width:1; border.color:"#313746"
                            ColumnLayout {
                                anchors.fill:parent; anchors.margins:10; spacing:3
                                Text {Layout.fillWidth:true; text:page.readable(modelData.name); color:"#ECF1FA"; font.pixelSize:12; font.bold:true; elide:Text.ElideRight}
                                Text {Layout.fillWidth:true; text:"Controlador: " + page.readable(modelData.driver); color:"#A8B5C9"; font.pixelSize:10; elide:Text.ElideRight}
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth:true; Layout.preferredHeight:45
                        radius:12; color:advancedMouse.containsMouse?"#2C3545":"#232A38"
                        border.width:1; border.color:page.advancedOpen?"#43617A":"#354256"
                        RowLayout {
                            anchors.fill:parent; anchors.leftMargin:13; anchors.rightMargin:13
                            spacing:9
                            Text {text:page.advancedOpen?"Ocultar detalles avanzados":"Ver detalles avanzados"; color:"#E2EBF8"; font.pixelSize:12; font.bold:true; Layout.fillWidth:true}
                            Text {text:page.advancedOpen?"⌃":"⌄"; color:"#A8C8E5"; font.pixelSize:18}
                        }
                        MouseArea {id:advancedMouse; anchors.fill:parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor; onClicked:page.advancedOpen=!page.advancedOpen}
                    }
                    ColumnLayout {
                        visible:page.advancedOpen
                        Layout.fillWidth:true
                        spacing:8
                        Repeater {
                            model:page.technicalFacts
                            delegate:Rectangle {
                                required property var modelData
                                Layout.fillWidth:true; Layout.preferredHeight:52
                                radius:9; color:"#202430"
                                RowLayout {
                                    anchors.fill:parent; anchors.leftMargin:11; anchors.rightMargin:11; spacing:10
                                    Text {text:modelData.label; color:"#AAB7CC"; font.pixelSize:10; Layout.preferredWidth:Math.max(110,parent.width*.34); elide:Text.ElideRight}
                                    Text {
                                        Layout.fillWidth:true; text:modelData.value; color:"#E8EEF7"; font.pixelSize:11
                                        horizontalAlignment:Text.AlignRight; elide:Text.ElideRight
                                        ToolTip.visible:techMouse.containsMouse && truncated
                                        ToolTip.text:modelData.value
                                    }
                                }
                                MouseArea {id:techMouse; anchors.fill:parent; hoverEnabled:true; acceptedButtons:Qt.NoButton}
                            }
                        }
                        Text {
                            visible:page.componentKind === "cpu"
                            text:"TEMPERATURAS POR NÚCLEO"; color:"#B2BCD0"; font.bold:true; font.pixelSize:10; Layout.topMargin:5
                        }
                        Text {
                            visible:page.componentKind === "cpu" && (!page.m.cpuCoreTemps || page.m.cpuCoreTemps.length === 0)
                            text:"N/A · El monitor no publicó sensores individuales."; color:"#9AA7BA"; font.pixelSize:11
                        }
                        Repeater {
                            model:page.componentKind === "cpu" ? (page.m.cpuCoreTemps || []) : []
                            delegate:Rectangle {
                                required property var modelData
                                Layout.fillWidth:true; Layout.preferredHeight:37
                                radius:9; color:"#202430"
                                RowLayout {
                                    anchors.fill:parent; anchors.leftMargin:11; anchors.rightMargin:11
                                    Text {Layout.fillWidth:true; text:page.readable(modelData.name); color:"#AAB7CC"; font.pixelSize:11; elide:Text.ElideRight}
                                    Text {text:page.number(modelData.value," °C"); color:page.accent; font.pixelSize:12; font.bold:true}
                                }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth:true; wrapMode:Text.WordWrap
                        text:"Los valores provienen de Windows y de sensores compatibles. N/A significa que esa lectura no está disponible o no se pudo verificar. No se realizan cambios en el equipo."
                        color:"#8293AB"; font.pixelSize:10; Layout.bottomMargin:12
                    }
                }
            }
            ThinScroll {
                target: scroller
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                anchors.rightMargin: 2
            }
        }
    }
}
