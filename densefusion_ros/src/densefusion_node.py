#! /usr/bin/env python
from __future__ import division
'''
This ros node subscribes to two camera topics: '/camera/color/image_raw' and 
'/camera/aligned_depth_to_color/image_raw' in a synchronized way. It then runs 
semantic segmentation and pose estimation with trained models using DenseFusion
(https://github.com/j96w/DenseFusion). The whole code structure is adapted from: 
(http://wiki.ros.org/rospy_tutorials/Tutorials/WritingImagePublisherSubscriber)
'''

import os
import sys
import cv2 as cv
from cv_bridge import CvBridge, CvBridgeError
import time
import PIL
import rospy
import random
import copy
import argparse
import numpy as np
import numpy.ma as ma
import message_filters
from sensor_msgs.msg import Image
from sensor_msgs.msg import CompressedImage
import scipy.io as scio

from estimator import DenseFusionEstimator
from segmentation import MRCNNDetector

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import CameraInfo, Image as ImageSensor_msg
from std_msgs.msg import String
from vision_msgs.msg import Detection3D, Detection3DArray, ObjectHypothesisWithPose
from visualization_msgs.msg import Marker, MarkerArray

ROOT_DIR = os.path.abspath("/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/densefusion_ros/src/")
print("ROOT_DIR: ", ROOT_DIR)

class ObjectDetector(MRCNNDetector):

    def __init__(self):
        self.__model = rospy.get_param('~model', None)
        self.__class_labels = rospy.get_param('~class_labels', None)
        self.__prob_thresh = rospy.get_param('~detection_threshold', 0.5)

        assert os.path.isfile(self.__model), 'Trained model file not found! {}'.format(self.__model)
        assert os.path.isfile(self.__class_labels), 'Class labels file not found! {}'.format(self.__class_labels)

        # ! read the object class name and labels
        lines = [line.rstrip('\n') for line in open(self.__class_labels)]

        self.__objects_meta = {}
        self.__labels = ['_']
        for line in lines:
            object_name, object_label = line.split()
            object_label = int(object_label)
            # ! color is for visualization
            color = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
            self.__objects_meta[object_label] = [object_name, color]
            self.__labels.append(object_name)

        """ --- Init MaskRCNN --- """
        MRCNNDetector.__init__(self, model_path=self.__model, logs=None, \
                               num_classes=len(self.__objects_meta) + 1)

class PoseEstimator(DenseFusionEstimator):

    def __init__(self):

        '''--- ROS PARAM --- '''
        # Densfusion
        self.__pose_model = rospy.get_param('~pose_model', None)
        self.__refine_model = rospy.get_param('~refine_model', None)

        self.__num_points = rospy.get_param('~num_points', None)
        self.__num_points_mesh = rospy.get_param('~num_points_mesh', None)
        self.__iteration = rospy.get_param('~iteration', None)
        self.__bs = rospy.get_param('~bs', None)
        self.__num_obj = rospy.get_param('~num_obj', None)

        # 3D Models
        self.__classes = rospy.get_param('~classes', None)
        self.__class_ids = rospy.get_param('~class_ids', None)

        # ZED Camera
        self.__rgb_image = rospy.get_param('~rgb_image', None)
        self.__rgb_encoding = rospy.get_param('~rgb_encoding', None)
        self.__depth_image = rospy.get_param('~depth_image', None)
        self.__depth_encoding = rospy.get_param('~depth_encoding', None)

        self.__cam_width = rospy.get_param('~cam_width', None)
        self.__cam_height = rospy.get_param('~cam_height', None)
        self.__cam_scale = rospy.get_param('~cam_scale', None)
        self.__cam_fx = rospy.get_param('~cam_fx', None)
        self.__cam_fy = rospy.get_param('~cam_fy', None)
        self.__cam_cx = rospy.get_param('~cam_cx', None)
        self.__cam_cy = rospy.get_param('~cam_cy', None)

        # TESTING
        self.__DEBUG = rospy.get_param('~debug', None)
        self.__VISUALIZE = rospy.get_param('~visualize', None)
        self.__USE_SYNTHETIC_IMAGES = rospy.get_param('~use_synthetic_images', None)
        self.__CHECK_POSE = rospy.get_param('~check_pose', None)

        # """ --- Init MaskRCNN --- """
        # self.Mask_RCNN = ObjectDetector()
        self.__model = rospy.get_param('~model', None)
        self.__class_labels = rospy.get_param('~class_labels', None)
        self.__prob_thresh = rospy.get_param('~detection_threshold', 0.5)

        assert os.path.isfile(self.__model), 'Trained model file not found! {}'.format(self.__model)
        assert os.path.isfile(self.__class_labels), 'Class labels file not found! {}'.format(self.__class_labels)

        # ! read the object class name and labels
        lines = [line.rstrip('\n') for line in open(self.__class_labels)]

        self.__objects_meta = {}
        self.__labels = ['_']
        for line in lines:
            object_name, object_label = line.split()
            object_label = int(object_label)
            # ! color is for visualization
            color = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
            self.__objects_meta[object_label] = [object_name, color]
            self.__labels.append(object_name)

        """ --- Init Mask R-CNN --- """
        self.Mask_RCNN = ObjectDetector()

        """ --- Init DenseFusion --- """
        DenseFusionEstimator.__init__(self, self.__pose_model, self.__refine_model,
                                      self.__num_points, self.__num_points_mesh, self.__iteration, self.__bs, self.__num_obj,
                                      self.__classes, self.__class_ids,
                                      self.__cam_width, self.__cam_height, self.__cam_scale,
                                      self.__cam_fx, self.__cam_fy, self.__cam_cx, self.__cam_cy)

        """ --- Subsribe to Camera --- """
        self.bridge = CvBridge()
        self.rgb_sub = message_filters.Subscriber(self.__rgb_image, Image)
        self.depth_sub = message_filters.Subscriber(self.__depth_image, Image)
        ts = message_filters.TimeSynchronizer([self.rgb_sub, self.depth_sub], 1)
        ts.registerCallback(self.camera_callback)

        """ --- Publisher --- """
        self.pub_mask_rcnn = rospy.Publisher('~mask_rcnn_mask', Image, queue_size=1)
        self.pub_pose = rospy.Publisher('~densefusion_pose', PoseStamped,queue_size=1)
        self.pub_point_cloud = rospy.Publisher('~densefusion_point_cloud', Image, queue_size=1)

        self.num_image = 0
        if self.__USE_SYNTHETIC_IMAGES:
            self.image_path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/densefusion_ros/images/syn/'
            print('*** Using Synthetic Images! ***\n')
        else:
            self.image_path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/densefusion_ros/images/zed/'
            print('*** Subscribed to rgb and depth topic in a sychronized way! ***\n')

    def camera_callback(self, rgb_msg, depth_msg):

        """ === Load Images with ROS === """
        rgb_cv = self.bridge.imgmsg_to_cv2(rgb_msg, self.__rgb_encoding)
        rgb_cv = self.bridge.cv2_to_imgmsg(rgb_cv, self.__rgb_encoding)
        bgr = np.frombuffer(rgb_cv.data, dtype=np.uint8).reshape(rgb_cv.height, rgb_cv.width, -1)
        rgb = np.array(cv.cvtColor(bgr, cv.COLOR_BGR2RGB))

        depth_cv = self.bridge.imgmsg_to_cv2(depth_msg, self.__depth_encoding) # "16UC1" or "32FC1"
        depth_cv = np.float32(depth_cv)
        depth = depth_cv

        ######################
        # in-painting
        ######################

        depth[np.isnan(depth)] = 0
        depth[depth == -np.inf] = 0
        depth[depth == np.inf] = 0

        # convert to 8-bit image
        depth = depth * (2 ** 16 -1) / np.max(depth)
        depth = np.array(depth, dtype=np.uint16)

        # print("depth min: ", np.min(np.array(depth)))
        # print("depth max: ", np.max(np.array(depth)))
        #
        # print("rgb type: ", rgb.dtype)
        # print("depth type: ", depth.dtype)

        ######################
        # NDDS
        ######################
        if self.__USE_SYNTHETIC_IMAGES:

            data_path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/densefusion_ros/images/gt/'

            rgb_addr = data_path + '000086_rgb.png'
            depth_addr = data_path + '000086_depth.png'
            gt_addr = data_path + '000086_label.png'

            rgb = np.array(PIL.Image.open(rgb_addr))
            depth = np.array(PIL.Image.open(depth_addr))
            gt = np.array(PIL.Image.open(gt_addr))

            ### SYNTHETIC
            rgb = np.array(rgb)
            if rgb.shape[-1] == 4:
                rgb = rgb[..., :3]

            if self.__CHECK_POSE:
                meta_addr = data_path + '000086-meta.mat'
                meta = scio.loadmat(meta_addr)

        ######################
        # Mask R-CNN
        ######################

        t_start = time.time()
        instance_mask = self.Mask_RCNN.detect_and_get_masks(rgb, depth, self.__VISUALIZE)
        t_mask_rcnn = time.time() - t_start
        print('Mask R-CNN Prediction time: {:.2f}s ..'.format(t_mask_rcnn))

        ######################
        # DenseFusion
        ######################
        t_start = time.time()
        if self.__CHECK_POSE:
            pred_R, pred_T, cld_img_pred = DenseFusionEstimator.get_refined_pose(self, rgb, depth, gt, meta,
                                                  self.__DEBUG, self.__VISUALIZE, self.__CHECK_POSE)
        else:
            pred_R, pred_T, cld_img_pred = DenseFusionEstimator.get_refined_pose(self, rgb, depth, instance_mask, debug=self.__DEBUG, visualize=self.__VISUALIZE)
        t_densefusion = time.time() - t_start
        print('DenseFusion Prediction time: {:.2f}s\n'.format(t_densefusion))

        ######################
        # RVIZ
        ######################

        # Mask R-CNN
        cv2_instance_mask = self.bridge.cv2_to_imgmsg(instance_mask, '8UC1') # TODO:
        self.pub_mask_rcnn.publish(cv2_instance_mask)

        # DenseFusion
        pose_msg = PoseStamped()
        pose_msg.header = rgb_msg.header
        pose_msg.pose.position.x = pred_T[0]
        pose_msg.pose.position.y = pred_T[1]
        pose_msg.pose.position.z = pred_T[2]
        pose_msg.pose.orientation.x = pred_R[0]
        pose_msg.pose.orientation.y = pred_R[1]
        pose_msg.pose.orientation.z = pred_R[2]
        pose_msg.pose.orientation.w = pred_R[3]
        self.pub_pose.publish(pose_msg)

        cv2_cld_img_pred = self.bridge.cv2_to_imgmsg(cld_img_pred, '8UC3') # TODO:
        self.pub_point_cloud.publish(cv2_cld_img_pred)

        ######################
        # save local images
        ######################

        rgb_name = self.image_path + np.str(self.num_image) + '_rgb.png'
        cv.imwrite(rgb_name, rgb)

        depth_name = self.image_path + np.str(self.num_image) + '_depth.png'
        cv.imwrite(depth_name, depth)

        mask_name = self.image_path + np.str(self.num_image) + '_mask.png'
        cv.imwrite(mask_name, instance_mask)

        self.num_image += 1


        return

def main(args):

    rospy.init_node('pose_estimation', anonymous=True)
    PoseEstimator()
    try:
        rospy.spin()
    except KeyboardInterrupt:
        print ('Shutting down ROS pose estimation module')
    cv.destroyAllWindows()

if __name__ == '__main__':
    main(sys.argv)