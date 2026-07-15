import tensorflow as tf
from tf_mnist.tf_model import create_model
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

    x_train = x_train.astype("float32") / 255.0
    x_test = x_test.astype("float32") / 255.0

    model = create_model()

    history = model.fit(x_train, y_train, epochs=5, validation_data=(x_test, y_test))

    model.save("model.keras")

    plot_history(history)


def plot_history(history):
    plt.figure()

    # accuracy
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="train")
    plt.plot(history.history["val_accuracy"], label="val")
    plt.title("Accuracy")
    plt.legend()

    # loss
    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="train")
    plt.plot(history.history["val_loss"], label="val")
    plt.title("Loss")
    plt.legend()

    plt.tight_layout()
    # plt.show()
    plt.savefig("training_curves.png")


if __name__ == "__main__":
    main()
