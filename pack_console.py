import os
import zipfile
import sys

def zip_dir(zip_file, source_dir, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = set()
    for root, dirs, files in os.walk(source_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for file in files:
            if file.endswith('.pyc') or file.startswith('.'):
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, start=os.path.dirname(os.path.abspath(source_dir)))
            zip_file.write(file_path, arcname)

def main():
    output_filename = "AbEngineCore_Console_System.zip"
    directories_to_include = [
        "api",
        "core",
        "config",
        "data",
        "docs",
        "pipeline",
        "scripts",
        "insynbio-web-source"
    ]
    files_to_include = [
        "requirements.txt",
        "environment.yml",
        "config.yaml",
        "README.md",
        "SYSTEM_OVERVIEW.md"
    ]
    exclude_dirs = {'__pycache__', 'node_modules', 'dist', 'build', '.job_storage', 'archive', '.cursor', '.agent', '.git'}

    print(f"Creating {output_filename}...")
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for d in directories_to_include:
            if os.path.exists(d):
                print(f"Adding directory: {d}")
                zip_dir(zipf, d, exclude_dirs)
            else:
                print(f"Warning: Directory {d} not found.")
        
        for f in files_to_include:
            if os.path.exists(f):
                print(f"Adding file: {f}")
                zipf.write(f, f)
            else:
                print(f"Warning: File {f} not found.")
                
    print(f"Successfully created {output_filename} ({os.path.getsize(output_filename) / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    main()
