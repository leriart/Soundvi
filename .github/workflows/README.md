# 🚀 Soundvi CI/CD Workflows

## ⚠️ **IMPORTANTE: Solo un workflow activo**

**Todos los workflows excepto MASTER_BUILD.yml están DESHABILITADOS (.disabled)**
Esto evita confusiones y errores de ejecución.

---

## 🎯 **WORKFLOWS ACTIVOS:**

### **1. MASTER_BUILD.yml (Linux/macOS)**
**Para builds en Linux y macOS.**

#### **Características:**
- ✅ **Todo en uno**: Build + Test + Release
- ✅ **Virtual environment** automático (evita PEP 668)
- ✅ **Node.js 24** compatible (sin warnings)
- ✅ **Debugging** extensivo
- ✅ **Summary** automático

#### **Cómo usar:**
1. Ve a **Actions** → **MASTER BUILD - Soundvi CI/CD**
2. Configura:
   - **Action**: `build` (solo build) o `build-and-release` (build + release)
   - **Platform**: `linux` o `macos` (NO windows)
   - **Version**: `4.8.0` (o la que quieras)
   - **Mode**: `onefile` (ejecutable único) o `onedir` (directorio)
3. **¡Ejecuta!**

---

### **2. windows-build.yml (Windows)**
**Workflow específico para Windows con PowerShell nativo.**

#### **¿Por qué separado?**
- PowerShell tiene sintaxis diferente a bash
- Problemas con `if [ ... ]` en PowerShell
- Mejor compatibilidad con Windows

#### **Cómo usar:**
1. Ve a **Actions** → **Windows Build**
2. Configura:
   - **Version**: `4.8.0` (o la que quieras)
   - **Mode**: `onefile` (ejecutable único) o `onedir` (directorio)
3. **¡Ejecuta!**

---

## ⚠️ Workflows Deshabilitados (NO USAR)

**Todos estos están deshabilitados (.disabled):**

### **Deshabilitados por problemas de sintaxis:**
- `build.yml` - ❌ Problemas con PowerShell argument parsing
- `python-app.yml` - ❌ Mismos problemas
- `multi-platform-release.yml` - ❌ Error: "unrecognized arguments"
- `manual-build.yml` - ❌ Mezcla bash/PowerShell problemática
- `simple-build.yml` - ❌ Mezcla bash/PowerShell problemática
- `universal-build.yml` - ❌ Mezcla bash/PowerShell problemática

### **Deshabilitados por obsolescencia:**
- `release.yml` - ❌ Reemplazado por workflows específicos
- `Optimized.yml` - ❌ Reemplazado
- `test.yml` - ❌ Reemplazado por MASTER_BUILD

---

## 🐛 Problemas Conocidos y Soluciones

### **Error: "unrecognized arguments"**
**Causa:** Ejecutando workflows viejos que tienen problemas con PowerShell.

**Solución:** **SOLO usar MASTER_BUILD.yml**

### **Error: "externally-managed-environment" (PEP 668)**
**Causa:** Ubuntu 22.04+ con Python 3.11+.

**Solución:** MASTER_BUILD.yml usa **virtual environment automático**.

### **Warning: "Node.js 20 actions are deprecated"**
**Causa:** GitHub Actions migrando a Node.js 24.

**Solución:** MASTER_BUILD.yml usa `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`.

### **Error: "No files in dist/"**
**Causa:** `build.py` tenía un bug con `--clean` (ya corregido).

**Solución:** Versión actualizada en commit `853327e`.

---

## 🚀 Flujo de Trabajo Recomendado

### **Para pruebas rápidas:**
```
Action: build
Platform: linux
Version: 4.8.0-test
Mode: onefile
```

### **Para release oficial:**
```
Action: build-and-release
Platform: linux,windows
Version: 4.8.0
Mode: onefile
```

### **Para pruebas de código:**
```
Action: test
```

---

## 🔗 Enlaces

- **Repositorio:** https://github.com/leriart/Soundvi
- **Actions:** https://github.com/leriart/Soundvi/actions
- **MASTER BUILD:** Único workflow activo
- **Releases:** https://github.com/leriart/Soundvi/releases
- **Issues:** https://github.com/leriart/Soundvi/issues

---

## 📞 Soporte

**Si encuentras problemas:**
1. **Asegúrate** de usar **MASTER_BUILD.yml**
2. **Verifica** que no estés ejecutando workflows `.disabled`
3. **Revisa** los logs completos en GitHub Actions
4. **Reporta** issues si persiste el problema

**¡NO uses workflows .disabled!** 🚫

**¡Happy building!** 🦀