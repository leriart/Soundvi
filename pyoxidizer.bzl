# pyoxidizer.bzl for Soundvi - Corrected configuration based on real examples
# Version compatible with PyOxidizer 0.24+

def make_exe():
    # Python distribution
    dist = default_python_distribution()
    
    # Packaging policy
    policy = dist.make_python_packaging_policy()
    
    # Extension module configuration
    policy.extension_module_filter = "all"
    policy.allow_in_memory_shared_library_loading = True
    policy.resources_location = "in-memory"
    policy.resources_location_fallback = "filesystem-relative:prefix"
    
    # Interpreter configuration
    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "main"
    
    # Create executable
    exe = dist.to_python_executable(
        name="soundvi",
        packaging_policy=policy,
        config=python_config,
    )
    
    # Install dependencies from requirements.txt
    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))
    
    # Include project source code
    # Use current directory and specify packages
    exe.add_python_resources(exe.read_package_root(
        path=".",
        packages=["core", "gui", "modules", "utils"],
    ))
    
    # Also include files in root directory (like main.py)
    # PyOxidizer should automatically detect Python modules
    
    # Platform-specific configuration
    # Use VARS instead of BUILD_CONFIG
    target_triple = VARS.get("target_triple", "")
    if "windows" in target_triple:
        exe.windows_subsystem = "windows"
        # For Windows, we can copy runtime DLLs
        exe.windows_runtime_dlls_mode = "when-present"
    
    return exe

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

register_target("exe", make_exe)
register_target("install", make_install, depends=["exe"], default=True)
resolve_targets()
