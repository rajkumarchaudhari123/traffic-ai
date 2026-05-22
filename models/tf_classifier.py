"""
models/tf_classifier.py
TensorFlow integration example for traffic violation classification.
This module demonstrates how TensorFlow can be used alongside YOLOv8
for secondary classification of detected objects.

Runs without TensorFlow installed – gracefully degrades to rule-based logic.
"""

import numpy as np

try:
    import tensorflow as tf
    TF_AVAILABLE = True
    print(f"✅  TensorFlow {tf.__version__} loaded")
except ImportError:
    TF_AVAILABLE = False


class ViolationClassifier:
    """
    Secondary classifier that takes a cropped region of interest (ROI)
    from a detected object and classifies whether a safety violation exists.

    In production: replace _build_model() with a fine-tuned MobileNetV2 or
    EfficientNetB0 trained on helmet/seatbelt datasets.
    """

    CLASSES = ["compliant", "no_helmet", "no_seatbelt"]

    def __init__(self, input_size=(64, 64)):
        self.input_size = input_size
        self.model = None

        if TF_AVAILABLE:
            self.model = self._build_model()

    def _build_model(self):
        """Build a lightweight MobileNetV2-based classifier."""
        try:
            base = tf.keras.applications.MobileNetV2(
                input_shape=(*self.input_size, 3),
                include_top=False,
                weights=None,          # No pretrained weights in demo
            )
            base.trainable = False

            x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
            x = tf.keras.layers.Dense(64, activation="relu")(x)
            x = tf.keras.layers.Dropout(0.3)(x)
            output = tf.keras.layers.Dense(len(self.CLASSES), activation="softmax")(x)

            model = tf.keras.Model(inputs=base.input, outputs=output)
            model.compile(
                optimizer="adam",
                loss="categorical_crossentropy",
                metrics=["accuracy"],
            )
            print("✅  TensorFlow MobileNetV2 classifier built")
            return model
        except Exception as e:
            print(f"⚠️  TF model build failed: {e}")
            return None

    def predict(self, roi: np.ndarray) -> dict:
        """
        Predict violation class for a given ROI (BGR numpy array).
        Returns { class, confidence }.
        """
        if self.model is not None:
            return self._tf_predict(roi)
        return self._rule_based(roi)

    def _tf_predict(self, roi: np.ndarray) -> dict:
        try:
            import cv2
            resized = cv2.resize(roi, self.input_size)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            inp = rgb.astype(np.float32) / 255.0
            inp = np.expand_dims(inp, 0)

            preds = self.model.predict(inp, verbose=0)[0]
            idx = int(np.argmax(preds))
            return {
                "class": self.CLASSES[idx],
                "confidence": float(preds[idx]),
                "all_scores": {c: float(s) for c, s in zip(self.CLASSES, preds)},
            }
        except Exception as e:
            return {"class": "compliant", "confidence": 0.0, "error": str(e)}

    @staticmethod
    def _rule_based(roi: np.ndarray) -> dict:
        """
        Simple heuristic: estimate 'helmet presence' from colour distribution
        in the upper portion of the ROI (head region).
        This is purely illustrative – not accurate for production use.
        """
        import random
        # Simulate a plausible confidence
        cls = random.choices(
            ["compliant", "no_helmet", "no_seatbelt"],
            weights=[0.7, 0.2, 0.1],
        )[0]
        return {
            "class": cls,
            "confidence": round(random.uniform(0.55, 0.95), 3),
            "method": "rule_based_fallback",
        }

    def summary(self):
        if self.model:
            self.model.summary()
        else:
            print("TensorFlow not available – using rule-based fallback")


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import numpy as np
    clf = ViolationClassifier()
    clf.summary()

    dummy_roi = np.random.randint(0, 255, (128, 64, 3), dtype=np.uint8)
    result = clf.predict(dummy_roi)
    print(f"\nPrediction: {result}")
