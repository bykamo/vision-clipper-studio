from setuptools import setup, find_packages

setup(
    name="vision-clipper",
    version="1.0.0",
    description="AI Viral Video Clipper Studio",
    author="kam2k-dev",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "requests",
        "opencv-python",
        "mediapipe",
        "moviepy",
        "yt-dlp",
        "faster-whisper",
        "torch"
    ],
    entry_points={
        "console_scripts": [
            "vision-clipper=backend.cli:main",
            "visionclipper=backend.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
