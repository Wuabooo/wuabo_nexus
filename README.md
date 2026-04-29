# 🏎️ WUABO Nexus Bridge: The Ultimate GTA V Asset Pipeline

**WUABO Nexus** is a professional-grade Blender addon designed to bridge the gap between Grand Theft Auto V assets and the Blender workspace. It provides a seamless, high-performance workflow for developers and 3D artists, powered by an integrated **CodeWalker API** backend.

---

## ✨ Key Features

### 🛠️ Integrated API Lifecycle Management
* **One-Click Start/Stop**: Launch and terminate the `CodeWalker.API` directly from the Blender sidebar.
* **Auto-Elevation**: The addon handles Windows UAC elevation automatically, ensuring the API has full access to GTA V archives without needing to run Blender as Administrator.

### 🔄 Intelligent Configuration Sync
* **Zero-Touch Setup**: The addon automatically reads settings from `userconfig.json` on startup.
* **Auto-Sync**: Settings like GTA V paths, temporary folders, and Mod support are synchronized with the backend automatically upon connection.
* **Minimalist UI**: Dynamic interface that hides complex settings when not needed, keeping your workspace clean.

### 🔍 Advanced Asset Management
* **Global Search**: Search through thousands of GTA V assets (YFT, YDR, YTD) in real-time.
* **Persistent Cache**: Asset indexing is stored in `~/Documents/wuabo_nexus/`, ensuring lightning-fast search results that persist across Blender updates.
* **Mod Support**: Fully compatible with the `mods` folder, allowing you to access custom game content easily.

### 📥 Optimized Import Pipeline
* **"Static" Mode**: Automatically strips collisions, armatures, and unnecessary data for a clean mesh import.
* **Texture Extraction**: Automatic extraction and assignment of textures (DDS/PNG) to Blender materials.
* **Asset Browser Integration**: Option to automatically mark imported objects as assets for use in the Blender Asset Browser.
* **Clean Workflow**: Automatically cleans up temporary files after import to save disk space.

---

## 🚀 Installation & Setup

1. **Install the Addon**: Zip the `wuabo_nexus` folder and install it in Blender as a standard extension/addon.
2. **Setup the Binaries**:
   * Create a `bin` folder inside the addon directory.
   * Place the `CodeWalker.API.exe` and all its dependencies inside the `bin` folder.
3. **Configure Paths**: 
   * Open `bin/Config/userconfig.json` and set your `GTAPath` and `CodewalkerOutputDir`.
   * Alternatively, start the API and configure it directly through the **Bridge Configuration** panel in Blender.

---

## 🛠️ Tech Stack

* **Frontend**: Blender Python API (BPY)
* **Backend**: .NET 9 (C#) powered by CodeWalker.Core
* **Communication**: REST API (HTTP) with automatic process management

---

## 🎨 Design Philosophy

WUABO Nexus follows a **Premium & Minimalist** design. We believe that professional tools should stay out of your way until you need them. The interface is state-aware, transitioning from a simple "Start" button to a full-featured asset explorer only when the bridge is active.

---

## ⚖️ License & Credits

* **Developer**: WUABO Team
* **Core Engine**: Powered by CodeWalker (Credits to dexyfex)
* **Purpose**: Designed for premium GTA V asset stores and high-end modding workflows.

---
<p align="center">
  <b>Developed with ❤️ for the GTA V Modding Community</b>
</p>
