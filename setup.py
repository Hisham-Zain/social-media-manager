from setuptools import find_packages, setup

setup(
    name="social_media_manager",
    version="3.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "moviepy",
        "pillow",
        "google-api-python-client",
        "requests",
        "schedule",
        "openai-whisper",
        "watchdog",
        "pydub",
        "pandas",
        "PyQt6",
    ],
    entry_points={
        "gui_scripts": [
            "agencyos=social_media_manager.gui.main:main",
        ],
    },
    python_requires=">=3.10",
)
