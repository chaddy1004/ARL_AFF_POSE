import cv2
import glob
import numpy as np

# =================== argparse ========================
# import argparse
#
# parser = argparse.ArgumentParser(description='Compute Image Mean and Stddev')
# parser.add_argument('--dataset', required=True,
#                     metavar="/path/to//dataset/",
#                     help='Directory of the dataset')
# args = parser.parse_args()

images = []
# =================== load images ========================
images_path = '/data/Akeaveny/Datasets/pringles/zed/train/000???.png'
print("Images: ", images_path)
images = [cv2.imread(file) for file in glob.glob(images_path)]
# images = [images.append(file) for file in glob.glob(images_path)]
print("Loaded Images: ", len(images))

dataset_mean, dataset_std, dataset_count = 0, 0, 0
for img in images:
    mean, stddev = cv2.meanStdDev(img.astype(np.float32) / 255)
    dataset_mean += mean
    dataset_std += stddev
    dataset_count += 1

dataset_mean /= dataset_count
dataset_std /= dataset_count
print("---------stats---------------")
print("Means: \n", dataset_mean)
print("STD: \n", dataset_std)