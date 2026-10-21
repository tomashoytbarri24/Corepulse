import QtQuick

// REBUILD 143: material de tarjetas compartido, incluyendo Diagnóstico.
// Este componente no se utiliza para controles, barras ni modales: únicamente
// superficies informativas. La transparencia muestra el degradado real detrás.
Rectangle {
    id: glassPanel
    // Para tarjetas anidadas (p. ej. cada indicador del diagnóstico), se
    // evita superponer dos capas de vidrio normal y crear placas grisáceas.
    property bool nested: false
    radius: 16
    color: "transparent"
    gradient: Gradient {
        GradientStop { position: 0.00; color: Qt.alpha(themeManager.palette.bgStart, glassPanel.nested ? 0.015 : 0.07) }
        GradientStop { position: 0.48; color: Qt.alpha(themeManager.palette.bgMid, glassPanel.nested ? 0.015 : 0.065) }
        GradientStop { position: 1.00; color: Qt.alpha(themeManager.palette.bgEnd, glassPanel.nested ? 0.015 : 0.07) }
    }
    border.width: 1
    border.color: Qt.alpha(themeManager.palette.ink, glassPanel.nested ? 0.055 : 0.075)
}
