import cv2
import numpy as np
from PIL import Image

def is_chart_like(image_pil):
    img_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bar_like, pie_like = 0, 0
    for cnt in contours:
        if cv2.contourArea(cnt) < 300:
            continue
        approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect = w / h if h else 0
            if 0.2 < aspect < 5:
                bar_like += 1
        elif len(approx) > 6:
            pie_like += 1
    return bar_like >= 3 or pie_like >= 1
