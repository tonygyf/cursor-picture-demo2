import cv2
import numpy as np
import mediapipe as mp


class ImageProcessor:
    def __init__(self):
        self.BLUE_GRADIENT = {
            'top': (255, 200, 160),
            'bottom': (180, 120, 90)
        }
        self.GRAY_GRADIENT = {
            'top': (180, 180, 180),
            'bottom': (60, 60, 60)
        }

        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        self.selfie_segmentation = self.mp_selfie_segmentation.SelfieSegmentation(model_selection=1)

    def create_gradient_background(self, size, color_top, color_bottom):
        height, width = size
        background = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            alpha = y / height
            color = tuple(map(lambda i, j: int((1 - alpha) * i + alpha * j),
                              color_top, color_bottom))
            background[y:y + 1, :] = color
        return background

    def remove_background(self, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        results = self.selfie_segmentation.process(rgb_image)

        mask = results.segmentation_mask
        mask = (mask > 0.1).astype(np.uint8) * 255

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)

        if num_labels > 1:
            max_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
            mask = np.uint8(labels == max_label) * 255

            height = image.shape[0]
            top_half_height = height // 2
            top_half_mask = np.zeros_like(mask)
            top_half_mask[:top_half_height, :] = 1
            mask = cv2.bitwise_or(mask, cv2.bitwise_and(mask, top_half_mask))

        return mask

    def change_background(self, image, background_type='blue', manual_mask=None):
        height, width = image.shape[:2]

        if background_type == 'blue':
            background = self.create_gradient_background(
                (height, width),
                self.BLUE_GRADIENT['top'],
                self.BLUE_GRADIENT['bottom']
            )
        else:
            background = self.create_gradient_background(
                (height, width),
                self.GRAY_GRADIENT['top'],
                self.GRAY_GRADIENT['bottom']
            )

        auto_mask = self.remove_background(image)

        if manual_mask is not None:
            manual_mask = (manual_mask > 0).astype(np.uint8)
            mask = cv2.bitwise_or(auto_mask, manual_mask)
        else:
            mask = auto_mask

        black_3_channel = np.zeros_like(image)
        mask_3_channel = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        person = cv2.bitwise_and(image, mask_3_channel)
        background_instance = cv2.bitwise_and(background, cv2.bitwise_not(mask_3_channel))

        result = cv2.addWeighted(person, 1, background_instance, 1, 0)

        return result


