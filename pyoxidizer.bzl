# pyoxidizer.bzl para Soundvi
# Configuración minimal y funcional

def make_exe():
    dist = default_python_distribution()
    
    policy = dist.make_python_packaging_policy()
    policy.extension_module_filter = "all"
    policy.allow_in_memory_shared_library_loading = True
    policy.resources_location = "in-memory"
    policy.resources_location_fallback = "filesystem-relative:prefix"
    
    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "main"
    
    exe = dist.to_python_executable(
        name="soundvi",
        packaging_policy=policy,
        config=python_config,
    )
    
    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))
    
    exe.add_python_resources(exe.read_package_root(
        path=".",
        packages=["core", "gui", "modules", "utils"],
    ))
    
    return exe

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

register_target("exe", make_exe)
register_target("install", make_install, depends=["exe"], default=True)
resolve_targets()