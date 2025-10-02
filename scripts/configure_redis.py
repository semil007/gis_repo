#!/usr/bin/env python3
"""
Quick configuration script for Redis credentials.
Updates .env file with your Redis configuration.
"""

import os
import sys
from pathlib import Path
import secrets


def generate_secret_key():
    """Generate a secure secret key."""
    return secrets.token_hex(32)


def test_redis_connection(host, port, password, db=0):
    """Test Redis connection with provided credentials."""
    try:
        import redis
        
        client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password if password else None,
            socket_connect_timeout=5,
            decode_responses=True
        )
        
        client.ping()
        return True, "Connection successful!"
        
    except redis.ConnectionError as e:
        return False, f"Connection failed: {e}"
    except redis.AuthenticationError as e:
        return False, f"Authentication failed: {e}"
    except ImportError:
        return False, "Redis package not installed. Run: pip install redis"
    except Exception as e:
        return False, f"Error: {e}"


def update_env_file(redis_host, redis_port, redis_password, redis_db=0):
    """Update .env file with Redis configuration."""
    project_root = Path(__file__).parent.parent
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"
    
    # Read .env.example as template
    if not env_example.exists():
        print("❌ .env.example not found!")
        return False
        
    with open(env_example, 'r') as f:
        content = f.read()
    
    # Update Redis configuration
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
    
    content = content.replace(
        'REDIS_URL=redis://localhost:6379/0',
        f'REDIS_URL={redis_url}'
    )
    
    content = content.replace(
        'REDIS_PASSWORD=',
        f'REDIS_PASSWORD={redis_password}'
    )
    
    content = content.replace(
        'REDIS_DB=0',
        f'REDIS_DB={redis_db}'
    )
    
    # Generate and set secret key
    secret_key = generate_secret_key()
    content = content.replace(
        'SECRET_KEY=your-secret-key-here',
        f'SECRET_KEY={secret_key}'
    )
    
    # Write to .env file
    with open(env_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Configuration saved to {env_file}")
    return True


def main():
    """Main configuration script."""
    print("=" * 60)
    print("HMO Document Processing Pipeline - Redis Configuration")
    print("=" * 60)
    print()
    
    # Get Redis credentials
    print("Enter your Redis credentials:")
    print()
    
    redis_host = input("Redis Host [192.168.1.49]: ").strip() or "192.168.1.49"
    redis_port = input("Redis Port [6379]: ").strip() or "6379"
    redis_password = input("Redis Password [redis12345]: ").strip() or "redis12345"
    redis_db = input("Redis DB [0]: ").strip() or "0"
    
    try:
        redis_port = int(redis_port)
        redis_db = int(redis_db)
    except ValueError:
        print("❌ Port and DB must be numbers!")
        sys.exit(1)
    
    print()
    print("Testing Redis connection...")
    
    # Test connection
    success, message = test_redis_connection(redis_host, redis_port, redis_password, redis_db)
    
    if success:
        print(f"✅ {message}")
        print()
        
        # Ask to save configuration
        save = input("Save this configuration to .env file? [Y/n]: ").strip().lower()
        
        if save in ['', 'y', 'yes']:
            if update_env_file(redis_host, redis_port, redis_password, redis_db):
                print()
                print("=" * 60)
                print("Configuration Complete!")
                print("=" * 60)
                print()
                print("Next steps:")
                print("1. Review the .env file for any additional settings")
                print("2. Start the application with: streamlit run app.py")
                print("3. Or use Docker: docker-compose up -d")
                print()
                print("Your Redis configuration:")
                print(f"  Host: {redis_host}")
                print(f"  Port: {redis_port}")
                print(f"  DB: {redis_db}")
                print(f"  Password: {'*' * len(redis_password)}")
                print()
            else:
                print("❌ Failed to save configuration")
                sys.exit(1)
        else:
            print("Configuration not saved.")
    else:
        print(f"❌ {message}")
        print()
        print("Please check:")
        print("1. Redis server is running")
        print("2. Host and port are correct")
        print("3. Password is correct")
        print("4. Firewall allows connection to Redis port")
        print()
        print("Test manually with:")
        print(f"  redis-cli -h {redis_host} -p {redis_port} -a {redis_password} ping")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
