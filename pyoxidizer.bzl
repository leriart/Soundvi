# pyoxidizer.bzl para Soundvi - Generador de Video con Visualizador
# Configuración específica para el proyecto Soundvi de https://github.com/leriart/Soundvi

def make_exe():
    """Crea un ejecutable para Soundvi."""
    
    # Usar la distribución de Python por defecto
    dist = default_python_distribution()
    
    # Configurar política de empaquetado
    policy = dist.make_python_packaging_policy()
    
    # Configurar ubicación de recursos (en memoria para mejor rendimiento)
    policy.resources_location_fallback = "in-memory"
    
    # Excluir módulos pesados que no son necesarios
    policy.excluded_module_names.update([
        "matplotlib", "sklearn", "scikit-learn", "imageio_ffmpeg",
        "PyQt5", "PySide2", "PyQt6", "IPython", "jupyter",
        "tensorflow", "torch", "pandas", "notebook",
    ])
    
    # Configuración del intérprete Python
    python_config = dist.make_python_interpreter_config()
    
    # Ejecutar el módulo main al iniciar
    python_config.run_module = "main"
    
    # Configurar para usar el intérprete embebido
    python_config.use_module_runner = True
    
    # Crear ejecutable
    exe = dist.to_python_executable(
        name="soundvi",
        packaging_policy=policy,
        config=python_config,
    )
    
    # Instalar dependencias desde requirements.txt
    print("[PyOxidizer] Instalando dependencias desde requirements.txt...")
    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))
    
    # Incluir módulos de código fuente como paquetes Python
    print("[PyOxidizer] Incluyendo módulos de código fuente...")
    
    # Core - motor de procesamiento
    exe.add_python_resources(exe.read_package_root(
        path="core",
        packages=["core"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # GUI - interfaz gráfica
    exe.add_python_resources(exe.read_package_root(
        path="gui",
        packages=["gui"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # Modules - sistema modular plug-and-play
    exe.add_python_resources(exe.read_package_root(
        path="modules",
        packages=["modules"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # Utils - utilidades
    exe.add_python_resources(exe.read_package_root(
        path="utils",
        packages=["utils"],
        excludes=["**/__pycache__", "**/*.pyc"],
    ))
    
    # Incluir main.py como módulo principal
    exe.add_python_resources(exe.read_file("main.py", dest="main.py"))
    
    # Incluir archivos de configuración
    exe.add_python_resources(exe.read_file("config.json", dest="config.json"))
    exe.add_python_resources(exe.read_file("README.md", dest="README.md"))
    
    # Incluir directorios de recursos
    exe.add_python_resources(exe.read_directory("fonts", dest="fonts"))
    exe.add_python_resources(exe.read_directory("logos", dest="logos"))
    
    # Incluir directorios de configuración de módulos
    exe.add_python_resources(exe.read_directory("modules_config", dest="modules_config"))
    
    # Configuración específica de plataforma
    if VARS.get("TARGET_TRIPLE", "").endswith("-windows-msvc"):
        # Configuración para Windows
        exe.windows_runtime_dlls_mode = "always"
        exe.windows_subsystem = "windows"  # O "console" para aplicaciones de consola
        
        # Configurar icono si existe
        icon_path = "logos/logo.ico"
        if file_exists(icon_path):
            exe.icon = icon_path
            print(f"[PyOxidizer] Icono configurado: {icon_path}")
            
    elif VARS.get("TARGET_TRIPLE", "").endswith("-linux-"):
        # Configuración para Linux
        icon_path = "logos/logo.png"
        if file_exists(icon_path):
            exe.icon = icon_path
            print(f"[PyOxidizer] Icono configurado: {icon_path}")
            
    elif VARS.get("TARGET_TRIPLE", "").endswith("-darwin"):
        # Configuración para macOS
        icon_path = "logos/logo.icns"
        if file_exists(icon_path):
            exe.icon = icon_path
            print(f"[PyOxidizer] Icono configurado: {icon_path}")
    
    return exe

def make_embedded_resources(exe):
    """Crea recursos embebidos a partir del ejecutable."""
    return exe.to_embedded_resources()

def make_install(exe):
    """Crea un manifiesto de instalación."""
    files = FileManifest()
    files.add_python_resource(".", exe)
    
    # Agregar archivos adicionales si es necesario
    for extra_file in ["README.md", "LICENSE"]:
        if file_exists(extra_file):
            files.add_file(extra_file)
    
    return files

def make_windows_installer(exe):
    """Crea un instalador MSI para Windows."""
    return exe.to_wix_msi_builder(
        id_prefix="soundvi",
        product_name="Soundvi",
        product_version="1.0.0",
        product_manufacturer="Lerit",
        arch="x64" if "x86_64" in VARS.get("TARGET_TRIPLE", "") else "x86",
    )

def make_macos_app_bundle(exe):
    """Crea un bundle de aplicación para macOS."""
    bundle = MacOsApplicationBundleBuilder("Soundvi")
    bundle.set_info_plist_required_keys(
        display_name="Soundvi",
        identifier="com.leriart.soundvi",
        version="1.0.0",
        signature="????",  # Necesita un código de firma real
        executable="soundvi",
    )
    
    m = FileManifest()
    m.add_python_resource(".", exe)
    bundle.add_macos_manifest(m)
    
    return bundle

# Función auxiliar para verificar existencia de archivos
def file_exists(path):
    """Verifica si un archivo existe en el contexto de Starlark."""
    try:
        return read_file(path) is not None
    except:
        return False

# Registrar targets
register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"])
register_target("install", make_install, depends=["exe"], default=True)

# Registrar targets específicos de plataforma (opcional)
if VARS.get("TARGET_TRIPLE", "").endswith("-windows-msvc"):
    register_target("msi_installer", make_windows_installer, depends=["exe"])
elif VARS.get("TARGET_TRIPLE", "").endswith("-darwin"):
    register_target("macos_bundle", make_macos_app_bundle, depends=["exe"])

resolve_targets()
