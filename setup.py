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
        "python-dotenv",
        "opencv-python-headless>=4.8.0",
        "moviepy",
        "yt-dlp",
        "youtube-transcript-api>=1.2.4,<2.0.0",
        "webvtt-py",
        "ultralytics",
        "google-auth",
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-api-python-client",
        # Emoji berwarna: Pillow merasterisasi NotoColorEmoji, fontTools membaca
        # metrik font yang sama dengan yang dipakai libass (lihat emoji_overlay.py).
        "pillow>=10.1.0",
        "fonttools>=4.40.0",
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
