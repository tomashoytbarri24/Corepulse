import QtQuick
import QtQuick.Window

Window {
    id: splash
    width:460
    height:258
    flags:Qt.SplashScreen | Qt.FramelessWindowHint
    color:"transparent"
    title:"CorePulse · Iniciando"
    x:initialWindowX + (initialWindowWidth-width)/2
    y:initialWindowY + (initialWindowHeight-height)/2
    Rectangle {
        anchors.fill:parent
        radius:26
        color:"#111822"
        border.color:"#294252"
        border.width:1
        Rectangle {
            x:1; y:1; width:parent.width-2; height:parent.height-2; radius:25
            gradient:Gradient {
                GradientStop { position:0; color:"#172631" }
                GradientStop { position:0.65; color:"#111822" }
                GradientStop { position:1; color:"#171626" }
            }
        }
        Row {
            anchors.horizontalCenter:parent.horizontalCenter
            y:52; spacing:0
            Text { text:"Core"; color:"#f4f8fc"; font.pixelSize:40; font.bold:true }
            Text { text:"Pulse"; color:"#24b8ed"; font.pixelSize:40; font.bold:true }
        }
        Text {
            anchors.horizontalCenter:parent.horizontalCenter
            y:116; text:"Preparando las lecturas de tu equipo"
            color:"#a9bcca"; font.pixelSize:14
        }
        Rectangle {
            anchors.horizontalCenter:parent.horizontalCenter
            y:172; width:276; height:3; radius:2; color:"#293843"; clip:true
            Rectangle {
                id:glow
                width:90; height:3; radius:2; color:"#3bd3c5"
                SequentialAnimation on x {
                    running:splash.visible; loops:Animation.Infinite
                    NumberAnimation { from:-90; to:276; duration:1050; easing.type:Easing.InOutSine }
                }
            }
        }
        Text {
            anchors.horizontalCenter:parent.horizontalCenter
            y:207; text:"COREPULSE"; color:"#5e7889"; font.pixelSize:10; font.letterSpacing:3
        }
    }
}
