# controller/setup_tool.py

import os
import subprocess


REQUIREMENTS_FILE = "requirements.txt"
OUTPUT_DIR = "output"


def install_dependencies():
    print("Installing dependencies...")
    result = subprocess.call(["pip", "install", "-r", REQUIREMENTS_FILE])
    if result != 0:
        raise Exception("Dependency installation failed")


def create_output_dir():
    print(f"Ensuring '{OUTPUT_DIR}/' exists...")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    os.chmod(OUTPUT_DIR, 0o777)


def init_database():
    from db.session import engine, Base, SessionLocal
    from db import models

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Optional: Insert a default S3 credential if none exists
    if db.query(models.S3Credential).count() == 0:
        print("Inserting initial S3 credentials...")
        s3 = models.S3Credential(
            name="default-test-cred",
            access_key="your-access-key",
            secret_key="your-secret-key",
            bucket="your-bucket-name",
            region="us-east-1"
        )
        db.add(s3)
        db.commit()
        print(f"S3 credential inserted with id: {s3.id}")
    else:
        print("S3 credentials already exist, skipping...")


    if db.query(models.WorkerInstance).count() == 0:
            print("Inserting sample Worker instance records...")
            workers = [
                models.WorkerInstance(name="Worker-1", instance_id="i-abc123", public_ip="1.2.3.4", ec2_credential_id=1),
                models.WorkerInstance(name="Worker-2", instance_id="i-def456", public_ip="5.6.7.8", ec2_credential_id=1),
            ]
            db.add_all(workers)
            db.commit()

    else:
        print("Worker instance details already exist, skipping...")

    admin = db.query(models.Client).filter_by(client_id="admin").first()
    if not admin:
        admin = models.Client(
            client_id="admin",
            license_key="admin-key",  # CHANGE TO A STRONG VALUE IN PROD
            name="System Admin",
            email="admin@example.com",
            organization="DRM Controller",
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")
    db.close()


def show_success():
    print("\nSetup complete!")
    print("You can now run the Controller server with:")
    print("python start_controller.py")


if __name__ == "__main__":
    try:
        install_dependencies()
        create_output_dir()
        init_database()
        show_success()
    except Exception as e:
        print(f"Setup failed: {e}")
