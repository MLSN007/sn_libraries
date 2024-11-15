"""
Script to automatically update __init__.py files across the project.
"""

import os
import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_exportable_names(file_path: Path) -> List[str]:
    """
    Extract exportable names from a Python file using AST.
    Only extracts classes and explicitly marked exports.
    
    Args:
        file_path (Path): Path to the Python file
        
    Returns:
        List[str]: List of exportable names
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            tree = ast.parse(file.read())
            
        exports = set()
        
        for node in ast.walk(tree):
            # Get class definitions
            if isinstance(node, ast.ClassDef):
                exports.add(node.name)
            # Get explicitly marked exports (variables with type annotations)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id.isupper() or node.target.id.startswith('__'):
                    exports.add(node.target.id)
                    
        return sorted(list(exports))
    except Exception as e:
        logger.error("Error parsing %s: %s", file_path, e)
        return []

def get_python_files(directory: Path) -> List[Tuple[str, List[str]]]:
    """
    Get all Python files in a directory and their exportable names.
    
    Args:
        directory (Path): Directory to scan
        
    Returns:
        List[Tuple[str, List[str]]]: List of (filename, exports) tuples
    """
    python_files = []
    
    for file in directory.glob("*.py"):
        if file.name == "__init__.py":
            continue
            
        exports = get_exportable_names(file)
        if exports:
            python_files.append((file.name, exports))
            
    return sorted(python_files)

def generate_init_content(package_name: str, files: List[Tuple[str, List[str]]]) -> str:
    """
    Generate content for __init__.py file.
    """
    package_descriptions = {
        'proxy_services': 'Proxy management and rotation services',
        'sn_ig': 'Instagram API integration and content management',
        'sn_fb': 'Facebook API integration and content management',
        'sn_tt': 'TikTok API integration and content management',
        'sn_yt': 'YouTube API integration and content management',
        'sn_utils': 'Shared utilities and helper functions',
        'gen_ai': 'AI and ML integration services',
        'google_services': 'Google API integration and service management'
    }
    
    description = package_descriptions.get(package_name, f'{package_name} functionality')
    
    content = f'"""\n{package_name}\n\n{description}\n"""\n\n'
    
    # Collect all exports and imports
    all_exports = []
    imports = []
    
    for file_name, exports in files:
        module_name = file_name[:-3]  # Remove .py extension
        for export in exports:
            all_exports.append(export)
            imports.append(f"from .{module_name} import {export}")
    
    # Add imports if any exist
    if imports:
        content += "# Classes and Types\n"
        content += "\n".join(sorted(imports))
        content += "\n\n"
    
    # Add __all__
    if all_exports:
        content += "__all__ = [\n"
        content += ",\n".join(f'    "{name}"' for name in sorted(all_exports))
        content += "\n]\n"
    
    return content

def main() -> None:
    """Main function to update all __init__.py files."""
    root_dir = Path(__file__).parent
    src_dir = root_dir / "src"
    
    if not src_dir.exists():
        raise FileNotFoundError(f"Source directory {src_dir} does not exist")
    
    # List of packages to process
    packages = [
        'proxy_services',
        'sn_ig',
        'sn_fb',
        'sn_tt',
        'sn_yt',
        'sn_utils',
        'gen_ai',
        'google_services'
    ]
    
    for package_name in packages:
        package_dir = src_dir / package_name
        if not package_dir.exists() or not package_dir.is_dir():
            logger.warning(f"Package directory {package_name} not found, skipping...")
            continue
            
        try:
            files = get_python_files(package_dir)
            content = generate_init_content(package_name, files)
            
            init_file = package_dir / "__init__.py"
            with open(init_file, "w", encoding='utf-8') as f:
                f.write(content)
                
            logger.info("Successfully updated %s", init_file)
            print(f"Created/Modified: {init_file.absolute()}")
                
        except Exception as e:
            logger.error("Error updating %s: %s", package_name, e)

if __name__ == "__main__":
    main()