"""Special importer for Jac files."""
import inspect
import sys
import traceback
import types
from os import path
from typing import Optional

from jaclang.jac.transpiler import transpile_jac_file


def import_jac(target: str, save_file: bool = False) -> Optional[types.ModuleType]:
    """Import a module from a path."""
    # Convert python import paths to directory paths
    target = path.join(*(target.split("."))) + ".jac"

    # Get module name and package path
    dir_path, file_name = path.split(target)
    module_name = path.splitext(file_name)[0]
    package_path = dir_path.replace(path.sep, ".")

    # Get the directory of the calling module
    frame = inspect.stack()[1]
    caller_dir = path.dirname(path.abspath(frame[0].f_code.co_filename))

    # Transpile the Jac file
    code_string = transpile_jac_file(file_path=target, base_dir=caller_dir)
    if save_file:
        with open(path.join(dir_path, module_name + ".py"), "w") as f:
            f.write(code_string)

    # Create a module object
    module = types.ModuleType(module_name)

    # Set __file__ attribute
    module.__file__ = path.normpath(path.join(caller_dir, target))
    module.__name__ = module_name

    # Execute the code in the context of the module's namespace
    try:
        exec(code_string, module.__dict__)
    except Exception as e:
        traceback.print_exc()
        print(f"Error in module {module_name}\nJac file: {target}\nError: {str(e)}")
        return None

    # Register the module in sys.modules
    if package_path:
        # Register the package and all subpackages
        parts = package_path.split(".")
        for i in range(len(parts)):
            package_name = ".".join(parts[: i + 1])
            if package_name not in sys.modules:
                sys.modules[package_name] = types.ModuleType(package_name)

        # Set the module as an attribute of the package
        setattr(sys.modules[package_path], module_name, module)

    sys.modules[module_name] = module

    # Add the module to the calling context's global variables
    return module
