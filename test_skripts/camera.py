#!/usr/bin/env python3
"""
GPU-accelerated Hand Tracking for Jetson Orin NX.
Fixed version: handles multiple TensorRT outputs, correct colors, and confidence display.
"""

import os
import sys
import warnings
import urllib.request
import subprocess
import numpy as np
import cv2

# ------------------------------------------------------------
# 1. Suppress unnecessary warnings
# ------------------------------------------------------------
warnings.filterwarnings("ignore", category=UserWarning, module="numpy.core.getlimits")
os.environ["NPY_DISABLE_CPU_FEATURES"] = "FP16C"
cv2.setLogLevel(0)

# ------------------------------------------------------------
# 2. Configuration
# ------------------------------------------------------------
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080
CAPTURE_FPS = 30

WORK_WIDTH = 1600
WORK_HEIGHT = 900

MODEL_INPUT_WIDTH = 224
MODEL_INPUT_HEIGHT = 224

MODEL_DIR = "models"
TFLITE_MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmark.tflite")
ONNX_MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmark.onnx")
TRT_ENGINE_PATH = os.path.join(MODEL_DIR, "hand_landmark.trt")

MODEL_URL = "https://storage.googleapis.com/mediapipe-assets/hand_landmark_lite.tflite"

# ------------------------------------------------------------
# 3. Model Setup: Download, Convert, and Build TensorRT Engine
# ------------------------------------------------------------
def setup_model():
    """Ensures the TensorRT engine is ready. Downloads and converts if necessary."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    if not os.path.exists(TFLITE_MODEL_PATH):
        print(f"Downloading TFLite model from {MODEL_URL}...")
        try:
            urllib.request.urlretrieve(MODEL_URL, TFLITE_MODEL_PATH)
            print("Download complete.")
        except Exception as e:
            print(f"Error downloading model: {e}")
            sys.exit(1)
    else:
        print(f"TFLite model found at {TFLITE_MODEL_PATH}")

    if not os.path.exists(ONNX_MODEL_PATH):
        print("Converting TFLite model to ONNX...")
        try:
            subprocess.run([
                "python", "-m", "tf2onnx.convert",
                "--tflite", TFLITE_MODEL_PATH,
                "--output", ONNX_MODEL_PATH,
                "--opset", "13"
            ], check=True, capture_output=True, text=True)
            print("Conversion to ONNX complete.")
        except subprocess.CalledProcessError as e:
            print(f"Error during TFLite to ONNX conversion: {e.stderr}")
            sys.exit(1)
    else:
        print(f"ONNX model found at {ONNX_MODEL_PATH}")

    if not os.path.exists(TRT_ENGINE_PATH):
        print("Building TensorRT engine from ONNX. This may take a few minutes...")
        try:
            import tensorrt as trt
        except ImportError:
            print("Error: TensorRT Python package (tensorrt) not found.")
            print("Please install it with: sudo apt install python3-libnvinfer")
            sys.exit(1)

        logger = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(logger)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, logger)

        with open(ONNX_MODEL_PATH, 'rb') as model:
            if not parser.parse(model.read()):
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                sys.exit(1)

        config = builder.create_builder_config()
        
        # Set workspace size (compatible with TensorRT 8.x and 10.x)
        try:
            # TensorRT 10.x API
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1 GB
        except AttributeError:
            # TensorRT 8.x and older API
            config.max_workspace_size = 1 << 30
        
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)

        # Build serialized engine (TensorRT 10.x compatible)
        serialized_engine = builder.build_serialized_network(network, config)
        if serialized_engine is None:
            print("Error: Failed to build TensorRT engine.")
            sys.exit(1)
        
        with open(TRT_ENGINE_PATH, "wb") as f:
            f.write(serialized_engine)
        print(f"TensorRT engine saved to {TRT_ENGINE_PATH}")
    else:
        print(f"TensorRT engine found at {TRT_ENGINE_PATH}")

# ------------------------------------------------------------
# 4. TensorRT Inference Wrapper (Handles multiple outputs)
# ------------------------------------------------------------
class HandLandmarkTRT:
    def __init__(self, engine_path):
        import tensorrt as trt
        import pycuda.driver as cuda
        import pycuda.autoinit

        self.cuda = cuda
        self.logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f, trt.Runtime(self.logger) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()

        # Collect information about all tensors
        num_tensors = self.engine.num_io_tensors
        print(f"Total IO tensors: {num_tensors}")
        self.input_name = None
        self.output_names = []
        self.output_shapes = {}
        self.output_dtypes = {}

        for i in range(num_tensors):
            name = self.engine.get_tensor_name(i)
            mode = self.engine.get_tensor_mode(name)
            shape = self.engine.get_tensor_shape(name)
            dtype = self.engine.get_tensor_dtype(name)
            print(f"  {i}: {name} | mode={mode} | shape={shape} | dtype={dtype}")

            if mode == trt.TensorIOMode.INPUT:
                self.input_name = name
                self.input_shape = shape
                self.input_dtype = dtype
            else:
                self.output_names.append(name)
                self.output_shapes[name] = shape
                self.output_dtypes[name] = dtype

        if self.input_name is None:
            raise RuntimeError("No input tensor found in engine")

        # Allocate GPU memory for input
        input_size = trt.volume(self.input_shape) * np.dtype(trt.nptype(self.input_dtype)).itemsize
        self.d_input = cuda.mem_alloc(input_size)

        # Allocate GPU memory and set addresses for all output tensors
        self.d_outputs = {}
        self.h_outputs = {}  # host buffers for results
        self.output_buffers = {}

        for name in self.output_names:
            shape = self.output_shapes[name]
            dtype = self.output_dtypes[name]
            size = trt.volume(shape) * np.dtype(trt.nptype(dtype)).itemsize
            d_buf = cuda.mem_alloc(size)
            self.d_outputs[name] = d_buf
            self.context.set_tensor_address(name, int(d_buf))
            self.h_outputs[name] = np.empty(shape, dtype=trt.nptype(dtype))

        # Set input tensor address
        self.context.set_tensor_address(self.input_name, int(self.d_input))
        self.stream = cuda.Stream()

    def infer(self, image_rgb):
        """
        Run inference on a preprocessed image.
        Args:
            image_rgb: Numpy array of shape (224, 224, 3), dtype float32, normalized [0, 1].
        Returns:
            Dictionary with all output tensors:
                'Identity'      : landmarks (1,63) -> reshape to (21,3)
                'Identity_1'    : confidence (1,1)
                'Identity_2'    : handedness (1,1)  (value > 0.5 means right hand)
                'Identity_3'    : world landmarks (1,63) (3D metric coordinates)
        """
        image_rgb = np.ascontiguousarray(image_rgb, dtype=np.float32)
        image_rgb = np.expand_dims(image_rgb, axis=0)  # Add batch dimension

        # Copy input to GPU
        self.cuda.memcpy_htod_async(self.d_input, image_rgb, self.stream)

        # Execute inference
        self.context.execute_async_v3(self.stream.handle)

        # Copy all outputs from GPU to host
        for name in self.output_names:
            self.cuda.memcpy_dtoh_async(self.h_outputs[name], self.d_outputs[name], self.stream)

        self.stream.synchronize()

        # Return a copy of results to avoid overwriting on next call
        results = {}
        for name in self.output_names:
            results[name] = self.h_outputs[name].copy()

        return results

# ------------------------------------------------------------
# 5. GPU-Accelerated Video Pipeline (GStreamer)
# ------------------------------------------------------------
def gstreamer_pipeline_gpu(
    capture_width=1920,
    capture_height=1080,
    framerate=30,
    display_width=1600,
    display_height=900
):
    """
    GStreamer pipeline that uses nvjpegdec for hardware JPEG decoding,
    nvvidconv for GPU scaling and color conversion.
    Output is RGBA frames in system memory ready for OpenCV.
    """
    return (
        f"v4l2src device=/dev/video0 ! "
        f"image/jpeg, width={capture_width}, height={capture_height}, framerate={framerate}/1 ! "
        f"nvjpegdec ! "
        f"nvvidconv ! "
        f"video/x-raw(memory:NVMM), format=RGBA, width={display_width}, height={display_height} ! "
        f"nvvidconv ! video/x-raw, format=RGBA ! "
        f"appsink"
    )

# ------------------------------------------------------------
# 6. Gesture Recognition Logic
# ------------------------------------------------------------
def get_landmark_coords(landmarks, width, height):
    coords = []
    for x, y, _ in landmarks:
        coords.append((int(x * width), int(y * height)))
    return coords

def is_finger_extended(coords, tip_idx, dip_idx, pip_idx, mcp_idx):
    tip = np.array(coords[tip_idx])
    dip = np.array(coords[dip_idx])
    mcp = np.array(coords[mcp_idx])
    return np.linalg.norm(tip - mcp) > np.linalg.norm(dip - mcp)

def recognise_gesture(landmarks, width, height):
    coords = get_landmark_coords(landmarks, width, height)
    
    fingers = {
        "thumb": is_finger_extended(coords, 4, 3, 2, 2),
        "index": is_finger_extended(coords, 8, 7, 6, 5),
        "middle": is_finger_extended(coords, 12, 11, 10, 9),
        "ring": is_finger_extended(coords, 16, 15, 14, 13),
        "pinky": is_finger_extended(coords, 20, 19, 18, 17),
    }
    
    thumb_tip = np.array(coords[4])
    index_tip = np.array(coords[8])
    distance = np.linalg.norm(thumb_tip - index_tip)
    if distance < 30:
        return "OK"
    
    extended_count = sum(1 for v in fingers.values() if v)
    if extended_count == 1 and fingers["index"]:
        return "Pointing"
    elif extended_count == 2 and fingers["index"] and fingers["middle"]:
        return "Peace"
    elif extended_count == 5:
        return "Open Hand"
    elif extended_count == 0:
        return "Fist"
    
    return None

# ------------------------------------------------------------
# 7. Visualization (correct colors)
# ------------------------------------------------------------
def draw_landmarks(frame_bgr, landmarks, width, height):
    """Draws hand landmarks and connections on the BGR frame."""
    connections = [
        (0,1),(1,2),(2,3),(3,4),     # Thumb
        (0,5),(5,6),(6,7),(7,8),     # Index
        (0,9),(9,10),(10,11),(11,12), # Middle
        (0,13),(13,14),(14,15),(15,16), # Ring
        (0,17),(17,18),(18,19),(19,20)  # Pinky
    ]
    for x, y, _ in landmarks:
        cv2.circle(frame_bgr, (int(x * width), int(y * height)), 3, (0, 255, 0), -1)
    for start, end in connections:
        x1, y1 = int(landmarks[start][0] * width), int(landmarks[start][1] * height)
        x2, y2 = int(landmarks[end][0] * width), int(landmarks[end][1] * height)
        cv2.line(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)

# ------------------------------------------------------------
# 8. Main Execution
# ------------------------------------------------------------
def main():
    # Step 1: Ensure model is ready
    print("Setting up model...")
    setup_model()

    # Step 2: Initialize TensorRT inference
    print("Initializing TensorRT engine...")
    try:
        trt_inference = HandLandmarkTRT(TRT_ENGINE_PATH)
    except Exception as e:
        print(f"Failed to initialize TensorRT engine: {e}")
        sys.exit(1)

    # Step 3: Initialize video capture with GPU pipeline
    print("Starting GPU-accelerated video pipeline...")
    pipeline = gstreamer_pipeline_gpu()
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Error: Could not open camera with GPU pipeline.")
        sys.exit(1)

    print(f"Camera opened. Working resolution: {WORK_WIDTH}x{WORK_HEIGHT}")
    print("Press 'q' or ESC to exit.\n")

    while True:
        ret, frame_rgba = cap.read()
        if not ret:
            print("Failed to read frame.")
            break

        # Prepare model input: RGBA -> RGB, resize, normalize
        frame_rgb = cv2.cvtColor(frame_rgba, cv2.COLOR_RGBA2RGB)
        model_input = cv2.resize(frame_rgb, (MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT))
        model_input = model_input.astype(np.float32) / 255.0

        # Run inference
        outputs = trt_inference.infer(model_input)

        # Extract landmarks (Identity output)
        landmarks_norm = outputs["Identity"].reshape(21, 3)

        # Optional: get confidence and handedness
        confidence = outputs["Identity_1"][0][0]
        handedness = outputs["Identity_2"][0][0]  # >0.5 typically right hand

        # Convert RGBA to BGR for correct display colors
        frame_bgr = cv2.cvtColor(frame_rgba, cv2.COLOR_RGBA2BGR)

        # Draw results and overlay gesture
        draw_landmarks(frame_bgr, landmarks_norm, WORK_WIDTH, WORK_HEIGHT)
        action = recognise_gesture(landmarks_norm, WORK_WIDTH, WORK_HEIGHT)
        if action:
            cv2.putText(frame_bgr, f"Action: {action}", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)

        # Show confidence and handedness for debugging
        hand_label = "Right" if handedness > 0.5 else "Left"
        cv2.putText(frame_bgr, f"Conf: {confidence:.2f} | Hand: {hand_label}",
                    (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow("Hand Tracking (GPU Accelerated)", frame_bgr)
        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
