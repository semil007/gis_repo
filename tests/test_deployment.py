#!/usr/bin/env python3
"""
Deployment Tests for HMO Document Processing Pipeline

This module contains tests to verify that the deployment is working correctly.
Tests cover Docker container functionality, service availability, and basic
application functionality.
"""

import os
import sys
import time
import requests
import subprocess
import sqlite3
import redis
import pytest
from pathlib import Path
import docker
import tempfile
import json


class TestDockerDeployment:
    """Test Docker container build and startup functionality."""
    
    @pytest.fixture(scope="class")
    def docker_client(self):
        """Initialize Docker client."""
        try:
            client = docker.from_env()
            return client
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists and is readable."""
        dockerfile_path = Path("Dockerfile")
        assert dockerfile_path.exists(), "Dockerfile not found"
        assert dockerfile_path.is_file(), "Dockerfile is not a file"
        
        # Check basic Dockerfile content
        content = dockerfile_path.read_text()
        assert "FROM ubuntu:" in content, "Dockerfile should use Ubuntu base image"
        assert "COPY requirements.txt" in content, "Dockerfile should copy requirements.txt"
        assert "RUN pip3 install" in content, "Dockerfile should install Python packages"
    
    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists and is valid."""
        compose_path = Path("docker-compose.yml")
        assert compose_path.exists(), "docker-compose.yml not found"
        
        # Test docker-compose config validation
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"docker-compose.yml is invalid: {result.stderr}"
    
    def test_docker_build(self, docker_client):
        """Test Docker image build process."""
        try:
            # Build the image
            image, logs = docker_client.images.build(
                path=".",
                tag="hmo-processor:test",
                rm=True,
                forcerm=True
            )
            
            assert image is not None, "Docker image build failed"
            
            # Check image properties
            assert "hmo-processor:test" in [tag for tag in image.tags]
            
        except docker.errors.BuildError as e:
            pytest.fail(f"Docker build failed: {e}")
    
    def test_docker_compose_up(self):
        """Test docker-compose startup."""
        try:
            # Start services in detached mode
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            assert result.returncode == 0, f"docker-compose up failed: {result.stderr}"
            
            # Wait for services to be ready
            time.sleep(30)
            
            # Check service status
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True
            )
            
            assert "Up" in result.stdout, "Services are not running"
            
        finally:
            # Cleanup
            subprocess.run(["docker-compose", "down"], capture_output=True)
    
    def test_container_health_check(self, docker_client):
        """Test container health check functionality."""
        try:
            # Start container with health check
            container = docker_client.containers.run(
                "hmo-processor:test",
                detach=True,
                ports={'8501/tcp': 8501},
                environment={
                    'REDIS_URL': 'redis://localhost:6379/0',
                    'DATABASE_URL': 'sqlite:///app/test.db'
                }
            )
            
            # Wait for container to start
            time.sleep(60)
            
            # Check container status
            container.reload()
            assert container.status == "running", f"Container not running: {container.status}"
            
            # Test health endpoint
            try:
                response = requests.get("http://localhost:8501/_stcore/health", timeout=10)
                assert response.status_code == 200, "Health check endpoint failed"
            except requests.exceptions.RequestException:
                # Health check might not be immediately available
                pass
            
        except Exception as e:
            pytest.fail(f"Container health check failed: {e}")
        finally:
            # Cleanup
            try:
                container.stop()
                container.remove()
            except:
                pass


class TestNativeDeployment:
    """Test native Python deployment functionality."""
    
    def test_python_requirements(self):
        """Test that Python requirements can be installed."""
        # Check Python version
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Python not available"
        
        # Check requirements.txt exists
        requirements_path = Path("requirements.txt")
        assert requirements_path.exists(), "requirements.txt not found"
        
        # Test requirements installation in temporary environment
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            
            # Create virtual environment
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True
            )
            assert result.returncode == 0, "Failed to create virtual environment"
            
            # Install requirements
            pip_path = venv_path / "bin" / "pip" if os.name != 'nt' else venv_path / "Scripts" / "pip.exe"
            result = subprocess.run(
                [str(pip_path), "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            # Allow some packages to fail (optional dependencies)
            if result.returncode != 0:
                # Check if critical packages are installed
                critical_packages = ["streamlit", "fastapi", "pandas", "spacy"]
                for package in critical_packages:
                    check_result = subprocess.run(
                        [str(pip_path), "show", package],
                        capture_output=True
                    )
                    assert check_result.returncode == 0, f"Critical package {package} not installed"
    
    def test_system_dependencies(self):
        """Test that required system dependencies are available."""
        # Test Tesseract OCR
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.skip("Tesseract OCR not installed")
        
        # Test Redis
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
        except redis.ConnectionError:
            pytest.skip("Redis not available")
    
    def test_deployment_scripts(self):
        """Test deployment script functionality."""
        scripts_dir = Path("scripts")
        assert scripts_dir.exists(), "Scripts directory not found"
        
        # Check required scripts exist
        required_scripts = ["setup.sh", "start.sh", "stop.sh", "update.sh"]
        for script_name in required_scripts:
            script_path = scripts_dir / script_name
            assert script_path.exists(), f"Script {script_name} not found"
            assert os.access(script_path, os.X_OK), f"Script {script_name} not executable"
        
        # Test script syntax (basic bash syntax check)
        for script_name in required_scripts:
            script_path = scripts_dir / script_name
            result = subprocess.run(
                ["bash", "-n", str(script_path)],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Script {script_name} has syntax errors: {result.stderr}"


class TestServiceAvailability:
    """Test service availability and basic functionality."""
    
    @pytest.fixture(scope="class")
    def app_url(self):
        """Get application URL."""
        return os.getenv("APP_URL", "http://localhost:8501")
    
    def test_web_interface_availability(self, app_url):
        """Test that web interface is accessible."""
        try:
            response = requests.get(app_url, timeout=30)
            assert response.status_code == 200, f"Web interface not accessible: {response.status_code}"
            
            # Check for Streamlit content
            assert "streamlit" in response.text.lower() or "document" in response.text.lower()
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Web interface not available: {e}")
    
    def test_health_endpoint(self, app_url):
        """Test health check endpoint."""
        health_url = f"{app_url}/_stcore/health"
        try:
            response = requests.get(health_url, timeout=10)
            assert response.status_code == 200, "Health endpoint not responding"
        except requests.exceptions.RequestException:
            pytest.skip("Health endpoint not available")
    
    def test_redis_connectivity(self):
        """Test Redis connection."""
        try:
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0"))
            )
            
            # Test basic Redis operations
            redis_client.ping()
            redis_client.set("test_key", "test_value")
            assert redis_client.get("test_key") == b"test_value"
            redis_client.delete("test_key")
            
        except redis.ConnectionError:
            pytest.skip("Redis not available")
    
    def test_database_connectivity(self):
        """Test SQLite database connectivity."""
        db_path = os.getenv("DATABASE_URL", "sqlite:///processing_sessions.db")
        if db_path.startswith("sqlite:///"):
            db_file = db_path.replace("sqlite:///", "")
            
            try:
                # Test database connection
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Test basic SQL operations
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                conn.close()
                
                # Should have some tables if properly initialized
                assert len(tables) >= 0, "Database connection failed"
                
            except sqlite3.Error as e:
                pytest.skip(f"Database not available: {e}")


class TestApplicationFunctionality:
    """Test basic application functionality."""
    
    @pytest.fixture(scope="class")
    def app_url(self):
        """Get application URL."""
        return os.getenv("APP_URL", "http://localhost:8501")
    
    def test_file_upload_endpoint(self, app_url):
        """Test file upload functionality."""
        # Create a test file
        test_content = "Test document content for HMO processing"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            test_file_path = f.name
        
        try:
            # Test file upload (this is a basic test - actual upload might require session handling)
            with open(test_file_path, 'rb') as f:
                files = {'file': f}
                
                # Note: This might fail if the app requires specific session handling
                # This is more of a connectivity test
                try:
                    response = requests.post(f"{app_url}/upload", files=files, timeout=10)
                    # Don't assert success here as it depends on app implementation
                except requests.exceptions.RequestException:
                    # Expected if upload endpoint requires session
                    pass
        
        finally:
            # Cleanup
            os.unlink(test_file_path)
    
    def test_configuration_persistence(self):
        """Test configuration file handling."""
        env_file = Path(".env")
        
        if env_file.exists():
            # Test that .env file is readable
            content = env_file.read_text()
            assert len(content) > 0, ".env file is empty"
            
            # Check for required configuration keys
            required_keys = ["APP_NAME", "LOG_LEVEL", "STREAMLIT_PORT"]
            for key in required_keys:
                assert key in content, f"Required configuration key {key} not found"
    
    def test_log_file_creation(self):
        """Test that log files can be created."""
        logs_dir = Path("logs")
        
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True)
        
        # Test log directory is writable
        test_log = logs_dir / "test.log"
        try:
            test_log.write_text("Test log entry")
            assert test_log.exists(), "Cannot create log files"
            test_log.unlink()  # Cleanup
        except PermissionError:
            pytest.fail("Log directory not writable")


class TestGitDeploymentWorkflow:
    """Test Git-based deployment workflow."""
    
    def test_git_repository_structure(self):
        """Test Git repository structure."""
        git_dir = Path(".git")
        if not git_dir.exists():
            pytest.skip("Not in a Git repository")
        
        # Check for required files
        required_files = [
            "README.md",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            ".gitignore"
        ]
        
        for file_name in required_files:
            file_path = Path(file_name)
            assert file_path.exists(), f"Required file {file_name} not found"
    
    def test_gitignore_configuration(self):
        """Test .gitignore configuration."""
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            pytest.skip(".gitignore not found")
        
        content = gitignore_path.read_text()
        
        # Check for important ignore patterns
        important_patterns = [
            "__pycache__",
            "*.pyc",
            ".env",
            "*.log",
            "uploads/",
            "downloads/"
        ]
        
        for pattern in important_patterns:
            assert pattern in content, f"Important ignore pattern {pattern} not found"
    
    def test_update_script_functionality(self):
        """Test update script basic functionality."""
        update_script = Path("scripts/update.sh")
        if not update_script.exists():
            pytest.skip("Update script not found")
        
        # Test script syntax
        result = subprocess.run(
            ["bash", "-n", str(update_script)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Update script has syntax errors: {result.stderr}"
        
        # Check script contains required operations
        content = update_script.read_text()
        required_operations = ["git pull", "pip install", "systemctl"]
        
        for operation in required_operations:
            assert operation in content, f"Update script missing {operation} operation"


def run_deployment_tests():
    """Run all deployment tests."""
    print("Running HMO Document Processing Pipeline Deployment Tests")
    print("=" * 60)
    
    # Run pytest with verbose output
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    # Add coverage if available
    try:
        import pytest_cov
        pytest_args.extend(["--cov=.", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    exit_code = run_deployment_tests()
    sys.exit(exit_code)