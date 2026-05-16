import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt


def main():
    model = tf.keras.models.load_model("model.keras")

    (_, _), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    x_test = x_test.astype("float32") / 255.0

    plt.figure(figsize=(10, 5))

    for i in range(10):
        img = x_test[i]
        true_label = y_test[i]

        pred = model.predict(np.expand_dims(img, axis=0))
        pred_label = np.argmax(pred)

        plt.subplot(2, 5, i + 1)
        plt.imshow(img, cmap="gray")
        plt.title(f"T:{true_label} P:{pred_label}")
        plt.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
