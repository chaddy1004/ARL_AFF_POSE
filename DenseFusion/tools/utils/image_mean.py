import cv2
import glob
import numpy as np

import argparse

############################################################
#  argparse
############################################################
parser = argparse.ArgumentParser(description='Evaluate trained model for DenseFusion')

parser.add_argument('--dataset', required=False, default='/data/Akeaveny/Datasets/part-affordance_combined/ndds2/',
                    type=str,
                    metavar="/path/to/Affordance/dataset/")
parser.add_argument('--dataset_type', required=False, default='val',
                    type=str,
                    metavar='train or val')

args = parser.parse_args()

#########################
# load images
#########################

if args.dataset_type == 'val':
    images_file = 'test_data_list_15k.txt'
elif args.dataset_type == 'train':
    images_file = 'train_data_list.txt'
dataset_config = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/parts_affordance/dataset_config/'

images_paths = np.loadtxt('{}/{}'.format(dataset_config, images_file), dtype=np.str)

# images = []
# for images_path in images_paths:
#     images_path_ = args.dataset + images_path + "_rgb.png"
#     images.append(cv2.imread(images_path_))
# images = np.asarray(images)
# print("Loaded Images: ", len(images))
#
# print("---------stats---------------")
# print("Color mean (RGB):{:.2f} {:.2f} {:.2f}".format(*[images[i].mean() for i in range(images.shape[-1])]))
# print("normalized (RGB):{:.4f} {:.4f} {:.4f}".format(*[images[i].mean()/255 for i in range(images.shape[-1])]))
# print("Color std (RGB):{:.2f} {:.2f} {:.2f}".format(*[images[i].std() for i in range(images.shape[-1])]))
# print("normalized (RGB):{:.4} {:.4f} {:.4f}".format(*[images[i].std()/255 for i in range(images.shape[-1])]))

dataset_mean, dataset_std, dataset_count = 0, 0, 0
for images_path in images_paths:
    image_path_ = args.dataset + images_path + "_rgb.png"
    image = cv2.imread(image_path_)
    mean, stddev = cv2.meanStdDev(image.astype(np.uint8))
    dataset_mean += mean
    dataset_std += stddev
    dataset_count += 1
    ### print("{}/{}".format(dataset_count, len(images_paths)))

dataset_mean /= dataset_count
dataset_std /= dataset_count
print("**************** dataset stats (in reverse) ****************")
print("Means (RGB): ",dataset_mean[2], dataset_mean[1], dataset_mean[0])
print("std: ",dataset_std[2], dataset_std[1], dataset_std[0])
#print("Means normalized: \n", dataset_mean[0]/255)
#print("std normalized: \n", dataset_std[0]/255)
