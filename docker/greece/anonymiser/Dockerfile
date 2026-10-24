FROM python:3.12-slim

# Install OpenCV dependencies (no GUI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libgomp1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and verify YuNet face detector model (pinned commit)
# Source: github.com/opencv/opencv_zoo
# Commit: main (face_detection_yunet_2023mar.onnx)
# SHA256: 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    mkdir -p /usr/share/anonymiser && \
    curl -sL -o /usr/share/anonymiser/face_detection_yunet_2023mar.onnx \
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" && \
    echo "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4  /usr/share/anonymiser/face_detection_yunet_2023mar.onnx" | sha256sum -c - && \
    rm -rf /var/lib/apt/lists/*

# Warm up ALPR models during build (downloads + caches them in the image)
RUN python3 -c "from fast_alpr import ALPR; ALPR(detector_model='yolo-v9-t-384-license-plate-end2end', ocr_model='cct-xs-v2-global-model')"

COPY app.py .

EXPOSE 8080

CMD ["python3", "app.py"]
