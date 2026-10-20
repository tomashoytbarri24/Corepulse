<!-- ===================== CABECERA ===================== -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:1f6feb,100:00d4ff&height=190&section=header&text=CorePulse&fontSize=70&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=El%20pulso%20real%20de%20tu%20PC%20%F0%9F%92%93&descAlignY=60&descSize=20" alt="CorePulse">
</p>

<p align="center">
  <a href="#"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=2800&pause=900&color=00D4FF&center=true&vCenter=true&width=620&lines=%F0%9F%A9%BA+Diagn%C3%B3stico+con+datos+reales;%F0%9F%94%84+Optimizaciones+que+se+pueden+deshacer;%F0%9F%A4%96+Una+IA+que+no+inventa+nada;%F0%9F%8E%AE+FPS+reales+o+N%2FA%2C+sin+trampa" alt="Typing SVG"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Qt-PySide6%20%2F%20QML-41CD52?style=for-the-badge&logo=qt&logoColor=white">
  <img src="https://img.shields.io/badge/Cloudflare-Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white">
  <img src="https://img.shields.io/badge/versi%C3%B3n-REBUILD%20146-8A2BE2?style=for-the-badge">
</p>

<p align="center">
  <img src="docs/corepulse_temas.gif" width="820" alt="CorePulse cambiando de tema">
</p>

---

## 🤔 ¿Qué es CorePulse?

¿Alguna vez abriste **cinco programas distintos** solo para saber por qué tu PC anda lenta? 🐌
Uno para temperaturas, otro para el disco, otro para los FPS, otro para limpiar...

**CorePulse junta todo en una sola app** 🧩 y además te lo explica en español, sin humo:

> 💡 Si un sensor no existe en tu equipo, CorePulse te muestra **`N/A`**.
> Nunca vas a ver un número inventado. **Dato real o nada.**

---

## ✨ Lo que trae

| | Módulo | Qué hace |
|:-:|---|---|
| 📊 | **Resumen en vivo** | CPU, GPU (🟢 NVIDIA · 🔴 AMD · 🔵 Intel), RAM y SSD en tiempo real, con el logo de cada fabricante |
| 🩺 | **Centro de Salud** | Revisa Windows, repara con **DISM/SFC**, lee **SMART/NVMe** y te dice cuánto se gastó tu disco |
| 🔍 | **Diagnóstico** | Un botón ❤️‍🔥 que late mientras analiza y termina en un **PDF** listo para compartir |
| 🤖 | **CorePulse AI** | Te explica el diagnóstico con **fuentes oficiales** (Microsoft, Intel, AMD, NVIDIA) y compara la salud de tu PC **entre arranques** |
| ⚙️ | **Tweaks de Windows 11** | 78 optimizaciones que guardan **cómo estaba todo antes**: un clic y vuelve atrás ↩️ |
| 🧹 | **Limpieza** | Temporales, caché, RAM, duplicados y Papelera, siempre con confirmación |
| 🎮 | **Gaming** | Overlay con **FPS reales** (RTSS), Game Boost reversible y plan de energía automático por juego |
| 🏙️ | **Benchmark GPU** | Una ciudad de neón en **DirectX 11** que exprime tu tarjeta y guarda el historial para comparar |
| 📈 | **Tendencias** | Tu uso agrupado por **sesión de Windows**, para ver si el problema se repite |
| 🌐 | **Red avanzada** | Adaptadores, tráfico y Speedtest, con tu IP escondida detrás de un 👁️ |
| 🎨 | **Temas** | 15 paletas con estilo **Liquid Glass** 🫧 |

---

## 🛡️ Las 3 reglas de oro

```text
1️⃣  Dato real o N/A          → nada se estima, nada se inventa
2️⃣  Todo se puede deshacer    → snapshot ➜ verificación ➜ restaurar
3️⃣  Nada sale sin permiso     → compartir hardware o historial viene APAGADO
```

<details>
<summary>🔐 <b>¿Qué datos salen de mi PC?</b> (clic para ver)</summary>

<br>

| Dato | ¿Sale del equipo? |
|---|---|
| Lecturas de sensores, historial, respaldos de tweaks | ❌ Nunca: quedan en `%LOCALAPPDATA%\CorePulse` |
| Preguntas que escribís a CorePulse AI | ✅ Solo las que vos enviás |
| Resumen de hardware para la IA | ⚪ Solo si activás ese permiso |
| Resumen de Tendencias para la IA | ⚪ Solo si activás ese otro permiso |
| IP, MAC, SSID, ubicación | ❌ Nunca |

</details>

---

## 🚀 Probarlo en 2 pasos

```bash
# 1️⃣ Entrá a la carpeta de la versión actual
cd CorePulse_REBUILD_146

# 2️⃣ Doble clic o desde la terminal
Iniciar_CorePulse.bat
```

> ☕ La primera vez tarda un poco: prepara su propio entorno de Python e instala lo que necesita.
> Requisitos: **Windows 10/11 de 64 bits** y **Python 3.12+**.

¿Querés saber cómo está armado por dentro? 👉 **[Guía técnica](docs/TECNICO.md)**

---

## 👥 El equipo

<table align="center">
  <tr>
    <td align="center" width="200">
      <a href="https://github.com/tomashoytbarri24"><img src="https://github.com/tomashoytbarri24.png" width="90" style="border-radius:50%"><br><b>Tomás Hoyt</b></a><br>
      🏗️ Arquitectura · 📡 Telemetría · 🤖 IA
    </td>
    <td align="center" width="200">
      <a href="https://github.com/agtttttttttttt"><img src="https://github.com/agtttttttttttt.png" width="90" style="border-radius:50%"><br><b>Agustín Valdés</b></a><br>
      🎨 Interfaz · 🏙️ Benchmark · 🧪 Pruebas
    </td>
    <td align="center" width="200">
      <a href="https://github.com/maxicpa"><img src="https://github.com/maxicpa.png" width="90" style="border-radius:50%"><br><b>Maximiliano Carrasco</b></a><br>
      ✅ Validación · 📝 Documentación
    </td>
  </tr>
</table>

<p align="center">
  🎓 Proyecto <b>Capstone (PTY4614)</b> · Ingeniería en Informática · <b>Duoc UC</b> Valparaíso · Equipo 14
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:00d4ff,50:1f6feb,100:0f2027&height=110&section=footer" alt="">
</p>
