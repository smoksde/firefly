import tensorflow as tf
import numpy as np


def main():
    # Load model
    model = tf.keras.models.load_model("model.keras")

    # Load data
    (_, _), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

    x_test = x_test.astype("float32") / 255.0

    # pick one sample
    sample = np.expand_dims(x_test[0], axis=0)

    prediction = model.predict(sample)
    predicted_label = np.argmax(prediction)

    print("Prediction:", predicted_label)
    print("True label:", y_test[0])


if __name__ == "__main__":
    main()
