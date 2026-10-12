import QtQuick
import QtQuick.Layouts

// Resumen independiente, sin módulos históricos. Solo telemetría de telemetry.py.
Item {
    id: page
    readonly property var m: telemetry && telemetry.metrics ? telemetry.metrics : ({
        cpuPercent: null, gpuPercent: null, ramPercent: null, diskPercent: null,
        cpuName: "N/A", gpuName: "N/A", diskName: "N/A", diskLabel: "N/A",
        health: "N/A", alerts: "N/A", uptime: "N/A", coverage: "N/A"
    })
    signal openReadings()
    signal openComponent(string componentKind)
    signal restartRequested()
    readonly property color alertRed: "#F36B75"
    readonly property bool longSession: page.validNumber(page.m.uptimeSeconds) && page.m.uptimeSeconds >= 10 * 3600
    readonly property bool ramCritical: page.validNumber(page.m.ramPercent) && page.m.ramPercent >= 90
    function validNumber(v) { return typeof v === "number" && isFinite(v) }
    readonly property bool horizontal: width >= 810
    readonly property int tilesHeight: 152
    readonly property int panelsHeight: horizontal
        ? Math.max(335, height - tilesHeight - 18)
        : 690

    Flickable {
        id: scroll
        anchors.fill:parent
        contentWidth:width
        contentHeight: dashboard.implicitHeight
        boundsBehavior:Flickable.StopAtBounds
        clip:true

        ColumnLayout {
            id: dashboard
            width: scroll.width
            spacing:16

            GridLayout {
                id: primary
                Layout.fillWidth:true
                columns: page.horizontal ? 2 : 1
                columnSpacing:14
                rowSpacing:14

                Rectangle {
                    Layout.fillWidth:true;Layout.minimumWidth:0
                    Layout.preferredWidth: page.horizontal ? Math.max(1, (page.width - 14) * .70) : Math.max(1, page.width)
                    Layout.preferredHeight: page.horizontal ? page.panelsHeight : 385
                    Layout.row:0;Layout.column:0
                    radius:22;color:"#1A1C26";border.width:1;border.color:"#2C3040"
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:19;spacing:15
                        RowLayout {
                            Layout.fillWidth:true;spacing:12
                            Rectangle {
                                Layout.preferredHeight:52;Layout.preferredWidth:52
                                radius:15;color:"#17394E"
                                Glyph{anchors.centerIn:parent;width:30;height:30;kind:"chart";ink:"#19B9F5"}
                            }
                            ColumnLayout {
                                Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                                Text {
                                    text:"Rendimiento en tiempo real";color:"#F6F7FC";font.bold:true
                                    font.pixelSize:17;elide:Text.ElideRight;Layout.fillWidth:true
                                }
                                Text {
                                    text:"Muestras reales de CPU y GPU";color:"#9FABBE";font.pixelSize:11
                                    elide:Text.ElideRight;Layout.fillWidth:true
                                }
                            }
                            Rectangle {Layout.preferredWidth:8;Layout.preferredHeight:8;radius:4;color:"#16BEF5"}
                            Text{text:"CPU";color:"#B6C3D7";font.pixelSize:11}
                            Rectangle {Layout.preferredWidth:8;Layout.preferredHeight:8;radius:4;color:"#BB5DF0"}
                            Text{text:"GPU";color:"#B6C3D7";font.pixelSize:11}
                            Rectangle {
                                Layout.preferredWidth:94;Layout.preferredHeight:34
                                radius:12;color:"#232A3B"
                                Text { anchors.centerIn:parent;text:"Últimas 60";font.pixelSize:11;color:"#BECDE4" }
                            }
                        }
                        HistoryChart {
                            Layout.fillWidth:true
                            Layout.fillHeight:true
                            cpuValues:telemetry ? telemetry.cpuHistory : []
                            gpuValues:telemetry ? telemetry.gpuHistory : []
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth:true;Layout.minimumWidth:0
                    Layout.preferredWidth:page.horizontal ? Math.max(1,(page.width - 14) * .30) :Math.max(1,page.width)
                    Layout.preferredHeight:page.horizontal ? page.panelsHeight : 300
                    Layout.row:page.horizontal?0:1;Layout.column:page.horizontal?1:0
                    radius:22;color:"#1A1C26";border.width:1;border.color:"#2C3040"
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:18;spacing:13
                        RowLayout {
                            Layout.fillWidth:true;spacing:12
                            Rectangle {
                                Layout.preferredWidth:46;Layout.preferredHeight:46
                                radius:14;color:"#183B50"
                                Glyph{anchors.centerIn:parent;width:27;height:27;kind:"chart";ink:"#1DBAF4"}
                            }
                            ColumnLayout {
                                Layout.fillWidth:true;spacing:5
                                Text{text:"Estado del sistema";font.pixelSize:15;font.bold:true;color:"#F1F4FA"}
                                Text{text:"Uso actual de los componentes";font.pixelSize:10;color:"#A6B1C4"}
                            }
                        }
                        Item { Layout.preferredHeight:1 }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"CPU";kind:"cpu";interactive:true
                            onActivated:page.openComponent("cpu")
                            value:page.m.cpuPercent;accent:"#18B9F7"
                            hardwareName:page.m.cpuName
                            sourceHint:"Frecuencia: " + (page.m.cpuClockSource || "N/A")
                                + "\nTemperatura: " + (page.m.cpuTempSource || "N/A")
                            secondaryPrefix:page.validNumber(page.m.cpuGHz)
                                ? page.m.cpuGHz.toFixed(2)+" GHz"
                                    + (page.m.cpuClockSource && page.m.cpuClockSource.indexOf("Estimación")===0 ? " (est.)" : "")
                                : "Frecuencia N/A"
                            temperature: page.m.cpuTemp
                            hotThreshold: 90
                        }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"GPU";kind:"gpu";interactive:true
                            onActivated:page.openComponent("gpu")
                            value:page.m.gpuPercent;accent:"#BA5AEC"
                            hardwareName:page.m.gpuName
                            sourceHint:page.m.gpuUtilSource !== "N/A" ? page.m.gpuUtilSource
                                : "Porcentaje de GPU NVIDIA no disponible"
                            temperature: page.m.gpuTemp
                            hotThreshold: 85
                            secondary:page.validNumber(page.m.gpuTemp) ? page.m.gpuTemp.toFixed(1)+" °C" : "Temperatura N/A"
                        }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"RAM";kind:"ram";interactive:true
                            onActivated:page.openComponent("ram")
                            value:page.m.ramPercent;accent:page.ramCritical ? page.alertRed : "#19B9F4"
                            critical:page.ramCritical
                            secondary:page.validNumber(page.m.ramUsed)&&page.validNumber(page.m.ramTotal)
                                ? page.m.ramUsed.toFixed(1)+" GB / "+page.m.ramTotal.toFixed(1)+" GB" : "N/A"
                        }
                        MetricLine {
                            Layout.fillWidth:true;Layout.fillHeight:true
                            title:"SSD";kind:"storage";interactive:true
                            onActivated:page.openComponent("storage")
                            value:page.m.diskPercent;accent:"#BA5AEC"
                            hardwareName:page.m.diskName && page.m.diskName!=="N/A"
                                ? page.m.diskName : "Modelo N/A ("+page.m.diskLabel+")"
                            secondary:page.validNumber(page.m.diskUsed)&&page.validNumber(page.m.diskTotal)
                                ? page.m.diskUsed.toFixed(1)+" GB / "+page.m.diskTotal.toFixed(1)+" GB" : "N/A"
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth:true
                columns:page.width >= 810 ? 4 : 2
                columnSpacing:14;rowSpacing:14
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Salud del sistema";content:page.m.health;detail:"Diagnóstico pendiente"
                    kind:"health";accent:"#17B9FA"
                }
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Alertas";content:page.m.alerts;detail:"Módulo pendiente"
                    kind:"alerts";accent:"#B752EB"
                }
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Tiempo de sesión";content:page.m.uptime;detail:"Tiempo activo del sistema"
                    kind:"clock";accent:page.longSession ? page.alertRed : "#17B9FA"
                    restartVisible:page.longSession
                    onRestartRequested:page.restartRequested()
                }
                StatTile {
                    Layout.fillWidth:true;Layout.minimumWidth:0;Layout.preferredHeight:page.tilesHeight
                    title:"Lecturas disponibles";content:page.m.coverage;detail:page.m.coverageDetail || "Ver las 7 lecturas"
                    kind:"trace";accent:"#B752EB";interactive:true
                    onActivated:page.openReadings()
                }
            }
        }
    }
}
