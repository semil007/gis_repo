#!/usr/bin/env python3
"""
Cross-platform deployment test runner for HMO Document Processing Pipeline.
This script runs deployment tests on both Windows and Unix-like systems.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(command, shell=True, capture_output=True, timeout=300):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def print_result(test_name, success, message=""):
    """Print test result with colored output."""
    if success:
        print(f"✅ PASS - {test_name}")
    else:
        print(f"❌ FAIL - {test_name}: {message}")


def test_python_environment():
    """Test Python environment and dependencies."""
    print("\n🐍 Testing Python Environment")
    print("-" * 30)
    
    # Test Python version
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print_result("Python Version", True, f"{version.major}.{version.minor}.{version.micro}")
    else:
        print_result("Python Version", False, f"Requires Python 3.8+, found {version.major}.{version.minor}")
    
    # Test requirements.txt
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print_result("Requirements File", True)
        
        # Test pip install (dry run)
        success, stdout, stderr = run_command([sys.executable, "-m", "pip", "check"])
        print_result("Pip Dependencies", success, stderr if not success else "")
    else:
        print_result("Requirements File", False, "requirements.txt not found")


def test_docker_environment():
    """Test Docker environment."""
    print("\n🐳 Testing Docker Environment")
    print("-" * 30)
    
    # Test Docker availability
    success, stdout, stderr = run_command("docker --version")
    if success:
        version = stdout.strip()
        print_result("Docker Installation", True, version)
        
        # Test Docker daemon
        success, stdout, stderr = run_command("docker info")
        print_result("Docker Daemon", success, stderr if not success else "")
    else:
        print_result("Docker Installation", False, "Docker not found")
    
    # Test Docker Compose
    success, stdout, stderr = run_command("docker-compose --version")
    if success:
        version = stdout.strip()
        print_result("Docker Compose", True, version)
    else:
        print_result("Docker Compose", False, "docker-compose not found")


def test_project_structure():
    """Test project structure and required files."""
    print("\n📁 Testing Project Structure")
    print("-" * 30)
    
    required_files = [
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".env.example",
        "README.md",
        ".gitignore"
    ]
    
    for file_name in required_files:
        file_path = Path(file_name)
        print_result(f"File: {file_name}", file_path.exists())
    
    required_dirs = [
        "scripts",
        "web",
        "models",
        "services",
        "processors",
        "tests"
    ]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        print_result(f"Directory: {dir_name}", dir_path.exists())


def test_configuration():
    """Test configuration files."""
    print("\n⚙️ Testing Configuration")
    print("-" * 25)
    
    # Test .env.example
    env_example = Path(".env.example")
    if env_example.exists():
        content = env_example.read_text()
        required_keys = [
            "APP_NAME",
            "LOG_LEVEL", 
            "STREAMLIT_PORT",
            "REDIS_URL",
            "DATABASE_URL"
        ]
        
        for key in required_keys:
            found = key in content
            print_result(f"Config Key: {key}", found)
    else:
        print_result("Environment Template", False, ".env.example not found")
    
    # Test docker-compose.yml
    compose_file = Path("docker-compose.yml")
    if compose_file.exists():
        success, stdout, stderr = run_command("docker-compose config")
        print_result("Docker Compose Config", success, stderr if not success else "")


def test_scripts():
    """Test deployment scripts."""
    print("\n📜 Testing Scripts")
    print("-" * 18)
    
    scripts_dir = Path("scripts")
    if scripts_dir.exists():
        script_files = [
            "setup.sh",
            "start.sh", 
            "stop.sh",
            "update.sh"
        ]
        
        for script_name in script_files:
            script_path = scripts_dir / script_name
            exists = script_path.exists()
            print_result(f"Script: {script_name}", exists)
            
            if exists and platform.system() != "Windows":
                # Test script syntax on Unix-like systems
                success, stdout, stderr = run_command(f"bash -n {script_path}")
                print_result(f"Syntax: {script_name}", success, stderr if not success else "")


def test_git_repository():
    """Test Git repository configuration."""
    print("\n📦 Testing Git Repository")
    print("-" * 25)
    
    # Test if in Git repository
    success, stdout, stderr = run_command("git rev-parse --git-dir")
    print_result("Git Repository", success)
    
    if success:
        # Test for uncommitted changes
        success, stdout, stderr = run_command("git diff-index --quiet HEAD --")
        print_result("Clean Working Directory", success)
        
        # Test .gitignore
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            important_patterns = [
                "__pycache__",
                "*.pyc",
                ".env",
                "*.log",
                "uploads/",
                "downloads/"
            ]
            
            for pattern in important_patterns:
                found = pattern in content
                print_result(f"Gitignore: {pattern}", found)


def run_python_tests():
    """Run Python-based deployment tests."""
    print("\n🧪 Running Python Tests")
    print("-" * 24)
    
    test_file = Path("tests/test_deployment.py")
    if test_file.exists():
        # Try to run pytest
        success, stdout, stderr = run_command([
            sys.executable, "-m", "pytest", 
            str(test_file), "-v", "--tb=short"
        ])
        print_result("Python Deployment Tests", success, stderr if not success else "")
        
        if success:
            print("Test output:")
            print(stdout)
    else:
        print_result("Python Test File", False, "tests/test_deployment.py not found")


def main():
    """Main test runner."""
    print("🔍 HMO Document Processing Pipeline - Deployment Tests")
    print("=" * 55)
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"Testing from: {project_root}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    
    # Run all tests
    test_python_environment()
    test_docker_environment()
    test_project_structure()
    test_configuration()
    test_scripts()
    test_git_repository()
    run_python_tests()
    
    print("\n" + "=" * 55)
    print("✅ Deployment testing completed!")
    print("\nNext steps:")
    print("1. Address any failed tests")
    print("2. Run platform-specific tests:")
    if platform.system() == "Windows":
        print("   - Use Docker Desktop for containerized deployment")
        print("   - Consider WSL2 for Unix-like environment")
    else:
        print("   - Run ./scripts/validate-deployment.sh")
        print("   - Run ./scripts/test-docker.sh")
        print("   - Run ./scripts/test-git-deployment.sh")
    print("3. Deploy using preferred method (Docker recommended)")


if __name__ == "__main__":
    main()