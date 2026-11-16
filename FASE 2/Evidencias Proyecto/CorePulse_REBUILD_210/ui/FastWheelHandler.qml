import QtQuick

WheelHandler {
    id: handler
    required property var scrollTarget
    property real wheelStep: 112
    property real pixelMultiplier: 1.8
    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    target: null

    onWheel: function(event) {
        const view = handler.scrollTarget
        if (!view || typeof view.contentY !== "number") return
        const delta = event.pixelDelta.y !== 0
            ? event.pixelDelta.y * handler.pixelMultiplier
            : event.angleDelta.y / 120 * handler.wheelStep
        if (!isFinite(delta) || delta === 0) return
        const limit = Math.max(0, view.contentHeight - view.height)
        const next = Math.max(0, Math.min(limit, view.contentY - delta))
        if (Math.abs(next - view.contentY) < 0.01) {
            event.accepted = false
            return
        }
        view.contentY = next
        event.accepted = true
    }
}
