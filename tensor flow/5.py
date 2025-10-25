import os
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont
from keras.models import load_model

np.set_printoptions(suppress=True)

model = load_model("keras_Model.h5", compile=False)
class_names = [line.strip() for line in open("labels.txt", "r").readlines()]

def preprocess_image(image_path):
    image = Image.open(image_path).convert("RGB")
    image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    data = np.ndarray((1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array
    return data, image

def classify_images_in_folder(input_folder, output_folder="output"):
    os.makedirs(output_folder, exist_ok=True)
    counter = {}
    total_saved = 0
    threshold = 0.80

    for filename in os.listdir(input_folder):
        if total_saved >= 9:
            break

        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(input_folder, filename)
            data, image = preprocess_image(image_path)

            prediction = model.predict(data)
            index = np.argmax(prediction)
            class_name = class_names[index]
            confidence_score = prediction[0][index]

            if class_name == "4 BG" or confidence_score < threshold:
                continue  

            counter[class_name] = counter.get(class_name, 0)
            if counter[class_name] >= 3:
                continue  

            counter[class_name] += 1
            total_saved += 1
            ext = os.path.splitext(filename)[1]
            new_filename = f"{class_name}_{counter[class_name]}{ext}"
            output_image_path = os.path.join(output_folder, new_filename)
            image.save(output_image_path)

            print(f"{filename} → {new_filename} ({confidence_score:.2f})")

classify_images_in_folder("images")








